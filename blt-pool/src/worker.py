"""BLT GitHub App — Python Cloudflare Worker.

Handles GitHub webhooks and serves a landing homepage.
This is the Python / Cloudflare Workers port of the original Node.js Probot app.

Entry point: ``on_fetch(request, env)`` — called by the Cloudflare runtime for
every incoming HTTP request.

Environment variables / secrets (configure via ``wrangler.toml`` or
``wrangler secret put``):
    APP_ID             — GitHub App numeric ID
    PRIVATE_KEY        — GitHub App RSA private key (PEM, PKCS#1 or PKCS#8)
    WEBHOOK_SECRET     — GitHub App webhook secret
    GITHUB_APP_SLUG    — GitHub App slug used to build the install URL
    BLT_API_URL        — BLT API base URL (default: https://blt-api.owasp-blt.workers.dev)
    GITHUB_CLIENT_ID   — OAuth client ID (optional)
    GITHUB_CLIENT_SECRET — OAuth client secret (optional)
"""

import base64
import hashlib
import hmac as _hmac
import json
import time
from typing import Optional, Tuple
from urllib.parse import urlparse

from js import Headers, Response, console, fetch  # Cloudflare Workers JS bindings
from index_template import INDEX_HTML  # Landing page HTML template

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ASSIGN_COMMAND = "/assign"
UNASSIGN_COMMAND = "/unassign"
LEADERBOARD_COMMAND = "/leaderboard"
MAX_ASSIGNEES = 1
ASSIGNMENT_DURATION_HOURS = 8
BUG_LABELS = {"bug", "vulnerability", "security"}

# DER OID sequence for rsaEncryption (used when wrapping PKCS#1 → PKCS#8)
_RSA_OID_SEQ = bytes([
    0x30, 0x0D,
    0x06, 0x09, 0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x01, 0x01,
    0x05, 0x00,
])

# ---------------------------------------------------------------------------
# DER / PEM helpers (needed for PKCS#1 → PKCS#8 conversion)
# ---------------------------------------------------------------------------


def _der_len(n: int) -> bytes:
    """Encode a DER length field."""
    if n < 0x80:
        return bytes([n])
    if n < 0x100:
        return bytes([0x81, n])
    return bytes([0x82, (n >> 8) & 0xFF, n & 0xFF])


def _wrap_pkcs1_as_pkcs8(pkcs1_der: bytes) -> bytes:
    """Wrap a PKCS#1 RSAPrivateKey DER blob into a PKCS#8 PrivateKeyInfo."""
    version = bytes([0x02, 0x01, 0x00])  # INTEGER 0
    octet = bytes([0x04]) + _der_len(len(pkcs1_der)) + pkcs1_der
    content = version + _RSA_OID_SEQ + octet
    return bytes([0x30]) + _der_len(len(content)) + content


def pem_to_pkcs8_der(pem: str) -> bytes:
    """Convert a PEM private key (PKCS#1 or PKCS#8) to PKCS#8 DER bytes.

    GitHub App private keys are usually PKCS#1 (``BEGIN RSA PRIVATE KEY``).
    SubtleCrypto's ``importKey`` requires PKCS#8, so we wrap if necessary.
    """
    lines = pem.strip().splitlines()
    is_pkcs1 = lines[0].strip() == "-----BEGIN RSA PRIVATE KEY-----"
    b64 = "".join(line for line in lines if not line.startswith("-----"))
    der = base64.b64decode(b64)
    return _wrap_pkcs1_as_pkcs8(der) if is_pkcs1 else der


