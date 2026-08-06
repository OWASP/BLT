"""
Authentication helper for OWASP BLT-Toasty.
"""

import base64
import json
import logging
from typing import Any
from js import crypto, Date

from src.errors import JWTExpiredError, JWTInvalidError

logger = logging.getLogger("toasty.auth")


def _base64url_decode(payload: str) -> bytes:
    """Decode a base64url string."""
    rem = len(payload) % 4
    if rem > 0:
        payload += "=" * (4 - rem)
    return base64.urlsafe_b64decode(payload)


async def verify_agent_jwt(token: str, env: Any) -> dict:
    """
    Verify an RS256 JWT using Web Crypto API.

    Args:
        token: The Bearer token from the Authorization header.
        env: The Cloudflare Worker environment containing MCP_PUBLIC_KEY.

    Returns:
        The decoded claims dictionary.

    Raises:
        JWTInvalidError: If the token is malformed, signature is invalid, or claims are wrong.
        JWTExpiredError: If the token has expired.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise JWTInvalidError("Token must contain header, payload, and signature")

    header_b64, payload_b64, signature_b64 = parts

    try:
        payload_bytes = _base64url_decode(payload_b64)
        claims = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise JWTInvalidError(f"Malformed payload: {e}")

    # Check expiration before cryptographic verification
    now = int(Date.now() / 1000)
    exp = claims.get("exp")
    if not exp or not isinstance(exp, (int, float)):
        raise JWTInvalidError("Missing or invalid 'exp' claim")
    if exp <= now:
        raise JWTExpiredError("Token has expired")

    # Validate standard claims
    iss = claims.get("iss")
    if iss != "owasp-blt-service":
        raise JWTInvalidError("Invalid issuer (iss)")
    aud = claims.get("aud")
    if aud != "toasty-mcp":
        raise JWTInvalidError("Invalid audience (aud)")
    sub = claims.get("sub")
    if not sub or not isinstance(sub, str):
        raise JWTInvalidError("Missing or invalid 'sub' claim (agent ID)")

    # Perform cryptographic verification
    if not hasattr(env, "MCP_PUBLIC_KEY") or not env.MCP_PUBLIC_KEY:
        raise JWTInvalidError("Server configuration missing MCP_PUBLIC_KEY")

    pub_key_pem = env.MCP_PUBLIC_KEY.strip()
    # Strip PEM headers for Web Crypto SPKI import
    b64_key = (
        pub_key_pem.replace("-----BEGIN PUBLIC KEY-----", "")
        .replace("-----END PUBLIC KEY-----", "")
        .replace("\n", "")
        .replace("\r", "")
    )

    try:
        key_buf = base64.b64decode(b64_key)
    except Exception as e:
        logger.error("Failed to base64 decode MCP_PUBLIC_KEY: %s", e)
        raise JWTInvalidError("Internal configuration error")

    # The buffer to verify is header.payload
    data_to_verify = f"{header_b64}.{payload_b64}".encode("utf-8")

    try:
        signature_bytes = _base64url_decode(signature_b64)
    except Exception as e:
        raise JWTInvalidError(f"Malformed signature: {e}")

    try:
        # Import the public key
        key = await crypto.subtle.importKey(
            "spki", key_buf, {"name": "RSASSA-PKCS1-v1_5", "hash": "SHA-256"}, False, ["verify"]
        )

        # Verify the signature
        is_valid = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, signature_bytes, data_to_verify)
    except Exception as e:
        raise JWTInvalidError(f"Signature verification process failed: {e}")

    if not is_valid:
        raise JWTInvalidError("Invalid signature")

    return claims
