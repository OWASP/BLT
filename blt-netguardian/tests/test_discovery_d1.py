"""Discovery endpoints report the D1 domain queue; legacy stores read Workers rows."""

from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import types
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

if "workers" not in sys.modules:
    workers_module = types.ModuleType("workers")

    class FakeResponse:
        def __init__(self, body="", status=200, headers=None):
            self.body = body
            self.status = status
            self.headers = dict(headers or {})

    workers_module.Response = FakeResponse
    sys.modules["workers"] = workers_module

from netguardian_db import open_netguardian_db  # noqa: E402
from utils.storage import TaskQueueStore, VulnerabilityDatabase  # noqa: E402
from worker import BLTWorker  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


class JsProxyRow:
    """Like a Pyodide JsProxy D1 row: not subscriptable until .to_py()."""

    def __init__(self, data):
        self._data = data

    def to_py(self):
        return dict(self._data)


class JsStatement:
    def __init__(self, rows):
        self.rows = rows

    def bind(self, *_args):
        return self

    async def first(self):
        return JsProxyRow(self.rows[0]) if self.rows else None

    async def all(self):
        return SimpleNamespace(results=[JsProxyRow(r) for r in self.rows])


class JsDB:
    def __init__(self, rows):
        self.rows = rows

    def prepare(self, _sql):
        return JsStatement(self.rows)


@pytest.mark.asyncio
async def test_legacy_stats_read_jsproxy_rows():
    # Before: TypeError: 'pyodide.ffi.JsProxy' object is not subscriptable (HTTP 500).
    stats = await VulnerabilityDatabase(JsDB([{"severity": "high", "count": 2}])).get_stats()
    assert stats["high"] == 2 and stats["total"] == 2
    assert await TaskQueueStore(JsDB([{"count": 3}])).count_completed_tasks_today() == 3


def env_with_db():
    db = open_netguardian_db(REPO)
    return SimpleNamespace(DB=db, NG_DEFAULT_ORG="org-demo", AUTHENTICATE_READ_ENDPOINTS="false"), db


async def get(worker, path):
    resp = await worker.handle_request(SimpleNamespace(url=f"https://ng.example/{path}", method="GET", headers={}))
    return resp.status, json.loads(resp.body)


@pytest.mark.asyncio
async def test_status_is_idle_and_empty_without_data():
    env, _db = env_with_db()
    status, body = await get(BLTWorker(env), "api/discovery/status")
    assert status == 200
    assert body["status"] == "idle"
    assert body["current_target"] is None  # no more hard-coded example.com
    assert body["scanned_today"] == 0
    assert body["stats"]["domains_discovered"] == 0  # no more invented 12458
    status, body = await get(BLTWorker(env), "api/discovery/recent")
    assert status == 200 and body["discoveries"] == []


@pytest.mark.asyncio
async def test_status_reflects_queue_rows():
    env, db = env_with_db()
    now = int(datetime.now(timezone.utc).timestamp())
    rows = [
        ("a", "a.example.org", "in_progress", None, "scanner-1", now + 60),
        ("b", "b.example.org", "scanned", now, None, None),
        ("c", "c.example.org", "pending", None, None, None),
    ]
    for job_id, host, status, last, claimed_by, until in rows:
        await db.prepare(
            "INSERT INTO domain_jobs (id, org_id, host_key, seed_url, status, discovered_at, last_scan_at,"
            " claimed_by, claim_until) VALUES (?, 'org-demo', ?, ?, ?, ?, ?, ?, ?)"
        ).bind(job_id, host, f"https://{host}/", status, now - ord(job_id), last, claimed_by, until).run()
    # Another org's rows stay invisible.
    await db.prepare(
        "INSERT INTO domain_jobs (id, org_id, host_key, seed_url, status, discovered_at)"
        " VALUES ('z', 'org-other', 'z.example.org', 'https://z.example.org/', 'in_progress', 1)"
    ).run()

    status, body = await get(BLTWorker(env), "api/discovery/status")
    assert status == 200
    assert body["status"] == "active"
    assert body["current_target"] == "a.example.org"
    assert body["scanned_today"] == 1
    assert body["stats"]["domains_discovered"] == 3
    assert body["stats"]["active_scans"] == 1

    status, body = await get(BLTWorker(env), "api/discovery/recent?limit=2")
    assert [d["target"] for d in body["discoveries"]] == ["a.example.org", "b.example.org"]
    assert body["discoveries"][0]["source"] == "client"
