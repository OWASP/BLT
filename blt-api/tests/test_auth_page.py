"""Tests for the legacy browser auth route."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from handlers.auth_page import handle_auth_page  # noqa: E402


class MockRequest:
    def __init__(self, url="https://api.example.com/auth"):
        self.url = url
        self.method = "GET"


class MockEnv:
    pass


@pytest.mark.asyncio
async def test_auth_page_returns_html():
    response = await handle_auth_page(MockRequest(), MockEnv(), {}, {}, "/auth")

    assert response.status == 200
    assert "text/html" in response.headers["Content-Type"]
    assert "authModalSigninForm" in response.body
    assert "authModalSignupForm" in response.body


@pytest.mark.asyncio
async def test_auth_page_uses_api_auth_routes():
    response = await handle_auth_page(MockRequest(), MockEnv(), {}, {}, "/auth")

    assert "/api/auth/signin" in response.body
    assert "/api/auth/signup" in response.body
    assert "/api/auth/verify-email" in response.body
    assert "/api/auth/verify-local" in response.body
    assert "/api/auth/api-keys" in response.body
    assert "baseUrl + '/auth/signin'" not in response.body


@pytest.mark.asyncio
async def test_auth_page_uses_homepage_modal_instead_of_standalone_auth_page():
    response = await handle_auth_page(MockRequest(), MockEnv(), {}, {}, "/auth")

    assert "authStatus" not in response.body
    assert "modalLocalDevVerifyForm" in response.body
    assert "modalLocalVerifyCode" in response.body
    assert "isLocalDevelopment" in response.body
    assert "body.dev_otp" not in response.body
