"""Tests for the git.owaspblt.org issue-ledger reader and the blt://good-first-issues resource."""

import json

import httpx
import pytest

from blt_mcp import forge_issues, server, server_base


@pytest.fixture(autouse=True)
def real_send(monkeypatch):
    """Undo the BLT_MOCK_HTTP patch so each test's MockTransport answers."""
    original = getattr(server_base, "original_send", None)
    if original:
        monkeypatch.setattr(httpx.AsyncClient, "send", original)
    forge_issues._cache.clear()
    yield
    forge_issues._cache.clear()


def record(number, title, labels, status="open", body="Body text"):
    return {
        "number": number,
        "title": title,
        "status": status,
        "labels": [{"name": name} for name in labels],
        "events": [
            {"type": "open", "id": f"o{number}", "ts": 1, "body": body},
            {"type": "edit", "target": f"o{number}", "ts": 2, "body": body + " (edited)"},
        ],
    }


def ledger_transport(records, calls=None):
    """A MockTransport serving tree/blobs answers for the given {status: [record]}."""
    by_path = {}
    for status, items in records.items():
        for item in items:
            n = item["number"]
            by_path[f".forkmesh/issues/{status}/{n}/issue-{n}.json"] = item

    def handler(request):
        if calls is not None:
            calls.append(request)
        assert request.url.path.startswith("/api/repo/owasp-blt/BLT/")
        op = request.url.path.rsplit("/", 1)[1]
        target = request.url.params.get("path")
        if op == "tree" and target == ".forkmesh/issues":
            entries = [{"name": s, "type": "tree", "oid": s} for s in records]
            return httpx.Response(200, json={"commit": "abc", "entries": entries})
        if op == "tree":
            status = target.rsplit("/", 1)[1]
            assert request.url.params.get("ref") == "abc"
            entries = [{"name": str(i["number"]), "type": "tree", "oid": "x"} for i in records.get(status, [])]
            return httpx.Response(200, json={"entries": entries})
        if op == "blobs":
            paths = request.url.params.get_list("path")
            assert len(paths) <= forge_issues.BLOB_BATCH
            return httpx.Response(200, json={"blobs": {p: {"content": json.dumps(by_path[p])} for p in paths}})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


async def test_issues_reads_selected_status_folders_in_batches():
    many = [record(n, f"[blt-x] Issue {n}", []) for n in range(1, 121)]
    calls = []
    transport = ledger_transport({"open": many, "closed": [record(500, "x", [], "closed")]}, calls)
    async with httpx.AsyncClient(transport=transport) as client:
        found = await forge_issues.issues(client, statuses=("open",))
    assert [r["number"] for r in found[:2]] == [120, 119]
    assert len(found) == 120
    blob_calls = [c for c in calls if c.url.path.endswith("/blobs")]
    assert len(blob_calls) == 3
    assert not any("closed" in str(c.url) for c in calls)


async def test_cached_issues_reuses_answer_within_ttl():
    forge_issues._cache.clear()
    calls = []
    transport = ledger_transport({"open": [record(1, "a", [])]}, calls)
    clock = [1000.0]
    async with httpx.AsyncClient(transport=transport) as client:
        await forge_issues.cached_issues(client, now=lambda: clock[0])
        first = len(calls)
        await forge_issues.cached_issues(client, now=lambda: clock[0])
        assert len(calls) == first
        clock[0] += forge_issues.CACHE_SECONDS + 1
        await forge_issues.cached_issues(client, now=lambda: clock[0])
        assert len(calls) == 2 * first
    forge_issues._cache.clear()


def test_issue_projects_labels_then_title_prefix():
    assert forge_issues.issue_projects({"labels": ["project:blt-pages", "bug"], "title": "[blt-x] y"}) == ["blt-pages"]
    assert forge_issues.issue_projects({"labels": [{"name": "blt-mcp"}]}) == ["blt-mcp"]
    assert forge_issues.issue_projects({"labels": [], "title": "blt-jobs: fix"}) == ["blt-jobs"]
    assert forge_issues.issue_projects({"labels": [], "title": "No prefix here"}) == []


def test_body_follows_edits():
    assert forge_issues.body(record(1, "t", [], body="Hello")) == "Hello (edited)"


async def test_good_first_issues_resource(monkeypatch):
    forge_issues._cache.clear()
    records = {
        "open": [
            record(7, "[blt-pages] Fix typo", ["good first issue"], body="x" * 300),
            record(6, "Other", ["Good First Issue", "project:blt-mcp"]),
            record(5, "[blt-pages] Not for beginners", ["bug"]),
        ]
    }
    transport = ledger_transport(records)
    real_client = httpx.AsyncClient
    monkeypatch.setattr(server.httpx, "AsyncClient", lambda *a, **k: real_client(transport=transport))
    result = json.loads(await server.list_good_first_issues())
    forge_issues._cache.clear()
    assert result["success"] is True
    data = result["data"]
    assert [d["number"] for d in data] == [7, 6]
    assert data[0]["folder"] == "blt-pages"
    assert data[0]["repository"] == "blt-pages"
    assert data[0]["web_url"] == "https://git.owaspblt.org/BLT/issues/7"
    assert data[0]["description"].endswith("...") and len(data[0]["description"]) == 203
    assert data[1]["folder"] == "blt-mcp"
    assert data[1]["id"] == 6


async def test_good_first_issues_reports_errors(monkeypatch):
    forge_issues._cache.clear()
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    real_client = httpx.AsyncClient
    monkeypatch.setattr(server.httpx, "AsyncClient", lambda *a, **k: real_client(transport=transport))
    result = json.loads(await server.list_good_first_issues())
    assert result["success"] is False
