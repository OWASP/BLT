"""Tests for BLT-API client mapping and convert integration."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from blt_api_client import (
    BltApiError,
    build_bug_create_body,
    bugs_endpoint,
    create_bug_from_finding,
    normalize_target_url,
    parse_bug_id,
)
from findings_service import convert_to_issue_for_request
from findings_store import FindingsStore
from ingest_service import process_ingest
from ingest_store import IngestStore
from netguardian_db import open_netguardian_db
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_bugs_endpoint_appends_path():
    assert bugs_endpoint("http://localhost:8788/v2") == "http://localhost:8788/v2/bugs"


def test_build_bug_create_body_maps_finding():
    body = build_bug_create_body({
        "id": "fnd-1",
        "org_id": "org-demo",
        "rule_id": "semgrep.python.sql-injection",
        "title": "SQL injection",
        "severity": "critical",
        "target": "https://api.acme.example/reports",
        "cve_id": "CVE-2024-0001",
        "fingerprint": "fp-1",
    })
    assert body["url"] == "https://api.acme.example/reports"
    assert "SQL injection" in body["description"]
    assert body["cve_id"] == "CVE-2024-0001"
    assert body["score"] == 90
    assert "NetGuardian finding fnd-1" in body["markdown_description"]


def test_normalize_target_url_adds_https():
    assert normalize_target_url("acme.example").startswith("https://")


def test_parse_bug_id_from_blt_response():
    assert parse_bug_id({"success": True, "data": {"id": 42}}) == "42"


@pytest.mark.asyncio
async def test_create_bug_from_finding_uses_fetch_impl():
    captured = {}

    async def fake_fetch(url, headers, payload):
        captured["url"] = url
        captured["headers"] = dict(headers)
        captured["payload"] = payload
        return 201, {"success": True, "data": {"id": 99}}

    env = SimpleNamespace(
        BLT_API_BASE_URL="http://blt.test/v2",
        BLT_API_KEY="test-key",
    )
    bug_id = await create_bug_from_finding(
        env,
        {"id": "fnd-x", "title": "Test", "target": "https://x.example", "severity": "high"},
        fetch_impl=fake_fetch,
    )
    assert bug_id == "99"
    assert captured["url"] == "http://blt.test/v2/bugs"
    assert captured["headers"]["X-BLT-API-Key"] == "test-key"
    assert captured["payload"]["url"] == "https://x.example"


@pytest.mark.asyncio
async def test_create_bug_raises_on_api_error():
    async def fail_fetch(url, headers, payload):
        return 400, {"success": False, "message": "bad request"}

    env = SimpleNamespace(BLT_API_BASE_URL="http://blt.test/v2", BLT_API_KEY="k")
    with pytest.raises(BltApiError):
        await create_bug_from_finding(
            env, {"title": "t", "target": "https://x.example"},
            fetch_impl=fail_fetch,
        )


@pytest.mark.asyncio
async def test_convert_to_issue_calls_blt_api_when_configured(fixture_data, secret, db):
    import json
    from datetime import datetime, timezone
    from canonicalize import body_digest_hex
    from envelope import prepare_signed_envelope

    body = dict(fixture_data["envelope_unsigned"])
    body.pop("payload_digest", None)
    body["issued_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body["payload_plaintext"]["fingerprint"] = "fp-blt-api-wire"
    envelope = prepare_signed_envelope(body, secret)
    raw = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode()

    env = SimpleNamespace(
        NG_SENDER_SECRETS=json.dumps({"org-demo:scanner-1:k1": fixture_data["secret_hex"]}),
        NG_ORG_API_TOKENS=json.dumps({"triage-token": "org-demo"}),
        NG_INGEST_RPM="60",
        BLT_API_BASE_URL="http://blt.test/v2",
        BLT_API_KEY="key",
    )

    ingest = await process_ingest(
        raw_body=raw,
        body_digest_header=f"sha256={body_digest_hex(raw)}",
        envelope=envelope,
        env=env,
        db=db,
        store=IngestStore(db),
        new_id=lambda label: f"{label}-blt",
    )
    finding_id = ingest.body["finding_id"]

    async def ok_fetch(url, headers, payload):
        return 201, {"success": True, "data": {"id": 501}}

    result = await convert_to_issue_for_request(
        env=env,
        db=db,
        headers={"Authorization": "Bearer triage-token"},
        finding_id=finding_id,
        store=FindingsStore(db),
        new_id=lambda label: f"{label}-conv",
        fetch_impl=ok_fetch,
    )
    assert result.status == 201
    assert result.body["blt_issue_id"] == "501"
    assert "stub" not in result.body

    row = await FindingsStore(db).get_finding_detail("org-demo", finding_id)
    assert row["blt_issue_id"] == "501"


@pytest.fixture
def db():
    database = open_netguardian_db(REPO_ROOT)
    yield database
    database.conn.close()


@pytest.fixture
def fixture_data():
    import json
    return json.loads((REPO_ROOT / "tests" / "fixtures" / "canonical_vectors.json").read_text())


@pytest.fixture
def secret(fixture_data):
    return bytes.fromhex(fixture_data["secret_hex"])
