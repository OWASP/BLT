"""ztr-finding-1 envelope validation and signing helpers (Week 1 Day 5)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, MutableMapping

from canonicalize import (
    body_digest_hex,
    canonicalize_envelope_for_signing,
    hmac_sha256_hex,
    payload_digest_hex,
    verify_hmac_sha256_hex,
)
from errors import IngestError, IngestErrorCode

VERSION = "ztr-finding-1"
ALG = "hmac-sha256"
DEFAULT_SKEW_SECONDS = 300
ISSUED_AT_Z = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?Z$"
)

REQUIRED_CORE = (
    "version",
    "org_id",
    "sender_id",
    "kid",
    "alg",
    "issued_at",
    "nonce",
)


def validate_envelope_shape(
    envelope: Mapping[str, Any],
    *,
    for_signing: bool = False,
) -> None:
    """Structural checks only (no crypto)."""
    if envelope.get("version") != VERSION:
        raise IngestError(
            IngestErrorCode.INVALID_ENVELOPE,
            f"version must be {VERSION!r}",
        )

    missing = [field for field in REQUIRED_CORE if field not in envelope]
    if missing:
        raise IngestError(
            IngestErrorCode.INVALID_ENVELOPE,
            f"missing required fields: {', '.join(missing)}",
        )

    plaintext = envelope.get("payload_plaintext")
    ciphertext = envelope.get("payload_ciphertext")
    plaintext_mode = envelope.get("plaintext_mode")

    if plaintext is not None and ciphertext is not None:
        raise IngestError(
            IngestErrorCode.INVALID_PAYLOAD_MODE,
            "payload_plaintext and payload_ciphertext are mutually exclusive",
        )
    if plaintext is None and ciphertext is None:
        raise IngestError(
            IngestErrorCode.INVALID_PAYLOAD_MODE,
            "exactly one payload field is required",
        )
    if plaintext is not None:
        if plaintext_mode is not True:
            raise IngestError(
                IngestErrorCode.INVALID_PAYLOAD_MODE,
                "plaintext_mode must be true when payload_plaintext is set",
            )
        if not isinstance(plaintext, Mapping):
            raise IngestError(
                IngestErrorCode.INVALID_ENVELOPE,
                "payload_plaintext must be a JSON object",
            )
    elif plaintext_mode is True:
        raise IngestError(
            IngestErrorCode.INVALID_PAYLOAD_MODE,
            "plaintext_mode true requires payload_plaintext",
        )
    if ciphertext is not None and not isinstance(ciphertext, str):
        raise IngestError(
            IngestErrorCode.INVALID_ENVELOPE,
            "payload_ciphertext must be a base64 string",
        )

    if not for_signing:
        for field in ("payload_digest", "signature"):
            if field not in envelope:
                raise IngestError(
                    IngestErrorCode.INVALID_ENVELOPE,
                    f"missing required fields: {field}",
                )

    if envelope.get("alg") != ALG:
        raise IngestError(
            IngestErrorCode.INVALID_ENVELOPE,
            f"alg must be {ALG!r}",
        )

    issued_at = envelope.get("issued_at")
    if not isinstance(issued_at, str) or not ISSUED_AT_Z.match(issued_at):
        raise IngestError(
            IngestErrorCode.INVALID_ENVELOPE,
            "issued_at must be RFC 3339 UTC with Z suffix",
        )


def parse_issued_at_utc(value: str) -> datetime:
    if not ISSUED_AT_Z.match(value):
        raise IngestError(
            IngestErrorCode.INVALID_ENVELOPE,
            "issued_at must be RFC 3339 UTC with Z suffix",
        )
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def check_clock_skew(
    issued_at: datetime,
    *,
    now: datetime | None = None,
    window_seconds: int = DEFAULT_SKEW_SECONDS,
) -> None:
    now = now or datetime.now(timezone.utc)
    delta = abs((issued_at - now).total_seconds())
    if delta > window_seconds:
        raise IngestError(
            IngestErrorCode.CLOCK_SKEW,
            f"issued_at outside ±{window_seconds} second window",
        )


def verify_payload_digest_field(envelope: Mapping[str, Any]) -> None:
    declared = envelope.get("payload_digest")
    if not isinstance(declared, str):
        raise IngestError(
            IngestErrorCode.INVALID_ENVELOPE,
            "payload_digest must be a hex string",
        )
    plaintext = envelope.get("payload_plaintext")
    ciphertext = envelope.get("payload_ciphertext")
    try:
        expected = payload_digest_hex(
            plaintext=plaintext if isinstance(plaintext, Mapping) else None,
            ciphertext_b64=ciphertext if isinstance(ciphertext, str) else None,
        )
    except ValueError as exc:
        raise IngestError(
            IngestErrorCode.INVALID_PAYLOAD_MODE,
            str(exc),
        ) from exc
    if declared.lower() != expected:
        raise IngestError(
            IngestErrorCode.DIGEST_MISMATCH,
            "payload_digest does not match payload bytes",
        )


def parse_body_digest_header(header_value: str) -> str:
    if not header_value.startswith("sha256="):
        raise IngestError(
            IngestErrorCode.DIGEST_MISMATCH,
            "X-BLT-Body-Digest must start with sha256=",
        )
    hex_part = header_value[7:]
    if len(hex_part) != 64 or not all(c in "0123456789abcdef" for c in hex_part.lower()):
        raise IngestError(
            IngestErrorCode.DIGEST_MISMATCH,
            "X-BLT-Body-Digest must be sha256=<64 hex chars>",
        )
    return hex_part.lower()


def verify_body_digest(raw_body: bytes, header_value: str) -> None:
    declared = parse_body_digest_header(header_value)
    expected = body_digest_hex(raw_body)
    if declared != expected:
        raise IngestError(
            IngestErrorCode.DIGEST_MISMATCH,
            "request body digest does not match X-BLT-Body-Digest",
        )


def sign_envelope(envelope: MutableMapping[str, Any], secret: bytes) -> str:
    """Compute HMAC signature; does not mutate envelope except returning signature hex."""
    unsigned = {k: v for k, v in envelope.items() if k != "signature"}
    message = canonicalize_envelope_for_signing(unsigned)
    return hmac_sha256_hex(secret, message)


def verify_envelope_signature(envelope: Mapping[str, Any], secret: bytes) -> None:
    signature = envelope.get("signature")
    if not isinstance(signature, str):
        raise IngestError(
            IngestErrorCode.INVALID_ENVELOPE,
            "signature must be a hex string",
        )
    unsigned = {k: v for k, v in envelope.items() if k != "signature"}
    message = canonicalize_envelope_for_signing(unsigned)
    if not verify_hmac_sha256_hex(secret, message, signature):
        raise IngestError(
            IngestErrorCode.BAD_SIGNATURE,
            "HMAC verification failed",
        )


def prepare_signed_envelope(
    envelope: MutableMapping[str, Any],
    secret: bytes,
    *,
    now: datetime | None = None,
) -> MutableMapping[str, Any]:
    """Validate shape, set payload_digest if absent, sign, and return envelope."""
    validate_envelope_shape(envelope, for_signing=True)
    if "payload_digest" not in envelope or not envelope["payload_digest"]:
        plaintext = envelope.get("payload_plaintext")
        ciphertext = envelope.get("payload_ciphertext")
        envelope["payload_digest"] = payload_digest_hex(
            plaintext=plaintext if isinstance(plaintext, Mapping) else None,
            ciphertext_b64=ciphertext if isinstance(ciphertext, str) else None,
        )
    verify_payload_digest_field(envelope)
    issued = parse_issued_at_utc(envelope["issued_at"])
    check_clock_skew(issued, now=now)
    envelope["signature"] = sign_envelope(envelope, secret)
    return envelope
