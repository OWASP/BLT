"""
OAuth 2.0 PKCE Authentication Support for the OWASP BLT MCP Server.

This module implements the OAuth 2.0 Authorization Code Flow with PKCE (Proof Key for Code Exchange, RFC 7636).
It provides browser-based authentication capabilities for clients interacting with the OWASP BLT backend API.

Key Responsibilities:
- `generate_code_verifier()`: Generates a high-entropy 128-character URL-safe verifier string.
- `generate_code_challenge()`: Computes the SHA-256 S256 code challenge for a verifier.
- `pkce_login()`: Launches a local HTTP loopback server with port fallback (9876..9886, dynamic port 0),
  listens for the OAuth callback code, validates state parameters, and exchanges the authorization code
  for an access token while surfacing detailed OAuth error messages.

Dependencies:
- `asyncio`, `base64`, `hashlib`, `httpx`, `logging`, `secrets`, `urllib.parse`
"""

import asyncio
import base64
import hashlib
import logging
import secrets
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

logger = logging.getLogger("blt-mcp.oauth")


def generate_code_verifier() -> str:
    """Generate a 128-character high-entropy code verifier (RFC 7636)."""
    return secrets.token_urlsafe(96)


def generate_code_challenge(verifier: str) -> str:
    """Generate an S256 code challenge from the verifier."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


async def pkce_login(
    authorize_url: str,
    token_url: str,
    client_id: str,
    redirect_port: int = 9876,
    scopes: str = "read write",
) -> str:
    """Run the full PKCE flow. Returns the access token."""
    verifier = generate_code_verifier()
    challenge = generate_code_challenge(verifier)
    state = secrets.token_urlsafe(32)
    code_future = asyncio.get_running_loop().create_future()

    async def handle_callback(reader, writer):
        data = await reader.read(4096)
        request_text = data.decode("utf-8", errors="ignore")

        code = None
        state_received = None
        if "GET " in request_text:
            parts = request_text.split(" ")
            if len(parts) > 1:
                qs = parse_qs(urlparse(parts[1]).query)
                code = qs.get("code", [None])[0]
                state_received = qs.get("state", [None])[0]

        if not state_received or state_received != state:
            logger.warning(
                "OAuth callback received invalid or missing state parameter."
            )
            response = (
                "HTTP/1.1 400 Bad Request\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n\r\n"
                "Error: State validation failed."
            )
        elif code:
            if not code_future.done():
                code_future.set_result(code)
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n\r\n"
                "Login successful! You can close this tab."
            )
        else:
            logger.warning("OAuth callback received without authorization code.")
            response = (
                "HTTP/1.1 400 Bad Request\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n\r\n"
                "Error: Authorization code not found."
            )

        writer.write(response.encode("utf-8"))
        await writer.drain()
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass

    server = None
    actual_port = redirect_port
    for p in range(redirect_port, redirect_port + 10):
        try:
            server = await asyncio.start_server(handle_callback, "127.0.0.1", p)
            actual_port = p
            break
        except OSError:
            logger.warning(
                f"Port {p} occupied, attempting next port for OAuth callback server..."
            )
            continue

    if server is None:
        try:
            server = await asyncio.start_server(handle_callback, "127.0.0.1", 0)
            actual_port = server.sockets[0].getsockname()[1]
        except OSError as e:
            raise RuntimeError(
                f"Failed to bind local OAuth callback server: {e}"
            ) from e

    redirect_uri = f"http://127.0.0.1:{actual_port}/callback"

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "scope": scopes,
        "state": state,
    }
    login_url = f"{authorize_url}?{urlencode(params)}"

    # Print URL for user (no browser auto-open per user rule)
    print(f"\nOpen this URL to log in:\n\n  {login_url}\n")
    print(f"Waiting for callback on {redirect_uri} ...")

    try:
        # Wait up to 5 minutes (300 seconds)
        code = await asyncio.wait_for(code_future, timeout=300.0)
    finally:
        server.close()
        await server.wait_closed()

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": client_id,
                    "code_verifier": verifier,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            error_desc = None
            try:
                err_data = e.response.json()
                error_desc = (
                    err_data.get("error_description")
                    or err_data.get("error")
                    or err_data.get("message")
                )
            except Exception:  # noqa: BLE001
                error_desc = e.response.text
            if error_desc:
                raise RuntimeError(
                    f"OAuth token request failed (HTTP {e.response.status_code}): {error_desc}"
                ) from e
            raise

        if not isinstance(data, dict):
            raise TypeError(
                f"Unexpected OAuth token response structure: {type(data).__name__}"
            )

        if "error" in data:
            error_msg = data.get("error_description") or data.get("error")
            raise RuntimeError(f"OAuth token exchange error: {error_msg}")

        token = data.get("access_token") or data.get("token")
        if not token:
            raise RuntimeError(
                f"OAuth token exchange response missing 'access_token': {resp.text}"
            )
        return token
