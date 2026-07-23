"""
Tests for the leaderboard handler (src/handlers/leaderboard.py).
"""

import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# ---------------------------------------------------------------------------
# Mock infrastructure (same pattern as test_bugs.py)
# ---------------------------------------------------------------------------

class _MockResponse:
    def __init__(self, data, status=200):
        self.data = data
        self.status = status

    @classmethod
    def json(cls, data, status=200, **kwargs):
        return cls(data, status)

_mock_workers = MagicMock()
_mock_workers.Response = _MockResponse
sys.modules.setdefault("workers", _mock_workers)


class _AllResult:
    def __init__(self, rows):
        self.results = rows


class _FakeStatement:
    def __init__(self, db, sql):
        self._db = db
        self._sql = sql
        self._params = ()

    def bind(self, *params):
        self._params = params
        return self

    async def all(self):
        self._db._last_sql = self._sql
        self._db._last_params = self._params
        rows = self._db._all_queue.pop(0) if self._db._all_queue else self._db._default_all
        return _AllResult(rows)

    async def first(self):
        self._db._last_sql = self._sql
        self._db._last_params = self._params
        if self._db._first_queue:
            return self._db._first_queue.pop(0)
        return self._db._default_first

    async def run(self):
        self._db._last_sql = self._sql
        self._db._last_params = self._params
        self._db._run_calls.append((self._sql, self._params))


class MockDB:
    def __init__(self):
        self._last_sql = None
        self._last_params = ()
        self._run_calls = []
        self._default_all = []
        self._default_first = None
        self._all_queue = []
        self._first_queue = []

    def prepare(self, sql):
        return _FakeStatement(self, sql)

    def set_all(self, rows):
        self._default_all = rows

    def set_first(self, row):
        self._default_first = row

    def queue_all(self, *row_lists):
        self._all_queue.extend(row_lists)

    def queue_first(self, *rows):
        self._first_queue.extend(rows)


class MockRequest:
    def __init__(self, method="GET", body=None, headers=None):
        self.method = method
        self._body = body
        self.headers = headers or {}

    async def text(self):
        if self._body is None:
            return ""
        if isinstance(self._body, dict):
            return json.dumps(self._body)
        return str(self._body)


class MockEnv:
    JWT_SECRET = "test-secret-key"


from handlers.leaderboard import handle_leaderboard  # noqa: E402

@pytest.fixture(autouse=True)
def mock_workers_runtime():
    with patch("utils._WORKERS_RUNTIME", True), \
         patch("utils.WorkerResponse", _MockResponse):
        yield

# ---------------------------------------------------------------------------
# Tests: GET /leaderboard (global)
# ---------------------------------------------------------------------------

