"""
Tests for the bugs handler (src/handlers/bugs.py).
"""

import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

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
sys.modules.setdefault("libs", MagicMock())
sys.modules.setdefault("libs.db", MagicMock())
sys.modules.setdefault("models", MagicMock())

from handlers.bugs import handle_bugs  # noqa: E402


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
    def __init__(self, method="GET", body=None):
        self.method = method
        self._body = body

    async def text(self):
        if self._body is None:
            return ""
        if isinstance(self._body, dict):
            return json.dumps(self._body)
        return str(self._body)


class MockEnv:
    pass


def _make_mock_bug_class(count=0):
    mock_qs = MagicMock()
    mock_qs.filter.return_value = mock_qs
    mock_qs.count = AsyncMock(return_value=count)
    mock_bug = MagicMock()
    mock_bug.objects.return_value = mock_qs
    return mock_bug, mock_qs


class TestSearchBugs:
    async def test_missing_q_returns_400(self):
        db = MockDB()
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(), MockEnv(), {}, {}, "/bugs/search")
        assert resp.status == 400

    async def test_empty_q_returns_400(self):
        db = MockDB()
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(), MockEnv(), {}, {"q": ""}, "/bugs/search")
        assert resp.status == 400

    async def test_valid_query_returns_success(self):
        db = MockDB()
        db.set_all([{"id": 1, "url": "https://example.com", "description": "test bug"}])
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(), MockEnv(), {}, {"q": "test"}, "/bugs/search")
        assert resp.data["success"] is True
        assert resp.data["query"] == "test"

    async def test_no_matching_bugs_returns_empty_list(self):
        db = MockDB()
        db.set_all([])
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(), MockEnv(), {}, {"q": "zzznomatch"}, "/bugs/search")
        assert resp.data["data"] == []

    async def test_limit_clamped_to_100(self):
        db = MockDB()
        db.set_all([])
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(), MockEnv(), {}, {"q": "test", "limit": "9999"}, "/bugs/search")
        assert 100 in db._last_params

    async def test_invalid_limit_defaults_to_10(self):
        db = MockDB()
        db.set_all([])
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(), MockEnv(), {}, {"q": "test", "limit": "abc"}, "/bugs/search")
        assert 10 in db._last_params


class TestGetBugById:
    async def test_non_integer_id_returns_400(self):
        db = MockDB()
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(), MockEnv(), {"id": "abc"}, {}, "/bugs/abc")
        assert resp.status == 400

    async def test_bug_not_found_returns_404(self):
        db = MockDB()
        db.set_first(None)
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(), MockEnv(), {"id": "999"}, {}, "/bugs/999")
        assert resp.status == 404

    async def test_found_bug_has_screenshots_and_tags(self):
        db = MockDB()
        db.set_first({"id": 1, "url": "https://example.com", "description": "bug"})
        db.set_all([])
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(), MockEnv(), {"id": "1"}, {}, "/bugs/1")
        assert resp.data["success"] is True
        assert "screenshots" in resp.data["data"]
        assert "tags" in resp.data["data"]

    async def test_screenshots_included(self):
        db = MockDB()
        db.set_first({"id": 2, "url": "https://x.com", "description": "x"})
        screenshot = {"id": 10, "image": "https://img.example.com/1.png", "created": "2024-01-01"}
        db.queue_all([screenshot], [])
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(), MockEnv(), {"id": "2"}, {}, "/bugs/2")
        assert resp.data["data"]["screenshots"] == [screenshot]

    async def test_tags_included(self):
        db = MockDB()
        db.set_first({"id": 3, "url": "https://y.com", "description": "y"})
        tag = {"id": 5, "name": "xss"}
        db.queue_all([], [tag])
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(), MockEnv(), {"id": "3"}, {}, "/bugs/3")
        assert resp.data["data"]["tags"] == [tag]


class TestCreateBug:
    async def test_empty_body_returns_400(self):
        db = MockDB()
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(method="POST", body=None), MockEnv(), {}, {}, "/bugs")
        assert resp.status == 400

    async def test_missing_url_returns_400(self):
        db = MockDB()
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(method="POST", body={"description": "d"}), MockEnv(), {}, {}, "/bugs")
        assert resp.status == 400

    async def test_missing_description_returns_400(self):
        db = MockDB()
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(method="POST", body={"url": "https://example.com"}), MockEnv(), {}, {}, "/bugs")
        assert resp.status == 400

    async def test_url_over_200_chars_returns_400(self):
        db = MockDB()
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(method="POST", body={"url": "https://x.com/" + "a"*200, "description": "d"}), MockEnv(), {}, {}, "/bugs")
        assert resp.status == 400

    async def test_ftp_url_rejected(self):
        db = MockDB()
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(method="POST", body={"url": "ftp://example.com", "description": "d"}), MockEnv(), {}, {}, "/bugs")
        assert resp.status == 400

    async def test_valid_bug_created_returns_201(self):
        db = MockDB()
        db.queue_first({"id": 1}, {"id": 1, "url": "https://example.com", "description": "d"})
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)):
            resp = await handle_bugs(MockRequest(method="POST", body={"url": "https://example.com", "description": "d"}), MockEnv(), {}, {}, "/bugs")
        assert resp.status == 201
        assert resp.data["success"] is True


