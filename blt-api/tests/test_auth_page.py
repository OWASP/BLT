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
async def test_auth_page_returns_dashboard_html():
    response = await handle_auth_page(MockRequest(), MockEnv(), {}, {}, "/auth")

    assert response.status == 200
    assert "text/html" in response.headers["Content-Type"]
    assert "BLT API" in response.body
    assert "Try It" in response.body
    assert "profileModal" in response.body
    assert "apiKeyList" in response.body


@pytest.mark.asyncio
async def test_auth_page_exposes_auth_routes_in_dashboard_catalog():
    response = await handle_auth_page(MockRequest(), MockEnv(), {}, {}, "/auth")

    assert "/v2/auth/signin" in response.body
    assert "/v2/auth/signup" in response.body
    assert "/v2/auth/verify-email" in response.body
    assert "Create account" in response.body
    assert "Sign in" in response.body


@pytest.mark.asyncio
async def test_auth_page_uses_dashboard_instead_of_removed_modal_ui():
    response = await handle_auth_page(MockRequest(), MockEnv(), {}, {}, "/auth")

    assert "authModalSigninForm" not in response.body
    assert "authModalSignupForm" not in response.body
    assert "apiKeyInput" not in response.body
    assert "createApiKeyButton" in response.body