class TestGlobalLeaderboard:
    async def test_returns_success_with_empty_data(self):
        db = MockDB()
        db.set_all([])
        db.queue_first({"total": 0})
        with patch("handlers.leaderboard.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_leaderboard(MockRequest(), MockEnv(), {}, {}, "/leaderboard")
        assert resp.data["success"] is True
        assert resp.data["type"] == "global"
        assert resp.data["data"] == []
        assert "pagination" in resp.data

    async def test_returns_users_ranked_by_total_score(self):
        db = MockDB()
        db.set_all([
            {"id": 4, "username": "diana", "title": 4, "total_score": 650},
            {"id": 1, "username": "alice", "title": 3, "total_score": 450},
            {"id": 2, "username": "bob", "title": 2, "total_score": 320},
        ])
        db.queue_first({"total": 3})
        with patch("handlers.leaderboard.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_leaderboard(MockRequest(), MockEnv(), {}, {}, "/leaderboard")
        assert resp.data["success"] is True
        assert len(resp.data["data"]) == 3
        assert resp.data["data"][0]["username"] == "diana"
        assert resp.data["data"][0]["total_score"] == 650

    async def test_pagination_defaults(self):
        db = MockDB()
        db.set_all([])
        db.queue_first({"total": 0})
        with patch("handlers.leaderboard.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_leaderboard(MockRequest(), MockEnv(), {}, {}, "/leaderboard")
        assert resp.data["pagination"]["page"] == 1
        assert resp.data["pagination"]["per_page"] == 20


# ---------------------------------------------------------------------------
# Tests: GET /leaderboard/monthly
# ---------------------------------------------------------------------------

class TestMonthlyLeaderboard:
    async def test_missing_params_returns_400(self):
        db = MockDB()
        with patch("handlers.leaderboard.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_leaderboard(MockRequest(), MockEnv(), {}, {}, "/leaderboard/monthly")
        assert resp.status == 400

    async def test_missing_year_returns_400(self):
        db = MockDB()
        with patch("handlers.leaderboard.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_leaderboard(MockRequest(), MockEnv(), {}, {"month": "7"}, "/leaderboard/monthly")
        assert resp.status == 400

    async def test_missing_month_returns_400(self):
        db = MockDB()
        with patch("handlers.leaderboard.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_leaderboard(MockRequest(), MockEnv(), {}, {"year": "2026"}, "/leaderboard/monthly")
        assert resp.status == 400

    async def test_invalid_month_returns_400(self):
        db = MockDB()
        with patch("handlers.leaderboard.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_leaderboard(MockRequest(), MockEnv(), {}, {"month": "13", "year": "2026"}, "/leaderboard/monthly")
        assert resp.status == 400

    async def test_non_numeric_month_returns_400(self):
        db = MockDB()
        with patch("handlers.leaderboard.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_leaderboard(MockRequest(), MockEnv(), {}, {"month": "abc", "year": "2026"}, "/leaderboard/monthly")
        assert resp.status == 400

    async def test_valid_monthly_returns_success(self):
        db = MockDB()
        db.set_all([
            {"id": 1, "username": "alice", "title": 3, "total_score": 200},
        ])
        db.queue_first({"total": 1})
        with patch("handlers.leaderboard.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_leaderboard(MockRequest(), MockEnv(), {}, {"month": "7", "year": "2026"}, "/leaderboard/monthly")
        assert resp.data["success"] is True
        assert resp.data["type"] == "monthly"
        assert resp.data["month"] == "7"
        assert resp.data["year"] == "2026"


# ---------------------------------------------------------------------------
# Tests: GET /leaderboard/organizations
# ---------------------------------------------------------------------------

class TestOrganizationLeaderboard:
    async def test_returns_success_with_empty_data(self):
        db = MockDB()
        db.set_all([])
        db.queue_first({"total": 0})
        with patch("handlers.leaderboard.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_leaderboard(MockRequest(), MockEnv(), {}, {}, "/leaderboard/organizations")
        assert resp.data["success"] is True
        assert resp.data["type"] == "organizations"
        assert resp.data["data"] == []

    async def test_returns_orgs_ranked_by_score(self):
        db = MockDB()
        db.set_all([
            {"id": 1, "name": "OWASP", "total_score": 5000},
            {"id": 2, "name": "SecureCorp", "total_score": 3000},
        ])
        db.queue_first({"total": 2})
        with patch("handlers.leaderboard.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_leaderboard(MockRequest(), MockEnv(), {}, {}, "/leaderboard/organizations")
        assert resp.data["success"] is True
        assert len(resp.data["data"]) == 2
        assert resp.data["data"][0]["name"] == "OWASP"


# ---------------------------------------------------------------------------
# Tests: Database errors
# ---------------------------------------------------------------------------

class TestLeaderboardDatabaseErrors:
    async def test_db_error_on_global_returns_500(self):
        with patch("handlers.leaderboard.get_db_safe", AsyncMock(side_effect=Exception("DB down"))):
            resp = await handle_leaderboard(MockRequest(), MockEnv(), {}, {}, "/leaderboard")
        assert resp.status == 500

    async def test_db_error_on_monthly_returns_500(self):
        with patch("handlers.leaderboard.get_db_safe", AsyncMock(side_effect=Exception("DB down"))):
            resp = await handle_leaderboard(MockRequest(), MockEnv(), {}, {"month": "7", "year": "2026"}, "/leaderboard/monthly")
        assert resp.status == 500

    async def test_db_error_on_organizations_returns_500(self):
        with patch("handlers.leaderboard.get_db_safe", AsyncMock(side_effect=Exception("DB down"))):
            resp = await handle_leaderboard(MockRequest(), MockEnv(), {}, {}, "/leaderboard/organizations")
        assert resp.status == 500
