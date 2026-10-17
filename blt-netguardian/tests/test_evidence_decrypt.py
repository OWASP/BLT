"""E2E: encrypted ingest -> server-side decrypt on detail view + audit."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("cryptography")

from canonicalize import body_digest_hex  # noqa: E402
from envelope import prepare_signed_envelope  # noqa: E402
from findings_service import get_finding_for_request  # noqa: E402
from findings_store import FindingsStore  # noqa: E402
from ingest_service import process_ingest  # noqa: E402
from ingest_store import IngestStore  # noqa: E402
from netguardian_db import open_netguardian_db  # noqa: E402
from payload_crypto import encrypt_payload  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
SECRET_HEX = "736563726574"
ORG = "org-demo"
KEY = b"netguardian-demo-aesgcm-key-0032"
KEY_B64 = base64.b64encode(KEY).decode()

PAYLOAD = {
    "rule_id": "semgrep.python.sql-injection",
    "severity": "critical",
    "title": "SQL injection in reporting export",
    "target": "https://api.acme.example/reports",
    "fingerprint": "fp-enc-1",
    "cve_id": "CVE-2024-0001",
    "password": "should-be-redacted",
    "evidence": {"snippet": "SELECT * FROM x", "token": "redact-me"},
}


def _env(*, with_key: bool = True):
    kwargs = dict(
        NG_SENDER_SECRETS=json.dumps({f"{ORG}:scanner-1:k1": SECRET_HEX}),
        NG_ORG_API_TOKENS=json.dumps({"triage-token": ORG}),
        NG_INGEST_RPM="600",
    )
    if with_key:
        kwargs["NG_PAYLOAD_KEYS"] = json.dumps({ORG: KEY_B64})
    return SimpleNamespace(**kwargs)


def _encrypted_envelope():
    now = datetime.now(timezone.utc)
    body = {
        "version": "ztr-finding-1",
        "org_id": ORG,
        "sender_id": "scanner-1",
        "kid": "k1",
        "alg": "hmac-sha256",
        "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nonce": f"enc-{now.timestamp()}",
        "payload_ciphertext": encrypt_payload(KEY, PAYLOAD, aad=ORG.encode()),
    }
    return prepare_signed_envelope(body, bytes.fromhex(SECRET_HEX))


@pytest.fixture
def db():
    conn = open_netguardian_db(REPO_ROOT)
    yield conn
    conn.conn.close()


async def _ingest(env, db):
    signed = _encrypted_envelope()
    raw = json.dumps(signed, separators=(",", ":"), ensure_ascii=False).encode()
    result = await process_ingest(
        raw_body=raw,
        body_digest_header=f"sha256={body_digest_hex(raw)}",
        envelope=signed,
        env=env,
        db=db,
        store=IngestStore(db),
        new_id=lambda label: f"{label}-enc",
    )
    return result


@pytest.mark.asyncio
async def test_encrypted_ingest_then_decrypt_on_view(db):
    env = _env(with_key=True)
    ingest = await _ingest(env, db)
    assert ingest.status == 201
    finding_id = ingest.body["finding_id"]

    # Metadata columns are populated from the decrypted payload at ingest.
    listed = await list_metadata(env, db)
    assert listed["rule_id"] == PAYLOAD["rule_id"]

    detail = await get_finding_for_request(
        env=env, db=db, headers={"Authorization": "Bearer triage-token"},
        finding_id=finding_id, store=FindingsStore(db),
        new_id=lambda label: f"{label}-1",
    )
    assert detail.status == 200
    assert detail.body["evidence"]["encrypted_at_rest"] is True
    assert detail.body["evidence"]["decrypted"] is True
    # Secret is redacted even after server-side decrypt.
    assert detail.body["payload_snippet"]["password"] == "[REDACTED]"
    assert detail.body["payload_snippet"]["rule_id"] == PAYLOAD["rule_id"]

    logs = await FindingsStore(db).list_access_logs(ORG, finding_id)
    assert logs[0]["action"] == "decrypt_view"


@pytest.mark.asyncio
async def test_ciphertext_stored_at_rest_not_plaintext(db):
    env = _env(with_key=True)
    ingest = await _ingest(env, db)
    finding_id = ingest.body["finding_id"]
    row = await FindingsStore(db).get_finding_detail(ORG, finding_id)
    stored = row["payload_json"]
    assert "should-be-redacted" not in stored
    assert json.loads(stored)["enc"] == "aes-256-gcm"


@pytest.mark.asyncio
async def test_detail_without_key_does_not_decrypt(db):
    ingest = await _ingest(_env(with_key=True), db)
    finding_id = ingest.body["finding_id"]

    detail = await get_finding_for_request(
        env=_env(with_key=False), db=db,
        headers={"Authorization": "Bearer triage-token"},
        finding_id=finding_id, store=FindingsStore(db),
        new_id=lambda label: f"{label}-2",
    )
    assert detail.status == 200
    assert detail.body["evidence"]["encrypted_at_rest"] is True
    assert detail.body["evidence"]["decrypted"] is False
    assert detail.body["payload_snippet"] == {}


@pytest.mark.asyncio
async def test_ingest_ciphertext_without_key_rejected(db):
    signed = _encrypted_envelope()
    raw = json.dumps(signed, separators=(",", ":"), ensure_ascii=False).encode()
    from errors import IngestError

    with pytest.raises(IngestError):
        await process_ingest(
            raw_body=raw,
            body_digest_header=f"sha256={body_digest_hex(raw)}",
            envelope=signed,
            env=_env(with_key=False),
            db=db,
            store=IngestStore(db),
            new_id=lambda label: f"{label}-nokey",
        )


async def list_metadata(env, db):
    result = await FindingsStore(db).list_findings(
        _query(ORG)
    )
    items, _ = result
    return items[0]


def _query(org_id):
    from findings_store import FindingsQuery
    return FindingsQuery(org_id=org_id, limit=10, offset=0)