# ---------------------------------------------------------------------------
# Base64url encoding
# ---------------------------------------------------------------------------


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Return True when the X-Hub-Signature-256 header matches the payload."""
    if not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + _hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return _hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# JWT creation via SubtleCrypto (no external packages required)
# ---------------------------------------------------------------------------


async def create_github_jwt(app_id: str, private_key_pem: str) -> str:
    """Create a signed GitHub App JWT using the Web Crypto SubtleCrypto API."""
    from js import Uint8Array, crypto, Array, Object  # noqa: PLC0415 — runtime import
    from pyodide.ffi import to_js  # noqa: PLC0415 — runtime import

    now = int(time.time())
    header_b64 = _b64url(
        json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    payload_b64 = _b64url(
        json.dumps(
            {"iat": now - 60, "exp": now + 600, "iss": str(app_id)},
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{header_b64}.{payload_b64}"

    # Import private key into SubtleCrypto
    pkcs8_der = pem_to_pkcs8_der(private_key_pem)
    key_array = Uint8Array.new(len(pkcs8_der))
    for i, b in enumerate(pkcs8_der):
        key_array[i] = b

    # Create a proper JS Array for keyUsages
    key_usages = getattr(Array, "from")(["sign"])

    crypto_key = await crypto.subtle.importKey(
        "pkcs8",
        key_array.buffer,
        to_js({"name": "RSASSA-PKCS1-v1_5", "hash": "SHA-256"}, dict_converter=Object.fromEntries),
        False,
        key_usages,
    )

    # Sign the JWT header.payload
    msg_bytes = signing_input.encode("ascii")
    msg_array = Uint8Array.new(len(msg_bytes))
    for i, b in enumerate(msg_bytes):
        msg_array[i] = b

    sig_buf = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", crypto_key, msg_array.buffer)
    sig_bytes = bytes(Uint8Array.new(sig_buf))
    return f"{signing_input}.{_b64url(sig_bytes)}"


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------


def _gh_headers(token: str) -> Headers:
    return Headers.new({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "BLT-GitHub-App/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }.items())


async def github_api(method: str, path: str, token: str, body=None):
    """Make an authenticated request to the GitHub REST API."""
    url = f"https://api.github.com{path}"
    kwargs = {"method": method, "headers": _gh_headers(token)}
    if body is not None:
        kwargs["body"] = json.dumps(body)
    return await fetch(url, **kwargs)


async def get_installation_token(
    installation_id: int, app_id: str, private_key: str
) -> Optional[str]:
    """Exchange a GitHub App JWT for an installation access token."""
    jwt = await create_github_jwt(app_id, private_key)
    resp = await fetch(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        method="POST",
        headers=Headers.new({
            "Authorization": f"Bearer {jwt}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "BLT-GitHub-App/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }.items()),
    )
    if resp.status != 201:
        console.error(f"[BLT] Failed to get installation token: {resp.status}")
        return None
    data = json.loads(await resp.text())
    return data.get("token")


async def create_comment(
    owner: str, repo: str, number: int, body: str, token: str
) -> None:
    """Post a comment on a GitHub issue or pull request."""
    await github_api(
        "POST",
        f"/repos/{owner}/{repo}/issues/{number}/comments",
        token,
        {"body": body},
    )


async def create_reaction(
    owner: str, repo: str, comment_id: int, reaction: str, token: str
) -> None:
    """Add a reaction to a comment. Common reactions: +1, -1, laugh, confused, heart, hooray, rocket, eyes."""
    await github_api(
        "POST",
        f"/repos/{owner}/{repo}/issues/comments/{comment_id}/reactions",
        token,
        {"content": reaction},
    )


# ---------------------------------------------------------------------------
# BLT API helper
# ---------------------------------------------------------------------------


async def report_bug_to_blt(blt_api_url: str, issue_data: dict):
    """Report a bug to the BLT API; returns the created bug object or None."""
    try:
        payload = {
            "url": issue_data.get("url") or issue_data.get("github_url"),
            "description": issue_data.get("description", ""),
            "github_url": issue_data.get("github_url", ""),
            "label": issue_data.get("label", "general"),
            "status": "open",
        }
        resp = await fetch(
            f"{blt_api_url}/bugs",
            method="POST",
            headers=Headers.new({"Content-Type": "application/json"}.items()),
            body=json.dumps(payload),
        )
        data = json.loads(await resp.text())
        return data.get("data") if data.get("success") else None
    except Exception as exc:
        console.error(f"[BLT] Failed to report bug: {exc}")
        return None


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _is_human(user: dict) -> bool:
    """Return True for human GitHub users (not bots or apps).

    'Mannequin' is a placeholder user type GitHub assigns to contributions
    imported from external version-control systems (e.g. SVN migrations).
    """
    return bool(user and user.get("type") in ("User", "Mannequin"))


def _is_bot(user: dict) -> bool:
    """Return True if the user is a bot account.
    
    Returns True for None or malformed user objects to safely filter them out.
    """
    if not user or not user.get("login"):
        return True  # Treat invalid/missing users as bots for safety
    login_lower = user["login"].lower()
    bot_patterns = [
        "copilot", "[bot]", "dependabot", "github-actions",
        "renovate", "actions-user", "coderabbitai", "coderabbit",
        "sentry-autofix"
    ]
    return user.get("type") == "Bot" or any(p in login_lower for p in bot_patterns)


def _is_coderabbit_ping(body: str) -> bool:
    """Return True if the comment body mentions coderabbit."""
    if not body:
        return False
    lower = body.lower()
    return "coderabbit" in lower or "@coderabbitai" in lower


# ---------------------------------------------------------------------------
# Leaderboard — Calculation & Display
# ---------------------------------------------------------------------------

# Leaderboard configuration constants
LEADERBOARD_MARKER = "<!-- leaderboard-bot -->"
MAX_OPEN_PRS_PER_AUTHOR = 50
LEADERBOARD_COMMENT_MARKER = LEADERBOARD_MARKER


def _month_key(ts: Optional[int] = None) -> str:
    """Return YYYY-MM month key for UTC timestamp (or now)."""
    if ts is None:
        ts = int(time.time())
    return time.strftime("%Y-%m", time.gmtime(ts))


def _month_window(month_key: str) -> Tuple[int, int]:
    """Return start/end timestamps (UTC) for a YYYY-MM key."""
    year, month = month_key.split("-")
    y = int(year)
    m = int(month)
    start_struct = time.struct_time((y, m, 1, 0, 0, 0, 0, 0, 0))
    start_ts = int(time.mktime(start_struct))
    if m == 12:
        next_struct = time.struct_time((y + 1, 1, 1, 0, 0, 0, 0, 0, 0))
    else:
        next_struct = time.struct_time((y, m + 1, 1, 0, 0, 0, 0, 0, 0))
    end_ts = int(time.mktime(next_struct)) - 1
    return start_ts, end_ts


def _d1_binding(env):
    """Return D1 binding object if configured, otherwise None."""
    return getattr(env, "LEADERBOARD_DB", None)


async def _d1_run(db, sql: str, params: tuple = ()):
    stmt = db.prepare(sql)
    if params:
        stmt = stmt.bind(*params)
    return await stmt.run()


async def _d1_all(db, sql: str, params: tuple = ()) -> list:
    stmt = db.prepare(sql)
    if params:
        stmt = stmt.bind(*params)
    result = await stmt.all()
    rows = result.get("results") if isinstance(result, dict) else None
    return rows or []


async def _d1_first(db, sql: str, params: tuple = ()):
    rows = await _d1_all(db, sql, params)
    return rows[0] if rows else None


async def _ensure_leaderboard_schema(db) -> None:
    """Create leaderboard tables if they do not exist."""
    await _d1_run(
        db,
        """
        CREATE TABLE IF NOT EXISTS leaderboard_monthly_stats (
            org TEXT NOT NULL,
            month_key TEXT NOT NULL,
            user_login TEXT NOT NULL,
            merged_prs INTEGER NOT NULL DEFAULT 0,
            closed_prs INTEGER NOT NULL DEFAULT 0,
            reviews INTEGER NOT NULL DEFAULT 0,
            comments INTEGER NOT NULL DEFAULT 0,
            updated_at INTEGER NOT NULL,
            PRIMARY KEY (org, month_key, user_login)
        )
        """,
    )
    await _d1_run(
        db,
        """
        CREATE TABLE IF NOT EXISTS leaderboard_open_prs (
            org TEXT NOT NULL,
            user_login TEXT NOT NULL,
            open_prs INTEGER NOT NULL DEFAULT 0,
            updated_at INTEGER NOT NULL,
            PRIMARY KEY (org, user_login)
        )
        """,
    )
    await _d1_run(
        db,
        """
        CREATE TABLE IF NOT EXISTS leaderboard_pr_state (
            org TEXT NOT NULL,
            repo TEXT NOT NULL,
            pr_number INTEGER NOT NULL,
            author_login TEXT NOT NULL,
            state TEXT NOT NULL,
            merged INTEGER NOT NULL DEFAULT 0,
            closed_at INTEGER,
            updated_at INTEGER NOT NULL,
            PRIMARY KEY (org, repo, pr_number)
        )
        """,
    )
    await _d1_run(
        db,
        """
        CREATE TABLE IF NOT EXISTS leaderboard_review_credits (
            org TEXT NOT NULL,
            repo TEXT NOT NULL,
            pr_number INTEGER NOT NULL,
            month_key TEXT NOT NULL,
            reviewer_login TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            PRIMARY KEY (org, repo, pr_number, month_key, reviewer_login)
        )
        """,
    )


async def _d1_inc_open_pr(db, org: str, user_login: str, delta: int) -> None:
    now = int(time.time())
    await _d1_run(
        db,
        """
        INSERT INTO leaderboard_open_prs (org, user_login, open_prs, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(org, user_login) DO UPDATE SET
            open_prs = MAX(0, leaderboard_open_prs.open_prs + excluded.open_prs),
            updated_at = excluded.updated_at
        """,
        (org, user_login, delta, now),
    )


async def _d1_inc_monthly(db, org: str, month_key: str, user_login: str, field: str, delta: int = 1) -> None:
    now = int(time.time())
    if field not in {"merged_prs", "closed_prs", "reviews", "comments"}:
        return
    await _d1_run(
        db,
        f"""
        INSERT INTO leaderboard_monthly_stats (org, month_key, user_login, {field}, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(org, month_key, user_login) DO UPDATE SET
            {field} = leaderboard_monthly_stats.{field} + excluded.{field},
            updated_at = excluded.updated_at
        """,
        (org, month_key, user_login, delta, now),
    )


async def _track_pr_opened_in_d1(payload: dict, env) -> None:
    db = _d1_binding(env)
    if not db:
        return
    pr = payload.get("pull_request") or {}
    author = pr.get("user") or {}
    if _is_bot(author):
        return
    org = (payload.get("repository") or {}).get("owner", {}).get("login", "")
    repo = (payload.get("repository") or {}).get("name", "")
    pr_number = pr.get("number")
    author_login = author.get("login", "")
    if not (org and repo and pr_number and author_login):
        return

    await _ensure_leaderboard_schema(db)
    existing = await _d1_first(
        db,
        "SELECT state FROM leaderboard_pr_state WHERE org = ? AND repo = ? AND pr_number = ?",
        (org, repo, pr_number),
    )
    if not existing or existing.get("state") != "open":
        await _d1_inc_open_pr(db, org, author_login, 1)

    now = int(time.time())
    await _d1_run(
        db,
        """
        INSERT INTO leaderboard_pr_state (org, repo, pr_number, author_login, state, merged, closed_at, updated_at)
        VALUES (?, ?, ?, ?, 'open', 0, NULL, ?)
        ON CONFLICT(org, repo, pr_number) DO UPDATE SET
            author_login = excluded.author_login,
            state = 'open',
            merged = 0,
            closed_at = NULL,
            updated_at = excluded.updated_at
        """,
        (org, repo, pr_number, author_login, now),
    )


async def _track_pr_closed_in_d1(payload: dict, env) -> None:
    db = _d1_binding(env)
    if not db:
        return
    pr = payload.get("pull_request") or {}
    author = pr.get("user") or {}
    if _is_bot(author):
        return
    org = (payload.get("repository") or {}).get("owner", {}).get("login", "")
    repo = (payload.get("repository") or {}).get("name", "")
    pr_number = pr.get("number")
    author_login = author.get("login", "")
    closed_at = pr.get("closed_at")
    merged_at = pr.get("merged_at")
    merged = bool(pr.get("merged"))
    closed_ts = _parse_github_timestamp(closed_at) if closed_at else int(time.time())
    if not (org and repo and pr_number and author_login):
        return

    await _ensure_leaderboard_schema(db)
    existing = await _d1_first(
        db,
        "SELECT state, merged, closed_at FROM leaderboard_pr_state WHERE org = ? AND repo = ? AND pr_number = ?",
        (org, repo, pr_number),
    )

    # Idempotency: skip if we already recorded the same closed state.
    if existing and existing.get("state") == "closed" and int(existing.get("merged") or 0) == int(merged):
        existing_closed_at = int(existing.get("closed_at") or 0)
        if existing_closed_at == int(closed_ts or 0):
            return

    if existing and existing.get("state") == "open":
        await _d1_inc_open_pr(db, org, author_login, -1)

    event_ts = _parse_github_timestamp(merged_at) if merged and merged_at else closed_ts
    mk = _month_key(event_ts)
    if merged:
        await _d1_inc_monthly(db, org, mk, author_login, "merged_prs", 1)
    else:
        await _d1_inc_monthly(db, org, mk, author_login, "closed_prs", 1)

    now = int(time.time())
    await _d1_run(
        db,
        """
        INSERT INTO leaderboard_pr_state (org, repo, pr_number, author_login, state, merged, closed_at, updated_at)
        VALUES (?, ?, ?, ?, 'closed', ?, ?, ?)
        ON CONFLICT(org, repo, pr_number) DO UPDATE SET
            author_login = excluded.author_login,
            state = 'closed',
            merged = excluded.merged,
            closed_at = excluded.closed_at,
            updated_at = excluded.updated_at
        """,
        (org, repo, pr_number, author_login, 1 if merged else 0, closed_ts, now),
    )


async def _track_comment_in_d1(payload: dict, env) -> None:
    db = _d1_binding(env)
    if not db:
        return
    comment = payload.get("comment") or {}
    user = comment.get("user") or {}
    if _is_bot(user):
        return
    body = comment.get("body", "")
    if _is_coderabbit_ping(body):
        return
    org = (payload.get("repository") or {}).get("owner", {}).get("login", "")
    login = user.get("login", "")
    created_at = comment.get("created_at")
    if not (org and login):
        return

    await _ensure_leaderboard_schema(db)
    mk = _month_key(_parse_github_timestamp(created_at) if created_at else int(time.time()))
    await _d1_inc_monthly(db, org, mk, login, "comments", 1)


async def _track_review_in_d1(payload: dict, env) -> None:
    db = _d1_binding(env)
    if not db:
        return
    review = payload.get("review") or {}
    reviewer = review.get("user") or {}
    if _is_bot(reviewer):
        return
    pr = payload.get("pull_request") or {}
    org = (payload.get("repository") or {}).get("owner", {}).get("login", "")
    repo = (payload.get("repository") or {}).get("name", "")
    pr_number = pr.get("number")
    reviewer_login = reviewer.get("login", "")
    submitted_at = review.get("submitted_at")
    if not (org and repo and pr_number and reviewer_login):
        return

    await _ensure_leaderboard_schema(db)
    mk = _month_key(_parse_github_timestamp(submitted_at) if submitted_at else int(time.time()))

    # Only first two unique reviewers per PR/month get credit.
    exists = await _d1_first(
        db,
        """
        SELECT 1 FROM leaderboard_review_credits
        WHERE org = ? AND repo = ? AND pr_number = ? AND month_key = ? AND reviewer_login = ?
        """,
        (org, repo, pr_number, mk, reviewer_login),
    )
    if exists:
        return

    cnt_row = await _d1_first(
        db,
        """
        SELECT COUNT(*) AS cnt FROM leaderboard_review_credits
        WHERE org = ? AND repo = ? AND pr_number = ? AND month_key = ?
        """,
        (org, repo, pr_number, mk),
    )
    already = int((cnt_row or {}).get("cnt") or 0)
    if already >= 2:
        return

    await _d1_run(
        db,
        """
        INSERT INTO leaderboard_review_credits (org, repo, pr_number, month_key, reviewer_login, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (org, repo, pr_number, mk, reviewer_login, int(time.time())),
    )
    await _d1_inc_monthly(db, org, mk, reviewer_login, "reviews", 1)


async def _calculate_leaderboard_stats_from_d1(owner: str, env) -> Optional[dict]:
    """Read current-month leaderboard stats from D1 if configured."""
    db = _d1_binding(env)
    if not db:
        return None

    await _ensure_leaderboard_schema(db)
    mk = _month_key()
    start_timestamp, end_timestamp = _month_window(mk)

    monthly_rows = await _d1_all(
        db,
        """
        SELECT user_login, merged_prs, closed_prs, reviews, comments
        FROM leaderboard_monthly_stats
        WHERE org = ? AND month_key = ?
        """,
        (owner, mk),
    )
    open_rows = await _d1_all(
        db,
        """
        SELECT user_login, open_prs
        FROM leaderboard_open_prs
        WHERE org = ?
        """,
        (owner,),
    )

    user_stats = {}

    def ensure(login: str):
        if login not in user_stats:
            user_stats[login] = {
                "openPrs": 0,
                "mergedPrs": 0,
                "closedPrs": 0,
                "reviews": 0,
                "comments": 0,
                "total": 0,
            }

    for row in monthly_rows:
        login = row.get("user_login")
        if not login:
            continue
        ensure(login)
        user_stats[login]["mergedPrs"] = int(row.get("merged_prs") or 0)
        user_stats[login]["closedPrs"] = int(row.get("closed_prs") or 0)
        user_stats[login]["reviews"] = int(row.get("reviews") or 0)
        user_stats[login]["comments"] = int(row.get("comments") or 0)

    for row in open_rows:
        login = row.get("user_login")
        if not login:
            continue
        ensure(login)
        user_stats[login]["openPrs"] = int(row.get("open_prs") or 0)

    for login in user_stats:
        s = user_stats[login]
        s["total"] = (s["openPrs"] * 1) + (s["mergedPrs"] * 10) + (s["closedPrs"] * -2) + (s["reviews"] * 5) + (s["comments"] * 2)

    sorted_users = sorted(
        [{"login": login, **stats} for login, stats in user_stats.items()],
        key=lambda u: (-u["total"], -u["mergedPrs"], -u["reviews"], u["login"].lower())
    )

    return {
        "users": user_stats,
        "sorted": sorted_users,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
    }


async def _fetch_org_repos(org: str, token: str, limit: int = 10) -> list:
    """Fetch repositories in the organization (most recently updated first).
    
    Args:
        org: Organization name
        token: GitHub API token
        limit: Maximum number of repos to return (default: 10 to prevent subrequest limits)
    """
    # Fetch repos sorted by most recently pushed to reduce API calls for active repos
    resp = await github_api("GET", f"/orgs/{org}/repos?sort=pushed&direction=desc&per_page={limit}", token)
    if resp.status != 200:
        return []
    repos = json.loads(await resp.text())
    return repos[:limit]


async def _calculate_leaderboard_stats(owner: str, repos: list, token: str, window_months: int = 1) -> dict:
    """Calculate leaderboard stats across ALL repositories using GitHub Search API.
    
    This approach uses GitHub's search API to query across all org repos efficiently,
    staying well under Cloudflare's 50 subrequest limit even with 50+ repos.
    
    Args:
        owner: Organization or user name
        repos: List of repository objects (used for repo count, not iteration)
        token: GitHub API token
        window_months: Number of months to look back (default: 1 for monthly)
    
    Returns:
        Dictionary with user stats and sorted leaderboard
    """
    now_seconds = int(time.time())
    now = time.gmtime(now_seconds)
    
    # Calculate time window
    start_of_month = time.struct_time((now.tm_year, now.tm_mon, 1, 0, 0, 0, 0, 0, 0))
    start_timestamp = int(time.mktime(start_of_month))
    
    # End of month calculation
    if now.tm_mon == 12:
        end_month = 1
        end_year = now.tm_year + 1
    else:
        end_month = now.tm_mon + 1
        end_year = now.tm_year
    end_of_month = time.struct_time((end_year, end_month, 1, 0, 0, 0, 0, 0, 0))
    end_timestamp = int(time.mktime(end_of_month)) - 1
    
    # Format date range for search API
    start_date = time.strftime("%Y-%m-%d", time.gmtime(start_timestamp))
    end_date = time.strftime("%Y-%m-%d", time.gmtime(end_timestamp))
    
    user_stats = {}
    
    def ensure_user(login: str):
        if login not in user_stats:
            user_stats[login] = {
                "openPrs": 0,
                "mergedPrs": 0,
                "closedPrs": 0,
                "reviews": 0,
                "comments": 0,
                "total": 0
            }
    
    # Use GitHub Search API to query across ALL repos efficiently
    # This dramatically reduces API calls: ~6 calls total vs 150+ with per-repo approach
    
    # 1. Count open PRs (current state across all repos) - 1-2 calls
    page = 1
    while page <= 3:  # Max 3 pages = 300 PRs
        resp = await github_api(
            "GET",
            f"/search/issues?q=is:pr+is:open+org:{owner}&per_page=100&page={page}",
            token
        )
        if resp.status != 200:
            break
        data = json.loads(await resp.text())
        items = data.get("items", [])
        if not items:
            break
        
        for pr in items:
            if pr.get("user") and not _is_bot(pr["user"]):
                login = pr["user"]["login"]
                ensure_user(login)
                user_stats[login]["openPrs"] += 1
        
        if len(items) < 100:
            break
        page += 1
    
    # 2. Fetch merged PRs from this month - 1-2 calls
    page = 1
    while page <= 3:
        resp = await github_api(
            "GET",
            f"/search/issues?q=is:pr+is:merged+org:{owner}+merged:{start_date}..{end_date}&per_page=100&page={page}",
            token
        )
        if resp.status != 200:
            break
        data = json.loads(await resp.text())
        items = data.get("items", [])
        if not items:
            break
        
        for pr in items:
            if pr.get("user") and not _is_bot(pr["user"]):
                login = pr["user"]["login"]
                ensure_user(login)
                user_stats[login]["mergedPrs"] += 1
        
        if len(items) < 100:
            break
        page += 1
    
    # 3. Fetch closed (not merged) PRs from this month - 1-2 calls
    page = 1
    while page <= 3:
        resp = await github_api(
            "GET",
            f"/search/issues?q=is:pr+is:closed+is:unmerged+org:{owner}+closed:{start_date}..{end_date}&per_page=100&page={page}",
            token
        )
        if resp.status != 200:
            break
        data = json.loads(await resp.text())
        items = data.get("items", [])
        if not items:
            break
        
        for pr in items:
            if pr.get("user") and not _is_bot(pr["user"]):
                login = pr["user"]["login"]
                ensure_user(login)
                user_stats[login]["closedPrs"] += 1
        
        if len(items) < 100:
            break
        page += 1
    
    # 4. Search for comments in this month across org (optional, budget permitting)
    # Limit to 2 pages to stay under budget
    since_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_timestamp))
    # Note: Skipping comment counting to conserve API budget
    # With 50 repos, we need to prioritize PRs and reviews
    
    # 5. Fetch reviews from a sample of merged PRs - budget 15 calls
    # Strategy: Get repo URLs from merged PRs, fetch reviews for top 15 PRs
    max_review_calls = 15
    review_calls_used = 0
    
    # Get merged PRs again (already cached in memory from step 2)
    page = 1
    sampled_prs = []
    while page <= 2 and len(sampled_prs) < max_review_calls:
        resp = await github_api(
            "GET",
            f"/search/issues?q=is:pr+is:merged+org:{owner}+merged:{start_date}..{end_date}&per_page=50&page={page}&sort=updated",
            token
        )
        if resp.status != 200:
            break
        data = json.loads(await resp.text())
        items = data.get("items", [])
        if not items:
            break
        
        # Extract repo and PR number from each PR
        for pr in items:
            if len(sampled_prs) >= max_review_calls:
                break
            # Parse repo from repository_url: /repos/{owner}/{repo}
            repo_url = pr.get("repository_url", "")
            if repo_url:
                parts = repo_url.split("/")
                if len(parts) >= 2:
                    repo_name = parts[-1]
                    pr_number = pr.get("number")
                    if repo_name and pr_number:
                        sampled_prs.append((repo_name, pr_number))
        
        if len(items) < 50:
            break
        page += 1
    
    # Fetch reviews for sampled PRs
    for repo_name, pr_number in sampled_prs:
        if review_calls_used >= max_review_calls:
            break
        
        resp_reviews = await github_api(
            "GET",
            f"/repos/{owner}/{repo_name}/pulls/{pr_number}/reviews",
            token
        )
        review_calls_used += 1
        
        if resp_reviews.status == 200:
            reviews = json.loads(await resp_reviews.text())
            pr_review_count = {}
            
            for review in reviews:
                if review.get("user") and not _is_bot(review["user"]):
                    submitted_at = review.get("submitted_at")
                    if submitted_at:
                        review_ts = _parse_github_timestamp(submitted_at)
                        if start_timestamp <= review_ts <= end_timestamp:
                            login = review["user"]["login"]
                            pr_review_count[login] = pr_review_count.get(login, 0) + 1
            
            # Count only first 2 reviewers per PR to avoid spam
            for login in list(pr_review_count.keys())[:2]:
                ensure_user(login)
                user_stats[login]["reviews"] += 1
    
    # Calculate total scores
    # open: +1, merged: +10, closed: -2, reviews: +5, comments: +2
    for login in user_stats:
        s = user_stats[login]
        s["total"] = (s["openPrs"] * 1) + (s["mergedPrs"] * 10) + (s["closedPrs"] * -2) + (s["reviews"] * 5) + (s["comments"] * 2)
    
    # Sort users by total score, then merged PRs, then reviews, then alphabetically
    sorted_users = sorted(
        [{"login": login, **stats} for login, stats in user_stats.items()],
        key=lambda u: (-u["total"], -u["mergedPrs"], -u["reviews"], u["login"].lower())
    )
    
    return {
        "users": user_stats,
        "sorted": sorted_users,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp
    }