class TestListBugs:
    async def test_returns_success_with_pagination(self):
        db = MockDB()
        db.set_all([])
        mock_bug, _ = _make_mock_bug_class(count=0)
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)),              patch("handlers.bugs.Bug", mock_bug):
            resp = await handle_bugs(MockRequest(), MockEnv(), {}, {}, "/bugs")
        assert resp.data["success"] is True
        assert "pagination" in resp.data

    async def test_default_pagination_values(self):
        db = MockDB()
        db.set_all([])
        mock_bug, _ = _make_mock_bug_class(count=0)
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)),              patch("handlers.bugs.Bug", mock_bug):
            resp = await handle_bugs(MockRequest(), MockEnv(), {}, {}, "/bugs")
        assert resp.data["pagination"]["page"] == 1
        assert resp.data["pagination"]["per_page"] == 20

    async def test_custom_pagination_reflected(self):
        db = MockDB()
        db.set_all([])
        mock_bug, _ = _make_mock_bug_class(count=0)
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)),              patch("handlers.bugs.Bug", mock_bug):
            resp = await handle_bugs(MockRequest(), MockEnv(), {}, {"page": "3", "per_page": "5"}, "/bugs")
        assert resp.data["pagination"]["page"] == 3
        assert resp.data["pagination"]["per_page"] == 5

    async def test_total_pages_calculated_correctly(self):
        db = MockDB()
        db.set_all([{"id": i} for i in range(20)])
        mock_bug, _ = _make_mock_bug_class(count=45)
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)),              patch("handlers.bugs.Bug", mock_bug):
            resp = await handle_bugs(MockRequest(), MockEnv(), {}, {"per_page": "20"}, "/bugs")
        assert resp.data["pagination"]["total_pages"] == 3

    async def test_empty_results_zero_total_pages(self):
        db = MockDB()
        db.set_all([])
        mock_bug, _ = _make_mock_bug_class(count=0)
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)),              patch("handlers.bugs.Bug", mock_bug):
            resp = await handle_bugs(MockRequest(), MockEnv(), {}, {}, "/bugs")
        assert resp.data["pagination"]["total_pages"] == 0

    async def test_status_filter_applied(self):
        db = MockDB()
        db.set_all([])
        mock_bug, mock_qs = _make_mock_bug_class(count=0)
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)),              patch("handlers.bugs.Bug", mock_bug):
            await handle_bugs(MockRequest(), MockEnv(), {}, {"status": "open"}, "/bugs")
        mock_qs.filter.assert_called()

    async def test_non_digit_domain_ignored(self):
        db = MockDB()
        db.set_all([])
        mock_bug, mock_qs = _make_mock_bug_class(count=0)
        with patch("handlers.bugs.get_db_safe", AsyncMock(return_value=db)),              patch("handlers.bugs.Bug", mock_bug):
            resp = await handle_bugs(MockRequest(), MockEnv(), {}, {"domain": "not-a-number"}, "/bugs")
        assert resp.data["success"] is True


class TestDatabaseConnectionErrors:
    async def test_db_error_on_list_returns_500(self):
        with patch("handlers.bugs.get_db_safe", AsyncMock(side_effect=Exception("DB down"))):
            resp = await handle_bugs(MockRequest(), MockEnv(), {}, {}, "/bugs")
        assert resp.status == 500

    async def test_db_error_on_search_returns_500(self):
        with patch("handlers.bugs.get_db_safe", AsyncMock(side_effect=Exception("DB down"))):
            resp = await handle_bugs(MockRequest(), MockEnv(), {}, {"q": "test"}, "/bugs/search")
        assert resp.status == 500

    async def test_db_error_on_get_by_id_returns_500(self):
        with patch("handlers.bugs.get_db_safe", AsyncMock(side_effect=Exception("DB down"))):
            resp = await handle_bugs(MockRequest(), MockEnv(), {"id": "1"}, {}, "/bugs/1")
        assert resp.status == 500

    async def test_db_error_on_create_returns_500(self):
        with patch("handlers.bugs.get_db_safe", AsyncMock(side_effect=Exception("DB down"))):
            resp = await handle_bugs(MockRequest(method="POST", body={"url": "https://x.com", "description": "d"}), MockEnv(), {}, {}, "/bugs")
        assert resp.status == 500
