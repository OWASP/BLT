"""Tests for the GitLab linker.

Covers:
    1. Post comment success (201)
    2. Comment body format (contains issue number, confidence, rationale)
    3. Rate limit backoff (RateLimit-Remaining < 100)
    4. Rate limit OK (RateLimit-Remaining >= 100)
    5. Non-201 raises GitLabAPIError
    6. Add label success (200)
    7. Add label rate limit backoff
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.errors import GitLabAPIError
from src.gitlab_linker import (
    GITLAB_API_BASE,
    add_duplicate_label,
    post_duplicate_comment,
)


@pytest.fixture(autouse=True)
def clear_js_mocks():
    """Clear polluted js module imports from other tests so env mocks are used."""
    from unittest.mock import patch

    with patch("src.gitlab_linker.fetch", None), patch("src.gitlab_linker.AbortController", None):
        yield


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


def _make_gitlab_fetch_mock(*, status=201, ok=True, rate_limit_remaining=500, response_body=None):
    """Create a mock ``fetch`` that returns a GitLab-shaped response.

    Args:
        status: HTTP status code to return.
        ok: Whether the response is considered OK.
        rate_limit_remaining: Value for the RateLimit-Remaining header.
        response_body: Optional response body dict.
    """
    if response_body is None:
        response_body = {"id": 1, "body": "mock comment"}

    async def mock_fetch(url, options):
        resp = MagicMock()
        resp.ok = ok
        resp.status = status
        resp.headers = MagicMock()
        resp.headers.get = MagicMock(
            side_effect=lambda key: str(rate_limit_remaining) if key == "RateLimit-Remaining" else None
        )

        async def mock_text():
            return json.dumps(response_body)

        async def mock_json():
            return response_body

        resp.text = mock_text
        resp.json = mock_json
        return resp

    return AsyncMock(side_effect=mock_fetch)


def _make_env(*, fetch_mock=None, rate_limit_remaining=500):
    """Build a mock env with GitLab API configuration."""
    env = MagicMock()
    env._fetch_impl = fetch_mock or _make_gitlab_fetch_mock(rate_limit_remaining=rate_limit_remaining)
    env._abort_controller_cls = _make_abort_controller_cls()
    return env


# ---------------------------------------------------------------------------
# Tests: post_duplicate_comment
# ---------------------------------------------------------------------------


class TestPostDuplicateComment:
    """Tests for the post_duplicate_comment function."""

    @pytest.mark.asyncio
    async def test_post_comment_success(self):
        """Successful 201 response returns True."""
        env = _make_env()

        result = await post_duplicate_comment(
            access_token="glpat-test-token",
            project_id=123,
            issue_iid=42,
            duplicate_of_iid=10,
            confidence=0.92,
            rationale="Same XSS in login form.",
            env=env,
        )

        assert result is True
        env._fetch_impl.assert_awaited_once()

        # Verify correct URL
        call_args = env._fetch_impl.call_args
        url = call_args[0][0]
        assert f"{GITLAB_API_BASE}/projects/123/issues/42/notes" == url

    @pytest.mark.asyncio
    async def test_post_comment_body_format(self):
        """Comment body contains issue number, confidence percentage, and rationale."""
        env = _make_env()

        await post_duplicate_comment(
            access_token="glpat-test-token",
            project_id=123,
            issue_iid=42,
            duplicate_of_iid=10,
            confidence=0.92,
            rationale="Same XSS in login form.",
            env=env,
        )

        call_args = env._fetch_impl.call_args
        options = call_args[0][1]
        body = json.loads(options["body"])
        comment = body["body"]

        assert "#10" in comment
        assert "92%" in comment
        assert "Same XSS in login form." in comment
        assert "Toasty Triage" in comment

    @pytest.mark.asyncio
    async def test_rate_limit_backoff(self, caplog):
        """When RateLimit-Remaining < 100, logs a warning and returns True."""
        fetch_mock = _make_gitlab_fetch_mock(status=201, rate_limit_remaining=50)
        env = _make_env(fetch_mock=fetch_mock)

        result = await post_duplicate_comment(
            access_token="glpat-test-token",
            project_id=123,
            issue_iid=42,
            duplicate_of_iid=10,
            confidence=0.92,
            rationale="Same issue.",
            env=env,
        )

        assert result is True
        assert "Rate-limit quota low after posting duplicate comment" in caplog.text

    @pytest.mark.asyncio
    async def test_rate_limit_ok(self):
        """When RateLimit-Remaining >= 100, proceeds normally."""
        fetch_mock = _make_gitlab_fetch_mock(status=201, rate_limit_remaining=500)
        env = _make_env(fetch_mock=fetch_mock)

        result = await post_duplicate_comment(
            access_token="glpat-test-token",
            project_id=123,
            issue_iid=42,
            duplicate_of_iid=10,
            confidence=0.92,
            rationale="Same issue.",
            env=env,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_non_201_raises_error(self):
        """HTTP 403 raises GitLabAPIError with correct status_code."""
        fetch_mock = _make_gitlab_fetch_mock(status=403, ok=False, response_body={"error": "forbidden"})
        env = _make_env(fetch_mock=fetch_mock)

        with pytest.raises(GitLabAPIError) as exc_info:
            await post_duplicate_comment(
                access_token="glpat-test-token",
                project_id=123,
                issue_iid=42,
                duplicate_of_iid=10,
                confidence=0.92,
                rationale="Same issue.",
                env=env,
            )

        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Tests: add_duplicate_label
# ---------------------------------------------------------------------------


class TestAddDuplicateLabel:
    """Tests for the add_duplicate_label function."""

    @pytest.mark.asyncio
    async def test_add_label_success(self):
        """Successful 200 response returns True."""
        fetch_mock = _make_gitlab_fetch_mock(status=200)
        env = _make_env(fetch_mock=fetch_mock)

        result = await add_duplicate_label(
            access_token="glpat-test-token",
            project_id=123,
            issue_iid=42,
            env=env,
        )

        assert result is True

        # Verify PUT method and correct URL
        call_args = env._fetch_impl.call_args
        url = call_args[0][0]
        options = call_args[0][1]
        assert f"{GITLAB_API_BASE}/projects/123/issues/42" == url
        assert options["method"] == "PUT"

        # Verify body contains add_labels
        body = json.loads(options["body"])
        assert body["add_labels"] == "possible-duplicate"

    @pytest.mark.asyncio
    async def test_add_label_rate_limit_backoff(self, caplog):
        """When RateLimit-Remaining < 100, logs a warning and returns True."""
        fetch_mock = _make_gitlab_fetch_mock(status=200, rate_limit_remaining=50)
        env = _make_env(fetch_mock=fetch_mock)

        result = await add_duplicate_label(
            access_token="glpat-test-token",
            project_id=123,
            issue_iid=42,
            env=env,
        )

        assert result is True
        assert "Rate-limit quota low after adding label" in caplog.text

    @pytest.mark.asyncio
    async def test_add_label_non_200_raises_error(self):
        """HTTP 403 raises GitLabAPIError with correct status_code."""
        fetch_mock = _make_gitlab_fetch_mock(status=403, ok=False, response_body={"error": "forbidden"})
        env = _make_env(fetch_mock=fetch_mock)

        with pytest.raises(GitLabAPIError) as exc_info:
            await add_duplicate_label(
                access_token="glpat-test-token",
                project_id=123,
                issue_iid=42,
                env=env,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_network_timeout_mapped_to_408(self):
        """Abort/Timeout exception maps to 408."""

        async def timeout_fetch(url, options):
            raise Exception("The operation was aborted.")

        env = _make_env(fetch_mock=AsyncMock(side_effect=timeout_fetch))

        with pytest.raises(GitLabAPIError) as exc_info:
            await add_duplicate_label(access_token="test", project_id=1, issue_iid=1, env=env)
        assert exc_info.value.status_code == 408

    @pytest.mark.asyncio
    async def test_network_error_mapped_to_503(self):
        """Generic network exception maps to 503."""

        async def network_error_fetch(url, options):
            raise Exception("Connection refused")

        env = _make_env(fetch_mock=AsyncMock(side_effect=network_error_fetch))

        with pytest.raises(GitLabAPIError) as exc_info:
            await add_duplicate_label(access_token="test", project_id=1, issue_iid=1, env=env)
        assert exc_info.value.status_code == 503
