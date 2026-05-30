"""Authentication context helpers for Bearer JWT requests."""

from typing import Any, Optional

from libs.jwt_utils import decode_jwt


def get_header(request: Any, name: str) -> str:
    """Safely read a request header in Workers and local tests."""
    headers = getattr(request, "headers", None)
    if not headers or not hasattr(headers, "get"):
        return ""

    value = headers.get(name)
    if value is None and isinstance(headers, dict):
        for header_name, header_value in headers.items():
            if str(header_name).lower() == name.lower():
                value = header_value
                break

    return str(value) if value is not None else ""


def get_bearer_token(request: Any) -> str:
    """Extract a Bearer token from Authorization, or return an empty string."""
    auth_header = get_header(request, "Authorization").strip()
    if not auth_header or not auth_header[:7].lower() == "bearer ":
        return ""
    return auth_header[7:].strip()


def get_authenticated_user_id(request: Any, env: Any) -> Optional[int]:
    """Decode a user session JWT and return its user id.

    Purpose-scoped tokens, such as email verification links, are not accepted
    as authenticated sessions.
    """
    token = get_bearer_token(request)
    if not token:
        return None

    payload = decode_jwt(token, getattr(env, "JWT_SECRET", ""))
    if not payload or payload.get("purpose") or not payload.get("user_id"):
        return None

    try:
        return int(payload["user_id"])
    except (TypeError, ValueError):
        return None

