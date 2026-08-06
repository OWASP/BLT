"""Tests for the ConversationDO Durable Object.

Since ConversationDO relies on Cloudflare Workers JS APIs (Response, Headers,
Date, URL), all JS imports are mocked at the module level before importing
the module under test.
"""

import json
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Mock JS modules before importing the module under test
# ---------------------------------------------------------------------------

_mock_js = MagicMock()


def _make_mock_url(url_str):
    """Create a mock URL object that parses the URL string."""
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url_str)
    mock_url = MagicMock()
    mock_url.pathname = parsed.path
    mock_url.searchParams = MagicMock()
    params = parse_qs(parsed.query)
    mock_url.searchParams.get = lambda key: params.get(key, [None])[0]
    return mock_url


_mock_js.URL.new = _make_mock_url
_mock_js.Date.now = MagicMock(return_value=1700000000000)
_mock_js.Headers.new = lambda: MagicMock()


def _mock_response_new(body, headers=None, status=200):
    resp = MagicMock()
    resp.status = status
    resp._body = body
    return resp


_mock_js.Response.new = _mock_response_new

sys.modules["js"] = _mock_js

from src.durable_objects import ConversationDO  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state():
    """Create a mock DO state with in-memory storage."""
    state = MagicMock()
    storage_data = {}

    async def mock_get(key):
        return storage_data.get(key)

    async def mock_put(key, value):
        storage_data[key] = value

    async def mock_delete_all():
        storage_data.clear()

    state.storage = MagicMock()
    state.storage.get = AsyncMock(side_effect=mock_get)
    state.storage.put = AsyncMock(side_effect=mock_put)
    state.storage.deleteAll = AsyncMock(side_effect=mock_delete_all)
    state.storage.setAlarm = AsyncMock()
    state.storage._data = storage_data
    return state


def _make_env(db_run_side_effect=None):
    """Create a mock env with DB binding."""
    env = MagicMock()
    stmt_mock = MagicMock()
    stmt_mock.bind = MagicMock(return_value=stmt_mock)
    stmt_mock.run = AsyncMock(side_effect=db_run_side_effect)

    all_result = MagicMock()
    all_result.results = []
    stmt_mock.all = AsyncMock(return_value=all_result)

    env.DB.prepare = MagicMock(return_value=stmt_mock)
    env.DB._stmt_mock = stmt_mock
    return env


def _make_request(method, path, body=None):
    """Create a mock DO fetch request."""
    req = MagicMock()
    req.method = method
    req.url = f"https://do-internal.example.com{path}"
    if body:
        req.text = AsyncMock(return_value=json.dumps(body))
    else:
        req.text = AsyncMock(return_value="")
    return req


def _parse_response(resp):
    """Parse a mock Response body into a dict."""
    return json.loads(resp._body)


# ---------------------------------------------------------------------------
# Tests: POST /reply
# ---------------------------------------------------------------------------


