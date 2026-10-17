"""
Unit and Integration Tests for OAuth 2.0 PKCE Helpers and Login Flow.

This module validates PKCE code verifier and challenge generation, local callback server binding with port fallback,
and detailed OAuth error handling.

Test Scenarios:
- `test_generate_code_verifier`: Validates high-entropy verifier format, length (43-128 chars), and URL-safe character set.
- `test_generate_code_challenge`: Validates S256 code challenge output against RFC 7636 test vectors.
- `test_pkce_login_port_fallback`: Ensures that `pkce_login()` falls back to port 9877 when default port 9876 is occupied.
- `test_oauth_error_response_handling`: Validates that error descriptions (`invalid_grant`, `error_description`) surface
  cleanly as `RuntimeError` instances.
"""

import asyncio
import re
import socket
import urllib.error
import urllib.request

import httpx
import pytest

from blt_mcp.oauth import (
    generate_code_challenge,
    generate_code_verifier,
    pkce_login,
)


def test_generate_code_verifier():
    """Verify that verifier is a high-entropy URL-safe string of appropriate length."""
    verifier = generate_code_verifier()
    assert isinstance(verifier, str)
    assert len(verifier) >= 43 and len(verifier) <= 128
    # Ensure URL-safe characters
    allowed_chars = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~"
    )
    assert all(c in allowed_chars for c in verifier)


def test_generate_code_challenge():
    """Verify code challenge generation matches specification (S256)."""
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    # S256 challenge for this exact verifier should be E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
    expected_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

    challenge = generate_code_challenge(verifier)
    assert challenge == expected_challenge


@pytest.mark.asyncio
async def test_pkce_login_port_fallback(monkeypatch, capsys):
    """Verify that pkce_login falls back to an available port when the default port is occupied."""
    # Occupy port 9876
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 9876))
    sock.listen(1)

    try:
        # Mock httpx token exchange so we don't hit external servers
        async def mock_post(*args, **kwargs):
            class MockResponse:
                status_code = 200

                def raise_for_status(self):
                    pass

                def json(self):
                    return {"access_token": "mocked_oauth_token"}

            return MockResponse()

        monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

        login_task = asyncio.create_task(
            pkce_login(
                authorize_url="http://example.com/auth",
                token_url="http://example.com/token",
                client_id="test_client",
                redirect_port=9876,
            )
        )

        # Give loop time to bind callback server and print URL
        await asyncio.sleep(0.3)

        captured = capsys.readouterr()
        # Extract state parameter from printed login URL
        match = re.search(r"state=([A-Za-z0-9_-]+)", captured.out)
        assert match is not None, f"State not found in printed stdout: {captured.out}"
        valid_state = match.group(1)

        # 1. Send callback request with invalid state (should get 400 Bad Request but login session remains open)
        def send_invalid_callback():
            try:
                urllib.request.urlopen(
                    "http://127.0.0.1:9877/callback?state=invalid_state", timeout=2.0
                )
            except urllib.error.HTTPError as e:
                assert e.code == 400

        await asyncio.to_thread(send_invalid_callback)

        # 2. Send callback request with valid state and code (should complete login_task)
        def send_valid_callback():
            resp = urllib.request.urlopen(
                f"http://127.0.0.1:9877/callback?code=testcode&state={valid_state}",
                timeout=2.0,
            )
            assert resp.status == 200

        await asyncio.to_thread(send_valid_callback)

        token = await login_task
        assert token == "mocked_oauth_token"
    finally:
        sock.close()


@pytest.mark.asyncio
async def test_oauth_error_response_handling(monkeypatch, capsys):
    """Verify that OAuth error responses surface the error_description properly."""

    async def mock_post(*args, **kwargs):
        class MockResponse:
            status_code = 400
            text = '{"error": "invalid_grant", "error_description": "Authorization code expired"}'

            def raise_for_status(self):
                request = httpx.Request("POST", "http://example.com/token")
                response = httpx.Response(
                    400, content=self.text.encode("utf-8"), request=request
                )
                raise httpx.HTTPStatusError(
                    "400 Bad Request", request=request, response=response
                )

            def json(self):
                return {
                    "error": "invalid_grant",
                    "error_description": "Authorization code expired",
                }

        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    login_task = asyncio.create_task(
        pkce_login(
            authorize_url="http://example.com/auth",
            token_url="http://example.com/token",
            client_id="test_client",
            redirect_port=9890,
        )
    )

    await asyncio.sleep(0.3)

    captured = capsys.readouterr()

    match = re.search(r"state=([A-Za-z0-9_-]+)", captured.out)
    assert match is not None, f"State not found in printed stdout: {captured.out}"
    valid_state = match.group(1)

    # Send callback with valid state to trigger token exchange
    def send_valid_callback():
        resp = urllib.request.urlopen(
            f"http://127.0.0.1:9890/callback?code=testcode&state={valid_state}",
            timeout=2.0,
        )
        assert resp.status == 200

    await asyncio.to_thread(send_valid_callback)

    with pytest.raises(RuntimeError) as exc_info:
        await login_task

    assert "Authorization code expired" in str(exc_info.value)
