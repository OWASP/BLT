"""
Tests for shared static API-key validation.
"""

import json

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
        ("GET", "https://api.example.com/health"),
        ("GET", "https://api.example.com/v2/health"),
    ],
)
def test_public_requests_do_not_require_api_key(method, url):
    assert is_api_key_required(method, url) is False
    response = validate_api_key_request(MockRequest(method=method, url=url), EmptyEnv())
    assert response is None


@pytest.mark.parametrize(
    "url",
    [
        "https://api.example.com/bugs",
        "https://api.example.com/routes",
        "https://api.example.com/auth/signin",
        "https://api.example.com/v2/bugs",
    ],
)
def test_protected_routes_require_api_key(url):
    assert is_api_key_required("GET", url) is True


def test_missing_api_key_returns_401():
    response = validate_api_key_request(MockRequest(), MockEnv())

    assert response.status == 401
    data = _response_data(response)
    assert data["message"] == "Missing API key"


def test_invalid_api_key_returns_401():
    request = MockRequest(headers={API_KEY_HEADER: "wrong-key"})

    response = validate_api_key_request(request, MockEnv())

    assert response.status == 401
    data = _response_data(response)
    assert data["message"] == "Invalid API key"


def test_valid_api_key_allows_request():
    request = MockRequest(headers={API_KEY_HEADER: "docs-static-key"})

    response = validate_api_key_request(request, MockEnv())

    assert response is None


def test_public_static_api_key_allows_request_without_env():
    request = MockRequest(headers={API_KEY_HEADER: PUBLIC_BLT_API_KEY})

    response = validate_api_key_request(request, EmptyEnv())

    assert response is None


def test_api_key_header_is_case_insensitive():
    request = MockRequest(headers={"x-blt-api-key": "docs-static-key"})

    response = validate_api_key_request(request, MockEnv())

    assert response is None


def test_plain_dict_api_key_header_is_case_insensitive():
    request = MockRequest()
    request.headers = {"x-blt-api-key": "docs-static-key"}

    response = validate_api_key_request(request, MockEnv())

    assert response is None


def test_env_api_key_remains_accepted_for_local_overrides():
    request = MockRequest(headers={API_KEY_HEADER: "docs-static-key"})

    response = validate_api_key_request(request, MockEnv())

    assert response is None
