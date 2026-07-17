"""W7 acceptance gates: replay golden fixtures through process_ingest."""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from canonicalize import body_digest_hex, payload_digest_hex
from envelope import prepare_signed_envelope, sign_envelope, validate_envelope_shape
from errors import IngestError
from ingest_service import process_ingest
from ingest_store import IngestStore
from netguardian_db import open_netguardian_db
from payload_crypto import encrypt_payload

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = REPO_ROOT / "tests" / "fixtures" / "acceptance_cases.json"


@pytest.fixture(scope="module")
def pack():
    return json.loads(CASES_PATH.read_text())


@pytest.fixture(scope="module")
def secret(pack):
    return bytes.fromhex(pack["meta"]["secret_hex"])


@pytest.fixture(scope="module")
def payload_key(pack):
    return base64.b64decode(pack["meta"]["payload_key_b64"])


@pytest.fixture
def env(pack):
    meta = pack["meta"]
    return SimpleNamespace(
        NG_SENDER_SECRETS=json.dumps({
            f"{meta['org_id']}:{meta['sender_id']}:{meta['kid']}": meta["secret_hex"],
        }),
        NG_ORG_API_TOKENS=json.dumps({"triage-token": meta["org_id"]}),
        NG_PAYLOAD_KEYS=json.dumps({meta["org_id"]: meta["payload_key_b64"]}),
        NG_INGEST_RPM="120",
        NG_INGEST_MAX_BODY_BYTES=str(1_048_576),
    )


@pytest.fixture
def db():
    database = open_netguardian_db(REPO_ROOT)
    yield database
    database.conn.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _issued_at(now: datetime, offset_seconds: int = 0) -> str:
    return (now + timedelta(seconds=offset_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _base_envelope(pack: dict, case: dict, *, now: datetime, nonce: str) -> dict:
    meta = pack["meta"]
    payload = dict(case["payload"])
    envelope: dict = {
        "version": "ztr-finding-1",
        "org_id": meta["org_id"],
        "sender_id": meta["sender_id"],
        "kid": meta["kid"],
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

    # Missing required fields must still be signed so digest/HMAC checks run
    # after shape/payload field validation inside process_ingest.
    if "severity" not in case["payload"] and case.get("mode") != "ciphertext":
        # prepare_signed_envelope validates shape only; severity checked later.
        return prepare_signed_envelope(envelope, secret, now=now)

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
    return envelope, raw, digest


async def run_case(pack, case, *, env, db, secret, payload_key, now) -> dict:
    """Execute one fixture; return a result dict for gate scoring."""
    store = IngestStore(db)

    if case.get("seed_same_fingerprint"):
        seed = dict(case)
        seed = {**seed, "id": f"{case['id']}-seed"}
        seed_env = build_case_envelope(
            pack, seed, secret=secret, payload_key=payload_key, now=now,
        )
        seed_raw = json.dumps(seed_env, separators=(",", ":"), ensure_ascii=False).encode()
        seed_result = await process_ingest(
            raw_body=seed_raw,
            body_digest_header=f"sha256={body_digest_hex(seed_raw)}",
            envelope=seed_env,
            env=env,
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
            env=env,
            db=db,
            store=store,
            now=now,
            new_id=lambda label: f"{label}-{uuid.uuid4().hex[:8]}",
        )
        assert first.status == 201, f"first ingest for replay failed: {first.body}"

    raw = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode()
    envelope, raw, digest = apply_tamper(envelope, raw, case.get("tamper"))

    try:
        result = await process_ingest(
            raw_body=raw,
            body_digest_header=digest,
            envelope=envelope,
            env=env,
            db=db,
            store=store,
            now=now,
            new_id=lambda label: f"{label}-{uuid.uuid4().hex[:8]}",
        )
        return {
            "id": case["id"],
            "kind": case["kind"],
            "ok": _matches_expect(case, status=result.status, body=result.body, error=None),
            "status": result.status,
            "body": result.body,
            "error": None,
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


def _matches_expect(case: dict, *, status: int, body: dict, error: str | None) -> bool:
    expect = case["expect"]
    if case["kind"] == "accept":
        return status == expect["status"] and body.get("status") == expect["body_status"]
    return error == expect["error"] and status == expect["http_status"]


@pytest.mark.asyncio
async def test_each_acceptance_case(pack, env, db, secret, payload_key):
    now = _now()
    failures = []
    for case in pack["cases"]:
        outcome = await run_case(
            pack, case, env=env, db=db, secret=secret, payload_key=payload_key, now=now,
        )
        if not outcome["ok"]:
            failures.append(outcome)
    assert not failures, f"fixture failures: {json.dumps(failures, indent=2)}"


@pytest.mark.asyncio
async def test_accept_success_gate_threshold(pack, env, secret, payload_key):
    """≥95% of accept fixtures must hit expected status (W7 gate)."""
    threshold = float(pack["meta"]["accept_success_threshold"])
    accept_cases = [c for c in pack["cases"] if c["kind"] == "accept"]
    assert accept_cases, "no accept cases in fixture pack"

    # Fresh DB so accept cases do not collide across the matrix.
    database = open_netguardian_db(REPO_ROOT)
    try:
        now = _now()
        results = []
        for case in accept_cases:
            outcome = await run_case(
                pack,
                case,
                env=env,
                db=database,
                secret=secret,
                payload_key=payload_key,
                now=now,
            )
            results.append(outcome)
    finally:
        database.conn.close()

    passed = sum(1 for r in results if r["ok"])
    rate = passed / len(results)
    assert rate >= threshold, (
        f"accept success {rate:.0%} < {threshold:.0%}: "
        f"{json.dumps(results, indent=2)}"
    )


@pytest.mark.asyncio
async def test_reject_cases_all_correct(pack, env, secret, payload_key):
    reject_cases = [c for c in pack["cases"] if c["kind"] == "reject"]
    database = open_netguardian_db(REPO_ROOT)
    try:
        now = _now()
        for case in reject_cases:
            outcome = await run_case(
                pack,
                case,
                env=env,
                db=database,
                secret=secret,
                payload_key=payload_key,
                now=now,
            )
            assert outcome["ok"], f"reject case failed: {outcome}"
    finally:
        database.conn.close()
