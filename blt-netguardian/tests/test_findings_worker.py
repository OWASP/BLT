"""Worker-level tests for GET /api/findings."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_findings_api import FindingsFakeDB
from test_worker_api import BLTWorker, FakeRequest, parse_json


@pytest.fixture
def env(sample_findings):
    return SimpleNamespace(
        DB=FindingsFakeDB(sample_findings),
        NG_ORG_API_TOKENS=json.dumps({"token-org-a": "org-a"}),
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
            "created_at": 100,
            "updated_at": 300,
        }
    ]


@pytest.mark.asyncio
async def test_handle_findings_success(env):
    worker = BLTWorker(env)
    request = FakeRequest(
        "https://api.example.com/api/findings?limit=10",
        method="GET",
        headers={"Authorization": "Bearer token-org-a"},
    )

    response = await worker.handle_findings(request)
    payload = parse_json(response)

    assert response.status == 200
    assert payload["org_id"] == "org-a"
    assert payload["total"] == 1
    assert payload["findings"][0]["id"] == "f1"


@pytest.mark.asyncio
async def test_handle_findings_unauthorized(env):
    worker = BLTWorker(env)
    request = FakeRequest(
        "https://api.example.com/api/findings",
        method="GET",
    )

    response = await worker.handle_findings(request)
    payload = parse_json(response)

    assert response.status == 401
    assert payload["error"] == "unauthorized"


@pytest.mark.asyncio
async def test_handle_findings_no_db():
    worker = BLTWorker(
        SimpleNamespace(
            DB=None,
            NG_ORG_API_TOKENS=json.dumps({"token-org-a": "org-a"}),
        )
    )
    request = FakeRequest(
        "https://api.example.com/api/findings",
        method="GET",
        headers={"Authorization": "Bearer token-org-a"},
    )

    response = await worker.handle_findings(request)
    payload = parse_json(response)

    assert response.status == 503
    assert payload["error"] == "service_unavailable"