def _parse_github_timestamp(ts_str: str) -> int:
    """Parse GitHub ISO 8601 timestamp to Unix timestamp."""
    # GitHub timestamps are like: 2024-03-05T12:34:56Z
    import re
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z", ts_str)
    if match:
        year, month, day, hour, minute, second = map(int, match.groups())
        dt = time.struct_time((year, month, day, hour, minute, second, 0, 0, 0))
        return int(time.mktime(dt))
    return 0


def _format_leaderboard_comment(author_login: str, leaderboard_data: dict, owner: str) -> str:
    """Format a leaderboard comment for a specific user."""
    sorted_users = leaderboard_data["sorted"]
    start_ts = leaderboard_data["start_timestamp"]
    
    # Find author's index
    author_index = -1
    for i, user in enumerate(sorted_users):
        if user["login"] == author_login:
            author_index = i
            break
    
    # Format month display
    month_struct = time.gmtime(start_ts)
    display_month = time.strftime("%B %Y", month_struct)
    
    # Build comment
    comment = LEADERBOARD_MARKER + "\n"
    comment += "## 📊 Monthly Leaderboard\n\n"
    comment += f"Hi @{author_login}! Here's how you rank for {display_month}:\n\n"
    
    # Table header
    comment += "| Rank | User | Open PRs | PRs (merged) | PRs (closed) | Reviews | Comments | Total |\n"
    comment += "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
    
    def row_for(rank: int, u: dict, bold: bool = False, medal: str = "") -> str:
        user_cell = f"**`@{u['login']}`** ✨" if bold else f"`@{u['login']}`"
        rank_cell = f"{medal} #{rank}" if medal else f"#{rank}"
        return (f"| {rank_cell} | {user_cell} | {u['openPrs']} | {u['mergedPrs']} | "
                f"{u['closedPrs']} | {u['reviews']} | {u['comments']} | **{u['total']}** |")
    
    # Show context rows around the author
    if author_index == -1:
        # Author not in leaderboard, show top 3
        for i in range(min(3, len(sorted_users))):
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else ""
            comment += row_for(i + 1, sorted_users[i], False, medal) + "\n"
    else:
        # Show author and neighbors
        if author_index > 0:
            medal = ["🥇", "🥈", "🥉"][author_index - 1] if author_index - 1 < 3 else ""
            comment += row_for(author_index, sorted_users[author_index - 1], False, medal) + "\n"
        
        medal = ["🥇", "🥈", "🥉"][author_index] if author_index < 3 else ""
        comment += row_for(author_index + 1, sorted_users[author_index], True, medal) + "\n"
        
        if author_index < len(sorted_users) - 1:
            comment += row_for(author_index + 2, sorted_users[author_index + 1]) + "\n"
    
    comment += "\n---\n"
    comment += (
        f"**Scoring this month** (across {owner} org): Open PRs (+1 each), Merged PRs (+10), "
        "Closed (not merged) (−2), Reviews (+5; first two per PR in-month), "
        "Comments (+2, excludes CodeRabbit). Run `/leaderboard` on any issue or PR to see your rank!\n"
    )
    
    return comment


