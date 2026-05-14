"""
Shared static API-key validation for BLT API requests.
"""

import hmac
from typing import Any, Optional
from urllib.parse import urlparse

from utils import error_response


API_KEY_HEADER = "X-BLT-API-Key"
API_KEY_ENV_VAR = "BLT_API_KEY"
PUBLIC_BLT_API_KEY = "f5537412b459790f9fa1cc47b862b9c7016471957178dc9b161d59355b6fd051"
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


def _accepted_api_keys(env: Any) -> list[str]:
    """Return public static key plus optional local override for compatibility."""
    keys = [PUBLIC_BLT_API_KEY]
    env_key = str(getattr(env, API_KEY_ENV_VAR, "") or "").strip()
    if env_key and env_key not in keys:
        keys.append(env_key)
    return keys


def validate_api_key_request(request: Any, env: Any) -> Optional[Any]:
    """Validate the shared API key for protected requests.

    Returns None when the request may continue, otherwise returns an error response.
    """
    method = str(getattr(request, "method", "GET"))
    url = str(getattr(request, "url", "/"))

    if not is_api_key_required(method, url):
        return None

    provided_key = _get_header(request, API_KEY_HEADER).strip()
    if not provided_key:
        return error_response("Missing API key", status=401)

    for expected_key in _accepted_api_keys(env):
        if hmac.compare_digest(provided_key, expected_key):
            return None

    return error_response("Invalid API key", status=401)
