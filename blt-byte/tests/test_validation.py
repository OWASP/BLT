import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from unittest.mock import AsyncMock, MagicMock
from main import handle_chat, handle_scan, handle_mcp


def make_mock_request(body_dict, headers=None, method="POST"):
    """
    Build a mock request object that returns a body string
    via .text() to simulate how Cloudflare Workers requests behave.
    """
    req = MagicMock()
    req.method = method
    req.text = AsyncMock(return_value=json.dumps(body_dict))
    req.headers = headers or {}
    return req


class TestEndpointValidation:

    # --- Chat Endpoint ---
    @pytest.mark.asyncio
    async def test_chat_rejects_missing_message(self):
        req = make_mock_request({})
        response = await handle_chat(req, MagicMock())
        assert response.status == 400
        assert b"required" in response.body.lower()

    @pytest.mark.asyncio
    async def test_chat_rejects_oversized_message(self):
        # Limit is 2000
        req = make_mock_request({"message": "A" * 2001})
        response = await handle_chat(req, MagicMock())
        assert response.status == 400
        assert b"long" in response.body.lower()

    @pytest.mark.asyncio
    async def test_chat_rejects_non_dict_payload(self):
        # We simulate this slightly differently because handle_chat expects json.loads
        req = MagicMock()
        req.text = AsyncMock(return_value="[1, 2, 3]")
        response = await handle_chat(req, MagicMock())
        assert response.status == 400
        assert b"object" in response.body.lower()

    # --- Scan Endpoint ---
    @pytest.mark.asyncio
    async def test_scan_rejects_missing_url(self):
        req = make_mock_request({})
        response = await handle_scan(req, MagicMock())
        assert response.status == 400
        assert b"required" in response.body.lower()

    @pytest.mark.asyncio
    async def test_scan_rejects_oversized_url(self):
        # Limit is 500
        req = make_mock_request({"url": "http://" + "A" * 501})
        response = await handle_scan(req, MagicMock())
        assert response.status == 400
        assert b"long" in response.body.lower()

    @pytest.mark.asyncio
    async def test_scan_rejects_invalid_type(self):
        req = make_mock_request({"url": "example.com", "scan_type": "mega"})
        response = await handle_scan(req, MagicMock())
        assert response.status == 400
        assert b"scan_type" in response.body.lower()

    # --- MCP Endpoint ---
    @pytest.mark.asyncio
    async def test_mcp_rejects_unknown_tool(self):
        req = make_mock_request({"tool": "hack_the_world", "params": {}})
        response = await handle_mcp(req, MagicMock())
        assert response.status == 404

    @pytest.mark.asyncio
    async def test_mcp_chat_validates_message_length(self):
        req = make_mock_request({
            "tool": "chat",
            "params": {"message": "X" * 2001}
        })
        response = await handle_mcp(req, MagicMock())
        assert response.status == 400
        assert b"long" in response.body.lower()

    @pytest.mark.asyncio
    async def test_mcp_scan_validates_url_length(self):
        req = make_mock_request({
            "tool": "scan_url",
            "params": {"url": "H" * 501}
        })
        response = await handle_mcp(req, MagicMock())
        assert response.status == 400
        assert b"long" in response.body.lower()

    @pytest.mark.asyncio
    async def test_mcp_rejects_non_dict_params(self):
        req = make_mock_request({"tool": "chat", "params": "string"})
        response = await handle_mcp(req, MagicMock())
        assert response.status == 400
        assert b"object" in response.body.lower()
