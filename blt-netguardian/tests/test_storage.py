"""Tests for D1 storage abstractions."""
from pathlib import Path
import json
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.storage import JobStateStore, TaskQueueStore, VulnerabilityDatabase


class FakePreparedStatement:
    """Prepared-statement test double with D1-like API shape."""

    def __init__(self, db, sql):
        self.db = db
        self.sql = sql
        self.params = ()

    def bind(self, *params):
        self.params = params
        self.db.bind_calls.append((self.sql, params))
        return self

    async def run(self):
        self.db.run_calls.append((self.sql, self.params))
        if self.db.run_results:
            return self.db.run_results.pop(0)
        return {}

    async def first(self):
        self.db.first_calls.append((self.sql, self.params))
        if self.db.first_results:
            return self.db.first_results.pop(0)
        return None

    async def all(self):
        self.db.all_calls.append((self.sql, self.params))
        if self.db.all_results:
            return self.db.all_results.pop(0)
        return SimpleNamespace(results=[])


class FakeDB:
    """Minimal D1-like DB object for storage tests."""

    def __init__(self, *, run_results=None, first_results=None, all_results=None):
        self.prepare_calls = []
        self.bind_calls = []
        self.run_calls = []
        self.first_calls = []
        self.all_calls = []
        self.run_results = list(run_results or [])
        self.first_results = list(first_results or [])
        self.all_results = list(all_results or [])

    def prepare(self, sql):
        self.prepare_calls.append(sql)
        return FakePreparedStatement(self, sql)


@pytest.mark.asyncio
async def test_get_job_parses_task_ids_json():
    db = FakeDB(first_results=[{
        "job_id": "job-1",
        "target_id": "target-1",
        "status": "queued",
        "total_tasks": 2,
        "completed_tasks": 0,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": None,
        "task_ids": json.dumps(["task-a", "task-b"]),
        "source": "user_suggestion",
    }])
    store = JobStateStore(db)

    job = await store.get_job("job-1")

    assert job["task_ids"] == ["task-a", "task-b"]
    assert job["source"] == "user_suggestion"


@pytest.mark.asyncio
async def test_update_job_progress_marks_job_completed_when_all_tasks_done():
    db = FakeDB(
        first_results=[{
            "job_id": "job-2",
            "target_id": "target-2",
            "status": "running",
            "total_tasks": 1,
            "completed_tasks": 0,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": None,
            "task_ids": json.dumps(["task-1"]),
            "source": None,
        }]
    )
    store = JobStateStore(db)

    await store.update_job_progress("job-2")

    update_sql, update_params = db.bind_calls[-1]
    assert "UPDATE jobs SET completed_tasks = ?, status = ?, updated_at = ?" in update_sql
    assert update_params[0] == 1
    assert update_params[1] == "completed"
    assert update_params[3] == "job-2"


@pytest.mark.asyncio
async def test_update_task_only_includes_whitelisted_columns():
    db = FakeDB()
    store = TaskQueueStore(db)

    await store.update_task(
        "task-1",
        {
            "status": "failed",
            "result_id": "res-1",
            "error": "boom",
            "created_at": "should-be-ignored",
        },
    )

    sql, params = db.bind_calls[-1]
    normalized_sql = " ".join(sql.split())
    assert "status = ?" in normalized_sql
    assert "result_id = ?" in normalized_sql
    assert "error = ?" in normalized_sql
    assert "created_at = ?" not in normalized_sql
    assert params[-1] == "task-1"


@pytest.mark.asyncio
async def test_get_vulnerabilities_uses_severity_filter_when_provided():
    payload = {"type": "xss", "severity": "high"}
    db = FakeDB(all_results=[SimpleNamespace(results=[{"data": json.dumps(payload)}])])
    vuln_db = VulnerabilityDatabase(db)

    vulnerabilities = await vuln_db.get_vulnerabilities(limit=10, severity="high")

    assert vulnerabilities == [payload]
    sql, params = db.all_calls[-1]
    assert "WHERE severity = ?" in sql
    assert params == ("high", 10)

