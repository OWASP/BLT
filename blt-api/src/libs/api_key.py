"""
Shared static API-key validation for BLT API requests.
"""

import hmac
from typing import Any, Optional
from urllib.parse import urlparse

from utils import error_response


API_KEY_HEADER = "X-BLT-API-Key"
API_KEY_ENV_VAR = "BLT_API_KEY"
PUBLIC_API_KEY_PATHS = {"/", "/v2", "/health", "/v2/health"}


def _request_path(url: str) -> str:
    """Normalize a request URL into the path used for API-key decisions."""
    parsed = urlparse(str(url))
    if (parsed.scheme or parsed.netloc) and not parsed.path:
        path = "/"
    else:
        path = parsed.path or str(url).split("?", 1)[0]

    if not path.startswith("/"):
        path = f"/{path}"

    if path != "/" and path.endswith("/"):
        path = path[:-1]

    return path


def is_api_key_required(method: str, url: str) -> bool:
    """Return whether a request method/path should require the shared API key."""
    if str(method).upper() == "OPTIONS":
        return False

    return _request_path(url) not in PUBLIC_API_KEY_PATHS


def _get_header(request: Any, name: str) -> str:
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


def validate_api_key_request(request: Any, env: Any) -> Optional[Any]:
    """Validate the shared API key for protected requests.

    Returns None when the request may continue, otherwise returns an error response.
    """
    method = str(getattr(request, "method", "GET"))
    url = str(getattr(request, "url", "/"))

    if not is_api_key_required(method, url):
        return None

    expected_key = str(getattr(env, API_KEY_ENV_VAR, "") or "").strip()
    if not expected_key:
        return error_response("API key authentication is not configured", status=500)

    provided_key = _get_header(request, API_KEY_HEADER).strip()
    if not provided_key:
        return error_response("Missing API key", status=401)

    if not hmac.compare_digest(provided_key, expected_key):
        return error_response("Invalid API key", status=401)

    return None
