"""GitHub OAuth PKCE + session coexistence with Bearer tokens."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

from auth import require_org_auth_async, resolve_org_auth_async
from findings_service import list_findings_for_request
from netguardian_db import open_netguardian_db
from oauth_github import (
    SESSION_COOKIE,
    code_challenge_s256,
    handle_github_callback,
    logout_session,
    new_code_verifier,
    start_github_login,
)
from test_worker_api import BLTWorker, FakeRequest, parse_json

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def db():
    db = open_netguardian_db(REPO_ROOT)
    yield db
    db.conn.close()


@pytest.fixture
def env():
    return SimpleNamespace(
        GITHUB_CLIENT_ID="client-id",
        GITHUB_CLIENT_SECRET="client-secret",
        GITHUB_OAUTH_REDIRECT_URI="https://app.example/api/auth/github/callback",
        NG_GITHUB_ORG_MAP='{"octocat":"org-demo"}',
        NG_ORG_API_TOKENS='{"triage-token":"org-demo"}',
        AUTHENTICATE_READ_ENDPOINTS="true",
        NG_DEFAULT_ORG="org-demo",
    )


def test_pkce_challenge_is_s256():
    verifier = new_code_verifier()
    challenge = code_challenge_s256(verifier)
    assert len(challenge) >= 43
    assert "=" not in challenge


@pytest.mark.asyncio
async def test_login_redirect_includes_pkce(env, db):
    result = await start_github_login(
        env=env,
        db=db,
        request_url="https://app.example/triage.html",
        redirect_to="/triage.html",
    )
    assert result.status == 302
    parsed = urlparse(result.redirect_url)
    qs = parse_qs(parsed.query)
    assert qs["client_id"] == ["client-id"]
    assert qs["code_challenge_method"] == ["S256"]
    assert qs["code_challenge"][0]
    assert qs["state"][0]


@pytest.mark.asyncio
async def test_callback_sets_session_and_list_works(env, db):
    start = await start_github_login(
        env=env,
        db=db,
        request_url="https://app.example/triage.html",
    )
    state = parse_qs(urlparse(start.redirect_url).query)["state"][0]

    async def fake_fetch(url, method="GET", headers=None, body=None):
        if "login/oauth/access_token" in url:
            return 200, {"access_token": "gho_test"}
        if url.endswith("/user"):
            return 200, {"login": "octocat", "id": 1}
        raise AssertionError(url)

    cb = await handle_github_callback(
        env=env,
        db=db,
        request_url="https://app.example/api/auth/github/callback",
        query={"code": "abc", "state": state},
        fetch_impl=fake_fetch,
    )
    assert cb.status == 302
    assert cb.redirect_url == "/triage.html"
    assert SESSION_COOKIE + "=" in cb.headers["Set-Cookie"]

    cookie = cb.headers["Set-Cookie"].split(";")[0]
    listed = await list_findings_for_request(
        env=env,
        db=db,
        headers={"Cookie": cookie},
        query_params={},
    )
    assert listed.status == 200
    assert listed.body["total"] == 0

    auth = await require_org_auth_async(env, {"Cookie": cookie}, db)
    assert auth.org_id == "org-demo"
    assert auth.auth_mode == "session"
    assert auth.github_login == "octocat"


@pytest.mark.asyncio
async def test_bearer_still_works_alongside_sessions(env, db):
    auth = await resolve_org_auth_async(
        env, {"Authorization": "Bearer triage-token"}, db
    )
    assert auth.auth_mode == "bearer"
    assert auth.org_id == "org-demo"


@pytest.mark.asyncio
async def test_unmapped_github_user_forbidden(env, db):
    start = await start_github_login(env=env, db=db, request_url="https://app.example/")
    state = parse_qs(urlparse(start.redirect_url).query)["state"][0]

    async def fake_fetch(url, method="GET", headers=None, body=None):
        if "access_token" in url:
            return 200, {"access_token": "gho"}
        return 200, {"login": "stranger", "id": 9}

    cb = await handle_github_callback(
        env=env,
        db=db,
        request_url="https://app.example/api/auth/github/callback",
        query={"code": "abc", "state": state},
        fetch_impl=fake_fetch,
    )
    assert cb.status == 403
    assert cb.body["error"] == "org_not_mapped"


@pytest.mark.asyncio
async def test_logout_and_worker_routes(env, db):
    start = await start_github_login(env=env, db=db, request_url="https://app.example/")
    state = parse_qs(urlparse(start.redirect_url).query)["state"][0]

    async def fake_fetch(url, method="GET", headers=None, body=None):
        if "access_token" in url:
            return 200, {"access_token": "gho"}
        return 200, {"login": "octocat", "id": 1}

    cb = await handle_github_callback(
        env=env,
        db=db,
        request_url="https://app.example/api/auth/github/callback",
        query={"code": "abc", "state": state},
        fetch_impl=fake_fetch,
    )
    cookie = cb.headers["Set-Cookie"].split(";")[0]
    out = await logout_session(db=db, headers={"Cookie": cookie}, request_url="https://app.example/")
    assert out.status == 200
    assert "Max-Age=0" in out.headers["Set-Cookie"]

    env.DB = db
    worker = BLTWorker(env)
    login = await worker.handle_request(
        FakeRequest("https://app.example/api/auth/github/login", method="GET")
    )
    assert login.status == 302
    assert "github.com/login/oauth/authorize" in login.headers["Location"]

    me = await worker.handle_request(
        FakeRequest(
            "https://app.example/api/auth/me",
            method="GET",
            headers={"Cookie": cookie},
        )
    )
    # session revoked by logout above
    assert me.status == 401
    body = parse_json(me)
    assert body["error"] == "unauthorized"
