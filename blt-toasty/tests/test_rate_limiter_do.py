import json
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Provide a basic mock for js before importing RateLimiterDO
js_mock = MagicMock()
Date = MagicMock()
Date.now.return_value = 1000000
js_mock.Date = Date
sys.modules["js"] = js_mock

from src.durable_objects import RateLimiterDO


class MockResponse:
    def __init__(self, body, status):
        self._body = body
        self.status = status

    async def text(self):
        return self._body


def mock_json_response(data, status=200):
    return MockResponse(json.dumps(data), status)


class TestRateLimiterDO:
    @pytest.fixture
    def mock_env(self):
        return MagicMock()

    @pytest.fixture
    def mock_state(self):
        state = MagicMock()
        state.storage = AsyncMock()
        return state

    @pytest.mark.asyncio
    @patch("src.durable_objects._json_response", side_effect=mock_json_response)
    async def test_missing_agent_id(self, mock_json_resp, mock_env, mock_state):
        do = RateLimiterDO(mock_state, mock_env)
        req = AsyncMock()
        req.text = AsyncMock(return_value="{}")

        resp = await do.fetch(req)
        assert resp.status == 400
        body = json.loads(await resp.text())
        assert "missing agent_id" in body["error"]

    @pytest.mark.asyncio
    @patch("src.durable_objects._json_response", side_effect=mock_json_response)
    @patch("src.durable_objects.Date.now", return_value=1000000)
    async def test_first_request_allowed(self, mock_date, mock_json_resp, mock_env, mock_state):
        do = RateLimiterDO(mock_state, mock_env)
        req = AsyncMock()
        req.text = AsyncMock(return_value='{"agent_id": "agent-1"}')

        mock_state.storage.get = AsyncMock(return_value=None)

        resp = await do.fetch(req)
        assert resp.status == 200
        body = json.loads(await resp.text())
        assert body["allowed"] is True
        assert body["remaining"] == 99

        mock_state.storage.put.assert_called_once()
        put_args = mock_state.storage.put.call_args[0]
        assert put_args[0] == "rl:agent-1"
        saved = json.loads(put_args[1])
        assert saved["count"] == 1

    @pytest.mark.asyncio
    @patch("src.durable_objects._json_response", side_effect=mock_json_response)
    @patch("src.durable_objects.Date.now", return_value=1000000)
    async def test_rate_limit_exceeded(self, mock_date, mock_json_resp, mock_env, mock_state):
        do = RateLimiterDO(mock_state, mock_env)
        req = AsyncMock()
        req.text = AsyncMock(return_value='{"agent_id": "agent-1"}')

        # Existing record with 100 count within the same minute
        mock_state.storage.get = AsyncMock(return_value=json.dumps({"count": 100, "window_start": 1000000}))

        resp = await do.fetch(req)
        assert resp.status == 429
        body = json.loads(await resp.text())
        assert body["error"] == "rate_limit_exceeded"

    @pytest.mark.asyncio
    @patch("src.durable_objects._json_response", side_effect=mock_json_response)
    @patch("src.durable_objects.Date.now", return_value=1000000)
    async def test_window_reset(self, mock_date, mock_json_resp, mock_env, mock_state):
        do = RateLimiterDO(mock_state, mock_env)
        req = AsyncMock()
        req.text = AsyncMock(return_value='{"agent_id": "agent-1"}')

        # Existing record with 100 count but older than 1 minute
        mock_state.storage.get = AsyncMock(return_value=json.dumps({"count": 100, "window_start": 1000000 - 60001}))

        resp = await do.fetch(req)
        assert resp.status == 200
        body = json.loads(await resp.text())
        assert body["allowed"] is True
        assert body["remaining"] == 99
