"""Shared W7 acceptance fixture helpers (usable from tests and CLI)."""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Optional

from canonicalize import body_digest_hex, payload_digest_hex
from envelope import prepare_signed_envelope, sign_envelope, validate_envelope_shape
from errors import IngestError
from ingest_service import process_ingest
from ingest_store import IngestStore
from payload_crypto import encrypt_payload

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = REPO_ROOT / "tests" / "fixtures" / "acceptance_cases.json"


def build_env(pack: Mapping[str, Any], overrides: Optional[Mapping[str, Any]] = None) -> SimpleNamespace:
    """Build process_ingest env from fixture meta (+ optional per-case overrides)."""
    meta = pack["meta"]
    env = SimpleNamespace(
        NG_SENDER_SECRETS=json.dumps({
            f"{meta['org_id']}:{meta['sender_id']}:{meta['kid']}": meta["secret_hex"],
        }),
        NG_ORG_API_TOKENS=json.dumps({"triage-token": meta["org_id"]}),
        NG_PAYLOAD_KEYS=json.dumps({meta["org_id"]: meta["payload_key_b64"]}),
        NG_INGEST_RPM="120",
        NG_INGEST_RPH="1000",
        NG_INGEST_MAX_BODY_BYTES=str(1_048_576),
    )
    if overrides:
        for key, value in overrides.items():
            setattr(env, key, str(value))
    return env


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _issued_at(now: datetime, offset_seconds: int = 0) -> str:
    return (now + timedelta(seconds=offset_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _base_envelope(pack: dict, case: dict, *, now: datetime, nonce: str) -> dict:
    meta = pack["meta"]
    payload = dict(case["payload"])
    kid = "kid-not-configured" if case.get("unknown_kid") else meta["kid"]
    envelope: dict = {
        "version": "ztr-finding-1",
        "org_id": meta["org_id"],
        "sender_id": meta["sender_id"],
        "kid": kid,
        "alg": "hmac-sha256",
        "issued_at": _issued_at(now, case.get("issued_at_offset_seconds", 0)),
        "nonce": nonce,
        "plaintext_mode": True,
        "payload_plaintext": payload,
    }
    return envelope


def _sign_without_skew(envelope: dict, secret: bytes) -> dict:
    """Sign for reject fixtures where issued_at is intentionally skewed."""
    validate_envelope_shape(envelope, for_signing=True)
    if not envelope.get("payload_digest"):
        plaintext = envelope.get("payload_plaintext")
        ciphertext = envelope.get("payload_ciphertext")
        envelope["payload_digest"] = payload_digest_hex(
            plaintext=plaintext if isinstance(plaintext, dict) else None,
            ciphertext_b64=ciphertext if isinstance(ciphertext, str) else None,
        )
    envelope["signature"] = sign_envelope(envelope, secret)
    return envelope


def build_case_envelope(
    pack: dict,
    case: dict,
    *,
    secret: bytes,
    payload_key: bytes,
    now: datetime,
    nonce: str | None = None,
) -> dict:
    nonce = nonce or f"{case['id']}-{uuid.uuid4().hex[:12]}"
    envelope = _base_envelope(pack, case, now=now, nonce=nonce)

    if case.get("mode") == "ciphertext":
        ciphertext = encrypt_payload(
            payload_key,
            case["payload"],
            aad=pack["meta"]["org_id"].encode(),
        )
        envelope.pop("payload_plaintext", None)
        envelope["plaintext_mode"] = False
        envelope["payload_ciphertext"] = ciphertext

    if case.get("issued_at_offset_seconds"):
        return _sign_without_skew(envelope, secret)

    return prepare_signed_envelope(envelope, secret, now=now)


def apply_tamper(envelope: dict, raw: bytes, tamper: str | None) -> tuple[dict, bytes, str]:
    digest = f"sha256={body_digest_hex(raw)}"
    if tamper == "signature":
        envelope = dict(envelope)
        sig = envelope.get("signature", "")
        envelope["signature"] = ("0" if not sig.startswith("0") else "1") + sig[1:]
        raw = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode()
        digest = f"sha256={body_digest_hex(raw)}"
    elif tamper == "body_digest":
        digest = "sha256=" + ("0" * 64)
    elif tamper == "both_payloads":
        envelope = dict(envelope)
        if envelope.get("payload_plaintext") is None:
            envelope["payload_plaintext"] = {"rule_id": "x", "severity": "low", "title": "x"}
            envelope["plaintext_mode"] = True
        if envelope.get("payload_ciphertext") is None:
            envelope["payload_ciphertext"] = "AAAA"
        raw = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode()
        digest = f"sha256={body_digest_hex(raw)}"
    return envelope, raw, digest


async def _stored_payload_json(db: Any, finding_id: str) -> str:
    row = await db.prepare(
        "SELECT payload_json FROM envelopes WHERE finding_id = ?"
    ).bind(finding_id).first()
    if row is None:
        return ""
    if isinstance(row, dict):
        return str(row.get("payload_json") or "")
    return str(getattr(row, "payload_json", "") or "")


def _matches_expect(
    case: dict,
    *,
    status: int,
    body: dict,
    error: str | None,
    stored_payload: str | None = None,
) -> bool:
    expect = case["expect"]
    if case["kind"] == "accept":
        if status != expect["status"] or body.get("status") != expect["body_status"]:
            return False
        forbidden = expect.get("stored_must_not_contain") or []
        if forbidden:
            blob = stored_payload or ""
            for token in forbidden:
                if token in blob:
                    return False
        return True
    err = error if error is not None else body.get("error")
    return err == expect["error"] and status == expect["http_status"]


async def run_case(pack, case, *, env, db, secret, payload_key, now) -> dict:
    """Execute one fixture; return a result dict for gate scoring."""
    case_env = build_env(pack, case.get("env")) if case.get("env") else env
    store = IngestStore(db)

    if case.get("pre_accept_count"):
        org_id = pack["meta"]["org_id"]
        for _ in range(int(case["pre_accept_count"])):
            await store.record_rate_accept(org_id, now)

    if case.get("seed_same_fingerprint"):
        seed = {**case, "id": f"{case['id']}-seed"}
        seed.pop("env", None)
        seed.pop("pre_accept_count", None)
        seed_env = build_case_envelope(
            pack, seed, secret=secret, payload_key=payload_key, now=now,
        )
        seed_raw = json.dumps(seed_env, separators=(",", ":"), ensure_ascii=False).encode()
        seed_result = await process_ingest(
            raw_body=seed_raw,
            body_digest_header=f"sha256={body_digest_hex(seed_raw)}",
            envelope=seed_env,
            env=case_env,
            db=db,
            store=store,
            now=now,
            new_id=lambda label: f"{label}-{uuid.uuid4().hex[:8]}",
        )
        assert seed_result.status == 201, f"seed failed for {case['id']}: {seed_result.body}"

    nonce = f"{case['id']}-{uuid.uuid4().hex[:12]}"
    envelope = build_case_envelope(
        pack, case, secret=secret, payload_key=payload_key, now=now, nonce=nonce,
    )

    if case.get("replay_nonce"):
        first_raw = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode()
        first = await process_ingest(
            raw_body=first_raw,
            body_digest_header=f"sha256={body_digest_hex(first_raw)}",
            envelope=envelope,
            env=case_env,
            db=db,
            store=store,
            now=now,
            new_id=lambda label: f"{label}-{uuid.uuid4().hex[:8]}",
        )
        assert first.status == 201, f"first ingest for replay failed: {first.body}"

    raw = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode()
    envelope, raw, digest = apply_tamper(envelope, raw, case.get("tamper"))
    if case.get("pad_body_to"):
        target = int(case["pad_body_to"])
        if len(raw) < target:
            raw = raw + (b"x" * (target - len(raw)))

    try:
        result = await process_ingest(
            raw_body=raw,
            body_digest_header=digest,
            envelope=envelope,
            env=case_env,
            db=db,
            store=store,
            now=now,
            new_id=lambda label: f"{label}-{uuid.uuid4().hex[:8]}",
        )
        stored = None
        if case["kind"] == "accept" and case["expect"].get("stored_must_not_contain"):
            finding_id = result.body.get("finding_id")
            if finding_id:
                stored = await _stored_payload_json(db, finding_id)
        return {
            "id": case["id"],
            "kind": case["kind"],
            "ok": _matches_expect(
                case,
                status=result.status,
                body=result.body,
                error=None,
                stored_payload=stored,
            ),
            "status": result.status,
            "body": result.body,
            "error": result.body.get("error"),
        }
    except IngestError as exc:
        return {
            "id": case["id"],
            "kind": case["kind"],
            "ok": _matches_expect(
                case,
                status=exc.http_status,
                body=exc.to_response_body(),
                error=exc.code.value,
            ),
            "status": exc.http_status,
            "body": exc.to_response_body(),
            "error": exc.code.value,
        }
