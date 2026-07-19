"""Tests for the embedding client.

Covers:
    1. Successful 384-dimension embedding retrieval
    2. Timeout → EmbeddingServiceError (status_code=408)
    3. Non-200 response → EmbeddingServiceError
    4. Wrong dimensions → EmbeddingServiceError (status_code=500)
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.embedding_client import EMBEDDING_DIMENSIONS, get_embedding
from src.errors import EmbeddingServiceError


# ---------------------------------------------------------------------------
# Helpers: mock objects
# ---------------------------------------------------------------------------


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


def _make_sidecar_fetch_mock(*, embeddings=None, status=200, ok=True):
    """Create a mock ``fetch`` that returns a FastEmbed sidecar-shaped response."""
    if embeddings is None:
        embeddings = [[0.1] * EMBEDDING_DIMENSIONS]

    async def mock_fetch(url, options):
        resp = MagicMock()
        resp.ok = ok
        resp.status = status

        async def mock_text():
            return json.dumps({"detail": "mock error"})

        async def mock_json():
            return {
                "embeddings": embeddings,
                "model": "sentence-transformers/all-MiniLM-L6-v2",
                "dimensions": EMBEDDING_DIMENSIONS,
            }

        resp.text = mock_text
        resp.json = mock_json
        return resp

    return AsyncMock(side_effect=mock_fetch)


def _make_env(*, fetch_mock=None, sidecar_url="http://localhost:5003"):
    """Build a mock env with FastEmbed sidecar configuration."""
    env = MagicMock()
    env.FASTEMBED_URL = sidecar_url
    env._fetch_impl = fetch_mock or _make_sidecar_fetch_mock()
    env._abort_controller_cls = _make_abort_controller_cls()
    return env


# ---------------------------------------------------------------------------
# Tests: get_embedding
# ---------------------------------------------------------------------------


class TestGetEmbedding:
    """Tests for the get_embedding function."""

    @pytest.mark.asyncio
    async def test_returns_384_dimensions(self):
        """Successful call returns a list of exactly 384 floats."""
        env = _make_env()
        result = await get_embedding("test redacted text", env)
        assert isinstance(result, list)
        assert len(result) == EMBEDDING_DIMENSIONS
        assert all(isinstance(v, float) for v in result)

    @pytest.mark.asyncio
    async def test_timeout_raises_embedding_service_error(self):
        """AbortController abort triggers EmbeddingServiceError with 408."""

        async def aborting_fetch(url, options):
            raise Exception("The operation was aborted")

        env = _make_env(fetch_mock=AsyncMock(side_effect=aborting_fetch))
        with pytest.raises(EmbeddingServiceError) as exc_info:
            await get_embedding("test", env)
        assert exc_info.value.status_code == 408
        assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_non_200_raises_embedding_service_error(self):
        """Non-200 HTTP response raises EmbeddingServiceError with status code."""
        env = _make_env(fetch_mock=_make_sidecar_fetch_mock(status=500, ok=False))
        with pytest.raises(EmbeddingServiceError) as exc_info:
            await get_embedding("test", env)
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_wrong_dimensions_raises_embedding_service_error(self):
        """Response with wrong number of dimensions raises EmbeddingServiceError."""
        wrong_dims = [[0.1] * 256]  # 256 instead of 384
        env = _make_env(fetch_mock=_make_sidecar_fetch_mock(embeddings=wrong_dims))
        with pytest.raises(EmbeddingServiceError) as exc_info:
            await get_embedding("test", env)
        assert exc_info.value.status_code == 500
        assert "256" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_fastembed_url_raises(self):
        """Missing FASTEMBED_URL raises EmbeddingServiceError with 503."""
        env = _make_env(sidecar_url=None)
        env.FASTEMBED_URL = None
        with pytest.raises(EmbeddingServiceError) as exc_info:
            await get_embedding("test", env)
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_network_error_raises_embedding_service_error(self):
        """Generic network error raises EmbeddingServiceError with 503."""

        async def network_error_fetch(url, options):
            raise ConnectionError("Connection refused")

        env = _make_env(fetch_mock=AsyncMock(side_effect=network_error_fetch))
        with pytest.raises(EmbeddingServiceError) as exc_info:
            await get_embedding("test", env)
        assert exc_info.value.status_code == 503