async def _post_or_update_leaderboard(owner: str, repo: str, issue_number: int, author_login: str, token: str, env=None) -> None:
    """Post or update a leaderboard comment on an issue/PR."""
    # Prefer D1-backed stats for accurate and scalable org-wide leaderboard.
    leaderboard_data = await _calculate_leaderboard_stats_from_d1(owner, env)

    # Fallback to API-based calculation when D1 is unavailable.
    if leaderboard_data is None:
        # Determine if owner is an org or user only when fallback is needed.
        resp = await github_api("GET", f"/users/{owner}", token)
        if resp.status != 200:
            console.error(f"[Leaderboard] Failed to fetch owner info for {owner}: status={resp.status}")
            await create_comment(
                owner,
                repo,
                issue_number,
                f"@{author_login} I couldn't load leaderboard data right now (owner lookup failed). Please try again shortly.",
                token,
            )
            return

        owner_data = json.loads(await resp.text())
        is_org = owner_data.get("type") == "Organization"
        if is_org:
            repos = await _fetch_org_repos(owner, token)
        else:
            repos = [{"name": repo}]
        leaderboard_data = await _calculate_leaderboard_stats(owner, repos, token)
    
    # Format comment
    comment_body = _format_leaderboard_comment(author_login, leaderboard_data, owner)
    
    # Delete existing leaderboard comment(s), then always create a fresh one.
    resp = await github_api("GET", f"/repos/{owner}/{repo}/issues/{issue_number}/comments?per_page=100", token)
    if resp.status == 200:
        comments = json.loads(await resp.text())
        for c in comments:
            if c.get("body") and LEADERBOARD_MARKER in c["body"]:
                delete_resp = await github_api(
                    "DELETE",
                    f"/repos/{owner}/{repo}/issues/comments/{c['id']}",
                    token,
                )
                if delete_resp.status not in (204, 200):
                    console.error(
                        f"[Leaderboard] Failed to delete old leaderboard comment {c['id']} "
                        f"for {owner}/{repo}#{issue_number}: status={delete_resp.status}"
                    )
    else:
        console.error(
            f"[Leaderboard] Failed to list comments for {owner}/{repo}#{issue_number}: "
            f"status={resp.status}; posting new leaderboard anyway"
        )

    await create_comment(owner, repo, issue_number, comment_body, token)


