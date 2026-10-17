"""E2E: ingest a signed finding, then list it via org-scoped GET /api/findings."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from canonicalize import body_digest_hex
from envelope import prepare_signed_envelope
from findings_service import list_findings_for_request
from findings_store import FindingsStore
from ingest_service import process_ingest
from ingest_store import IngestStore
from netguardian_db import open_netguardian_db
from test_worker_api import BLTWorker, FakeRequest, parse_json

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "canonical_vectors.json"


@pytest.fixture(scope="module")
def fixture_data():
    return json.loads(FIXTURES.read_text())


@pytest.fixture
def secret(fixture_data):
    return bytes.fromhex(fixture_data["secret_hex"])


@pytest.fixture
def env(fixture_data):
    return SimpleNamespace(
        NG_SENDER_SECRETS=json.dumps({"org-demo:scanner-1:k1": fixture_data["secret_hex"]}),
        NG_ORG_API_TOKENS=json.dumps({"triage-token": "org-demo"}),
        NG_INGEST_RPM="60",
    )


@pytest.fixture
def signed_envelope(fixture_data, secret):
    body = dict(fixture_data["envelope_unsigned"])
    body.pop("payload_digest", None)
    body["issued_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return prepare_signed_envelope(body, secret)


@pytest.fixture
def sqlite_db():
    db = open_netguardian_db(REPO_ROOT)
    yield db
    db.conn.close()


@pytest.mark.asyncio
async def test_ingest_then_list_findings_sqlite(env, signed_envelope, sqlite_db):
    """Service-layer E2E against real SQLite schema."""
    raw = json.dumps(signed_envelope, separators=(",", ":"), ensure_ascii=False).encode()
    now = datetime.now(timezone.utc)

    ingest_result = await process_ingest(
        raw_body=raw,
        body_digest_header=f"sha256={body_digest_hex(raw)}",
        envelope=signed_envelope,
        env=env,
        db=sqlite_db,
        store=IngestStore(sqlite_db),
        now=now,
        new_id=lambda label: f"{label}-e2e",
    )

    assert ingest_result.status == 201
    finding_id = ingest_result.body["finding_id"]

    list_result = await list_findings_for_request(
        env=env,
        db=sqlite_db,
        headers={"Authorization": "Bearer triage-token"},
        query_params={"limit": "10"},
        store=FindingsStore(sqlite_db),
    )

    assert list_result.status == 200
    assert list_result.body["org_id"] == "org-demo"
    assert list_result.body["total"] == 1
    assert list_result.body["findings"][0]["id"] == finding_id
    assert list_result.body["findings"][0]["title"] == "Test finding"
    assert list_result.body["findings"][0]["rule_id"] == "semgrep.test"


@pytest.mark.asyncio
async def test_ingest_then_list_findings_worker(env, signed_envelope, sqlite_db):
    """Worker handlers: POST ingest then GET findings on shared D1."""
    env.DB = sqlite_db
    worker = BLTWorker(env)
    body_bytes = json.dumps(signed_envelope, separators=(",", ":"), ensure_ascii=False).encode()

    ingest_response = await worker.handle_ingest(
        FakeRequest(
            "https://api.example.com/api/ingest",
            method="POST",
            body_bytes=body_bytes,
            headers={"X-BLT-Body-Digest": f"sha256={body_digest_hex(body_bytes)}"},
        )
    )
    ingest_payload = parse_json(ingest_response)
    assert ingest_response.status == 201
    assert ingest_payload["status"] == "created"

    list_response = await worker.handle_findings(
        FakeRequest(
            "https://api.example.com/api/findings",
            method="GET",
            headers={"Authorization": "Bearer triage-token"},
        )
    )
    list_payload = parse_json(list_response)

    assert list_response.status == 200
    assert list_payload["total"] == 1
    assert list_payload["findings"][0]["id"] == ingest_payload["finding_id"]
    assert list_payload["findings"][0]["rule_id"] == "semgrep.test"


@pytest.mark.asyncio
async def test_org_b_cannot_see_org_a_findings(env, signed_envelope, sqlite_db):
    """Cross-org isolation after ingest."""
    raw = json.dumps(signed_envelope, separators=(",", ":"), ensure_ascii=False).encode()
    await process_ingest(
        raw_body=raw,
        body_digest_header=f"sha256={body_digest_hex(raw)}",
        envelope=signed_envelope,
        env=env,
        db=sqlite_db,
        store=IngestStore(sqlite_db),
        new_id=lambda label: f"{label}-iso",
    )

    env_other = SimpleNamespace(
        NG_ORG_API_TOKENS=json.dumps({"other-token": "org-other"}),
    )
    result = await list_findings_for_request(
        env=env_other,
        db=sqlite_db,
        headers={"Authorization": "Bearer other-token"},
        query_params={},
        store=FindingsStore(sqlite_db),
    )

    assert result.status == 200
    assert result.body["org_id"] == "org-other"
    assert result.body["total"] == 0
    assert result.body["findings"] == []
