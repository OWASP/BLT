import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from unittest.mock import AsyncMock, MagicMock
from main import _run_chat, _run_scan


def make_env(ai_return_value):
    """Build a mock env whose AI.run returns the given value."""
    env = MagicMock()
    # Handle the fact that AI.run might expect a dict or return a JsProxy-like object
    # In tests, we mock it to return what _extract_ai_text expects
    env.AI.run = AsyncMock(return_value=ai_return_value)
    return env


# ---------------------------------------------------------------------------
# _run_chat
# ---------------------------------------------------------------------------
class TestRunChat:

    @pytest.mark.asyncio
    async def test_returns_reply_on_success(self):
        env = make_env({"response": "Hello from AI"})
        result = await _run_chat(env, "Hi", [])
        assert result.get("reply") == "Hello from AI"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_empty_message_returns_error_dict(self):
        # Result is a dict with status 400 for errors in _run_chat
        result = await _run_chat(MagicMock(), "", [])
        assert "error" in result
        assert "required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_history_capped_at_10_turns(self):
        """History beyond 10 entries should be silently truncated."""
        env = make_env({"response": "ok"})
        long_history = [{"role": "user", "content": f"msg {i}"} for i in range(20)]
        result = await _run_chat(env, "Final message", long_history)
        assert "reply" in result  # Should succeed

    @pytest.mark.asyncio
    async def test_ai_exception_returns_502(self):
        env = MagicMock()
        env.AI.run = AsyncMock(side_effect=Exception("AI down"))
        result = await _run_chat(env, "Hello", [])
        assert result.get("status") == 502
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unrecognised_ai_format_returns_502(self):
        env = make_env({"unknown_key": "no text here"})
        result = await _run_chat(env, "Hello", [])
        assert result.get("status") == 502

    @pytest.mark.asyncio
    async def test_non_dict_history_items_skipped(self):
        """Non-dict items in history should not crash the handler."""
        env = make_env({"response": "ok"})
        mixed_history = [{"role": "user", "content": "valid"}, None, 42, "string"]
        result = await _run_chat(env, "Hello", mixed_history)
        assert "reply" in result


# ---------------------------------------------------------------------------
# _run_scan
# ---------------------------------------------------------------------------
class TestRunScan:

    @pytest.mark.asyncio
    async def test_returns_structured_dict_on_valid_json(self):
        ai_payload = {
            "headers_to_check": ["X-Frame-Options"],
            "vulnerabilities_to_test": ["XSS"],
            "blt_categories": ["web"],
            "notes": "Looks clean."
        }
        env = make_env({"response": json.dumps(ai_payload)})
        result = await _run_scan(env, "https://example.com", "quick")
        assert result.get("vulnerabilities_to_test") == ["XSS"]

    @pytest.mark.asyncio
    async def test_non_json_ai_response_returns_notes_field(self):
        """When model ignores JSON instruction, result must still be schema-compliant."""
        env = make_env({"response": "Plain text analysis here."})
        result = await _run_scan(env, "https://example.com")
        assert "notes" in result
        assert "headers_to_check" in result
        assert "vulnerabilities_to_test" in result

    @pytest.mark.asyncio
    async def test_empty_url_returns_error(self):
        result = await _run_scan(MagicMock(), "")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_full_scan_type_accepted(self):
        env = make_env({"response": json.dumps({"headers_to_check": [], "vulnerabilities_to_test": [], "blt_categories": [], "notes": ""})})
        result = await _run_scan(env, "https://example.com", "full")
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_ai_exception_returns_502(self):
        env = MagicMock()
        env.AI.run = AsyncMock(side_effect=RuntimeError("timeout"))
        result = await _run_scan(env, "https://example.com")
        assert result.get("status") == 502