async def _check_and_close_excess_prs(owner: str, repo: str, pr_number: int, author_login: str, token: str) -> bool:
    """Check if author has too many open PRs and close if needed.
    
    Returns:
        True if PR was closed, False otherwise
    """
    # Search for open PRs by this author
    resp = await github_api(
        "GET",
        f"/search/issues?q=repo:{owner}/{repo}+is:pr+is:open+author:{author_login}&per_page=100",
        token
    )
    
    if resp.status != 200:
        return False
    
    data = json.loads(await resp.text())
    open_prs = data.get("items", [])
    
    # Exclude the current PR from count
    pre_existing_count = len([pr for pr in open_prs if pr["number"] != pr_number])
    
    if pre_existing_count >= MAX_OPEN_PRS_PER_AUTHOR:
        # Close the PR
        msg = (
            f"Hi @{author_login}, thanks for your contribution!\n\n"
            f"This PR is being auto-closed because you currently have {pre_existing_count} "
            f"open PRs in this repository (limit: {MAX_OPEN_PRS_PER_AUTHOR}).\n"
            "Please finish or close some existing PRs before opening new ones.\n\n"
            "If you believe this was closed in error, please contact the maintainers."
        )
        
        await create_comment(owner, repo, pr_number, msg, token)
        
        await github_api(
            "PATCH",
            f"/repos/{owner}/{repo}/pulls/{pr_number}",
            token,
            {"state": "closed"}
        )
        
        return True
    
    return False


async def _check_rank_improvement(owner: str, repo: str, pr_number: int, author_login: str, token: str) -> None:
    """Check if author's rank improved and post congratulatory message."""
    # Get org repos
    resp = await github_api("GET", f"/users/{owner}", token)
    if resp.status != 200:
        return
    
    owner_data = json.loads(await resp.text())
    is_org = owner_data.get("type") == "Organization"
    
    if is_org:
        repos = await _fetch_org_repos(owner, token)
    else:
        repos = [{"name": repo}]
    
    # Calculate 6-month window
    now = int(time.time())
    six_months_ago = now - (6 * 30 * 24 * 60 * 60)  # Approximate
    
    # Count merged PRs in 6-month window for all users
    merged_prs_per_author = {}
    
    # Limit repos to prevent subrequest errors
    for repo_obj in repos[:10]:
        repo_name = repo_obj["name"]
        resp = await github_api(
            "GET",
            f"/repos/{owner}/{repo_name}/pulls?state=closed&per_page=30&sort=updated&direction=desc",
            token
        )
        
        if resp.status == 200:
            prs = json.loads(await resp.text())
            for pr in prs:
                if pr.get("merged_at"):
                    merged_ts = _parse_github_timestamp(pr["merged_at"])
                    if merged_ts >= six_months_ago:
                        pr_author = pr.get("user")
                        if pr_author and not _is_bot(pr_author):
                            login = pr_author["login"]
                            merged_prs_per_author[login] = merged_prs_per_author.get(login, 0) + 1
    
    author_count = merged_prs_per_author.get(author_login, 0)
    
    if author_count == 0:
        return
    
    # Calculate new rank (number of users with more PRs + 1)
    new_rank = len([c for c in merged_prs_per_author.values() if c > author_count]) + 1
    
    # Calculate old rank (before this merge)
    prev_count = author_count - 1
    old_rank = None
    if prev_count > 0:
        old_rank = len([c for c in merged_prs_per_author.values() if c > prev_count]) + 1
    
    # Check if rank improved
    rank_improved = old_rank is None or new_rank < old_rank
    
    if not rank_improved:
        return
    
    # Post congratulatory message
    if old_rank is None:
        msg = (
            f"🎉 Congratulations @{author_login}! "
            f"You've entered the BLT PR leaderboard at **rank #{new_rank}** with this merged PR! "
            "Keep up the great work! 🚀"
        )
    else:
        msg = (
            f"🎉 Congratulations @{author_login}! "
            f"This merged PR has moved you up to **rank #{new_rank}** on the BLT PR leaderboard "
            f"(up from #{old_rank})! Keep up the great work! 🚀"
        )
    
    await create_comment(owner, repo, pr_number, msg, token)


# ---------------------------------------------------------------------------
# Event handlers — mirror the Node.js handler logic exactly
# ---------------------------------------------------------------------------


