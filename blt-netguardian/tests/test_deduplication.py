"""Tests for task deduplication behavior."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.deduplication import TaskDeduplicator


class FakePreparedStatement:
    """Minimal prepared statement stub for D1-like chaining."""

    def __init__(self, db, sql):
        self.db = db
        self.sql = sql

    def bind(self, *params):
        self.db.bind_calls.append((self.sql, params))
        return self

    async def run(self):
        if self.db.results:
            return self.db.results.pop(0)
        return {"rows_affected": 1}


class FakeDB:
    """Minimal D1-like DB stub."""

    def __init__(self, *results):
        self.results = list(results)
        self.prepare_calls = []
        self.bind_calls = []

    def prepare(self, sql):
        self.prepare_calls.append(sql)
        return FakePreparedStatement(self, sql)


class FakeTaskQueue:
    """Task queue wrapper exposing `db` the way production code does."""

    def __init__(self, db=None):
        self.db = db


def make_task(target_id="target-1", task_type="crawler"):
    """Create a minimal task-like object for hash generation."""
    return SimpleNamespace(target_id=target_id, task_type=task_type)


@pytest.mark.asyncio
async def test_is_duplicate_uses_single_atomic_upsert():
    deduplicator = TaskDeduplicator()
    db = FakeDB({"rows_affected": 1})

    is_duplicate = await deduplicator.is_duplicate(make_task(), FakeTaskQueue(db))

    assert is_duplicate is False
    assert len(db.prepare_calls) == 1
    normalized_sql = " ".join(db.prepare_calls[0].split())
    assert "INSERT INTO task_hashes" in normalized_sql
    assert "ON CONFLICT(task_hash) DO UPDATE" in normalized_sql
    assert "SELECT" not in normalized_sql.upper()


@pytest.mark.asyncio
async def test_rows_affected_zero_marks_duplicate():
    deduplicator = TaskDeduplicator()
    db = FakeDB({"rows_affected": 0})

    is_duplicate = await deduplicator.is_duplicate(make_task(), FakeTaskQueue(db))

    assert is_duplicate is True


@pytest.mark.asyncio
async def test_rows_affected_one_marks_new_and_populates_memory_cache():
    deduplicator = TaskDeduplicator()
    db = FakeDB({"rows_affected": 1})
    task = make_task()

    first = await deduplicator.is_duplicate(task, FakeTaskQueue(db))
    second = await deduplicator.is_duplicate(task, FakeTaskQueue(db))

    assert first is False
    assert second is True
    assert len(db.prepare_calls) == 1


@pytest.mark.asyncio
async def test_expired_in_memory_hash_is_evictable_after_24_hours():
    deduplicator = TaskDeduplicator()
    task = make_task()
    task_hash = deduplicator.generate_task_hash(task)
    deduplicator.seen_hashes[task_hash] = datetime.now(timezone.utc) - timedelta(hours=25)

    first = await deduplicator.is_duplicate(task, FakeTaskQueue(db=None))
    second = await deduplicator.is_duplicate(task, FakeTaskQueue(db=None))

    assert first is False
    assert second is True


@pytest.mark.asyncio
async def test_rows_affected_can_be_read_from_meta():
    deduplicator = TaskDeduplicator()
    db = FakeDB({"meta": {"rows_written": 0}})

    is_duplicate = await deduplicator.is_duplicate(make_task(), FakeTaskQueue(db))

    assert is_duplicate is True
