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
# Mock infrastructure
# ---------------------------------------------------------------------------

from tests.mock_helpers import _MockResponse, MockDB, MockRequest, MockEnv

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