async def handle_issue_comment(payload: dict, token: str, env=None) -> None:
    comment = payload["comment"]
    issue = payload["issue"]
    if not _is_human(comment["user"]):
        return

    # Persist comments to D1 for leaderboard scoring.
    try:
        await _track_comment_in_d1(payload, env)
    except Exception as exc:
        console.error(f"[Leaderboard] Failed to persist comment event: {exc}")

    body = comment["body"].strip()
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    login = comment["user"]["login"]
    issue_number = issue["number"]
    comment_id = comment.get("id")
    
    # Add eyes reaction immediately to acknowledge command receipt
    if comment_id and (body.startswith(ASSIGN_COMMAND) or body.startswith(UNASSIGN_COMMAND) or body.startswith(LEADERBOARD_COMMAND)):
        await create_reaction(owner, repo, comment_id, "eyes", token)
    
    if body.startswith(ASSIGN_COMMAND):
        await _assign(owner, repo, issue, login, token)
    elif body.startswith(UNASSIGN_COMMAND):
        await _unassign(owner, repo, issue, login, token)
    elif body.startswith(LEADERBOARD_COMMAND):
        try:
            if env is None:
                await _post_or_update_leaderboard(owner, repo, issue_number, login, token)
            else:
                await _post_or_update_leaderboard(owner, repo, issue_number, login, token, env)
        except Exception as exc:
            console.error(f"[Leaderboard] Command failed for {owner}/{repo}#{issue_number}: {exc}")
            await create_comment(
                owner,
                repo,
                issue_number,
                f"@{login} I hit an error while generating the leaderboard. Please try again in a moment.",
                token,
            )


async def _assign(
    owner: str, repo: str, issue: dict, login: str, token: str
) -> None:
    num = issue["number"]
    if issue.get("pull_request"):
        await create_comment(
            owner, repo, num,
            f"@{login} This command only works on issues, not pull requests.",
            token,
        )
        return
    if issue["state"] == "closed":
        await create_comment(
            owner, repo, num,
            f"@{login} This issue is already closed and cannot be assigned.",
            token,
        )
        return
    assignees = [a["login"] for a in issue.get("assignees", [])]
    if login in assignees:
        await create_comment(
            owner, repo, num,
            f"@{login} You are already assigned to this issue.",
            token,
        )
        return
    if len(assignees) >= MAX_ASSIGNEES:
        await create_comment(
            owner, repo, num,
            f"@{login} This issue already has the maximum number of assignees "
            f"({MAX_ASSIGNEES}). Please work on a different issue.",
            token,
        )
        return
    await github_api(
        "POST",
        f"/repos/{owner}/{repo}/issues/{num}/assignees",
        token,
        {"assignees": [login]},
    )
    deadline = time.strftime(
        "%a, %d %b %Y %H:%M:%S UTC",
        time.gmtime(time.time() + ASSIGNMENT_DURATION_HOURS * 3600),
    )
    await create_comment(
        owner, repo, num,
        f"@{login} You have been assigned to this issue! 🎉\n\n"
        f"Please submit a pull request within **{ASSIGNMENT_DURATION_HOURS} hours** "
        f"(by {deadline}).\n\n"
        f"If you need more time or cannot complete the work, please comment "
        f"`{UNASSIGN_COMMAND}` so others can pick it up.\n\n"
        "Happy coding! 🚀 — [OWASP BLT](https://owaspblt.org)",
        token,
    )


async def _unassign(
    owner: str, repo: str, issue: dict, login: str, token: str
) -> None:
    num = issue["number"]
    assignees = [a["login"] for a in issue.get("assignees", [])]
    if login not in assignees:
        await create_comment(
            owner, repo, num,
            f"@{login} You are not currently assigned to this issue.",
            token,
        )
        return
    await github_api(
        "DELETE",
        f"/repos/{owner}/{repo}/issues/{num}/assignees",
        token,
        {"assignees": [login]},
    )
    await create_comment(
        owner, repo, num,
        f"@{login} You have been unassigned from this issue. "
        "Thanks for letting us know! 👍\n\n"
        "The issue is now open for others to pick up.",
        token,
    )


async def handle_issue_opened(
    payload: dict, token: str, blt_api_url: str
) -> None:
    issue = payload["issue"]
    sender = payload["sender"]
    if not _is_human(sender):
        return
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    labels = [lb["name"].lower() for lb in issue.get("labels", [])]
    is_bug = any(lb in BUG_LABELS for lb in labels)
    msg = (
        f"👋 Thanks for opening this issue, @{sender['login']}!\n\n"
        "Our team will review it shortly. In the meantime:\n"
        "- If you'd like to work on this issue, comment `/assign` to get assigned.\n"
        "- Visit [OWASP BLT](https://owaspblt.org) for more information about "
        "our bug bounty platform.\n"
    )
    if is_bug:
        bug_data = await report_bug_to_blt(blt_api_url, {
            "url": issue["html_url"],
            "description": issue["title"],
            "github_url": issue["html_url"],
            "label": labels[0] if labels else "bug",
        })
        if bug_data and bug_data.get("id"):
            msg += (
                "\n🐛 This issue has been automatically reported to "
                "[OWASP BLT](https://owaspblt.org) "
                f"(Bug ID: #{bug_data['id']}). "
                "Thank you for helping improve security!\n"
            )
    await create_comment(owner, repo, issue["number"], msg, token)


async def handle_issue_labeled(
    payload: dict, token: str, blt_api_url: str
) -> None:
    issue = payload["issue"]
    label = payload.get("label") or {}
    label_name = label.get("name", "").lower()
    if label_name not in BUG_LABELS:
        return
    all_labels = [lb["name"].lower() for lb in issue.get("labels", [])]
    # Only report the first time a bug label is added (avoid duplicates)
    if any(lb in BUG_LABELS for lb in all_labels if lb != label_name):
        return
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    bug_data = await report_bug_to_blt(blt_api_url, {
        "url": issue["html_url"],
        "description": issue["title"],
        "github_url": issue["html_url"],
        "label": label.get("name", "bug"),
    })
    if bug_data and bug_data.get("id"):
        await create_comment(
            owner, repo, issue["number"],
            f"🐛 This issue has been reported to [OWASP BLT](https://owaspblt.org) "
            f"(Bug ID: #{bug_data['id']}) after being labeled as "
            f"`{label.get('name', 'bug')}`.",
            token,
        )


async def handle_pull_request_opened(payload: dict, token: str, env=None) -> None:
    pr = payload["pull_request"]
    sender = payload["sender"]
    if not _is_human(sender):
        return
    
    # Skip bots more thoroughly
    if _is_bot(sender):
        return
    
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pr_number = pr["number"]
    author_login = sender["login"]
    
    # Check for too many open PRs and auto-close if needed
    was_closed = await _check_and_close_excess_prs(owner, repo, pr_number, author_login, token)
    if was_closed:
        return  # Stop further processing if auto-closed

    # Track open PR counter in D1.
    await _track_pr_opened_in_d1(payload, env)
    
    # Post welcome message
    body = (
        f"👋 Thanks for opening this pull request, @{author_login}!\n\n"
        "**Before your PR is reviewed, please ensure:**\n"
        "- [ ] Your code follows the project's coding style and guidelines.\n"
        "- [ ] You have written or updated tests for your changes.\n"
        "- [ ] The commit messages are clear and descriptive.\n"
        "- [ ] You have linked any relevant issues (e.g., `Closes #123`).\n\n"
        "🔍 Our team will review your PR shortly. "
        "If you have questions, feel free to ask in the comments.\n\n"
        "🚀 Keep up the great work! — [OWASP BLT](https://owaspblt.org)"
    )
    await create_comment(owner, repo, pr_number, body, token)
    
    # Post leaderboard
    if env is None:
        await _post_or_update_leaderboard(owner, repo, pr_number, author_login, token)
    else:
        await _post_or_update_leaderboard(owner, repo, pr_number, author_login, token, env)