class TestPostReply:
    @pytest.mark.asyncio
    async def test_first_reply_creates_conversation(self):
        """First POST sets conversation_id, turn_count=1, status=active."""
        state = _make_state()
        env = _make_env()
        do = ConversationDO(state, env)

        req = _make_request("POST", "/reply", {"role": "developer", "content": "hello", "triage_id": "evt-001"})
        resp = await do.fetch(req)

        assert resp.status == 200
        data = _parse_response(resp)
        assert data["turn_count"] == 1
        assert data["conversation_id"] == "evt-001"
        assert state.storage._data.get("status") == "active"
        assert state.storage._data.get("conversation_id") == "evt-001"

    @pytest.mark.asyncio
    async def test_five_turns_persist(self):
        """POST 5 turns → GET /history returns all 5 in order."""
        state = _make_state()
        env = _make_env()
        do = ConversationDO(state, env)

        for i in range(1, 6):
            role = "developer" if i % 2 != 0 else "ai"
            req = _make_request("POST", "/reply", {"role": role, "content": f"msg {i}", "triage_id": "evt-001"})
            await do.fetch(req)

        req_hist = _make_request("GET", "/history")
        resp_hist = await do.fetch(req_hist)

        assert resp_hist.status == 200
        data = _parse_response(resp_hist)
        assert data["turn_count"] == 5
        assert len(data["turns"]) == 5
        assert data["turns"][0]["content"] == "msg 1"
        assert data["turns"][-1]["content"] == "msg 5"

    @pytest.mark.asyncio
    async def test_sixth_turn_archives_oldest(self):
        """POST 6 turns → oldest archived to D1, DO has turns 2-6."""
        state = _make_state()
        env = _make_env()
        do = ConversationDO(state, env)

        for i in range(1, 7):
            req = _make_request("POST", "/reply", {"role": "developer", "content": f"msg {i}", "triage_id": "evt-001"})
            await do.fetch(req)

        # D1 INSERT should have been called for archival
        assert env.DB.prepare.called
        assert env.DB._stmt_mock.run.called

        req_hist = _make_request("GET", "/history")
        resp_hist = await do.fetch(req_hist)

        data = _parse_response(resp_hist)
        assert len(data["turns"]) == 5
        assert data["turns"][0]["content"] == "msg 2"
        assert data["turns"][-1]["content"] == "msg 6"
        assert data["turn_count"] == 6

    @pytest.mark.asyncio
    async def test_archive_failure_keeps_turn_in_do(self):
        """Mock D1 write failure → oldest turn NOT dropped from DO."""
        state = _make_state()
        env = _make_env(db_run_side_effect=Exception("DB Error"))
        do = ConversationDO(state, env)

        for i in range(1, 7):
            req = _make_request("POST", "/reply", {"role": "developer", "content": f"msg {i}", "triage_id": "evt-001"})
            await do.fetch(req)

        req_hist = _make_request("GET", "/history")
        resp_hist = await do.fetch(req_hist)

        data = _parse_response(resp_hist)
        # All 6 turns should remain since archival failed
        assert len(data["turns"]) == 6
        assert data["turns"][0]["content"] == "msg 1"
        assert data["turns"][-1]["content"] == "msg 6"

    @pytest.mark.asyncio
    async def test_invalid_role_rejected(self):
        """POST with role='admin' → 400 error."""
        state = _make_state()
        env = _make_env()
        do = ConversationDO(state, env)

        req = _make_request("POST", "/reply", {"role": "admin", "content": "hello", "triage_id": "evt-001"})
        resp = await do.fetch(req)

        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_empty_content_rejected(self):
        """POST with empty content → 400 error."""
        state = _make_state()
        env = _make_env()
        do = ConversationDO(state, env)

        req = _make_request("POST", "/reply", {"role": "developer", "content": "", "triage_id": "evt-001"})
        resp = await do.fetch(req)

        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_reply_to_closed_conversation(self):
        """POST to closed conversation → 409 error."""
        state = _make_state()
        state.storage._data["status"] = "closed"
        env = _make_env()
        do = ConversationDO(state, env)

        req = _make_request("POST", "/reply", {"role": "developer", "content": "hello", "triage_id": "evt-001"})
        resp = await do.fetch(req)

        assert resp.status == 409


# ---------------------------------------------------------------------------
# Tests: GET /history
# ---------------------------------------------------------------------------


class TestGetHistory:
    @pytest.mark.asyncio
    async def test_history_returns_do_turns_only(self):
        """GET /history (no full param) → only DO turns returned."""
        state = _make_state()
        env = _make_env()
        do = ConversationDO(state, env)

        for i in range(1, 4):
            req = _make_request("POST", "/reply", {"role": "developer", "content": f"msg {i}", "triage_id": "evt-001"})
            await do.fetch(req)

        req_hist = _make_request("GET", "/history")
        resp_hist = await do.fetch(req_hist)

        assert resp_hist.status == 200
        data = _parse_response(resp_hist)
        assert len(data["turns"]) == 3
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_full_history_includes_d1_archive(self):
        """GET /history?full=true → D1 archived + DO turns combined."""
        state = _make_state()
        env = _make_env()
        do = ConversationDO(state, env)

        # Post 3 turns
        for i in range(1, 4):
            req = _make_request("POST", "/reply", {"role": "developer", "content": f"msg {i}", "triage_id": "evt-001"})
            await do.fetch(req)

        # Mock D1 to return archived turns for the full history query
        archived_row = MagicMock()
        archived_row.role = "developer"
        archived_row.content = "archived msg"
        archived_row.timestamp = "2024-01-01T00:00:00"
        archived_row.turn_index = 0

        all_result = MagicMock()
        all_result.results = [archived_row]

        stmt_mock = MagicMock()
        stmt_mock.bind = MagicMock(return_value=stmt_mock)
        stmt_mock.all = AsyncMock(return_value=all_result)
        env.DB.prepare = MagicMock(return_value=stmt_mock)

        req_hist = _make_request("GET", "/history?full=true")
        resp_hist = await do.fetch(req_hist)

        assert resp_hist.status == 200
        data = _parse_response(resp_hist)
        # 1 archived + 3 active = 4
        assert len(data["turns"]) == 4
        assert data["turns"][0]["content"] == "archived msg"


