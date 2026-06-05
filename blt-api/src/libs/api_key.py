"""
API-key gate classification and validation for BLT-API.

`X-BLT-API-Key` gates protected API requests before router dispatch.
JWT/Bearer identity is separate and handled by auth context helpers.
"""

import hashlib
import hmac
import secrets
import time
from typing import Any, Optional
from urllib.parse import urlparse

from models import UserApiKey
from utils import error_response


API_KEY_HEADER = "X-BLT-API-Key"
API_KEY_ENV_VAR = "BLT_API_KEY"
PUBLIC_BLT_API_KEY = "f5537412b459790f9fa1cc47b862b9c7016471957178dc9b161d59355b6fd051"
USER_API_KEY_PREFIX = "blt_live_"
PUBLIC_API_KEY_PATHS = {
    "/",
    "/v2",
    "/auth",
    "/llm.txt",
    "/blt-api.png",
    "/dashboard",
    "/health",
    "/v2/health",
    "/api/auth/signup",
    "/api/auth/signin",
    "/api/auth/verify-email",
    "/api/auth/verify-local",
    "/auth/signup",
    "/v2/auth/signup",
    "/auth/signin",
    "/v2/auth/signin",
    "/auth/verify-email",
    "/v2/auth/verify-email",
    "/auth/verify-local",
    "/v2/auth/verify-local",
}
JWT_ONLY_PATH_PREFIXES = (
    "/api/auth/api-keys",
    "/auth/api-keys",
    "/v2/auth/api-keys",
)


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

    path = _request_path(url)
    if path in PUBLIC_API_KEY_PATHS:
        return False
    return not any(path == prefix or path.startswith(f"{prefix}/") for prefix in JWT_ONLY_PATH_PREFIXES)


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


def get_api_key_header(request: Any) -> str:
    """Return the provided API key header value, if any."""
    return _get_header(request, API_KEY_HEADER).strip()


def _accepted_api_keys(env: Any) -> list[str]:
    """Return public static key plus optional local override for compatibility."""
    keys = [PUBLIC_BLT_API_KEY]
    env_key = str(getattr(env, API_KEY_ENV_VAR, "") or "").strip()
    if env_key and env_key not in keys:
        keys.append(env_key)
    return keys


def _secret_seed(env: Any) -> str:
    return str(
        getattr(env, "USER_DATA_HASH_KEY", "")
        or getattr(env, "USER_DATA_ENCRYPTION_KEY", "")
        or getattr(env, "JWT_SECRET", "")
        or "owasp-blt-default-api-key"
    )


def generate_user_api_key() -> str:
    """Generate a new opaque user API key."""
    return USER_API_KEY_PREFIX + secrets.token_urlsafe(32)


def user_api_key_prefix(api_key: str) -> str:
    """Return a non-secret display prefix for an API key."""
    return str(api_key)[:20]


def hash_user_api_key(api_key: str, env: Any) -> str:
    """Create a keyed hash for a raw user API key."""
    key = hashlib.sha256(("user-api-key:" + _secret_seed(env)).encode("utf-8")).digest()
    return hmac.new(key, str(api_key).encode("utf-8"), hashlib.sha256).hexdigest()


def is_user_api_key_candidate(request: Any) -> bool:
    """Return whether the request appears to carry a generated user API key."""
    return get_api_key_header(request).startswith(USER_API_KEY_PREFIX)


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


async def validate_api_key_request(request: Any, env: Any, db: Any = None) -> Optional[Any]:
    """Validate an API key for protected requests.

    Returns None when the request may continue, otherwise returns an error response.
    """
    method = str(getattr(request, "method", "GET"))
    url = str(getattr(request, "url", "/"))

    if not is_api_key_required(method, url):
        return None

    provided_key = get_api_key_header(request)
    if not provided_key:
        return error_response("Missing API key", status=401)

    for expected_key in _accepted_api_keys(env):
        if hmac.compare_digest(provided_key, expected_key):
            return None

    if provided_key.startswith(USER_API_KEY_PREFIX):
        if db is None:
            return error_response("Invalid API key", status=401)

        key_hash = hash_user_api_key(provided_key, env)
        key_qs = UserApiKey.objects(db).filter(key_hash=key_hash, is_active=True)
        key = await key_qs.first()
        if not key or key.get("revoked_at"):
            return error_response("Invalid API key", status=401)

        try:
            setattr(request, "user_id", int(key["user_id"]))
            setattr(request, "api_key_id", int(key["id"]))
        except Exception:
            return error_response("Invalid API key", status=401)

        await key_qs.update(last_used=_utc_timestamp())
        return None

    return error_response("Invalid API key", status=401)
