"""Detection → signed envelope → ingest → findings list, end to end.

The point of these tests is the seam between the detection packs and the trust
boundary: detector output must survive canonicalization/HMAC unchanged, and a
re-scan of an unfixed target must merge rather than pile up duplicate rows.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from canonicalize import body_digest_hex
from detect.http_headers import scan_headers
from detect.normalize import DetectionFinding
from detect.semgrep import scan_semgrep_results
from envelope import prepare_signed_envelope
from findings_service import list_findings_for_request
from findings_store import FindingsStore
from ingest_service import process_ingest
from ingest_store import IngestStore
from netguardian_db import open_netguardian_db
from payload_crypto import encrypt_payload

REPO_ROOT = Path(__file__).resolve().parents[1]
SECRET_HEX = "736563726574"
PAYLOAD_KEY_B64 = "bmV0Z3VhcmRpYW4tZGVtby1hZXNnY20ta2V5LTAwMzI="
ORG = "org-demo"


@pytest.fixture
def env():
    return SimpleNamespace(
        NG_SENDER_SECRETS=json.dumps({f"{ORG}:scanner-1:k1": SECRET_HEX}),
        NG_ORG_API_TOKENS=json.dumps({"triage-token": ORG}),
        NG_PAYLOAD_KEYS=json.dumps({ORG: PAYLOAD_KEY_B64}),
        NG_INGEST_RPM="600",
        NG_INGEST_RPH="6000",
    )


@pytest.fixture
def db():
    database = open_netguardian_db(REPO_ROOT)
    yield database
    database.conn.close()


def _envelope_for(finding: DetectionFinding, *, encrypt: bool = False, now=None) -> tuple[dict, bytes]:
    now = now or datetime.now(timezone.utc)
    payload = finding.to_payload()
    envelope: dict = {
        "version": "ztr-finding-1",
        "org_id": ORG,
        "sender_id": "scanner-1",
        "kid": "k1",
        "alg": "hmac-sha256",
        "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nonce": f"detect-{uuid.uuid4().hex[:16]}",
    }
    if encrypt:
        import base64

        envelope["payload_ciphertext"] = encrypt_payload(
            base64.b64decode(PAYLOAD_KEY_B64), payload, aad=ORG.encode()
        )
    else:
        envelope["plaintext_mode"] = True
        envelope["payload_plaintext"] = payload

    signed = prepare_signed_envelope(envelope, bytes.fromhex(SECRET_HEX), now=now)
    raw = json.dumps(signed, separators=(",", ":"), ensure_ascii=False).encode()
    return signed, raw


async def _ingest(finding, env, db, *, encrypt=False):
    signed, raw = _envelope_for(finding, encrypt=encrypt)
    return await process_ingest(
        raw_body=raw,
        body_digest_header=f"sha256={body_digest_hex(raw)}",
        envelope=signed,
        env=env,
        db=db,
        store=IngestStore(db),
        new_id=lambda label: f"{label}-{uuid.uuid4().hex[:8]}",
    )


@pytest.mark.asyncio
async def test_header_findings_reach_the_triage_list(env, db):
    findings = scan_headers("https://app.example", {})
    assert findings, "bare response should produce header findings"

    for finding in findings:
        result = await _ingest(finding, env, db)
        assert result.status == 201, result.body
        assert result.body["status"] == "created"

    listed = await list_findings_for_request(
        env=env,
        db=db,
        headers={"Authorization": "Bearer triage-token"},
        query_params={},
        store=FindingsStore(db),
    )
    assert listed.status == 200
    assert listed.body["total"] == len(findings)
    assert {f["rule_id"] for f in listed.body["findings"]} == {f.rule_id for f in findings}


@pytest.mark.asyncio
async def test_rescan_merges_instead_of_duplicating(env, db):
    """Deterministic fingerprints mean an unfixed target does not pile up rows."""
    finding = scan_headers("https://app.example", {})[0]

    first = await _ingest(finding, env, db)
    assert first.status == 201

    # Same detector, same target, fresh nonce — i.e. a later scheduled scan.
    second = await _ingest(finding, env, db)
    assert second.status == 200
    assert second.body["status"] == "merged"
    assert second.body["finding_id"] == first.body["finding_id"]

    listed = await list_findings_for_request(
        env=env, db=db, headers={"Authorization": "Bearer triage-token"},
        query_params={}, store=FindingsStore(db),
    )
    assert listed.body["total"] == 1


@pytest.mark.asyncio
async def test_semgrep_finding_ingests_encrypted_and_hides_snippet(env, db):
    results = [{
        "check_id": "python.lang.security.audit.dangerous-subprocess-use",
        "path": "src/runner.py",
        "start": {"line": 42},
        "extra": {
            "message": "Detected subprocess call with user-controlled input",
            "severity": "ERROR",
            "lines": "subprocess.call(SUPER_SECRET_TOKEN, shell=True)",
        },
    }]
    finding = scan_semgrep_results(results, target="github.com/acme/app")[0]

    result = await _ingest(finding, env, db, encrypt=True)
    assert result.status == 201

    # Encrypted evidence must not be readable in the stored envelope row.
    row = await db.prepare(
        "SELECT payload_json FROM envelopes WHERE finding_id = ?"
    ).bind(result.body["finding_id"]).first()
    stored = row["payload_json"] if isinstance(row, dict) else row.payload_json
    assert "SUPER_SECRET_TOKEN" not in stored
    assert "aes-256-gcm" in stored


@pytest.mark.asyncio
async def test_severity_is_preserved_through_the_pipeline(env, db):
    finding = DetectionFinding(
        rule_id="http.missing-hsts",
        severity="high",
        title="Missing Strict-Transport-Security header",
        target="https://app.example",
        locator="Strict-Transport-Security",
    )
    result = await _ingest(finding, env, db)
    assert result.status == 201

    listed = await list_findings_for_request(
        env=env, db=db, headers={"Authorization": "Bearer triage-token"},
        query_params={}, store=FindingsStore(db),
    )
    assert listed.body["findings"][0]["severity"] == "high"