async def handle_pull_request_closed(payload: dict, token: str, env=None) -> None:
    pr = payload["pull_request"]
    sender = payload["sender"]
    if not pr.get("merged"):
        return
    if not _is_human(sender):
        return
    
    # Skip bots more thoroughly
    if _is_bot(pr.get("user", {})):
        return
    
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pr_number = pr["number"]
    author_login = pr["user"]["login"]

    # Track close/merge counters in D1.
    await _track_pr_closed_in_d1(payload, env)
    
    # Post merge congratulations
    body = (
        f"🎉 PR merged! Thanks for your contribution, @{author_login}!\n\n"
        "Your work is now part of the project. Keep contributing to "
        "[OWASP BLT](https://owaspblt.org) and help make the web a safer place! 🛡️"
    )
    await create_comment(owner, repo, pr_number, body, token)
    
    # Check for rank improvement and congratulate if improved
    await _check_rank_improvement(owner, repo, pr_number, author_login, token)
    
    # Post/update leaderboard
    if env is None:
        await _post_or_update_leaderboard(owner, repo, pr_number, author_login, token)
    else:
        await _post_or_update_leaderboard(owner, repo, pr_number, author_login, token, env)


async def handle_pull_request_review_submitted(payload: dict, env=None) -> None:
    """Track review credits in D1 (first two unique reviewers per PR per month)."""
    await _track_review_in_d1(payload, env)


# ---------------------------------------------------------------------------
# Webhook dispatcher
# ---------------------------------------------------------------------------


async def handle_webhook(request, env) -> Response:
    """Verify the GitHub webhook signature and route to the correct handler."""
    body_text = await request.text()
    payload_bytes = body_text.encode("utf-8")

    # Extract header metadata immediately so every webhook invocation is logged.
    delivery_id = request.headers.get("X-GitHub-Delivery", "")
    event = request.headers.get("X-GitHub-Event", "")

    # Parse payload once up front for concise logging fields.
    payload = {}
    payload_parse_error = False
    try:
        payload = json.loads(body_text)
    except Exception:
        payload_parse_error = True

    action = payload.get("action", "") if isinstance(payload, dict) else ""
    installation_id = ((payload.get("installation") or {}).get("id") if isinstance(payload, dict) else None)
    repo_full_name = ((payload.get("repository") or {}).get("full_name") if isinstance(payload, dict) else "")
    sender_login = ((payload.get("sender") or {}).get("login") if isinstance(payload, dict) else "")
    issue_number = ((payload.get("issue") or {}).get("number") if isinstance(payload, dict) else None)
    pr_number = ((payload.get("pull_request") or {}).get("number") if isinstance(payload, dict) else None)
    item_number = issue_number or pr_number or ""

    signature = request.headers.get("X-Hub-Signature-256") or ""
    secret = getattr(env, "WEBHOOK_SECRET", "")
    if secret and not verify_signature(payload_bytes, signature, secret):
        console.log(
            "[BLT][webhook] "
            f"delivery={delivery_id or '-'} event={event or '-'} action={action or '-'} "
            f"repo={repo_full_name or '-'} sender={sender_login or '-'} item={item_number or '-'} "
            f"installation={installation_id or '-'} method={request.method} status=rejected_invalid_signature"
        )
        return _json({"error": "Invalid signature"}, 401)

    if payload_parse_error:
        console.log(
            "[BLT][webhook] "
            f"delivery={delivery_id or '-'} event={event or '-'} action=- repo=- sender=- item=- "
            f"installation=- method={request.method} status=rejected_invalid_json"
        )
        return _json({"error": "Invalid JSON"}, 400)

    console.log(
        "[BLT][webhook] "
        f"delivery={delivery_id or '-'} event={event or '-'} action={action or '-'} "
        f"repo={repo_full_name or '-'} sender={sender_login or '-'} item={item_number or '-'} "
        f"installation={installation_id or '-'} method={request.method} status=received"
    )

    app_id = getattr(env, "APP_ID", "")
    private_key = getattr(env, "PRIVATE_KEY", "")
    token = None
    if installation_id and app_id and private_key:
        token = await get_installation_token(installation_id, app_id, private_key)

    if not token:
        console.error("[BLT] Could not obtain installation token")
        return _json({"error": "Authentication failed"}, 500)

    blt_api_url = getattr(env, "BLT_API_URL", "https://blt-api.owasp-blt.workers.dev")

    try:
        if event == "issue_comment" and action == "created":
            await handle_issue_comment(payload, token, env)
        elif event == "issues":
            if action == "opened":
                await handle_issue_opened(payload, token, blt_api_url)
            elif action == "labeled":
                await handle_issue_labeled(payload, token, blt_api_url)
        elif event == "pull_request":
            if action == "opened":
                await handle_pull_request_opened(payload, token, env)
            elif action == "closed":
                await handle_pull_request_closed(payload, token, env)
        elif event == "pull_request_review" and action == "submitted":
            await handle_pull_request_review_submitted(payload, env)
    except Exception as exc:
        console.error(f"[BLT] Webhook handler error: {exc}")
        return _json({"error": "Internal server error"}, 500)

    return _json({"ok": True})


# ---------------------------------------------------------------------------
# Landing page HTML — separated into src/index_template.py for maintainability.
# Edit public/index.html and regenerate src/index_template.py before deploying.
# ---------------------------------------------------------------------------

_CALLBACK_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BLT GitHub App — Installed!</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link
    rel="stylesheet"
    href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"
    crossorigin="anonymous"
    referrerpolicy="no-referrer"
  />
</head>
<body class="min-h-screen flex items-center justify-center" style="background:#111827;color:#e5e7eb;">
  <div class="text-center rounded-xl p-12 max-w-md w-full mx-4" style="background:#1F2937;border:1px solid #374151;">
    <div class="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-6" style="background:rgba(225,1,1,0.1);">
      <i class="fa-solid fa-circle-check text-3xl" style="color:#E10101;" aria-hidden="true"></i>
    </div>
    <h1 class="text-2xl font-bold text-white mb-4">Installation complete!</h1>
    <p class="leading-relaxed mb-6" style="color:#9ca3af;">
      BLT GitHub App has been successfully installed on your organization.<br />
      Issues and pull requests will now be handled automatically.
    </p>
    <a
      href="https://owaspblt.org"
      target="_blank"
      rel="noopener"
      style="color:#E10101;"
      onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'"
    >
      Visit OWASP BLT <i class="fa-solid fa-arrow-right text-xs" aria-hidden="true"></i>
    </a>
  </div>
