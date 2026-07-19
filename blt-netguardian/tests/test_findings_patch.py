"""Tests for PATCH /api/findings/{id} and extended list filters."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from findings_service import list_findings_for_request, update_finding_for_request
from findings_store import FindingsStore
from test_findings_api import FindingsFakeDB


@pytest.fixture
def env():
    return SimpleNamespace(
        NG_ORG_API_TOKENS=json.dumps({"token-org-a": "org-a"})
    )


@pytest.fixture
def sample_findings():
    return [
        {
            "id": "f1",
            "org_id": "org-a",
            "envelope_id": "e1",
            "rule_id": "xss-reflected",
            "severity": "high",
            "title": "Reflected XSS",
            "target": "https://a.example",
            "status": "open",
            "fingerprint": "fp1",
            "cve_id": None,
            "cve_score": None,
            "blt_issue_id": None,
            "created_at": 100,
            "updated_at": 300,
        },
        {
            "id": "f2",
            "org_id": "org-a",
            "envelope_id": "e2",
            "rule_id": "sqli",
            "severity": "critical",
            "title": "SQL injection",
            "target": "https://a.example/login",
            "status": "open",
            "fingerprint": "fp2",
            "cve_id": "CVE-2024-0001",
            "cve_score": 9.1,
            "blt_issue_id": None,
            "created_at": 200,
            "updated_at": 200,
        },
    ]


@pytest.mark.asyncio
async def test_list_findings_date_range(env, sample_findings):
    db = FindingsFakeDB(sample_findings)
    headers = {"Authorization": "Bearer token-org-a"}

    result = await list_findings_for_request(
        env=env,
        db=db,
        headers=headers,
        query_params={"created_from": "150", "created_to": "250"},
        store=FindingsStore(db),
    )

    assert result.status == 200
    assert result.body["total"] == 1
    assert result.body["findings"][0]["id"] == "f2"


@pytest.mark.asyncio
async def test_list_findings_triage_queue(env, sample_findings):
    db = FindingsFakeDB(sample_findings)
    headers = {"Authorization": "Bearer token-org-a"}

    result = await list_findings_for_request(
        env=env,
        db=db,
        headers=headers,
        query_params={"triage_queue": "1"},
        store=FindingsStore(db),
    )

    assert result.status == 200
    assert result.body["total"] == 2
    assert {item["id"] for item in result.body["findings"]} == {"f1", "f2"}


@pytest.mark.asyncio
async def test_update_finding_status(env, sample_findings):
    db = FindingsFakeDB(sample_findings)
    store = FindingsStore(db)
    headers = {"Authorization": "Bearer token-org-a"}

    result = await update_finding_for_request(
        env=env,
        db=db,
        headers=headers,
        finding_id="f1",
        body={"status": "triaging"},
        store=store,
        new_id=lambda label: f"{label}-1",
    )

    assert result.status == 200
    assert result.body["finding"]["status"] == "triaging"


@pytest.mark.asyncio
async def test_update_finding_requires_token_even_when_reads_open(sample_findings):
    env = SimpleNamespace(
        NG_ORG_API_TOKENS=json.dumps({"token-org-a": "org-a"}),
        AUTHENTICATE_READ_ENDPOINTS="false",
    )
    db = FindingsFakeDB(sample_findings)
    from auth import AuthError

    with pytest.raises(AuthError):
        await update_finding_for_request(
            env=env,
            db=db,
            headers={},
            finding_id="f1",
            body={"status": "triaging"},
            store=FindingsStore(db),
        )


@pytest.mark.asyncio
async def test_list_findings_allows_open_reads_without_token(sample_findings):
    env = SimpleNamespace(
        NG_ORG_API_TOKENS=json.dumps({"token-org-a": "org-a"}),
        AUTHENTICATE_READ_ENDPOINTS="false",
        NG_DEFAULT_ORG="org-a",
    )
    db = FindingsFakeDB(sample_findings)
    result = await list_findings_for_request(
        env=env,
        db=db,
        headers={},
        query_params={},
        store=FindingsStore(db),
    )
    assert result.status == 200
    assert result.body["org_id"] == "org-a"
