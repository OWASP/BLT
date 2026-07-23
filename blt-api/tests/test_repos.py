"""
Tests for the repos handler (src/handlers/repos.py).
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


from handlers.repos import handle_repos  # noqa: E402

@pytest.fixture(autouse=True)
def mock_workers_runtime():
    with patch("utils._WORKERS_RUNTIME", True), \
         patch("utils.WorkerResponse", _MockResponse):
        yield

# ---------------------------------------------------------------------------
# Tests: GET /repos (list)
# ---------------------------------------------------------------------------

class TestListRepos:
    async def test_returns_success_with_empty_data(self):
        db = MockDB()
        db.queue_first({"total": 0})
        db.set_all([])
        with patch("handlers.repos.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_repos(MockRequest(), MockEnv(), {}, {}, "/repos")
        assert resp.data["success"] is True
        assert resp.data["data"] == []
        assert "pagination" in resp.data

    async def test_returns_repos_with_data(self):
        db = MockDB()
        db.queue_first({"total": 2})
        db.set_all([
            {"id": 1, "organization_id": 1, "project_id": 1, "name": "BLT", "url": "https://github.com/OWASP-BLT/BLT"},
            {"id": 2, "organization_id": 1, "project_id": 1, "name": "blt-api", "url": "https://gitlab.com/owasp-blt/blt-api"},
        ])
        with patch("handlers.repos.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_repos(MockRequest(), MockEnv(), {}, {}, "/repos")
        assert resp.data["success"] is True
        assert len(resp.data["data"]) == 2
        assert resp.data["pagination"]["total"] == 2

    async def test_filter_by_organization(self):
        db = MockDB()
        db.queue_first({"total": 1})
        db.set_all([{"id": 1, "organization_id": 1, "project_id": 1, "name": "BLT", "url": "https://github.com/BLT"}])
        with patch("handlers.repos.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_repos(MockRequest(), MockEnv(), {}, {"organization": "1"}, "/repos")
        assert resp.data["success"] is True

    async def test_filter_by_project(self):
        db = MockDB()
        db.queue_first({"total": 1})
        db.set_all([{"id": 1, "organization_id": 1, "project_id": 2, "name": "ZAP", "url": "https://github.com/zaproxy"}])
        with patch("handlers.repos.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_repos(MockRequest(), MockEnv(), {}, {"project": "2"}, "/repos")
        assert resp.data["success"] is True

    async def test_invalid_organization_filter_returns_400(self):
        db = MockDB()
        with patch("handlers.repos.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_repos(MockRequest(), MockEnv(), {}, {"organization": "abc"}, "/repos")
        assert resp.status == 400

    async def test_invalid_project_filter_returns_400(self):
        db = MockDB()
        with patch("handlers.repos.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_repos(MockRequest(), MockEnv(), {}, {"project": "xyz"}, "/repos")
        assert resp.status == 400

    async def test_combined_filters(self):
        db = MockDB()
        db.queue_first({"total": 0})
        db.set_all([])
        with patch("handlers.repos.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_repos(MockRequest(), MockEnv(), {}, {"organization": "1", "project": "2"}, "/repos")
        assert resp.data["success"] is True
        # Verify both filters are in the SQL params (org=1, project=2, plus LIMIT/OFFSET)
        assert 1 in db._last_params
        assert 2 in db._last_params


# ---------------------------------------------------------------------------
# Tests: GET /repos/{id}
# ---------------------------------------------------------------------------

class TestGetRepo:
    async def test_returns_repo(self):
        db = MockDB()
        db.set_first({"id": 1, "organization_id": 1, "project_id": 1, "name": "BLT", "url": "https://github.com/BLT"})
        with patch("handlers.repos.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_repos(MockRequest(), MockEnv(), {"id": "1"}, {}, "/repos/1")
        assert resp.data["success"] is True
        assert resp.data["data"]["name"] == "BLT"

    async def test_not_found_returns_404(self):
        db = MockDB()
        db.set_first(None)
        with patch("handlers.repos.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_repos(MockRequest(), MockEnv(), {"id": "999"}, {}, "/repos/999")
        assert resp.status == 404

    async def test_non_integer_id_returns_400(self):
        db = MockDB()
        with patch("handlers.repos.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_repos(MockRequest(), MockEnv(), {"id": "abc"}, {}, "/repos/abc")
        assert resp.status == 400


# ---------------------------------------------------------------------------
# Tests: Database errors
# ---------------------------------------------------------------------------

class TestReposDatabaseErrors:
    async def test_db_error_on_list_returns_500(self):
        with patch("handlers.repos.get_db_safe", AsyncMock(side_effect=Exception("DB down"))):
            resp = await handle_repos(MockRequest(), MockEnv(), {}, {}, "/repos")
        assert resp.status == 500

    async def test_db_error_on_get_returns_500(self):
        with patch("handlers.repos.get_db_safe", AsyncMock(side_effect=Exception("DB down"))):
            resp = await handle_repos(MockRequest(), MockEnv(), {"id": "1"}, {}, "/repos/1")
        assert resp.status == 500
