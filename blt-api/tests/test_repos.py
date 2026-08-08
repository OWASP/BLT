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
# Mock infrastructure
# ---------------------------------------------------------------------------

from tests.mock_helpers import _MockResponse, MockDB, MockRequest, MockEnv

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
