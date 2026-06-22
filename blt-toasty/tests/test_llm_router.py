"""
Tests for the LLM Router and LLM Client.

Covers:
    1. CF AI primary path (happy path, no fallback)
    2. Fallback to OpenAI after 3 consecutive CF AI failures
    3. Both providers fail → LLMUnavailableError
    4. Provider recovery via health check + reset
    5. Timeout behaviour (AbortController abort → fallback)
    6. Durable Object state persistence across calls
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.errors import LLMUnavailableError
from src.llm_router import (
    FAILURE_THRESHOLD,
    FALLBACK_PROVIDER,
    PRIMARY_PROVIDER,
    ProviderStatus,
    check_cf_ai_health,
    get_active_provider,
    mark_provider_failed,
    reset_provider,
)


# ---------------------------------------------------------------------------
# Helpers: mock Durable Object stub
# ---------------------------------------------------------------------------


class MockDOStorage:
    """In-memory mock of a Cloudflare Durable Object storage layer."""

    def __init__(self):
        self._store: dict[str, str] = {}

    async def get(self, key: str):
        return self._store.get(key)

    async def put(self, key: str, value: str):
        self._store[key] = value


class MockDOStub:
    """Mock Durable Object stub exposing a ``storage`` attribute."""

    def __init__(self):
        self.storage = MockDOStorage()


# ---------------------------------------------------------------------------
# Helpers: mock env objects
# ---------------------------------------------------------------------------


def _make_env(*, ai_result=None, ai_side_effect=None, openai_api_key="sk-test-key"):
    """Build a mock ``env`` object for testing.

    Args:
        ai_result: The value that ``env.AI.run()`` should return.
        ai_side_effect: An exception that ``env.AI.run()`` should raise.
        openai_api_key: The API key for OpenAI calls.
    """
    env = MagicMock()
    env.AI = MagicMock()
    env.AI.run = AsyncMock(return_value=ai_result, side_effect=ai_side_effect)
    env.OPENAI_API_KEY = openai_api_key
    env.OPENAI_BASE_URL = "https://api.openai.com/v1/chat/completions"
    return env


# ---------------------------------------------------------------------------
# Helpers: mock fetch for OpenAI
# ---------------------------------------------------------------------------


def _make_openai_fetch_mock(*, response_content="test response", status=200, ok=True):
    """Create a mock ``fetch`` function that returns an OpenAI-shaped response."""

    async def mock_fetch(url, options):
        resp = MagicMock()
        resp.ok = ok
        resp.status = status

        async def mock_text():
            return json.dumps({"error": {"message": "mock error"}})

        async def mock_json():
            return {"choices": [{"message": {"content": response_content}}]}

        resp.text = mock_text
        resp.json = mock_json
        return resp

    return AsyncMock(side_effect=mock_fetch)


def _make_abort_controller_cls():
    """Create a mock AbortController class for testing."""

    class MockAbortController:
        def __init__(self):
            self.signal = MagicMock()

        def abort(self):
            pass

        @classmethod
        def new(cls):
            return cls()

    return MockAbortController


# ---------------------------------------------------------------------------
# Tests: ProviderStatus dataclass
# ---------------------------------------------------------------------------


class TestProviderStatus:
    """Tests for the ProviderStatus dataclass serialisation."""

    def test_to_dict_roundtrip(self):
        status = ProviderStatus(provider="cf_ai", healthy=True, last_checked="2026-01-01T00:00:00", failure_count=2)
        data = status.to_dict()
        restored = ProviderStatus.from_dict(data)
        assert restored.provider == "cf_ai"
        assert restored.healthy is True
        assert restored.failure_count == 2

    def test_from_dict_defaults(self):
        status = ProviderStatus.from_dict({})
        assert status.provider == PRIMARY_PROVIDER
        assert status.healthy is True
        assert status.failure_count == 0


# ---------------------------------------------------------------------------
# Tests: LLM Router
# ---------------------------------------------------------------------------


class TestGetActiveProvider:
    """Tests for the get_active_provider function."""

    @pytest.mark.asyncio
    async def test_defaults_to_primary(self):
        """With no prior state, the primary provider should be selected."""
        do_stub = MockDOStub()
        provider = await get_active_provider(do_stub)
        assert provider == PRIMARY_PROVIDER

    @pytest.mark.asyncio
    async def test_switches_after_threshold_failures(self):
        """After FAILURE_THRESHOLD failures, router must switch to fallback."""
        do_stub = MockDOStub()

        for _ in range(FAILURE_THRESHOLD):
            await mark_provider_failed(do_stub, PRIMARY_PROVIDER)

        provider = await get_active_provider(do_stub)
        assert provider == FALLBACK_PROVIDER

    @pytest.mark.asyncio
    async def test_stays_primary_below_threshold(self):
        """Below FAILURE_THRESHOLD failures, router must stay on primary."""
        do_stub = MockDOStub()

        for _ in range(FAILURE_THRESHOLD - 1):
            await mark_provider_failed(do_stub, PRIMARY_PROVIDER)

        provider = await get_active_provider(do_stub)
        assert provider == PRIMARY_PROVIDER


class TestMarkProviderFailed:
    """Tests for the mark_provider_failed function."""

    @pytest.mark.asyncio
    async def test_increments_failure_count(self):
        do_stub = MockDOStub()
        await mark_provider_failed(do_stub, PRIMARY_PROVIDER)

        raw = await do_stub.storage.get(f"provider_status:{PRIMARY_PROVIDER}")
        data = json.loads(raw)
        assert data["failure_count"] == 1

    @pytest.mark.asyncio
    async def test_stores_fallback_reason_at_threshold(self):
        do_stub = MockDOStub()

        for _ in range(FAILURE_THRESHOLD):
            await mark_provider_failed(do_stub, PRIMARY_PROVIDER)

        reason = await do_stub.storage.get("last_fallback_reason")
        assert reason is not None
        assert "unhealthy" in reason

    @pytest.mark.asyncio
    async def test_marks_unhealthy_at_threshold(self):
        do_stub = MockDOStub()

        for _ in range(FAILURE_THRESHOLD):
            await mark_provider_failed(do_stub, PRIMARY_PROVIDER)

        raw = await do_stub.storage.get(f"provider_status:{PRIMARY_PROVIDER}")
        data = json.loads(raw)
        assert data["healthy"] is False


class TestResetProvider:
    """Tests for the reset_provider function."""

    @pytest.mark.asyncio
    async def test_resets_failure_count_to_zero(self):
        do_stub = MockDOStub()

        for _ in range(FAILURE_THRESHOLD):
            await mark_provider_failed(do_stub, PRIMARY_PROVIDER)

        # Provider should be on fallback now.
        assert await get_active_provider(do_stub) == FALLBACK_PROVIDER

        # Reset and verify recovery.
        await reset_provider(do_stub, PRIMARY_PROVIDER)
        assert await get_active_provider(do_stub) == PRIMARY_PROVIDER

    @pytest.mark.asyncio
    async def test_marks_healthy_after_reset(self):
        do_stub = MockDOStub()

        for _ in range(FAILURE_THRESHOLD):
            await mark_provider_failed(do_stub, PRIMARY_PROVIDER)

        await reset_provider(do_stub, PRIMARY_PROVIDER)
        raw = await do_stub.storage.get(f"provider_status:{PRIMARY_PROVIDER}")
        data = json.loads(raw)
        assert data["healthy"] is True
        assert data["failure_count"] == 0


class TestCheckCfAiHealth:
    """Tests for the check_cf_ai_health function."""

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self):
        env = _make_env(ai_result=MagicMock())
        result = await check_cf_ai_health(env)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        env = _make_env(ai_side_effect=RuntimeError("model unavailable"))
        result = await check_cf_ai_health(env)
        assert result is False

    @pytest.mark.asyncio
    async def test_never_raises(self):
        env = _make_env(ai_side_effect=Exception("catastrophic failure"))
        # Must not propagate; should return False.
        result = await check_cf_ai_health(env)
        assert result is False


# ---------------------------------------------------------------------------
# Tests: LLM Client — call_cf_ai
# ---------------------------------------------------------------------------


class TestCallCfAi:
    """Tests for the call_cf_ai function."""

    @pytest.mark.asyncio
    async def test_returns_response_text(self):
        from src.llm_client import call_cf_ai

        mock_result = MagicMock()
        mock_result.response = "Hello from CF AI"
        env = _make_env(ai_result=mock_result)

        response = await call_cf_ai([{"role": "user", "content": "Hi"}], env)
        assert response == "Hello from CF AI"

    @pytest.mark.asyncio
    async def test_raises_on_empty_response(self):
        from src.llm_client import call_cf_ai

        mock_result = MagicMock()
        mock_result.response = ""
        env = _make_env(ai_result=mock_result)

        with pytest.raises(ValueError, match="Empty response"):
            await call_cf_ai([{"role": "user", "content": "Hi"}], env)

    @pytest.mark.asyncio
    async def test_propagates_api_error(self):
        from src.llm_client import call_cf_ai

        env = _make_env(ai_side_effect=RuntimeError("CF AI down"))
        with pytest.raises(RuntimeError, match="CF AI down"):
            await call_cf_ai([{"role": "user", "content": "Hi"}], env)


# ---------------------------------------------------------------------------
# Tests: LLM Client — call_openai
# ---------------------------------------------------------------------------


class TestCallOpenai:
    """Tests for the call_openai function."""

    @pytest.mark.asyncio
    async def test_returns_response_content(self):
        from src.llm_client import call_openai

        env = _make_env()
        env._fetch_impl = _make_openai_fetch_mock(response_content="OpenAI says hello")
        env._abort_controller_cls = _make_abort_controller_cls()

        with (
            patch("src.llm_client.fetch", env._fetch_impl),
            patch("src.llm_client.AbortController", env._abort_controller_cls),
        ):
            response = await call_openai([{"role": "user", "content": "Hi"}], env)

        assert response == "OpenAI says hello"

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self):
        from src.llm_client import call_openai

        env = _make_env()
        env._fetch_impl = _make_openai_fetch_mock(status=500, ok=False)
        env._abort_controller_cls = _make_abort_controller_cls()

        with (
            patch("src.llm_client.fetch", env._fetch_impl),
            patch("src.llm_client.AbortController", env._abort_controller_cls),
        ):
            with pytest.raises(RuntimeError, match="HTTP 500"):
                await call_openai([{"role": "user", "content": "Hi"}], env)

    @pytest.mark.asyncio
    async def test_raises_on_missing_api_key(self):
        from src.llm_client import call_openai

        env = _make_env(openai_api_key="")
        env._fetch_impl = _make_openai_fetch_mock()
        env._abort_controller_cls = _make_abort_controller_cls()

        with (
            patch("src.llm_client.fetch", env._fetch_impl),
            patch("src.llm_client.AbortController", env._abort_controller_cls),
        ):
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                await call_openai([{"role": "user", "content": "Hi"}], env)

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self):
        from src.llm_client import call_openai

        async def fetch_abort(*args, **kwargs):
            raise Exception("The operation was aborted")

        env = _make_env()
        env._fetch_impl = AsyncMock(side_effect=fetch_abort)
        env._abort_controller_cls = _make_abort_controller_cls()

        with (
            patch("src.llm_client.fetch", env._fetch_impl),
            patch("src.llm_client.AbortController", env._abort_controller_cls),
        ):
            with pytest.raises(TimeoutError, match="timed out"):
                await call_openai([{"role": "user", "content": "Hi"}], env)


# ---------------------------------------------------------------------------
# Tests: LLM Client — call_llm (unified router entry point)
# ---------------------------------------------------------------------------


class TestCallLlm:
    """Tests for the call_llm unified entry point."""

    @pytest.mark.asyncio
    async def test_cf_ai_primary_path_no_fallback(self):
        """When CF AI succeeds, OpenAI should never be called."""
        from src.llm_client import call_llm

        mock_result = MagicMock()
        mock_result.response = "CF AI response"
        env = _make_env(ai_result=mock_result)
        do_stub = MockDOStub()

        messages = [{"role": "user", "content": "test"}]
        result = await call_llm(messages, env, do_stub)
        assert result == "CF AI response"
        # Verify CF AI was called.
        env.AI.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_to_openai_after_cf_ai_failure(self):
        """When CF AI fails, the router should fall back to OpenAI."""
        from src.llm_client import call_llm

        env = _make_env(ai_side_effect=RuntimeError("CF AI down"))
        env._fetch_impl = _make_openai_fetch_mock(response_content="OpenAI fallback")
        env._abort_controller_cls = _make_abort_controller_cls()
        do_stub = MockDOStub()

        messages = [{"role": "user", "content": "test"}]

        with (
            patch("src.llm_client.fetch", env._fetch_impl),
            patch("src.llm_client.AbortController", env._abort_controller_cls),
        ):
            result = await call_llm(messages, env, do_stub)

        assert result == "OpenAI fallback"

    @pytest.mark.asyncio
    async def test_both_providers_fail_raises_llm_unavailable(self):
        """When both providers fail, LLMUnavailableError must be raised."""
        from src.llm_client import call_llm

        env = _make_env(ai_side_effect=RuntimeError("CF AI down"))

        async def fetch_fail(*args, **kwargs):
            raise RuntimeError("OpenAI also down")

        env._fetch_impl = AsyncMock(side_effect=fetch_fail)
        env._abort_controller_cls = _make_abort_controller_cls()
        do_stub = MockDOStub()

        messages = [{"role": "user", "content": "test"}]

        with (
            patch("src.llm_client.fetch", env._fetch_impl),
            patch("src.llm_client.AbortController", env._abort_controller_cls),
        ):
            with pytest.raises(LLMUnavailableError) as exc_info:
                await call_llm(messages, env, do_stub)

        assert PRIMARY_PROVIDER in exc_info.value.providers_tried
        assert FALLBACK_PROVIDER in exc_info.value.providers_tried

    @pytest.mark.asyncio
    async def test_routes_to_openai_when_cf_ai_has_3_failures(self):
        """After 3 prior failures on CF AI, the router should go straight to OpenAI."""
        from src.llm_client import call_llm

        do_stub = MockDOStub()
        # Simulate 3 prior failures.
        for _ in range(FAILURE_THRESHOLD):
            await mark_provider_failed(do_stub, PRIMARY_PROVIDER)

        env = _make_env()  # CF AI configured but shouldn't be called.
        env._fetch_impl = _make_openai_fetch_mock(response_content="Direct OpenAI")
        env._abort_controller_cls = _make_abort_controller_cls()

        messages = [{"role": "user", "content": "test"}]

        with (
            patch("src.llm_client.fetch", env._fetch_impl),
            patch("src.llm_client.AbortController", env._abort_controller_cls),
        ):
            result = await call_llm(messages, env, do_stub)

        assert result == "Direct OpenAI"
        # CF AI should NOT have been called first since router selected OpenAI.
        env.AI.run.assert_not_called()


class TestProviderRecovery:
    """Tests for the full recovery cycle."""

    @pytest.mark.asyncio
    async def test_recovery_after_health_check(self):
        """After 3 failures, a successful health check + reset should restore CF AI."""
        do_stub = MockDOStub()

        # Drive CF AI into failure state.
        for _ in range(FAILURE_THRESHOLD):
            await mark_provider_failed(do_stub, PRIMARY_PROVIDER)

        assert await get_active_provider(do_stub) == FALLBACK_PROVIDER

        # Simulate a successful health check.
        env = _make_env(ai_result=MagicMock())
        health = await check_cf_ai_health(env)
        assert health is True

        # Reset the provider.
        await reset_provider(do_stub, PRIMARY_PROVIDER)
        assert await get_active_provider(do_stub) == PRIMARY_PROVIDER


class TestDOStatePersistence:
    """Tests that Durable Object state persists correctly across calls."""

    @pytest.mark.asyncio
    async def test_failure_count_persists_across_calls(self):
        """Each call to mark_provider_failed should increment persistently."""
        do_stub = MockDOStub()

        await mark_provider_failed(do_stub, PRIMARY_PROVIDER)
        await mark_provider_failed(do_stub, PRIMARY_PROVIDER)

        raw = await do_stub.storage.get(f"provider_status:{PRIMARY_PROVIDER}")
        data = json.loads(raw)
        assert data["failure_count"] == 2

    @pytest.mark.asyncio
    async def test_independent_provider_tracking(self):
        """Failures on one provider should not affect the other."""
        do_stub = MockDOStub()

        await mark_provider_failed(do_stub, PRIMARY_PROVIDER)
        await mark_provider_failed(do_stub, PRIMARY_PROVIDER)

        raw_primary = await do_stub.storage.get(f"provider_status:{PRIMARY_PROVIDER}")
        raw_fallback = await do_stub.storage.get(f"provider_status:{FALLBACK_PROVIDER}")

        assert json.loads(raw_primary)["failure_count"] == 2
        assert raw_fallback is None  # Never touched.
