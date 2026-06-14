"""
Tests for shared static API-key validation.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libs.api_key import API_KEY_HEADER, PUBLIC_BLT_API_KEY, is_api_key_required, validate_api_key_request


class MockHeaders(dict):
    """Case-insensitive enough header map for tests."""

    def get(self, key, default=None):
        for existing_key, value in self.items():
            if existing_key.lower() == key.lower():
                return value
        return default


class MockRequest:
    def __init__(self, method="GET", url="https://api.example.com/bugs", headers=None):
        self.method = method
        self.url = url
        self.headers = MockHeaders(headers or {})


class MockEnv:
    BLT_API_KEY = "docs-static-key"


class EmptyEnv:
    pass


def _response_data(response):
    if hasattr(response, "body"):
        return json.loads(response.body)
    return response.get("data", {})


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("OPTIONS", "https://api.example.com/bugs"),
        ("GET", "https://api.example.com"),
        ("GET", "https://api.example.com/"),
        ("GET", "https://api.example.com/v2"),
        ("GET", "https://api.example.com/auth"),
        ("GET", "https://api.example.com/v2/auth"),
        ("GET", "https://api.example.com/dashboard"),
        ("GET", "https://api.example.com/blt-api.png"),
        ("GET", "https://api.example.com/llm.txt"),
        ("GET", "https://api.example.com/health"),
        ("GET", "https://api.example.com/v2/health"),
    ],
)
@pytest.mark.asyncio
async def test_public_requests_do_not_require_api_key(method, url):
    assert is_api_key_required(method, url) is False
    response = await validate_api_key_request(MockRequest(method=method, url=url), EmptyEnv())
    assert response is None


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("POST", "https://api.example.com/auth/signup"),
        ("POST", "https://api.example.com/auth/signin"),
        ("GET", "https://api.example.com/auth/verify-email?token=abc"),
        ("POST", "https://api.example.com/auth/verify-local"),
        ("POST", "https://api.example.com/api/auth/signup"),
        ("POST", "https://api.example.com/api/auth/signin"),
        ("GET", "https://api.example.com/api/auth/verify-email?token=abc"),
        ("POST", "https://api.example.com/api/auth/verify-local"),
        ("POST", "https://api.example.com/v2/auth/signup"),
        ("POST", "https://api.example.com/v2/auth/signin"),
        ("GET", "https://api.example.com/v2/auth/verify-email?token=abc"),
        ("POST", "https://api.example.com/v2/auth/verify-local"),
        ("GET", "https://api.example.com/auth/api-keys"),
        ("POST", "https://api.example.com/auth/api-keys"),
        ("DELETE", "https://api.example.com/auth/api-keys/1"),
        ("GET", "https://api.example.com/api/auth/api-keys"),
        ("POST", "https://api.example.com/api/auth/api-keys"),
        ("DELETE", "https://api.example.com/api/auth/api-keys/1"),
    ],
)
def test_auth_requests_do_not_require_api_key(method, url):
    assert is_api_key_required(method, url) is False


@pytest.mark.parametrize(
    "url",
    [
        "https://api.example.com/bugs",
        "https://api.example.com/routes",
        "https://api.example.com/dashboard.html",
        "https://api.example.com/v2/dashboard",
        "https://api.example.com/v2/dashboard.html",
        "https://api.example.com/v2/bugs",
    ],
)
def test_protected_routes_require_api_key(url):
    assert is_api_key_required("GET", url) is True


@pytest.mark.asyncio
async def test_missing_api_key_returns_401():
    response = await validate_api_key_request(MockRequest(), MockEnv())

    assert response.status == 401
    data = _response_data(response)
    assert data["message"] == "Missing API key"


@pytest.mark.asyncio
async def test_invalid_api_key_returns_401():
    request = MockRequest(headers={API_KEY_HEADER: "wrong-key"})

    response = await validate_api_key_request(request, MockEnv())

    assert response.status == 401
    data = _response_data(response)
    assert data["message"] == "Invalid API key"


@pytest.mark.asyncio
async def test_valid_api_key_allows_request():
    request = MockRequest(headers={API_KEY_HEADER: "docs-static-key"})

    response = await validate_api_key_request(request, MockEnv())

    assert response is None


@pytest.mark.asyncio
async def test_public_static_api_key_allows_request_without_env():
    request = MockRequest(headers={API_KEY_HEADER: PUBLIC_BLT_API_KEY})

    response = await validate_api_key_request(request, EmptyEnv())

    assert response is None


@pytest.mark.asyncio
async def test_api_key_header_is_case_insensitive():
    request = MockRequest(headers={"x-blt-api-key": "docs-static-key"})

    response = await validate_api_key_request(request, MockEnv())

    assert response is None


@pytest.mark.asyncio
async def test_plain_dict_api_key_header_is_case_insensitive():
    request = MockRequest()
    request.headers = {"x-blt-api-key": "docs-static-key"}

    response = await validate_api_key_request(request, MockEnv())

    assert response is None


@pytest.mark.asyncio
async def test_env_api_key_remains_accepted_for_local_overrides():
    request = MockRequest(headers={API_KEY_HEADER: "docs-static-key"})

    response = await validate_api_key_request(request, MockEnv())

    assert response is None


@pytest.mark.asyncio
async def test_dynamic_user_api_key_allows_request_and_attaches_user_context():
    request = MockRequest(headers={API_KEY_HEADER: "blt_live_testsecret"})
    mock_model = MagicMock()
    mock_qs = MagicMock()
    mock_qs.filter.return_value = mock_qs
    mock_qs.first = AsyncMock(return_value={"id": 7, "user_id": 42, "is_active": 1})
    mock_qs.update = AsyncMock()
    mock_model.objects.return_value = mock_qs

    with patch("libs.api_key.UserApiKey", mock_model), \
         patch("libs.api_key.hash_user_api_key", return_value="key-hash"):
        response = await validate_api_key_request(request, MockEnv(), MagicMock())

    assert response is None
    mock_qs.filter.assert_called_once_with(key_hash="key-hash", is_active=True)
    mock_qs.update.assert_awaited_once()
    assert request.user_id == 42
    assert request.api_key_id == 7


@pytest.mark.asyncio
async def test_dynamic_user_api_key_rejects_unknown_hash():
    request = MockRequest(headers={API_KEY_HEADER: "blt_live_missing"})
    mock_model = MagicMock()
    mock_qs = MagicMock()
    mock_qs.filter.return_value = mock_qs
    mock_qs.first = AsyncMock(return_value=None)
    mock_model.objects.return_value = mock_qs

    with patch("libs.api_key.UserApiKey", mock_model), \
         patch("libs.api_key.hash_user_api_key", return_value="missing-hash"):
        response = await validate_api_key_request(request, MockEnv(), MagicMock())

    assert response.status == 401
    assert _response_data(response)["message"] == "Invalid API key"
