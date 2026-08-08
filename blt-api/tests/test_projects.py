"""
Tests for the projects handler (src/handlers/projects.py).
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

from handlers.projects import handle_projects  # noqa: E402

@pytest.fixture(autouse=True)
def mock_workers_runtime():
    with patch("utils._WORKERS_RUNTIME", True), \
         patch("utils.WorkerResponse", _MockResponse):
        yield

# ---------------------------------------------------------------------------
# Tests: GET /projects (list)
# ---------------------------------------------------------------------------

class TestListProjects:
    async def test_returns_success_with_empty_data(self):
        db = MockDB()
        db.queue_first({"total": 0})
        db.set_all([])
        with patch("handlers.projects.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_projects(MockRequest(), MockEnv(), {}, {}, "/projects")
        assert resp.data["success"] is True
        assert resp.data["data"] == []
        assert "pagination" in resp.data

    async def test_returns_projects_with_pagination(self):
        db = MockDB()
        db.queue_first({"total": 2})
        db.set_all([
            {"id": 1, "organization_id": 1, "name": "Project A", "description": "Desc A", "status": "active"},
            {"id": 2, "organization_id": 1, "name": "Project B", "description": "Desc B", "status": "active"},
        ])
        with patch("handlers.projects.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_projects(MockRequest(), MockEnv(), {}, {}, "/projects")
        assert resp.data["success"] is True
        assert len(resp.data["data"]) == 2
        assert resp.data["pagination"]["total"] == 2

    async def test_default_pagination_values(self):
        db = MockDB()
        db.queue_first({"total": 0})
        db.set_all([])
        with patch("handlers.projects.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_projects(MockRequest(), MockEnv(), {}, {}, "/projects")
        assert resp.data["pagination"]["page"] == 1
        assert resp.data["pagination"]["per_page"] == 20

    async def test_custom_pagination(self):
        db = MockDB()
        db.queue_first({"total": 0})
        db.set_all([])
        with patch("handlers.projects.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_projects(MockRequest(), MockEnv(), {}, {"page": "2", "per_page": "5"}, "/projects")
        assert resp.data["pagination"]["page"] == 2
        assert resp.data["pagination"]["per_page"] == 5

    async def test_filter_by_organization(self):
        db = MockDB()
        db.queue_first({"total": 1})
        db.set_all([{"id": 1, "organization_id": 1, "name": "P1", "description": "", "status": "active"}])
        with patch("handlers.projects.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_projects(MockRequest(), MockEnv(), {}, {"organization": "1"}, "/projects")
        assert resp.data["success"] is True
        # Verify the SQL included organization filter
        assert 1 in db._last_params

    async def test_invalid_organization_filter_returns_400(self):
        db = MockDB()
        with patch("handlers.projects.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_projects(MockRequest(), MockEnv(), {}, {"organization": "abc"}, "/projects")
        assert resp.status == 400


# ---------------------------------------------------------------------------
# Tests: GET /projects/{id}
# ---------------------------------------------------------------------------

class TestGetProject:
    async def test_returns_project(self):
        db = MockDB()
        db.set_first({"id": 1, "organization_id": 1, "name": "BLT", "description": "Bug Logging Tool", "status": "active"})
        with patch("handlers.projects.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_projects(MockRequest(), MockEnv(), {"id": "1"}, {}, "/projects/1")
        assert resp.data["success"] is True
        assert resp.data["data"]["name"] == "BLT"

    async def test_not_found_returns_404(self):
        db = MockDB()
        db.set_first(None)
        with patch("handlers.projects.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_projects(MockRequest(), MockEnv(), {"id": "999"}, {}, "/projects/999")
        assert resp.status == 404

    async def test_non_integer_id_returns_400(self):
        db = MockDB()
        with patch("handlers.projects.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_projects(MockRequest(), MockEnv(), {"id": "abc"}, {}, "/projects/abc")
        assert resp.status == 400


# ---------------------------------------------------------------------------
# Tests: GET /projects/{id}/contributors
# ---------------------------------------------------------------------------

class TestProjectContributors:
    async def test_returns_contributors_list(self):
        db = MockDB()
        db.queue_first({"total": 2})
        db.set_all([
            {"id": 1, "user_id": 1, "score": 450, "created": "2026-01-01", "username": "alice"},
            {"id": 2, "user_id": 2, "score": 320, "created": "2026-01-02", "username": "bob"},
        ])
        with patch("handlers.projects.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_projects(MockRequest(), MockEnv(), {"id": "1"}, {}, "/projects/1/contributors")
        assert resp.data["success"] is True
        assert len(resp.data["data"]) == 2
        assert resp.data["data"][0]["username"] == "alice"

    async def test_empty_contributors(self):
        db = MockDB()
        db.queue_first({"total": 0})
        db.set_all([])
        with patch("handlers.projects.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_projects(MockRequest(), MockEnv(), {"id": "1"}, {}, "/projects/1/contributors")
        assert resp.data["success"] is True
        assert resp.data["data"] == []

    async def test_invalid_project_id_returns_400(self):
        db = MockDB()
        with patch("handlers.projects.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_projects(MockRequest(), MockEnv(), {"id": "abc"}, {}, "/projects/abc/contributors")
        assert resp.status == 400


# ---------------------------------------------------------------------------
# Tests: Database errors
# ---------------------------------------------------------------------------

class TestProjectsDatabaseErrors:
    async def test_db_error_on_list_returns_500(self):
        with patch("handlers.projects.get_db_safe", AsyncMock(side_effect=Exception("DB down"))):
            resp = await handle_projects(MockRequest(), MockEnv(), {}, {}, "/projects")
        assert resp.status == 500

    async def test_db_error_on_get_returns_500(self):
        with patch("handlers.projects.get_db_safe", AsyncMock(side_effect=Exception("DB down"))):
            resp = await handle_projects(MockRequest(), MockEnv(), {"id": "1"}, {}, "/projects/1")
        assert resp.status == 500

    async def test_db_error_on_contributors_returns_500(self):
        with patch("handlers.projects.get_db_safe", AsyncMock(side_effect=Exception("DB down"))):
            resp = await handle_projects(MockRequest(), MockEnv(), {"id": "1"}, {}, "/projects/1/contributors")
        assert resp.status == 500