</body>
</html>
"""


def _secret_vars_status_html(env) -> str:
    """Generate HTML rows showing whether each secret/config variable is set."""
    _SET_BADGE = (
        '<span class="font-semibold flex items-center gap-1.5" style="color:#4ade80;">'
        '<i class="fa-solid fa-circle-check" aria-hidden="true"></i> Set'
        "</span>"
    )
    _MISSING_BADGE = (
        '<span class="font-semibold flex items-center gap-1.5" style="color:#f87171;">'
        '<i class="fa-solid fa-circle-xmark" aria-hidden="true"></i> Not set'
        "</span>"
    )
    _OPTIONAL_BADGE = (
        '<span class="font-semibold flex items-center gap-1.5" style="color:#9ca3af;">'
        '<i class="fa-solid fa-circle-minus" aria-hidden="true"></i> Not configured'
        "</span>"
    )

    required_vars = ["APP_ID", "PRIVATE_KEY", "WEBHOOK_SECRET"]
    optional_vars = ["GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"]

    rows = [
        '        <div style="border-top:1px solid #374151;margin-top:1rem;padding-top:0.5rem;">',
        '          <p class="text-xs font-semibold uppercase tracking-wider mb-1" style="color:#6b7280;">Secret Variables</p>',
        "        </div>",
    ]
    for name in required_vars:
        is_set = bool(getattr(env, name, ""))
        badge = _SET_BADGE if is_set else _MISSING_BADGE
        rows.append(
            f'        <div class="flex justify-between items-center py-3 text-sm" style="border-bottom:1px solid #374151;">'
            f'<span style="color:#d1d5db;"><code style="font-size:0.75rem;">{name}</code></span>'
            f"{badge}</div>"
        )
    for name in optional_vars:
        is_set = bool(getattr(env, name, ""))
        badge = _SET_BADGE if is_set else _OPTIONAL_BADGE
        rows.append(
            f'        <div class="flex justify-between items-center py-3 text-sm" style="border-bottom:1px solid #374151;">'
            f'<span style="color:#d1d5db;"><code style="font-size:0.75rem;">{name}</code>'
            f' <span style="color:#6b7280;font-size:0.7rem;">(optional)</span></span>'
            f"{badge}</div>"
        )
    return "\n".join(rows)


def _landing_html(app_slug: str, env=None) -> str:
    install_url = (
        f"https://github.com/apps/{app_slug}/installations/new"
        if app_slug
        else "https://github.com/apps/blt-github-app/installations/new"
    )
    year = time.gmtime().tm_year
    secret_vars_html = _secret_vars_status_html(env) if env is not None else ""
    return (
        INDEX_HTML
        .replace("{{INSTALL_URL}}", install_url)
        .replace("{{YEAR}}", str(year))
        .replace("{{SECRET_VARS_STATUS}}", secret_vars_html)
    )


def _callback_html() -> str:
    return _CALLBACK_HTML


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _json(data, status: int = 200) -> Response:
    return Response.new(
        json.dumps(data),
        status=status,
        headers=Headers.new({
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        }.items()),
    )


def _html(html: str, status: int = 200) -> Response:
    return Response.new(
        html,
        status=status,
        headers=Headers.new({"Content-Type": "text/html; charset=utf-8"}.items()),
    )


# ---------------------------------------------------------------------------
# Main entry point — called by the Cloudflare runtime
# ---------------------------------------------------------------------------


async def on_fetch(request, env) -> Response:
    method = request.method
    path = urlparse(str(request.url)).path.rstrip("/") or "/"

    if method == "GET" and path == "/":
        app_slug = getattr(env, "GITHUB_APP_SLUG", "")
        return _html(_landing_html(app_slug, env))

    if method == "GET" and path == "/health":
        return _json({"status": "ok", "service": "BLT GitHub App"})

    if method == "POST" and path == "/api/github/webhooks":
        return await handle_webhook(request, env)

    # GitHub redirects here after a successful installation
    if method == "GET" and path == "/callback":
        return _html(_callback_html())

    return _json({"error": "Not found"}, 404)


# ---------------------------------------------------------------------------
# Scheduled event handler — runs on cron triggers
# ---------------------------------------------------------------------------


async def scheduled(event, env):
    """Handle scheduled cron events to check and unassign stale issues.
    
    This runs periodically (configured in wrangler.toml) to find issues that:
    - Have assignees
    - Were assigned more than ASSIGNMENT_DURATION_HOURS ago
    - Have no linked pull requests
    
    Such issues are automatically unassigned to free them up for other contributors.
    """
    console.log("[CRON] Starting stale assignment check...")
    
    try:
        # Get GitHub App installation token
        app_id = getattr(env, "APP_ID", "")
        private_key = getattr(env, "PRIVATE_KEY", "")
        
        if not app_id or not private_key:
            console.error("[CRON] Missing APP_ID or PRIVATE_KEY")
            return
        
        # For cron jobs, we need to iterate through all installations
        # Get an app JWT first
        jwt_token = await create_github_jwt(app_id, private_key)
        
        # Fetch all installations
        installations_resp = await github_api("GET", "/app/installations", jwt_token)
        if installations_resp.status != 200:
            console.error(f"[CRON] Failed to fetch installations: {installations_resp.status}")
            return
        
        installations = json.loads(await installations_resp.text())
        console.log(f"[CRON] Found {len(installations)} installations")
        
        for installation in installations:
            install_id = installation["id"]
            account = installation["account"]
            account_login = account.get("login", "unknown")
            
            console.log(f"[CRON] Processing installation {install_id} for {account_login}")
            
            # Get installation token
            token = await get_installation_access_token(install_id, jwt_token)
            if not token:
                console.error(f"[CRON] Failed to get token for installation {install_id}")
                continue
            
            # Fetch all repos for this installation (limit to 20 for cron to prevent timeouts)
            repos = []
            if account.get("type") == "Organization":
                repos = await _fetch_org_repos(account_login, token, limit=20)
            else:
                # For user accounts, fetch user repos (limited)
                repos_resp = await github_api("GET", f"/users/{account_login}/repos?per_page=20", token)
                if repos_resp.status == 200:
                    repos = json.loads(await repos_resp.text())
            
            console.log(f"[CRON] Checking {len(repos)} repositories")
            
            # Check each repository for stale assignments
            for repo_data in repos:
                repo_name = repo_data["name"]
                owner = repo_data["owner"]["login"]
                
                await _check_stale_assignments(owner, repo_name, token)
        
        console.log("[CRON] Stale assignment check complete")
        
    except Exception as e:
        console.error(f"[CRON] Error during scheduled task: {e}")


async def _check_stale_assignments(owner: str, repo: str, token: str):
    """Check a repository for stale issue assignments and unassign them."""
    try:
        # Fetch open issues with assignees
        issues_resp = await github_api(
            "GET",
            f"/repos/{owner}/{repo}/issues?state=open&per_page=100",
            token
        )
        
        if issues_resp.status != 200:
            return
        
        issues = json.loads(await issues_resp.text())
        
        # Filter issues that have assignees and are not pull requests
        assigned_issues = [
            issue for issue in issues
            if issue.get("assignees") and "pull_request" not in issue
        ]
        
        if not assigned_issues:
            return
        
        console.log(f"[CRON] Found {len(assigned_issues)} assigned issues in {owner}/{repo}")
        
        current_time = time.time()
        deadline_seconds = ASSIGNMENT_DURATION_HOURS * 3600
        
        for issue in assigned_issues:
            issue_number = issue["number"]
            assignees = issue.get("assignees", [])
            
            # Check if issue has linked PRs
            timeline_resp = await github_api(
                "GET",
                f"/repos/{owner}/{repo}/issues/{issue_number}/timeline",
                token
            )
            
            if timeline_resp.status != 200:
                continue
            
            timeline = json.loads(await timeline_resp.text())
            
            # Look for assignment events and cross-referenced PRs
            assignment_time = None
            has_linked_pr = False
            
            for event in timeline:
                event_type = event.get("event")
                
                # Track the most recent assignment
                if event_type == "assigned":
                    created_at = event.get("created_at", "")
                    if created_at:
                        event_timestamp = _parse_github_timestamp(created_at)
                        if event_timestamp:
                            assignment_time = event_timestamp
                
                # Check for cross-referenced PRs
                if event_type == "cross-referenced":
                    source = event.get("source", {})
                    if source.get("type") == "issue" and "pull_request" in source.get("issue", {}):
                        has_linked_pr = True
                        break
            
            # If no assignment time found in timeline, use updated_at as fallback
            if assignment_time is None:
                updated_at = issue.get("updated_at", "")
                if updated_at:
                    assignment_time = _parse_github_timestamp(updated_at)
            
            # Skip if we couldn't determine assignment time
            if assignment_time is None:
                continue
            
            time_elapsed = current_time - assignment_time
            
            # Unassign if deadline passed and no linked PR
            if time_elapsed > deadline_seconds and not has_linked_pr:
                hours_elapsed = int(time_elapsed / 3600)
                
                console.log(
                    f"[CRON] Unassigning stale issue {owner}/{repo}#{issue_number} "
                    f"(assigned {hours_elapsed}h ago, no PR)"
                )
                
                # Unassign all assignees
                assignee_logins = [a["login"] for a in assignees]
                await github_api(
                    "DELETE",
                    f"/repos/{owner}/{repo}/issues/{issue_number}/assignees",
                    token,
                    {"assignees": assignee_logins}
                )
                
                # Post a comment explaining the unassignment
                assignee_mentions = ", ".join(f"@{login}" for login in assignee_logins)
                await create_comment(
                    owner, repo, issue_number,
                    f"{assignee_mentions} This issue has been automatically unassigned because "
                    f"the {ASSIGNMENT_DURATION_HOURS}-hour deadline has passed without a linked pull request.\n\n"
                    f"The issue is now available for others to claim. If you'd still like to work on this, "
                    f"please comment `{ASSIGN_COMMAND}` again.\n\n"
                    "Thank you for your interest! 🙏 — [OWASP BLT](https://owaspblt.org)",
                    token
                )
    
    except Exception as e:
        console.error(f"[CRON] Error checking {owner}/{repo}: {e}")
