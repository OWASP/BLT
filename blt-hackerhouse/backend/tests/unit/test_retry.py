"""Retry/backoff tests."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

import httpx

from src.core.retry import RetryConfig, RetryableHTTPError, retry_async


@pytest.mark.asyncio
async def test_returns_on_first_success():
    op = AsyncMock(return_value="ok")
    result = await retry_async(op, description="test")
    assert result == "ok"
    assert op.call_count == 1


@pytest.mark.asyncio
async def test_retries_then_succeeds():
    op = AsyncMock(side_effect=[httpx.ConnectError("boom"), httpx.ConnectError("boom"), "ok"])
    cfg = RetryConfig(max_attempts=5, base_delay=0.0, jitter=0.0)
    result = await retry_async(op, config=cfg, description="flaky")
    assert result == "ok"
    assert op.call_count == 3


@pytest.mark.asyncio
async def test_4xx_is_terminal():
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(403, request=request)
    op = AsyncMock(side_effect=httpx.HTTPStatusError("forbidden", request=request, response=response))
    with pytest.raises(httpx.HTTPStatusError):
        await retry_async(op, description="forbidden")
    assert op.call_count == 1


@pytest.mark.asyncio
async def test_exhausts_then_raises_retryable():
    op = AsyncMock(side_effect=httpx.ConnectError("never works"))
    cfg = RetryConfig(max_attempts=3, base_delay=0.0, jitter=0.0)
    with pytest.raises(RetryableHTTPError):
        await retry_async(op, config=cfg, description="hopeless")
    assert op.call_count == 3