# ---------------------------------------------------------------------------
# Tests: DELETE /archive
# ---------------------------------------------------------------------------


class TestDeleteArchive:
    @pytest.mark.asyncio
    async def test_delete_archives_and_closes(self):
        """DELETE /archive → all turns written to D1, status=closed."""
        state = _make_state()
        env = _make_env()
        do = ConversationDO(state, env)

        for i in range(1, 4):
            req = _make_request("POST", "/reply", {"role": "developer", "content": f"msg {i}", "triage_id": "evt-001"})
            await do.fetch(req)

        req_del = _make_request("DELETE", "/archive")
        resp_del = await do.fetch(req_del)

        assert resp_del.status == 200
        data = _parse_response(resp_del)
        assert data["archived"] is True
        assert data["turns_archived"] == 3

        # State should be cleared except for status=closed marker
        state.storage.deleteAll.assert_called_once()
        assert state.storage._data == {"status": "closed"}


# ---------------------------------------------------------------------------
# Tests: alarm()
# ---------------------------------------------------------------------------


class TestAlarm:
    @pytest.mark.asyncio
    async def test_alarm_closed_deletes_storage(self):
        """alarm() with status=closed → deleteAll() called."""
        state = _make_state()
        state.storage._data["status"] = "closed"
        env = _make_env()
        do = ConversationDO(state, env)

        await do.alarm()
        state.storage.deleteAll.assert_called_once()

    @pytest.mark.asyncio
    async def test_alarm_active_resets_alarm(self):
        """alarm() with status=active → new alarm set for 30 days."""
        state = _make_state()
        state.storage._data["status"] = "active"
        env = _make_env()
        do = ConversationDO(state, env)

        await do.alarm()
        state.storage.setAlarm.assert_called_once()

    @pytest.mark.asyncio
    async def test_alarm_set_on_first_reply(self):
        """After first POST, alarm is set ~30 days in future."""
        state = _make_state()
        env = _make_env()
        do = ConversationDO(state, env)

        req = _make_request("POST", "/reply", {"role": "developer", "content": "hello", "triage_id": "evt-001"})
        await do.fetch(req)

        state.storage.setAlarm.assert_called_once()
        alarm_time = state.storage.setAlarm.call_args[0][0]
        # Should be ~30 days from Date.now() (1700000000000)
        expected = 1700000000000 + 30 * 24 * 60 * 60 * 1000
        assert alarm_time == expected

    @pytest.mark.asyncio
    async def test_alarm_archive_failure_reschedules_alarm(self):
        """alarm() with unarchived turns and DB failure \u2192 reschedules alarm for 1 min."""
        state = _make_state()
        state.storage._data["status"] = "closed"
        state.storage._data["turns"] = json.dumps([{"role": "developer", "content": "hi", "turn_index": 1}])
        state.storage._data["conversation_id"] = "evt-001"

        env = _make_env(db_run_side_effect=Exception("DB Error"))
        do = ConversationDO(state, env)

        await do.alarm()

        # Turn stays in DO state
        turns_left = json.loads(state.storage._data["turns"])
        assert len(turns_left) == 1

        # Alarm scheduled for 60s
        state.storage.setAlarm.assert_called_once()
        alarm_time = state.storage.setAlarm.call_args[0][0]
        assert alarm_time == 1700000000000 + 60000
