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
    redirect_uri = f"http://127.0.0.1:{redirect_port}/callback"

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "scope": scopes,
    }
    login_url = f"{authorize_url}?{urlencode(params)}"

    # Print URL for user (no browser auto-open per user rule)
    print(f"\nOpen this URL to log in:\n\n  {login_url}\n")
    print(f"Waiting for callback on http://127.0.0.1:{redirect_port}/callback ...")

    code_future = asyncio.get_running_loop().create_future()

    async def handle_callback(reader, writer):
        data = await reader.read(4096)
        request_text = data.decode("utf-8", errors="ignore")

        code = None
        if "GET " in request_text:
            parts = request_text.split(" ")
            if len(parts) > 1:
                qs = parse_qs(urlparse(parts[1]).query)
                code = qs.get("code", [None])[0]

        if code:
            if not code_future.done():
                code_future.set_result(code)
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Connection: close\r\n\r\n"
                "Login successful! You can close this tab."
            )
        else:
            if not code_future.done():
                code_future.set_exception(
                    RuntimeError(
                        "Authorization code not found in callback query parameters."
                    )
                )
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

    server = await asyncio.start_server(handle_callback, "127.0.0.1", redirect_port)

    try:
        # Wait up to 5 minutes (300 seconds)
        code = await asyncio.wait_for(code_future, timeout=300.0)
    finally:
        server.close()
        await server.wait_closed()

    # Exchange code for token
    async with httpx.AsyncClient() as client:
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
        return data["access_token"]
