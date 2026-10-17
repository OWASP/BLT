"""GitHub OAuth 2.0 + PKCE for browser triage sessions."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from d1_compat import d1_row, row_get

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
SESSION_COOKIE = "ng_session"
DEFAULT_SESSION_TTL = 60 * 60 * 12
DEFAULT_STATE_TTL = 60 * 10


@dataclass
class OAuthResult:
    status: int
    body: dict | None = None
    headers: dict | None = None
    redirect_url: str | None = None


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def new_code_verifier() -> str:
    return _b64url(secrets.token_bytes(32))


def code_challenge_s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return _b64url(digest)


def new_state() -> str:
    return _b64url(secrets.token_bytes(24))


def new_session_id() -> str:
    return _b64url(secrets.token_bytes(32))


def oauth_configured(env: Any) -> bool:
    return bool(str(getattr(env, "GITHUB_CLIENT_ID", "") or "").strip()) and bool(
        str(getattr(env, "GITHUB_CLIENT_SECRET", "") or "").strip()
    )


def session_ttl(env: Any) -> int:
    raw = getattr(env, "NG_SESSION_TTL_SECONDS", None)
    try:
        value = int(raw) if raw is not None else DEFAULT_SESSION_TTL
    except (TypeError, ValueError):
        return DEFAULT_SESSION_TTL
    return max(300, min(value, 60 * 60 * 24 * 7))


def github_org_map(env: Any) -> dict[str, str]:
    raw = getattr(env, "NG_GITHUB_ORG_MAP", None)
    if not raw:
        return {}
    try:
        data = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k).lower(): str(v) for k, v in data.items() if k and v}


def resolve_org_for_github_login(env: Any, login: str) -> Optional[str]:
    mapped = github_org_map(env).get(str(login).lower())
    if mapped:
        return mapped
    default = str(getattr(env, "NG_GITHUB_DEFAULT_ORG", "") or "").strip()
    return default or None


def redirect_uri(env: Any, request_url: str) -> str:
    configured = str(getattr(env, "GITHUB_OAUTH_REDIRECT_URI", "") or "").strip()
    if configured:
        return configured
    parsed = urllib.parse.urlparse(request_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return f"{origin}/api/auth/github/callback"


def parse_cookie_header(header_value: Optional[str]) -> dict[str, str]:
    if not header_value:
        return {}
    out: dict[str, str] = {}
    for part in str(header_value).split(";"):
        name, _, value = part.strip().partition("=")
        if name:
            out[name] = urllib.parse.unquote(value)
    return out


def extract_session_id(headers: Mapping[str, str]) -> Optional[str]:
    cookies = parse_cookie_header(headers.get("Cookie") or headers.get("cookie"))
    value = cookies.get(SESSION_COOKIE)
    return value.strip() if value else None


def session_cookie_header(session_id: str, *, max_age: int, secure: bool = True) -> str:
    parts = [
        f"{SESSION_COOKIE}={urllib.parse.quote(session_id)}",
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
        f"Max-Age={max_age}",
    ]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def clear_session_cookie_header(*, secure: bool = True) -> str:
    parts = [
        f"{SESSION_COOKIE}=",
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
        "Max-Age=0",
    ]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def _urllib_json(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Mapping[str, str]] = None,
    body: Optional[bytes] = None,
) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=body, method=method, headers=dict(headers or {}))
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 - GitHub OAuth endpoints
            status = int(getattr(resp, "status", 200) or 200)
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        raw = exc.read().decode("utf-8", errors="replace")
    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        parsed = dict(urllib.parse.parse_qsl(raw))
    if not isinstance(parsed, dict):
        parsed = {"data": parsed}
    return status, parsed


async def _http_json(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Mapping[str, str]] = None,
    body: Optional[bytes] = None,
    fetch_impl: Any = None,
) -> tuple[int, dict]:
    if fetch_impl is not None:
        return await fetch_impl(url, method=method, headers=headers or {}, body=body)
    try:
        from js import fetch  # type: ignore[import-not-found]

        init: dict[str, Any] = {"method": method, "headers": dict(headers or {})}
        if body is not None:
            init["body"] = body.decode("utf-8")
        resp = await fetch(url, init)
        status = int(resp.status)
        text = await resp.text()
        try:
            parsed = json.loads(text) if text else {}
        except json.JSONDecodeError:
            parsed = dict(urllib.parse.parse_qsl(text))
        if not isinstance(parsed, dict):
            parsed = {"data": parsed}
        return status, parsed
    except ImportError:
        return await asyncio.to_thread(
            _urllib_json, url, method=method, headers=headers, body=body
        )


class OAuthStore:
    def __init__(self, db: Any):
        self.db = db

    async def save_state(
        self,
        *,
        state: str,
        code_verifier: str,
        redirect_to: str,
        created_at: int,
        expires_at: int,
    ) -> None:
        await self.db.prepare(
            """
            INSERT INTO oauth_states (state, code_verifier, redirect_to, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """
        ).bind(state, code_verifier, redirect_to, created_at, expires_at).run()

    async def consume_state(self, state: str, *, now: int) -> Optional[dict[str, Any]]:
        row = d1_row(
            await self.db.prepare(
                """
                SELECT state, code_verifier, redirect_to, created_at, expires_at
                FROM oauth_states WHERE state = ?
                """
            ).bind(state).first()
        )
        if row is None:
            return None
        await self.db.prepare("DELETE FROM oauth_states WHERE state = ?").bind(state).run()
        if int(row_get(row, "expires_at") or 0) < now:
            return None
        return {
            "state": row_get(row, "state"),
            "code_verifier": row_get(row, "code_verifier"),
            "redirect_to": row_get(row, "redirect_to") or "/triage.html",
        }

    async def create_session(
        self,
        *,
        session_id: str,
        org_id: str,
        github_login: str,
        github_user_id: Optional[str],
        created_at: int,
        expires_at: int,
    ) -> None:
        await self.db.prepare(
            """
            INSERT INTO auth_sessions
              (id, org_id, github_login, github_user_id, created_at, expires_at, revoked_at)
            VALUES (?, ?, ?, ?, ?, ?, NULL)
            """
        ).bind(
            session_id, org_id, github_login, github_user_id, created_at, expires_at
        ).run()

    async def get_session(self, session_id: str, *, now: int) -> Optional[dict[str, Any]]:
        row = d1_row(
            await self.db.prepare(
                """
                SELECT id, org_id, github_login, github_user_id, created_at, expires_at, revoked_at
                FROM auth_sessions WHERE id = ?
                """
            ).bind(session_id).first()
        )
        if row is None:
            return None
        if row_get(row, "revoked_at") is not None:
            return None
        if int(row_get(row, "expires_at") or 0) < now:
            return None
        return {
            "id": row_get(row, "id"),
            "org_id": row_get(row, "org_id"),
            "github_login": row_get(row, "github_login"),
            "github_user_id": row_get(row, "github_user_id"),
            "created_at": row_get(row, "created_at"),
            "expires_at": row_get(row, "expires_at"),
        }

    async def revoke_session(self, session_id: str, *, now: int) -> None:
        await self.db.prepare(
            """
            UPDATE auth_sessions SET revoked_at = ?
            WHERE id = ? AND revoked_at IS NULL
            """
        ).bind(now, session_id).run()


async def start_github_login(
    *,
    env: Any,
    db: Any,
    request_url: str,
    redirect_to: str = "/triage.html",
    now: Optional[datetime] = None,
) -> OAuthResult:
    if not oauth_configured(env):
        return OAuthResult(
            status=503,
            body={"error": "oauth_not_configured", "message": "GitHub OAuth secrets missing"},
        )
    if db is None:
        return OAuthResult(
            status=503,
            body={"error": "service_unavailable", "message": "auth storage not configured"},
        )

    now = now or datetime.now(timezone.utc)
    created = int(now.timestamp())
    state = new_state()
    verifier = new_code_verifier()
    store = OAuthStore(db)
    await store.save_state(
        state=state,
        code_verifier=verifier,
        redirect_to=redirect_to or "/triage.html",
        created_at=created,
        expires_at=created + DEFAULT_STATE_TTL,
    )

    client_id = str(getattr(env, "GITHUB_CLIENT_ID")).strip()
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri(env, request_url),
        "scope": "read:user",
        "state": state,
        "code_challenge": code_challenge_s256(verifier),
        "code_challenge_method": "S256",
    }
    url = f"{GITHUB_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return OAuthResult(status=302, redirect_url=url)


async def handle_github_callback(
    *,
    env: Any,
    db: Any,
    request_url: str,
    query: Mapping[str, str],
    now: Optional[datetime] = None,
    fetch_impl: Any = None,
) -> OAuthResult:
    if not oauth_configured(env):
        return OAuthResult(
            status=503,
            body={"error": "oauth_not_configured", "message": "GitHub OAuth secrets missing"},
        )
    if db is None:
        return OAuthResult(
            status=503,
            body={"error": "service_unavailable", "message": "auth storage not configured"},
        )

    if query.get("error"):
        return OAuthResult(
            status=400,
            body={"error": "oauth_denied", "message": query.get("error_description") or query["error"]},
        )

    code = (query.get("code") or "").strip()
    state = (query.get("state") or "").strip()
    if not code or not state:
        return OAuthResult(status=400, body={"error": "invalid_callback", "message": "missing code/state"})

    now = now or datetime.now(timezone.utc)
    ts = int(now.timestamp())
    store = OAuthStore(db)
    saved = await store.consume_state(state, now=ts)
    if saved is None:
        return OAuthResult(status=400, body={"error": "invalid_state", "message": "unknown or expired state"})

    token_body = urllib.parse.urlencode(
        {
            "client_id": str(getattr(env, "GITHUB_CLIENT_ID")).strip(),
            "client_secret": str(getattr(env, "GITHUB_CLIENT_SECRET")).strip(),
            "code": code,
            "redirect_uri": redirect_uri(env, request_url),
            "code_verifier": saved["code_verifier"],
        }
    ).encode("utf-8")
    status, token_json = await _http_json(
        GITHUB_TOKEN_URL,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body=token_body,
        fetch_impl=fetch_impl,
    )
    access_token = str(token_json.get("access_token") or "")
    if status >= 400 or not access_token:
        return OAuthResult(
            status=502,
            body={"error": "oauth_token_exchange_failed", "message": "GitHub token exchange failed"},
        )

    user_status, user_json = await _http_json(
        GITHUB_USER_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "blt-netguardian",
        },
        fetch_impl=fetch_impl,
    )
    login = str(user_json.get("login") or "").strip()
    if user_status >= 400 or not login:
        return OAuthResult(
            status=502,
            body={"error": "oauth_user_failed", "message": "GitHub user lookup failed"},
        )

    org_id = resolve_org_for_github_login(env, login)
    if not org_id:
        return OAuthResult(
            status=403,
            body={
                "error": "org_not_mapped",
                "message": f"GitHub user {login} is not mapped to a NetGuardian org",
            },
        )

    session_id = new_session_id()
    ttl = session_ttl(env)
    await store.create_session(
        session_id=session_id,
        org_id=org_id,
        github_login=login,
        github_user_id=str(user_json.get("id")) if user_json.get("id") is not None else None,
        created_at=ts,
        expires_at=ts + ttl,
    )

    secure = not str(request_url).startswith("http://localhost")
    return OAuthResult(
        status=302,
        redirect_url=str(saved.get("redirect_to") or "/triage.html"),
        headers={"Set-Cookie": session_cookie_header(session_id, max_age=ttl, secure=secure)},
    )


async def current_session(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    now: Optional[datetime] = None,
) -> OAuthResult:
    if db is None:
        return OAuthResult(status=503, body={"error": "service_unavailable"})
    session_id = extract_session_id(headers)
    if not session_id:
        return OAuthResult(status=401, body={"error": "unauthorized", "message": "no session"})
    now = now or datetime.now(timezone.utc)
    row = await OAuthStore(db).get_session(session_id, now=int(now.timestamp()))
    if row is None:
        return OAuthResult(status=401, body={"error": "unauthorized", "message": "invalid session"})
    return OAuthResult(
        status=200,
        body={
            "authenticated": True,
            "auth_mode": "session",
            "org_id": row["org_id"],
            "github_login": row["github_login"],
            "expires_at": row["expires_at"],
        },
    )


async def logout_session(
    *,
    db: Any,
    headers: Mapping[str, str],
    request_url: str = "https://example.invalid/",
    now: Optional[datetime] = None,
) -> OAuthResult:
    now = now or datetime.now(timezone.utc)
    session_id = extract_session_id(headers)
    if db is not None and session_id:
        await OAuthStore(db).revoke_session(session_id, now=int(now.timestamp()))
    secure = not str(request_url).startswith("http://localhost")
    return OAuthResult(
        status=200,
        body={"status": "logged_out"},
        headers={"Set-Cookie": clear_session_cookie_header(secure=secure)},
    )


async def resolve_session_org(
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    *,
    now: Optional[datetime] = None,
) -> Optional[tuple[str, str]]:
    """Return (org_id, session_id) when a valid session cookie is present."""
    if db is None:
        return None
    session_id = extract_session_id(headers)
    if not session_id:
        return None
    now = now or datetime.now(timezone.utc)
    row = await OAuthStore(db).get_session(session_id, now=int(now.timestamp()))
    if row is None:
        return None
    return str(row["org_id"]), session_id


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
