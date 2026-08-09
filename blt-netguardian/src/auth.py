"""Org-scoped API token + optional GitHub session auth for triage routes."""

from __future__ import annotations

import hmac
import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass
class OrgAuthContext:
    org_id: str
    token: str
    auth_mode: str = "bearer"  # bearer | session | demo
    github_login: str = ""


class AuthError(Exception):
    def __init__(self, message: str, *, status: int = 401) -> None:
        self.message = message
        self.status = status
        super().__init__(message)

    def to_response_body(self) -> dict:
        return {"error": "unauthorized", "message": self.message}


def extract_bearer_token(headers: Mapping[str, str]) -> Optional[str]:
    authorization = headers.get("Authorization") or headers.get("authorization")
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def _load_org_token_map(env: Any) -> dict[str, str]:
    raw = getattr(env, "NG_ORG_API_TOKENS", None)
    if not raw:
        return {}
    try:
        mapping = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    if not isinstance(mapping, dict):
        return {}
    result: dict[str, str] = {}
    for token, org_id in mapping.items():
        if token and org_id:
            result[str(token)] = str(org_id)
    return result


def resolve_org_from_token(env: Any, token: str) -> Optional[str]:
    """Map Bearer token to org_id using NG_ORG_API_TOKENS JSON."""
    if not token:
        return None
    for configured_token, org_id in _load_org_token_map(env).items():
        if hmac.compare_digest(configured_token, token):
            return org_id
    return None


def read_endpoints_require_auth(env: Any) -> bool:
    """When false, triage/findings routes accept unauthenticated reads (demo/pilot)."""
    raw = getattr(env, "AUTHENTICATE_READ_ENDPOINTS", None)
    if raw is None:
        return True
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def default_org_id(env: Any) -> str:
    raw = getattr(env, "NG_DEFAULT_ORG", None)
    if raw:
        return str(raw).strip()
    return "org-demo"


def resolve_org_auth(env: Any, headers: Mapping[str, str]) -> OrgAuthContext:
    """Resolve org from Bearer token, or use the default org when auth is disabled.

    Sync helper kept for unit tests. Prefer :func:`resolve_org_auth_async` when a
    DB is available so GitHub session cookies are honored.
    """
    token = extract_bearer_token(headers)
    if token:
        org_id = resolve_org_from_token(env, token)
        if org_id is not None:
            return OrgAuthContext(org_id=org_id, token=token, auth_mode="bearer")
        if read_endpoints_require_auth(env):
            raise AuthError("invalid or unknown API token")
    if not read_endpoints_require_auth(env):
        return OrgAuthContext(org_id=default_org_id(env), token="", auth_mode="demo")
    raise AuthError("missing Bearer token")


def require_org_auth(env: Any, headers: Mapping[str, str]) -> OrgAuthContext:
    token = extract_bearer_token(headers)
    if not token:
        raise AuthError("missing Bearer token")
    org_id = resolve_org_from_token(env, token)
    if org_id is None:
        raise AuthError("invalid or unknown API token")
    return OrgAuthContext(org_id=org_id, token=token, auth_mode="bearer")


async def resolve_org_auth_async(
    env: Any,
    headers: Mapping[str, str],
    db: Any = None,
) -> OrgAuthContext:
    """Bearer first, then GitHub session cookie, then demo default-org fallback."""
    token = extract_bearer_token(headers)
    if token:
        org_id = resolve_org_from_token(env, token)
        if org_id is not None:
            return OrgAuthContext(org_id=org_id, token=token, auth_mode="bearer")
        if read_endpoints_require_auth(env):
            raise AuthError("invalid or unknown API token")

    if db is not None:
        from oauth_github import resolve_session_org

        session = await resolve_session_org(env, db, headers)
        if session is not None:
            org_id, _session_id = session
            # Recover login for audit/UI; ignore lookup failures.
            login = ""
            try:
                from oauth_github import OAuthStore
                from datetime import datetime, timezone

                row = await OAuthStore(db).get_session(
                    _session_id, now=int(datetime.now(timezone.utc).timestamp())
                )
                if row:
                    login = str(row.get("github_login") or "")
            except Exception:  # noqa: BLE001
                login = ""
            return OrgAuthContext(
                org_id=org_id, token="", auth_mode="session", github_login=login
            )

    if not read_endpoints_require_auth(env):
        return OrgAuthContext(org_id=default_org_id(env), token="", auth_mode="demo")
    raise AuthError("missing Bearer token or session")


async def require_org_auth_async(
    env: Any,
    headers: Mapping[str, str],
    db: Any = None,
) -> OrgAuthContext:
    """Mutations: valid Bearer or valid GitHub session (no demo fallback)."""
    token = extract_bearer_token(headers)
    if token:
        org_id = resolve_org_from_token(env, token)
        if org_id is None:
            raise AuthError("invalid or unknown API token")
        return OrgAuthContext(org_id=org_id, token=token, auth_mode="bearer")

    if db is not None:
        ctx = await resolve_org_auth_async(env, headers, db)
        if ctx.auth_mode == "session":
            return ctx

    raise AuthError("missing Bearer token or session")
