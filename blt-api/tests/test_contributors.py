"""
Tests for the contributors handler (src/handlers/contributors.py).
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

from handlers.contributors import handle_contributors  # noqa: E402

@pytest.fixture(autouse=True)
def mock_workers_runtime():
    with patch("utils._WORKERS_RUNTIME", True), \
         patch("utils.WorkerResponse", _MockResponse):
        yield

# ---------------------------------------------------------------------------
# Tests: GET /contributors (list)
# ---------------------------------------------------------------------------

class TestListContributors:
    async def test_returns_success_with_empty_data(self):
        db = MockDB()
        db.queue_first({"total": 0})
        db.set_all([])
        with patch("handlers.contributors.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_contributors(MockRequest(), MockEnv(), {}, {}, "/contributors")
        assert resp.data["success"] is True
        assert resp.data["data"] == []
        assert "pagination" in resp.data

    async def test_returns_contributors_sorted_by_score(self):
        db = MockDB()
        db.queue_first({"total": 3})
        db.set_all([
            {"id": 4, "user_id": 4, "project_id": 1, "repository_id": 3, "score": 650, "created": "2026-01-01", "username": "diana"},
            {"id": 1, "user_id": 1, "project_id": 1, "repository_id": 1, "score": 450, "created": "2026-01-02", "username": "alice"},
            {"id": 2, "user_id": 2, "project_id": 1, "repository_id": 1, "score": 320, "created": "2026-01-03", "username": "bob"},
        ])
        with patch("handlers.contributors.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_contributors(MockRequest(), MockEnv(), {}, {}, "/contributors")
        assert resp.data["success"] is True
        assert len(resp.data["data"]) == 3
        # Verify ordering — highest score first
        assert resp.data["data"][0]["username"] == "diana"
        assert resp.data["data"][0]["score"] == 650

    async def test_includes_username_from_join(self):
        db = MockDB()
        db.queue_first({"total": 1})
        db.set_all([
            {"id": 1, "user_id": 1, "project_id": 1, "repository_id": 1, "score": 100, "created": "2026-01-01", "username": "alice"},
        ])
        with patch("handlers.contributors.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_contributors(MockRequest(), MockEnv(), {}, {}, "/contributors")
        assert resp.data["data"][0]["username"] == "alice"

    async def test_pagination_defaults(self):
        db = MockDB()
        db.queue_first({"total": 0})
        db.set_all([])
        with patch("handlers.contributors.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_contributors(MockRequest(), MockEnv(), {}, {}, "/contributors")
        assert resp.data["pagination"]["page"] == 1
        assert resp.data["pagination"]["per_page"] == 20


# ---------------------------------------------------------------------------
# Tests: GET /contributors/{id}
# ---------------------------------------------------------------------------

class TestGetContributor:
    async def test_returns_contributor(self):
        db = MockDB()
        db.set_first({"id": 1, "user_id": 1, "project_id": 1, "repository_id": 1, "score": 450, "created": "2026-01-01", "username": "alice"})
        with patch("handlers.contributors.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_contributors(MockRequest(), MockEnv(), {"id": "1"}, {}, "/contributors/1")
        assert resp.data["success"] is True
        assert resp.data["data"]["username"] == "alice"
        assert resp.data["data"]["score"] == 450

    async def test_not_found_returns_404(self):
        db = MockDB()
        db.set_first(None)
        with patch("handlers.contributors.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_contributors(MockRequest(), MockEnv(), {"id": "999"}, {}, "/contributors/999")
        assert resp.status == 404

    async def test_non_integer_id_returns_400(self):
        db = MockDB()
        with patch("handlers.contributors.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_contributors(MockRequest(), MockEnv(), {"id": "abc"}, {}, "/contributors/abc")
        assert resp.status == 400


# ---------------------------------------------------------------------------
# Tests: Database errors
# ---------------------------------------------------------------------------

class TestContributorsDatabaseErrors:
    async def test_db_error_on_list_returns_500(self):
        with patch("handlers.contributors.get_db_safe", AsyncMock(side_effect=Exception("DB down"))):
            resp = await handle_contributors(MockRequest(), MockEnv(), {}, {}, "/contributors")
        assert resp.status == 500

    async def test_db_error_on_get_returns_500(self):
        with patch("handlers.contributors.get_db_safe", AsyncMock(side_effect=Exception("DB down"))):
            resp = await handle_contributors(MockRequest(), MockEnv(), {"id": "1"}, {}, "/contributors/1")
        assert resp.status == 500
