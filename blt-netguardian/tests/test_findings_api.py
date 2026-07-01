"""Tests for GET /api/findings."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from auth import AuthError
from findings_service import list_findings_for_request
from findings_store import FindingsStore
from test_storage import FakeDB, FakePreparedStatement


class FindingsPreparedStatement(FakePreparedStatement):
    def _matching_rows(self):
        rows = list(self.db.findings)
        params = list(self.params)
        org_id = params[0]
        rows = [row for row in rows if row["org_id"] == org_id]
        idx = 1
        sql = self.sql.lower()
        if "status = ?" in sql and "update findings" not in sql:
            rows = [row for row in rows if row["status"] == params[idx]]
            idx += 1
        if "severity = ?" in sql:
            rows = [row for row in rows if row["severity"] == params[idx]]
            idx += 1
        if "cve_id = ?" in sql:
            rows = [row for row in rows if row.get("cve_id") == params[idx]]
            idx += 1
        if "created_at >= ?" in sql:
            rows = [row for row in rows if row["created_at"] >= params[idx]]
            idx += 1
        if "created_at <= ?" in sql:
            rows = [row for row in rows if row["created_at"] <= params[idx]]
            idx += 1
        if "severity in ('critical', 'high')" in sql:
            rows = [
                row for row in rows
                if row["severity"] in ("critical", "high")
                and row.get("status") == "open"
                and not row.get("blt_issue_id")
            ]

        sort_field = "updated_at"
        for candidate in ("updated_at", "created_at", "severity", "rule_id"):
            if f"order by {candidate}" in sql:
                sort_field = candidate
                break
        reverse = " desc" in sql
        rows.sort(key=lambda row: row[sort_field], reverse=reverse)
        return rows

    async def run(self):
        self.db.run_calls.append((self.sql, self.params))
        sql = self.sql.lower()
        if "update findings" in sql and "set status" in sql:
            status, updated_at, finding_id, org_id = self.params
            for row in self.db.findings:
                if row["id"] == finding_id and row["org_id"] == org_id:
                    row["status"] = status
                    row["updated_at"] = updated_at
                    break
        return {}

    async def first(self):
        self.db.first_calls.append((self.sql, self.params))
        sql = self.sql.lower()
        if "count(" in sql:
            return {"total": len(self._matching_rows())}
        if "from findings f" in sql and "join envelopes" in sql:
            finding_id, org_id = self.params[0], self.params[1]
            for row in self.db.findings:
                if row["id"] == finding_id and row["org_id"] == org_id:
                    detail = dict(row)
                    detail.setdefault("payload_json", "{}")
                    detail.setdefault("sender_id", "scanner-1")
                    detail.setdefault("kid", "k1")
                    detail.setdefault("envelope_received_at", row.get("created_at"))
                    return detail
            return None
        if "select status from findings" in sql:
            finding_id, org_id = self.params[0], self.params[1]
            for row in self.db.findings:
                if row["id"] == finding_id and row["org_id"] == org_id:
                    return {"status": row["status"]}
            return None
        return None

    async def all(self):
        self.db.all_calls.append((self.sql, self.params))
        rows = self._matching_rows()
        limit = int(self.params[-2])
        offset = int(self.params[-1])
        page = rows[offset : offset + limit]
        return SimpleNamespace(results=page)


class FindingsFakeDB(FakeDB):
    def __init__(self, findings):
        super().__init__()
        self.findings = findings

    def prepare(self, sql):
        self.prepare_calls.append(sql)
        return FindingsPreparedStatement(self, sql)


@pytest.fixture
def env():
    return SimpleNamespace(
        NG_ORG_API_TOKENS=json.dumps(
            {"token-org-a": "org-a", "token-org-b": "org-b"}
        )
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
            "created_at": 200,
            "updated_at": 200,
        },
        {
            "id": "f3",
            "org_id": "org-b",
            "envelope_id": "e3",
            "rule_id": "csrf",
            "severity": "medium",
            "title": "Missing CSRF token",
            "target": "https://b.example",
            "status": "open",
            "fingerprint": "fp3",
            "cve_id": None,
            "cve_score": None,
            "created_at": 150,
            "updated_at": 150,
        },
    ]


@pytest.mark.asyncio
async def test_list_findings_returns_org_scoped_page(env, sample_findings):
    db = FindingsFakeDB(sample_findings)
    headers = {"Authorization": "Bearer token-org-a"}

    result = await list_findings_for_request(
        env=env,
        db=db,
        headers=headers,
        query_params={"limit": "10"},
        store=FindingsStore(db),
    )

    assert result.status == 200
    assert result.body["org_id"] == "org-a"
    assert result.body["total"] == 2
    assert len(result.body["findings"]) == 2
    assert {item["id"] for item in result.body["findings"]} == {"f1", "f2"}


@pytest.mark.asyncio
async def test_list_findings_filters_by_status_and_severity(env, sample_findings):
    db = FindingsFakeDB(sample_findings)
    headers = {"Authorization": "Bearer token-org-a"}

    result = await list_findings_for_request(
        env=env,
        db=db,
        headers=headers,
        query_params={"status": "open", "severity": "high"},
        store=FindingsStore(db),
    )

    assert result.status == 200
    assert result.body["total"] == 1
    assert result.body["findings"][0]["id"] == "f1"


@pytest.mark.asyncio
async def test_list_findings_org_isolation(env, sample_findings):
    db = FindingsFakeDB(sample_findings)
    headers = {"Authorization": "Bearer token-org-b"}

    result = await list_findings_for_request(
        env=env,
        db=db,
        headers=headers,
        query_params={},
        store=FindingsStore(db),
    )

    assert result.status == 200
    assert result.body["total"] == 1
    assert result.body["findings"][0]["org_id"] == "org-b"


@pytest.mark.asyncio
async def test_list_findings_rejects_missing_token(env, sample_findings):
    db = FindingsFakeDB(sample_findings)

    with pytest.raises(AuthError):
        await list_findings_for_request(
            env=env,
            db=db,
            headers={},
            query_params={},
            store=FindingsStore(db),
        )


@pytest.mark.asyncio
async def test_list_findings_rejects_invalid_token(env, sample_findings):
    db = FindingsFakeDB(sample_findings)

    with pytest.raises(AuthError):
        await list_findings_for_request(
            env=env,
            db=db,
            headers={"Authorization": "Bearer not-a-real-token"},
            query_params={},
            store=FindingsStore(db),
        )


@pytest.mark.asyncio
async def test_list_findings_pagination(env, sample_findings):
    db = FindingsFakeDB(sample_findings)
    headers = {"Authorization": "Bearer token-org-a"}

    result = await list_findings_for_request(
        env=env,
        db=db,
        headers=headers,
        query_params={"limit": "1", "offset": "1", "sort": "created_at", "order": "asc"},
        store=FindingsStore(db),
    )

    assert result.status == 200
    assert result.body["total"] == 2
    assert len(result.body["findings"]) == 1
    assert result.body["findings"][0]["id"] == "f2"


@pytest.mark.asyncio
async def test_list_findings_invalid_sort(env, sample_findings):
    db = FindingsFakeDB(sample_findings)
    headers = {"Authorization": "Bearer token-org-a"}

    result = await list_findings_for_request(
        env=env,
        db=db,
        headers=headers,
        query_params={"sort": "title"},
        store=FindingsStore(db),
    )

    assert result.status == 400
    assert result.body["error"] == "invalid_query"
