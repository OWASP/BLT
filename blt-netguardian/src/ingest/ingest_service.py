"""POST /api/ng/ingest business logic."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from .canonicalize import body_digest_hex
from .envelope import (
    check_clock_skew,
    parse_issued_at_utc,
    validate_envelope_shape,
    verify_body_digest,
    verify_envelope_signature,
    verify_payload_digest_field,
)
from .errors import IngestError, IngestErrorCode
from .secrets import lookup_sender_secret
from .store import IngestStore

DEFAULT_MAX_BODY = 1_048_576
DEFAULT_RPM = 60


@dataclass
class IngestResult:
    status: int
    body: dict
    headers: dict


def _env_int(env: Any, key: str, default: int) -> int:
    raw = getattr(env, key, None)
    if raw is None:
        return default
    try:
        return int(str(raw))
    except ValueError:
        return default


async def process_ingest(
    *,
    raw_body: bytes,
    body_digest_header: Optional[str],
    envelope: Mapping[str, Any],
    env: Any,
    db: Any,
    store: Optional[IngestStore] = None,
    now: Optional[datetime] = None,
    new_id: Any = None,
) -> IngestResult:
    """Verify envelope and persist to D1; idempotent on duplicate nonce."""
    now = now or datetime.now(timezone.utc)
    store = store or IngestStore(db)
    max_body = _env_int(env, "NG_INGEST_MAX_BODY_BYTES", DEFAULT_MAX_BODY)
    rpm = _env_int(env, "NG_INGEST_RPM", DEFAULT_RPM)

    if len(raw_body) > max_body:
        raise IngestError(
            IngestErrorCode.PAYLOAD_TOO_LARGE,
            f"request body exceeds {max_body} bytes",
        )

    if not body_digest_header:
        raise IngestError(
            IngestErrorCode.DIGEST_MISMATCH,
            "missing X-BLT-Body-Digest header",
        )
    verify_body_digest(raw_body, body_digest_header)

    validate_envelope_shape(envelope)
    verify_payload_digest_field(envelope)

    issued = parse_issued_at_utc(envelope["issued_at"])
    check_clock_skew(issued, now=now)

    org_id = envelope["org_id"]
    sender_id = envelope["sender_id"]
    kid = envelope["kid"]
    nonce = envelope["nonce"]

    if db is None:
        raise RuntimeError("D1 not configured")

    if not await store.sender_key_active(org_id, sender_id, kid):
        raise IngestError(
            IngestErrorCode.UNKNOWN_KID,
            "kid not registered or inactive for sender",
        )

    secret = lookup_sender_secret(env, org_id, sender_id, kid)
    if secret is None:
        raise IngestError(
            IngestErrorCode.UNKNOWN_KID,
            "sender secret not configured",
        )

    verify_envelope_signature(envelope, secret)

    duplicate = await store.find_duplicate(org_id, sender_id, nonce)
    if duplicate and duplicate.get("finding_id"):
        return IngestResult(
            status=200,
            body={
                "status": "duplicate",
                "finding_id": duplicate["finding_id"],
                "replay": True,
            },
            headers={},
        )

    if not await store.check_rate_limit(org_id, limit_per_minute=rpm, now=now):
        return IngestResult(
            status=429,
            body={
                "error": IngestErrorCode.RATE_LIMITED.value,
                "message": "too many ingest requests for this org",
            },
            headers={"Retry-After": "60"},
        )

    payload = envelope.get("payload_plaintext")
    if not isinstance(payload, Mapping):
        raise IngestError(
            IngestErrorCode.INVALID_PAYLOAD_MODE,
            "only plaintext payload mode is currently supported",
        )

    for field in ("rule_id", "severity", "title"):
        if field not in payload:
            raise IngestError(
                IngestErrorCode.INVALID_ENVELOPE,
                f"payload_plaintext missing required field: {field}",
            )

    id_fn = new_id or (lambda prefix: __import__("hashlib").sha256(
        f"{prefix}-{org_id}-{nonce}-{now.timestamp()}".encode()
    ).hexdigest()[:16])
    envelope_id = id_fn("env")
    finding_id = id_fn("fnd")
    received_unix = int(now.timestamp())
    issued_unix = int(issued.timestamp())

    await store.insert_accepted(
        envelope_id=envelope_id,
        finding_id=finding_id,
        org_id=org_id,
        sender_id=sender_id,
        kid=kid,
        nonce=nonce,
        body_digest=body_digest_hex(raw_body),
        payload_digest=str(envelope["payload_digest"]).lower(),
        issued_at_unix=issued_unix,
        received_at_unix=received_unix,
        payload_json=json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
        payload=payload,
    )
    await store.record_rate_accept(org_id, now)

    return IngestResult(
        status=201,
        body={
            "status": "created",
            "finding_id": finding_id,
            "replay": False,
        },
        headers={},
    )


def ingest_error_response(exc: IngestError) -> IngestResult:
    return IngestResult(
        status=exc.http_status,
        body=exc.to_response_body(),
        headers={"Retry-After": "60"} if exc.code == IngestErrorCode.RATE_LIMITED else {},
    )
