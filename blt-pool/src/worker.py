"""BLT-Pool — Mentor Matching & GitHub Automation Platform.

A dual-purpose platform that:
1. Connects contributors with mentors through a shared mentor pool
2. Automates GitHub workflows (issue assignment, leaderboard, webhooks)

Homepage (/) displays the mentor grid with availability and assignments.
GitHub App documentation and installation at /github-app
(legacy alias: /github-app).

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
import calendar
import hashlib
import hmac as _hmac
import html as _html_mod
import json
import os
import re
import time
from typing import Optional, Tuple
from urllib.parse import quote, urlparse

from js import Headers, Response, console, fetch  # Cloudflare Workers JS bindings
from index_template import GITHUB_PAGE_HTML  # Landing page HTML template
from services.admin import AdminService, has_merged_pr_in_org
from services.mentor_seed import INITIAL_MENTORS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Backward-compatible alias kept for tests and older imports after mentor seed
# data moved to ``services.mentor_seed``.
_INITIAL_MENTORS = INITIAL_MENTORS

ASSIGN_COMMAND = "/assign"
UNASSIGN_COMMAND = "/unassign"
APPROVE_COMMAND = "/approve"
DENY_COMMAND = "/deny"
LEADERBOARD_COMMAND = "/leaderboard"
MAX_ASSIGNEES = 1
ASSIGNMENT_DURATION_HOURS = 8
BUG_LABELS = {"bug", "vulnerability", "security"}
HELP_WANTED_LABEL = "help wanted"
TRIAGE_REVIEWER = "donnieblt"

# ---------------------------------------------------------------------------
# Mentor pool — slash commands and label names
# ---------------------------------------------------------------------------

MENTOR_COMMAND = "/mentor"
UNMENTOR_COMMAND = "/unmentor"
MENTOR_PAUSE_COMMAND = "/mentor-pause"
HANDOFF_COMMAND = "/handoff"
REMATCH_COMMAND = "/rematch"
NEEDS_MENTOR_LABEL = "needs-mentor"
MENTOR_ASSIGNED_LABEL = "mentor-assigned"
NEEDS_APPROVAL_LABEL = "needs-approval"
NEEDS_APPROVAL_LABEL_COLOR = "e11d48"
MENTOR_MAX_MENTEES = 3
MENTOR_STALE_DAYS = 14
MENTOR_LABEL_COLOR = "7057ff"
MENTOR_ASSIGNED_LABEL_COLOR = "0075ca"
# Issues with these labels bypass mentor auto-assignment (go to core maintainers).
SECURITY_BYPASS_LABELS = {"security", "vulnerability", "security-sensitive", "private-security"}
# Seconds in a day — used for stale-assignment threshold calculations.
_SECONDS_PER_DAY = 86400
# TTL for cached GitHub-sourced all-time mentor stats in D1 (24 hours).
_MENTOR_STATS_CACHE_TTL = 86400
# When True, one active mentor is auto-requested as a reviewer on every newly
# opened PR using a deterministic round-robin order (PR number mod pool size).
# Set to False (default) to keep the existing behaviour of only requesting the
# mentor when the PR explicitly closes a mentored issue.
# This default can also be overridden at runtime by setting the Cloudflare
# Worker environment variable ``MENTOR_AUTO_PR_REVIEWER_ENABLED=true``.
MENTOR_AUTO_PR_REVIEWER_ENABLED = False

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
    h = {
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "BLT-Pool/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return Headers.new(h.items())


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
            "User-Agent": "BLT-Pool/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }.items()),
    )
    if resp.status != 201:
        console.error(f"[BLT] Failed to get installation token: {resp.status}")
        return None
    data = json.loads(await resp.text())
    return data.get("token")


async def get_installation_access_token(installation_id: int, jwt_token: str) -> Optional[str]:
    """Exchange a prebuilt GitHub App JWT for an installation access token."""
    resp = await fetch(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        method="POST",
        headers=Headers.new({
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "BLT-Pool/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }.items()),
    )
    if resp.status != 201:
        console.error(f"[BLT] Failed to get installation access token: {resp.status}")
        return None
    data = json.loads(await resp.text())
    return data.get("token")


async def create_comment(
    owner: str, repo: str, number: int, body: str, token: str
) -> None:
    """Post a comment on a GitHub issue or pull request."""
    resp = await github_api(
        "POST",
        f"/repos/{owner}/{repo}/issues/{number}/comments",
        token,
        {"body": body},
    )
    if resp.status not in (200, 201):
        try:
            err_text = await resp.text()
        except Exception:
            err_text = "<no response body>"
        console.error(
            f"[GitHub] Failed to create comment on {owner}/{repo}#{number}: "
            f"status={resp.status} body={err_text[:300]}"
        )


async def create_reaction(
    owner: str, repo: str, comment_id: int, reaction: str, token: str
) -> None:
    """Add a reaction to a comment. Common reactions: +1, -1, laugh, confused, heart, hooray, rocket, eyes."""
    resp = await github_api(
        "POST",
        f"/repos/{owner}/{repo}/issues/comments/{comment_id}/reactions",
        token,
        {"content": reaction},
    )
    if resp.status not in (200, 201):
        try:
            err_text = await resp.text()
        except Exception:
            err_text = "<no response body>"
        console.error(
            f"[GitHub] Failed to create reaction on {owner}/{repo} comment={comment_id}: "
            f"status={resp.status} body={err_text[:300]}"
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


async def _is_maintainer(owner: str, repo: str, login: str, token: str) -> bool:
    """Return True if ``login`` has admin or maintain permission in the repo.

    Uses the GitHub collaborator permission endpoint.  Returns False on any
    API error (fail-closed).
    """
    try:
        resp = await github_api(
            "GET",
            f"/repos/{owner}/{repo}/collaborators/{login}/permission",
            token,
        )
        if resp.status != 200:
            return False
        data = json.loads(await resp.text())
        return data.get("permission", "") in ("admin", "maintain")
    except Exception:
        return False


def _extract_command(body: str) -> Optional[str]:
    """Extract a supported slash command from comment body (case-insensitive)."""
    if not body:
        return None
    tokens = body.strip().split()
    if not tokens:
        return None
    supported = {
        ASSIGN_COMMAND,
        UNASSIGN_COMMAND,
        APPROVE_COMMAND,
        DENY_COMMAND,
        LEADERBOARD_COMMAND,
        MENTOR_COMMAND,
        UNMENTOR_COMMAND,
        MENTOR_PAUSE_COMMAND,
        HANDOFF_COMMAND,
        REMATCH_COMMAND,
    }
    for t in tokens:
        tok = t.strip().lower().rstrip(".,!?:;")
        if tok in supported:
            return tok
    return None


# ---------------------------------------------------------------------------
# Leaderboard — Calculation & Display
# ---------------------------------------------------------------------------

# Leaderboard configuration constants
LEADERBOARD_MARKER = "<!-- leaderboard-bot -->"
REVIEWER_LEADERBOARD_MARKER = "<!-- reviewer-leaderboard-bot -->"
MERGED_PR_COMMENT_MARKER = "<!-- merged-pr-comment-bot -->"
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
    start_ts = int(calendar.timegm(start_struct))
    if m == 12:
        next_struct = time.struct_time((y + 1, 1, 1, 0, 0, 0, 0, 0, 0))
    else:
        next_struct = time.struct_time((y, m + 1, 1, 0, 0, 0, 0, 0, 0))
    end_ts = int(calendar.timegm(next_struct)) - 1
    return start_ts, end_ts


def _d1_binding(env):
    """Return D1 binding object if configured, otherwise None."""
    db = getattr(env, "LEADERBOARD_DB", None) if env else None
    return db


async def _d1_run(db, sql: str, params: tuple = ()):
    try:
        stmt = db.prepare(sql)
        if params:
            stmt = stmt.bind(*params)
        result = await stmt.run()
        return result
    except Exception as e:
        console.error(f"[D1.run] Error executing {sql[:60]}: {e}")
        raise


def _to_py(value):
    """Best-effort conversion for JS proxy values returned by Workers runtime."""
    try:
        from pyodide.ffi import to_py  # noqa: PLC0415 - runtime import
        return to_py(value)
    except Exception:
        return value


async def _d1_all(db, sql: str, params: tuple = ()) -> list:
    stmt = db.prepare(sql)
    if params:
        stmt = stmt.bind(*params)
    raw_result = await stmt.all()

    # Cloudflare D1 returns JS proxy objects at runtime; serialize through JS JSON
    # first to reliably convert to Python dict/list structures.
    try:
        from js import JSON as JS_JSON  # noqa: PLC0415 - runtime import
        js_json = JS_JSON.stringify(raw_result)
        parsed = json.loads(str(js_json))
        rows = parsed.get("results") if isinstance(parsed, dict) else None
        if isinstance(rows, list):
            return rows
    except Exception:
        pass

    # Fallback path for local tests or non-JS proxy values.
    result = _to_py(raw_result)
    rows = None
    if isinstance(result, dict):
        rows = result.get("results")
    if rows is None:
        try:
            rows = result.get("results")
        except Exception:
            rows = getattr(result, "results", None)

    rows = _to_py(rows)
    if rows is None:
        return []
    if isinstance(rows, list):
        return rows
    try:
        return list(rows)
    except Exception:
        return []


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
    await _d1_run(
        db,
        """
        CREATE TABLE IF NOT EXISTS leaderboard_backfill_state (
            org TEXT NOT NULL,
            month_key TEXT NOT NULL,
            next_page INTEGER NOT NULL DEFAULT 1,
            completed INTEGER NOT NULL DEFAULT 0,
            updated_at INTEGER NOT NULL,
            PRIMARY KEY (org, month_key)
        )
        """,
    )
    await _d1_run(
        db,
        """
        CREATE TABLE IF NOT EXISTS leaderboard_backfill_repo_done (
            org TEXT NOT NULL,
            month_key TEXT NOT NULL,
            repo TEXT NOT NULL,
            updated_at INTEGER NOT NULL,
            PRIMARY KEY (org, month_key, repo)
        )
        """,
    )
    await _d1_run(
        db,
        """
        CREATE TABLE IF NOT EXISTS mentor_assignments (
            org TEXT NOT NULL,
            mentor_login TEXT NOT NULL,
            issue_repo TEXT NOT NULL,
            issue_number INTEGER NOT NULL,
            assigned_at INTEGER NOT NULL,
            mentee_login TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (org, issue_repo, issue_number)
        )
        """,
    )
    # Migration: add mentee_login column to existing tables that pre-date this field.
    try:
        await _d1_run(
            db,
            "ALTER TABLE mentor_assignments ADD COLUMN mentee_login TEXT NOT NULL DEFAULT ''",
        )
    except Exception:
        pass  # Column already exists — ignore the error.
    await _d1_run(
        db,
        """
        CREATE TABLE IF NOT EXISTS mentors (
            github_username TEXT NOT NULL PRIMARY KEY,
            name TEXT NOT NULL,
            specialties TEXT NOT NULL DEFAULT '[]',
            max_mentees INTEGER NOT NULL DEFAULT 3,
            active INTEGER NOT NULL DEFAULT 1,
            timezone TEXT NOT NULL DEFAULT '',
            referred_by TEXT NOT NULL DEFAULT ''
        )
        """,
    )
    await _d1_run(
        db,
        """
        CREATE TABLE IF NOT EXISTS mentor_stats_cache (
            org TEXT NOT NULL,
            github_username TEXT NOT NULL,
            merged_prs INTEGER NOT NULL DEFAULT 0,
            reviews INTEGER NOT NULL DEFAULT 0,
            fetched_at INTEGER NOT NULL,
            PRIMARY KEY (org, github_username)
        )
        """,
    )
    await _populate_mentors_table(db)


# ---------------------------------------------------------------------------
# Mentor table helpers
# ---------------------------------------------------------------------------

async def _populate_mentors_table(db) -> None:
    """Seed the mentors table with the initial mentor list (idempotent).

    Uses INSERT OR IGNORE so that existing rows are never overwritten; safe
    to call on every cold start.
    """
    for m in INITIAL_MENTORS:
        try:
            await _d1_run(
                db,
                """
                INSERT OR IGNORE INTO mentors
                    (github_username, name, specialties, max_mentees, active, timezone, referred_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    m["github_username"],
                    m["name"],
                    json.dumps(m.get("specialties") or []),
                    m.get("max_mentees", 3),
                    1 if m.get("active", True) else 0,
                    m.get("timezone", "") or "",
                    m.get("referred_by", "") or "",
                ),
            )
        except Exception as exc:
            console.error(f"[MentorPool] Failed to seed mentor {m['github_username']}: {exc}")


async def _load_mentors_from_d1(db) -> list:
    """Load the mentor list from the D1 ``mentors`` table.

    Returns a list of mentor dicts compatible with the rest of the codebase
    (same keys as the old YAML format).  Returns ``[]`` on error.
    """
    try:
        await _ensure_leaderboard_schema(db)
        rows = await _d1_all(
            db,
            "SELECT github_username, name, specialties, max_mentees, active, timezone, referred_by FROM mentors",
        )
        mentors = []
        for row in rows:
            try:
                specialties = json.loads(row.get("specialties") or "[]")
            except Exception:
                specialties = []
            mentors.append({
                "github_username": row["github_username"],
                "name": row["name"],
                "specialties": specialties,
                "max_mentees": int(row.get("max_mentees") or 3),
                "active": bool(row.get("active", 1)),
                "timezone": row.get("timezone") or "",
                "referred_by": row.get("referred_by") or "",
            })
        console.log(f"[MentorPool] Loaded {len(mentors)} mentors from D1")
        return mentors
    except Exception as exc:
        console.error(f"[MentorPool] Failed to load mentors from D1: {exc}")
        return []


async def _d1_add_mentor(
    db,
    github_username: str,
    name: str,
    specialties: list,
    max_mentees: int = 3,
    active: bool = True,
    timezone: str = "",
    referred_by: str = "",
) -> None:
    """Insert or replace a mentor row in the D1 ``mentors`` table."""
    await _d1_run(
        db,
        """
        INSERT INTO mentors
            (github_username, name, specialties, max_mentees, active, timezone, referred_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(github_username) DO UPDATE SET
            name        = excluded.name,
            specialties = excluded.specialties,
            max_mentees = excluded.max_mentees,
            active      = excluded.active,
            timezone    = excluded.timezone,
            referred_by = excluded.referred_by
        """,
        (
            github_username,
            name,
            json.dumps(specialties),
            max_mentees,
            1 if active else 0,
            timezone or "",
            referred_by or "",
        ),
    )


async def _d1_record_mentor_assignment(
    db, org: str, mentor_login: str, repo: str, issue_number: int, mentee_login: str = ""
) -> None:
    """Upsert a mentor→issue assignment into D1 for load-map tracking."""
    now = int(time.time())
    try:
        await _d1_run(
            db,
            """
            INSERT INTO mentor_assignments (org, mentor_login, issue_repo, issue_number, assigned_at, mentee_login)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(org, issue_repo, issue_number) DO UPDATE SET
                mentor_login = excluded.mentor_login,
                mentee_login = excluded.mentee_login,
                assigned_at  = excluded.assigned_at
            """,
            (org, mentor_login, repo, issue_number, now, mentee_login),
        )
        console.log(f"[D1] Recorded mentor assignment: @{mentor_login} → {org}/{repo}#{issue_number}")
    except Exception as exc:
        console.error(f"[D1] Failed to record mentor assignment: {exc}")


async def _d1_remove_mentor_assignment(db, org: str, repo: str, issue_number: int) -> None:
    """Remove a mentor assignment record from D1 (used on handoff/issue close)."""
    try:
        await _d1_run(
            db,
            "DELETE FROM mentor_assignments WHERE org = ? AND issue_repo = ? AND issue_number = ?",
            (org, repo, issue_number),
        )
        console.log(f"[D1] Removed mentor assignment: {org}/{repo}#{issue_number}")
    except Exception as exc:
        console.error(f"[D1] Failed to remove mentor assignment: {exc}")


async def _d1_get_mentor_loads(db, org: str) -> dict:
    """Return a mapping of mentor_login → active assignment count from D1."""
    try:
        rows = await _d1_all(
            db,
            """
            SELECT mentor_login, COUNT(*) as cnt
            FROM mentor_assignments
            WHERE org = ?
            GROUP BY mentor_login
            """,
            (org,),
        )
        return {
            row["mentor_login"]: int(row.get("cnt") or 0)
            for row in rows
            if row.get("mentor_login")
        }
    except Exception as exc:
        console.error(f"[D1] Failed to get mentor loads: {exc}")
        return {}


async def _d1_get_active_assignments(db, org: str) -> list:
    """Return all active mentor assignments from D1 for the given org.

    Returns a list of dicts with keys: org, mentor_login, mentee_login, issue_repo, issue_number, assigned_at.
    Returns an empty list when D1 is unavailable or the query fails.
    """
    try:
        rows = await _d1_all(
            db,
            """
            SELECT org, mentor_login, mentee_login, issue_repo, issue_number, assigned_at
            FROM mentor_assignments
            WHERE org = ?
            ORDER BY assigned_at DESC
            """,
            (org,),
        )
        return [
            {
                "org": row.get("org", org),
                "mentor_login": row.get("mentor_login", ""),
                "mentee_login": row.get("mentee_login", ""),
                "issue_repo": row.get("issue_repo", ""),
                "issue_number": int(row.get("issue_number") or 0),
                "assigned_at": int(row.get("assigned_at") or 0),
            }
            for row in rows
            if row.get("mentor_login") and row.get("issue_repo")
        ]
    except Exception as exc:
        console.error(f"[D1] Failed to get active assignments: {exc}")
        return []


def _time_ago(ts: int) -> str:
    """Return a human-readable 'X time ago' string for a Unix timestamp."""
    diff = int(time.time()) - ts
    if diff < 60:
        return "just now"
    if diff < 3600:
        m = diff // 60
        return f"{m} minute{'s' if m != 1 else ''} ago"
    if diff < 86400:
        h = diff // 3600
        return f"{h} hour{'s' if h != 1 else ''} ago"
    if diff < 86400 * 30:
        d = diff // 86400
        return f"{d} day{'s' if d != 1 else ''} ago"
    if diff < 86400 * 365:
        mo = diff // (86400 * 30)
        return f"{mo} month{'s' if mo != 1 else ''} ago"
    y = diff // (86400 * 365)
    return f"{y} year{'s' if y != 1 else ''} ago"


async def _d1_get_user_comment_totals(db, org: str, logins: list) -> dict:
    """Return total all-time comment counts per user from leaderboard_monthly_stats.

    Args:
        db:     D1 database binding.
        org:    GitHub organisation name.
        logins: List of GitHub usernames to look up.

    Returns a ``{login: total_comments}`` mapping.  Missing users default to 0.
    """
    if not logins:
        return {}
    try:
        placeholders = ",".join("?" for _ in logins)
        rows = await _d1_all(
            db,
            f"""
            SELECT user_login, COALESCE(SUM(comments), 0) AS total_comments
            FROM leaderboard_monthly_stats
            WHERE org = ? AND user_login IN ({placeholders})
            GROUP BY user_login
            """,
            (org, *logins),
        )
        return {
            row["user_login"]: int(row.get("total_comments") or 0)
            for row in rows
            if row.get("user_login")
        }
    except Exception as exc:
        console.error(f"[D1] Failed to get user comment totals: {exc}")
        return {}


async def _d1_inc_open_pr(db, org: str, user_login: str, delta: int) -> None:
    now = int(time.time())
    try:
        result = await _d1_run(
            db,
            """
            INSERT INTO leaderboard_open_prs (org, user_login, open_prs, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(org, user_login) DO UPDATE SET
                open_prs = CASE
                    WHEN leaderboard_open_prs.open_prs + excluded.open_prs < 0 THEN 0
                    ELSE leaderboard_open_prs.open_prs + excluded.open_prs
                END,
                updated_at = excluded.updated_at
            """,
            (org, user_login, delta, now),
        )
        console.log(f"[D1] Inserted/updated open PR count org={org} user={user_login} count={delta}")
    except Exception as e:
        console.error(f"[D1] Failed to update open PRs org={org} user={user_login}: {e}")


async def _d1_inc_monthly(db, org: str, month_key: str, user_login: str, field: str, delta: int = 1) -> None:
    now = int(time.time())
    if field not in {"merged_prs", "closed_prs", "reviews", "comments"}:
        return
    try:
        result = await _d1_run(
            db,
            f"""
            INSERT INTO leaderboard_monthly_stats (org, month_key, user_login, {field}, updated_at)
            VALUES (?, ?, ?, CASE WHEN ? < 0 THEN 0 ELSE ? END, ?)
            ON CONFLICT(org, month_key, user_login) DO UPDATE SET
                {field} = CASE
                    WHEN leaderboard_monthly_stats.{field} + ? < 0 THEN 0
                    ELSE leaderboard_monthly_stats.{field} + ?
                END,
                updated_at = excluded.updated_at
            """,
            (org, month_key, user_login, delta, delta, now, delta, delta),
        )
        console.log(f"[D1] Updated {field} org={org} month={month_key} user={user_login} +{delta}")
    except Exception as e:
        console.error(f"[D1] Failed to update {field} org={org} month={month_key} user={user_login}: {e}")


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


async def _track_pr_reopened_in_d1(payload: dict, env) -> None:
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
        "SELECT state, merged, closed_at FROM leaderboard_pr_state WHERE org = ? AND repo = ? AND pr_number = ?",
        (org, repo, pr_number),
    )

    # Reopening should reverse the previous close/merge credit so the final
    # state remains accurate when the PR is closed again later.
    if existing and existing.get("state") == "closed":
        prev_merged = int(existing.get("merged") or 0)
        prev_closed_at = int(existing.get("closed_at") or 0)
        prev_mk = _month_key(prev_closed_at) if prev_closed_at else _month_key()
        field = "merged_prs" if prev_merged else "closed_prs"
        await _d1_inc_monthly(db, org, prev_mk, author_login, field, -1)

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
    # Ignore slash commands so bot commands do not inflate leaderboard comments.
    if _extract_command(body):
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
        console.log("[D1] REVIEW: No DB binding")
        return
    review = payload.get("review") or {}
    reviewer = review.get("user") or {}
    if _is_bot(reviewer):
        bot_name = reviewer.get("login", "unknown")
        console.log(f"[D1] REVIEW: Skipped bot {bot_name}")
        return
    pr = payload.get("pull_request") or {}
    org = (payload.get("repository") or {}).get("owner", {}).get("login", "")
    repo = (payload.get("repository") or {}).get("name", "")
    pr_number = pr.get("number")
    reviewer_login = reviewer.get("login", "")
    submitted_at = review.get("submitted_at")
    if not (org and repo and pr_number and reviewer_login):
        console.log(f"[D1] REVIEW: Missing fields org={bool(org)} repo={bool(repo)} pr={pr_number} reviewer={reviewer_login}")
        return
    
    console.log(f"[D1] REVIEW: Processing {reviewer_login} reviewing {org}/{repo}#{pr_number}")

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
        console.error("[D1] No D1 binding available")
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

    console.log(f"[D1] Queried org={owner} mk={mk}: {len(monthly_rows or [])} monthly, {len(open_rows or [])} open")
    if not monthly_rows and not open_rows:
        console.log(f"[D1] WARNING: No D1 data found for org={owner}")

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


async def _get_backfill_state(db, owner: str, month_key: str) -> dict:
    row = await _d1_first(
        db,
        """
        SELECT next_page, completed FROM leaderboard_backfill_state
        WHERE org = ? AND month_key = ?
        """,
        (owner, month_key),
    )
    if row:
        return {
            "next_page": int(row.get("next_page") or 1),
            "completed": bool(int(row.get("completed") or 0)),
        }
    return {"next_page": 1, "completed": False}


async def _set_backfill_state(db, owner: str, month_key: str, next_page: int, completed: bool) -> None:
    try:
        await _d1_run(
            db,
            """
            INSERT INTO leaderboard_backfill_state (org, month_key, next_page, completed, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(org, month_key) DO UPDATE SET
                next_page = excluded.next_page,
                completed = excluded.completed,
                updated_at = excluded.updated_at
            """,
            (owner, month_key, next_page, 1 if completed else 0, int(time.time())),
        )
        console.log(f"[Backfill] State updated: org={owner} month={month_key} next_page={next_page} completed={completed}")
    except Exception as e:
        console.error(f"[Backfill] Failed to update state: {e}")


async def _run_incremental_backfill(owner: str, token: str, env, repos_per_request: int = 5) -> Optional[dict]:
    """Backfill leaderboard data in small chunks and report progress for user-facing notes."""
    db = _d1_binding(env)
    if not db:
        console.error("[Backfill] No D1 binding available")
        return None

    await _ensure_leaderboard_schema(db)
    month_key = _month_key()
    start_ts, end_ts = _month_window(month_key)
    start_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_ts))

    state = await _get_backfill_state(db, owner, month_key)
    console.log(f"[Backfill] Current state: page={state['next_page']}, completed={state['completed']}")
    if state["completed"]:
        console.log(f"[Backfill] Already completed for {owner}/{month_key}")
        return {"ran": False, "completed": True, "processed": 0, "next_page": state["next_page"]}

    page = state["next_page"]
    console.log(f"[Backfill] Fetching repos page {page} for {owner}")
    repos_resp = await github_api(
        "GET",
        f"/orgs/{owner}/repos?sort=full_name&direction=asc&per_page={repos_per_request}&page={page}",
        token,
    )
    if repos_resp.status != 200:
        console.error(f"[Backfill] Failed to fetch repo page {page}: status={repos_resp.status}")
        return {"ran": False, "completed": False, "processed": 0, "next_page": page}

    repos = json.loads(await repos_resp.text())
    console.log(f"[Backfill] Got {len(repos)} repos on page {page}")
    if not repos:
        console.log(f"[Backfill] No more repos, marking backfill complete")
        await _set_backfill_state(db, owner, month_key, page, True)
        return {"ran": False, "completed": True, "processed": 0, "next_page": page}

    processed = 0
    for repo_obj in repos:
        repo_name = repo_obj.get("name")
        if not repo_name:
            continue
        console.log(f"[Backfill] Backfilling repo {owner}/{repo_name}")
        seeded = await _backfill_repo_month_if_needed(owner, repo_name, token, env, month_key, start_ts, end_ts)
        if seeded:
            processed += 1
            console.log(f"[Backfill] Seeded {owner}/{repo_name} (total processed this run: {processed})")
        else:
            console.log(f"[Backfill] Skipped {owner}/{repo_name} (already seeded or failed)")

    done = len(repos) < repos_per_request
    console.log(f"[Backfill] Processed {processed} repos, done={done}")
    await _set_backfill_state(db, owner, month_key, page + 1, done)
    return {
        "ran": True,
        "completed": done,
        "processed": processed,
        "next_page": page + 1,
        "month_key": month_key,
        "since": start_iso,
    }


async def _backfill_repo_month_if_needed(
    owner: str,
    repo_name: str,
    token: str,
    env,
    month_key: Optional[str] = None,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
) -> bool:
    """Backfill leaderboard stats for one repo once per month. Returns True if newly seeded."""
    db = _d1_binding(env)
    if not db:
        console.error(f"[Backfill] No D1 binding available for {owner}/{repo_name}")
        return False

    await _ensure_leaderboard_schema(db)
    mk = month_key or _month_key()
    if start_ts is None or end_ts is None:
        start_ts, end_ts = _month_window(mk)

    already = await _d1_first(
        db,
        """
        SELECT 1 FROM leaderboard_backfill_repo_done
        WHERE org = ? AND month_key = ? AND repo = ?
        """,
        (owner, mk, repo_name),
    )
    if already:
        console.log(f"[Backfill] Repo {owner}/{repo_name} already seeded for {mk}")
        return False

    console.log(f"[Backfill] Starting backfill for {owner}/{repo_name} month={mk}")

    # Load all PR numbers already tracked via webhooks for this repo to avoid
    # double-counting PRs that were already processed by webhook event handlers.
    # Also load the recorded state so we can self-heal PRs that were tracked as
    # 'open' but whose close/merge webhook was missed.
    tracked_rows = await _d1_all(
        db,
        "SELECT pr_number, state FROM leaderboard_pr_state WHERE org = ? AND repo = ?",
        (owner, repo_name),
    )
    already_tracked_state = {int(row["pr_number"]): row.get("state", "") for row in (tracked_rows or [])}
    already_tracked = set(already_tracked_state.keys())
    console.log(f"[Backfill] {len(already_tracked)} PRs already tracked for {owner}/{repo_name}")

    now_ts = int(time.time())

    # Open PRs snapshot for this repo.
    open_resp = await github_api(
        "GET",
        f"/repos/{owner}/{repo_name}/pulls?state=open&per_page=100",
        token,
    )
    if open_resp.status == 200:
        open_prs = json.loads(await open_resp.text())
        open_by_user = {}
        for pr in open_prs:
            user = pr.get("user") or {}
            if _is_bot(user):
                continue
            login = user.get("login")
            pr_number = pr.get("number")
            if not login or not pr_number:
                continue
            if pr_number in already_tracked:
                console.log(f"[Backfill] Skipping open PR #{pr_number} (already tracked via webhook)")
                continue
            open_by_user[login] = open_by_user.get(login, 0) + 1
            # Record in pr_state so webhook handlers can coordinate future state changes.
            await _d1_run(
                db,
                """
                INSERT INTO leaderboard_pr_state (org, repo, pr_number, author_login, state, merged, closed_at, updated_at)
                VALUES (?, ?, ?, ?, 'open', 0, NULL, ?)
                ON CONFLICT(org, repo, pr_number) DO NOTHING
                """,
                (owner, repo_name, pr_number, login, now_ts),
            )
            already_tracked.add(pr_number)
            already_tracked_state[pr_number] = "open"
        console.log(f"[Backfill] Found {len(open_prs)} open PRs, {len(open_by_user)} unique users (new)")
        for login, cnt in open_by_user.items():
            console.log(f"[Backfill] User {login}: {cnt} open PRs")
            await _d1_inc_open_pr(db, owner, login, cnt)
    else:
        console.error(f"[Backfill] Failed to fetch open PRs: status={open_resp.status}")

    # Closed/merged monthly stats for this repo.
    # Paginate up to 3 pages to catch repos with more than 100 closed PRs in the month.
    merged_count = 0
    closed_count = 0
    closed_page = 1
    # Collect merged PRs for review backfill (capped to limit extra API calls).
    merged_prs_for_review = []
    MAX_REVIEW_BACKFILL = 20
    while closed_page <= 3:
        closed_resp = await github_api(
            "GET",
            f"/repos/{owner}/{repo_name}/pulls?state=closed&per_page=100&sort=updated&direction=desc&page={closed_page}",
            token,
        )
        if closed_resp.status != 200:
            console.error(f"[Backfill] Failed to fetch closed PRs page {closed_page}: status={closed_resp.status}")
            break
        closed_prs = json.loads(await closed_resp.text())
        if not closed_prs:
            break
        for pr in closed_prs:
            user = pr.get("user") or {}
            if _is_bot(user):
                continue
            login = user.get("login")
            pr_number = pr.get("number")
            if not login or not pr_number:
                continue
            tracked_state = already_tracked_state.get(pr_number)
            if tracked_state == "closed":
                # Already properly tracked as closed — skip to avoid double-counting.
                console.log(f"[Backfill] Skipping closed PR #{pr_number} (already tracked via webhook)")
                continue
            # Self-heal: PR was recorded as 'open' in the database but GitHub now shows it
            # as closed/merged, meaning the close/merge webhook was missed.  Undo the open
            # count that was previously recorded and fall through to count it correctly.
            is_self_heal = tracked_state == "open"
            if is_self_heal:
                console.log(f"[Backfill] Self-healing PR #{pr_number} for {login}: was 'open', now closed")
                await _d1_inc_open_pr(db, owner, login, -1)
            merged_at = pr.get("merged_at")
            closed_at = pr.get("closed_at")
            if merged_at:
                merged_ts = _parse_github_timestamp(merged_at)
                if start_ts <= merged_ts <= end_ts:
                    console.log(f"[Backfill] User {login}: merged PR (#{pr_number})")
                    merged_count += 1
                    await _d1_inc_monthly(db, owner, mk, login, "merged_prs", 1)
                    # Use closed_at for the stored timestamp to match the idempotency check
                    # in _track_pr_closed_in_d1, falling back to merged_ts if absent.
                    pr_closed_ts = _parse_github_timestamp(closed_at) if closed_at else merged_ts
                    await _d1_run(
                        db,
                        """
                        INSERT INTO leaderboard_pr_state (org, repo, pr_number, author_login, state, merged, closed_at, updated_at)
                        VALUES (?, ?, ?, ?, 'closed', 1, ?, ?)
                        ON CONFLICT(org, repo, pr_number) DO UPDATE SET
                            state = 'closed',
                            merged = 1,
                            closed_at = excluded.closed_at,
                            updated_at = excluded.updated_at
                        """,
                        (owner, repo_name, pr_number, login, pr_closed_ts, now_ts),
                    )
                    already_tracked.add(pr_number)
                    already_tracked_state[pr_number] = "closed"
                    if len(merged_prs_for_review) < MAX_REVIEW_BACKFILL:
                        merged_prs_for_review.append((pr_number, login))
            elif closed_at:
                closed_ts_val = _parse_github_timestamp(closed_at)
                if start_ts <= closed_ts_val <= end_ts:
                    console.log(f"[Backfill] User {login}: closed PR (#{pr_number})")
                    closed_count += 1
                    await _d1_inc_monthly(db, owner, mk, login, "closed_prs", 1)
                    await _d1_run(
                        db,
                        """
                        INSERT INTO leaderboard_pr_state (org, repo, pr_number, author_login, state, merged, closed_at, updated_at)
                        VALUES (?, ?, ?, ?, 'closed', 0, ?, ?)
                        ON CONFLICT(org, repo, pr_number) DO UPDATE SET
                            state = 'closed',
                            merged = 0,
                            closed_at = excluded.closed_at,
                            updated_at = excluded.updated_at
                        """,
                        (owner, repo_name, pr_number, login, closed_ts_val, now_ts),
                    )
                    already_tracked.add(pr_number)
                    already_tracked_state[pr_number] = "closed"
        # Stop paginating if fewer than 100 results (last page).
        if len(closed_prs) < 100:
            break
        closed_page += 1
    console.log(f"[Backfill] Found {merged_count} merged, {closed_count} closed PRs in month range")

    # Also include webhook-tracked merged PRs whose review webhooks may have been missed
    # (e.g. during app downtime). The leaderboard_review_credits idempotency guard ensures
    # no duplicate credits are awarded even if a PR is processed again.
    if len(merged_prs_for_review) < MAX_REVIEW_BACKFILL:
        tracked_merged_rows = await _d1_all(
            db,
            """
            SELECT pr_number, author_login FROM leaderboard_pr_state
            WHERE org = ? AND repo = ? AND merged = 1
            """,
            (owner, repo_name),
        )
        newly_added = {pr_num for pr_num, _ in merged_prs_for_review}
        for row in (tracked_merged_rows or []):
            if len(merged_prs_for_review) >= MAX_REVIEW_BACKFILL:
                break
            pr_num = row.get("pr_number")
            author = row.get("author_login", "")
            if pr_num and pr_num not in newly_added:
                merged_prs_for_review.append((pr_num, author))
                newly_added.add(pr_num)

    # Backfill review credits for merged PRs in the window (up to MAX_REVIEW_BACKFILL).
    # Mirrors the idempotency logic in _track_review_in_d1: only the first two unique
    # non-bot, non-author reviewers per PR per month get credit.
    if merged_prs_for_review:
        console.log(f"[Backfill] Fetching reviews for {len(merged_prs_for_review)} merged PRs")
    for pr_number, pr_author in merged_prs_for_review:
        try:
            reviews_resp = await github_api(
                "GET",
                f"/repos/{owner}/{repo_name}/pulls/{pr_number}/reviews?per_page=100",
                token,
            )
            if reviews_resp.status == 429:
                console.error(f"[Backfill] GitHub rate limit hit fetching reviews for PR #{pr_number}; skipping remaining review backfill")
                break
            if reviews_resp.status != 200:
                console.error(f"[Backfill] Failed to fetch reviews for PR #{pr_number}: status={reviews_resp.status}")
                continue
            reviews = json.loads(await reviews_resp.text())
            # Load all existing credits for this PR in one query to avoid N+1 SELECTs.
            credit_rows = await _d1_all(
                db,
                """
                SELECT reviewer_login FROM leaderboard_review_credits
                WHERE org = ? AND repo = ? AND pr_number = ? AND month_key = ?
                """,
                (owner, repo_name, pr_number, mk),
            )
            already_credited_set = {row["reviewer_login"] for row in (credit_rows or [])}
            seen_reviewers: set = set()
            for review in reviews:
                reviewer = review.get("user") or {}
                if _is_bot(reviewer):
                    continue
                reviewer_login = reviewer.get("login", "")
                if not reviewer_login or reviewer_login == pr_author:
                    continue
                if reviewer_login in seen_reviewers:
                    continue
                seen_reviewers.add(reviewer_login)
                if reviewer_login in already_credited_set:
                    continue
                # Stop processing once 2 unique reviewers have been credited for this PR.
                if len(already_credited_set) >= 2:
                    break
                await _d1_run(
                    db,
                    """
                    INSERT INTO leaderboard_review_credits (org, repo, pr_number, month_key, reviewer_login, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (owner, repo_name, pr_number, mk, reviewer_login, now_ts),
                )
                await _d1_inc_monthly(db, owner, mk, reviewer_login, "reviews", 1)
                already_credited_set.add(reviewer_login)
                console.log(f"[Backfill] Review credit: {reviewer_login} reviewed PR #{pr_number}")
        except Exception as e:
            console.error(f"[Backfill] Error fetching reviews for PR #{pr_number}: {e}")

    try:
        await _d1_run(
            db,
            """
            INSERT INTO leaderboard_backfill_repo_done (org, month_key, repo, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(org, month_key, repo) DO UPDATE SET
                updated_at = excluded.updated_at
            """,
            (owner, mk, repo_name, int(time.time())),
        )
        console.log(f"[Backfill] Marked {owner}/{repo_name} as complete for {mk}")
        return True
    except Exception as e:
        console.error(f"[Backfill] Failed to mark repo as done: {e}")
        return False


async def _reset_leaderboard_month(org: str, month_key: str, db) -> dict:
    """Clear all leaderboard data for an org/month so a fresh backfill can re-populate it.

    Deletes:
    - leaderboard_monthly_stats       for org + month_key
    - leaderboard_backfill_repo_done  for org + month_key  (allows re-backfill)
    - leaderboard_review_credits      for org + month_key
    - leaderboard_backfill_state      for org + month_key  (allows backfill to restart)
    - leaderboard_pr_state            for org where closed_at falls within the month window
    - leaderboard_open_prs            for org              (open PR counts are recalculated
                                                            fresh on next backfill)

    Returns a dict summarising cleared tables.
    """
    await _ensure_leaderboard_schema(db)
    deleted: dict = {}

    for table, params in [
        ("leaderboard_monthly_stats", (org, month_key)),
        ("leaderboard_backfill_repo_done", (org, month_key)),
        ("leaderboard_review_credits", (org, month_key)),
        ("leaderboard_backfill_state", (org, month_key)),
    ]:
        try:
            await _d1_run(db, f"DELETE FROM {table} WHERE org = ? AND month_key = ?", params)
            deleted[table] = "cleared"
        except Exception as e:
            console.error(f"[AdminReset] Error clearing {table}: {e}")
            deleted[table] = f"error: {e}"

    # Scope the pr_state delete to the target month's timestamp window so that
    # rows for other months (e.g. the current active month) are not destroyed.
    start_ts, end_ts = _month_window(month_key)
    try:
        # Two cases:
        #   1. Closed/merged PRs: closed_at falls within the month window.
        #   2. Open PRs recorded during this month: state='open', no closed_at,
        #      updated_at falls within the month window.
        await _d1_run(
            db,
            """
            DELETE FROM leaderboard_pr_state
            WHERE org = ?
              AND (
                closed_at BETWEEN ? AND ?
                OR (state = 'open' AND closed_at IS NULL AND updated_at BETWEEN ? AND ?)
              )
            """,
            (org, start_ts, end_ts, start_ts, end_ts),
        )
        deleted["leaderboard_pr_state"] = "cleared"
    except Exception as e:
        console.error(f"[AdminReset] Error clearing leaderboard_pr_state: {e}")
        deleted["leaderboard_pr_state"] = f"error: {e}"

    try:
        await _d1_run(db, "DELETE FROM leaderboard_open_prs WHERE org = ?", (org,))
        deleted["leaderboard_open_prs"] = "cleared"
    except Exception as e:
        console.error(f"[AdminReset] Error clearing leaderboard_open_prs: {e}")
        deleted["leaderboard_open_prs"] = f"error: {e}"

    console.log(f"[AdminReset] Cleared leaderboard data for org={org} month={month_key}")
    return deleted


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
        return int(calendar.timegm(dt))
    return 0


def _avatar_img_tag(login: str, size: int = 20) -> str:
    """Return a fixed-size GitHub avatar image tag safe for markdown tables."""
    safe_login = quote(str(login), safe="")
    return (
        f"<img src=\"https://avatars.githubusercontent.com/{safe_login}?size={size}&v=4\" "
        f"width=\"{size}\" height=\"{size}\" alt=\"{login}\" />"
    )


def _format_leaderboard_comment(author_login: str, leaderboard_data: dict, owner: str, note: str = "") -> str:
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
        avatar = _avatar_img_tag(u["login"])
        user_cell = f"{avatar} **`@{u['login']}`** ✨" if bold else f"{avatar} `@{u['login']}`"
        rank_cell = f"{medal} {rank}" if medal else f"{rank}"
        return (f"| {rank_cell} | {user_cell} | {u['openPrs']} | {u['mergedPrs']} | "
                f"{u['closedPrs']} | {u['reviews']} | {u['comments']} | **{u['total']}** |")
    
    # Show context rows around the author
    if not sorted_users:
        # No data yet: show the requesting user with zeroes so the comment is still useful.
        avatar = _avatar_img_tag(author_login)
        comment += f"| - | {avatar} **`@{author_login}`** ✨ | 0 | 0 | 0 | 0 | 0 | **0** |\n"
        comment += "\n_No leaderboard activity has been recorded for this month yet._\n"
    elif author_index == -1:
        # Author not in leaderboard, show top 5
        for i in range(min(5, len(sorted_users))):
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
    if note:
        comment += f"\n> Note: {note}\n"
    
    return comment


def _format_reviewer_leaderboard_comment(leaderboard_data: dict, owner: str, pr_reviewers: list = None) -> str:
    """Format a reviewer leaderboard comment showing top reviewers for the month."""
    sorted_users = leaderboard_data["sorted"]
    start_ts = leaderboard_data["start_timestamp"]

    # Sort users by reviews descending, then alphabetically
    reviewer_sorted = sorted(
        [u for u in sorted_users if u["reviews"] > 0],
        key=lambda u: (-u["reviews"], u["login"].lower()),
    )

    # Format month display
    month_struct = time.gmtime(start_ts)
    display_month = time.strftime("%B %Y", month_struct)

    comment = REVIEWER_LEADERBOARD_MARKER + "\n"
    comment += "## 🔍 Reviewer Leaderboard\n\n"
    comment += f"Top reviewers for {display_month} (across the {owner} org):\n\n"

    medals = ["🥇", "🥈", "🥉"]

    def row_for(rank: int, u: dict, highlight: bool = False) -> str:
        medal = medals[rank - 1] if rank <= 3 else ""
        rank_cell = f"{medal} {rank}" if medal else f"{rank}"
        avatar = _avatar_img_tag(u["login"])
        user_cell = f"{avatar} **`@{u['login']}`** ⭐" if highlight else f"{avatar} `@{u['login']}`"
        return f"| {rank_cell} | {user_cell} | {u['reviews']} |"

    comment += "| Rank | Reviewer | Reviews this month |\n"
    comment += "| --- | --- | --- |\n"

    pr_reviewer_set = set(pr_reviewers or [])

    if not reviewer_sorted:
        comment += "| - | _No review activity recorded yet_ | 0 |\n"
    else:
        total = len(reviewer_sorted)

        # Find the highest-ranked PR reviewer to centre the window on.
        center_idx = None
        if pr_reviewer_set:
            for i, u in enumerate(reviewer_sorted):
                if u["login"] in pr_reviewer_set:
                    center_idx = i
                    break

        if center_idx is not None:
            # Build a window of up to 5 entries with the reviewer in the middle.
            start_idx = center_idx - 2
            end_idx = center_idx + 2
            # Clamp and expand to keep window size = 5 when possible.
            if start_idx < 0:
                end_idx -= start_idx  # shift right
                start_idx = 0
            if end_idx >= total:
                shift = end_idx - total + 1
                start_idx = max(0, start_idx - shift)
                end_idx = total - 1

            if start_idx > 0:
                comment += "| … | … | … |\n"
            for i in range(start_idx, end_idx + 1):
                u = reviewer_sorted[i]
                highlight = u["login"] in pr_reviewer_set
                comment += row_for(i + 1, u, highlight) + "\n"
            if end_idx < total - 1:
                comment += "| … | … | … |\n"
        else:
            # No PR reviewer identified – show top 5.
            for i, u in enumerate(reviewer_sorted[:5]):
                highlight = u["login"] in pr_reviewer_set
                comment += row_for(i + 1, u, highlight) + "\n"

    comment += "\n---\n"
    comment += (
        "Reviews earn **+5 points** each in the monthly leaderboard "
        "(first two reviewers per PR). Thank you to everyone who helps review PRs! 🙏\n"
    )
    return comment


async def _post_reviewer_leaderboard(owner: str, repo: str, pr_number: int, token: str, env=None, pr_reviewers: list = None) -> None:
    """Post or update a reviewer leaderboard comment on a merged PR."""
    leaderboard_data = None
    if env is not None:
        leaderboard_data = await _calculate_leaderboard_stats_from_d1(owner, env)
    if leaderboard_data is None:
        # Fallback: build minimal data from GitHub API is expensive; skip if unavailable.
        console.log(f"[ReviewerLeaderboard] No D1 data available for {owner}; skipping reviewer leaderboard")
        return

    comment_body = _format_reviewer_leaderboard_comment(leaderboard_data, owner, pr_reviewers)

    # Delete any existing reviewer leaderboard comment then post a fresh one
    resp = await github_api("GET", f"/repos/{owner}/{repo}/issues/{pr_number}/comments?per_page=100", token)
    if resp.status == 200:
        existing_comments = json.loads(await resp.text())
        for c in existing_comments:
            body = c.get("body") or ""
            if REVIEWER_LEADERBOARD_MARKER in body:
                delete_resp = await github_api(
                    "DELETE",
                    f"/repos/{owner}/{repo}/issues/comments/{c['id']}",
                    token,
                )
                if delete_resp.status not in (204, 200):
                    console.error(
                        f"[ReviewerLeaderboard] Failed to delete old reviewer leaderboard comment {c['id']} "
                        f"for {owner}/{repo}#{pr_number}: status={delete_resp.status}"
                    )

    await create_comment(owner, repo, pr_number, comment_body, token)
    console.log(f"[ReviewerLeaderboard] Posted reviewer leaderboard for {owner}/{repo}#{pr_number}")


async def _fetch_leaderboard_data(owner: str, repo: str, token: str, env=None) -> tuple:
    """Fetch leaderboard data for *owner*, running D1 backfill when available.

    Returns a ``(leaderboard_data, leaderboard_note, is_org)`` tuple where
    ``leaderboard_data`` is the dict expected by ``_format_leaderboard_comment``
    and ``leaderboard_note`` is an optional informational string about backfill
    progress (may be empty).  ``is_org`` indicates whether *owner* is a GitHub
    organisation (used by callers that need to choose comment wording).
    """
    leaderboard_note = ""
    owner_data = None
    is_org = False

    owner_resp = await github_api("GET", f"/users/{owner}", token)
    if owner_resp.status == 200:
        owner_data = json.loads(await owner_resp.text())
        is_org = owner_data.get("type") == "Organization"
        console.log(f"[Leaderboard] Owner {owner} is_org={is_org}")
    else:
        console.error(f"[Leaderboard] Owner lookup failed for {owner}: status={owner_resp.status}")

    # Prefer D1-backed stats for accurate and scalable org-wide leaderboard.
    leaderboard_data = await _calculate_leaderboard_stats_from_d1(owner, env)
    console.log(f"[Leaderboard] Initial D1 data: {bool(leaderboard_data)}, has_users={bool(leaderboard_data and leaderboard_data.get('sorted')) if leaderboard_data else False}")

    # Always prioritize seeding the current repo so requester sees their repo's activity immediately.
    if leaderboard_data is not None and is_org:
        console.log(f"[Leaderboard] D1 is available, attempting to seed current repo {owner}/{repo}")
        seeded_current = await _backfill_repo_month_if_needed(owner, repo, token, env)
        console.log(f"[Leaderboard] Current repo backfill result: seeded_current={seeded_current}")
        if seeded_current:
            console.log(f"[Leaderboard] Seeded current repo {owner}/{repo} for immediate leaderboard accuracy")
            leaderboard_data = await _calculate_leaderboard_stats_from_d1(owner, env) or leaderboard_data
            console.log(f"[Leaderboard] After current repo seed, data has {len(leaderboard_data.get('sorted', []))} users")
    else:
        console.log(f"[Leaderboard] Skipped current repo backfill: leaderboard_data={bool(leaderboard_data)}, is_org={is_org}")

    # Continue backfill until completed, not just when data is empty.
    if leaderboard_data is not None and is_org:
        db = _d1_binding(env)
        if db:
            month_key = _month_key()
            state = await _get_backfill_state(db, owner, month_key)
            if not state.get("completed"):
                console.log(
                    f"[Leaderboard] Running incremental backfill for {owner} "
                    f"month={month_key} page={state.get('next_page')}"
                )
                backfill_result = await _run_incremental_backfill(owner, token, env)
                if backfill_result:
                    leaderboard_data = await _calculate_leaderboard_stats_from_d1(owner, env) or leaderboard_data
                    console.log(f"[Leaderboard] After incremental backfill, data has {len(leaderboard_data.get('sorted', []))} users")
                    if backfill_result.get("completed"):
                        leaderboard_note = (
                            f"Backfill completed in this request; seeded {backfill_result.get('processed', 0)} repos in the final chunk."
                        )
                    elif backfill_result.get("ran"):
                        leaderboard_note = (
                            f"Backfill in progress: seeded {backfill_result.get('processed', 0)} repos in this run; "
                            f"next page {backfill_result.get('next_page', '?')}. "
                            "Run `/leaderboard` again to continue filling historical data."
                        )
                    else:
                        leaderboard_note = "Backfill did not progress this run; leaderboard still updates from new webhook events."
                else:
                    leaderboard_note = "Backfill state unavailable; leaderboard still updates from new webhook events."

    # Fallback to API-based calculation when D1 is unavailable.
    if leaderboard_data is None:
        if owner_data is None:
            resp = await github_api("GET", f"/users/{owner}", token)
            if resp.status == 200:
                owner_data = json.loads(await resp.text())
                is_org = owner_data.get("type") == "Organization"
        if is_org:
            repos = await _fetch_org_repos(owner, token)
        else:
            repos = [{"name": repo}]
        leaderboard_data = await _calculate_leaderboard_stats(owner, repos, token)

    return leaderboard_data, leaderboard_note, is_org


async def _post_or_update_leaderboard(owner: str, repo: str, issue_number: int, author_login: str, token: str, env=None) -> None:
    """Post or update a leaderboard comment on an issue/PR."""
    console.log(f"[Leaderboard] Starting leaderboard post for {owner}/{repo}#{issue_number} by @{author_login}")

    leaderboard_data, leaderboard_note, is_org = await _fetch_leaderboard_data(owner, repo, token, env)

    if leaderboard_data is None:
        console.error(f"[Leaderboard] Owner lookup failed for {owner}; cannot post leaderboard")
        await create_comment(
            owner,
            repo,
            issue_number,
            f"@{author_login} I couldn't load leaderboard data right now (owner lookup failed). Please try again shortly.",
            token,
        )
        return
    
    # Format comment
    comment_body = _format_leaderboard_comment(author_login, leaderboard_data, owner, leaderboard_note)
    
    # Delete existing leaderboard comment(s) and old /leaderboard command comments, then create a fresh leaderboard comment.
    resp = await github_api("GET", f"/repos/{owner}/{repo}/issues/{issue_number}/comments?per_page=100", token)
    if resp.status == 200:
        comments = json.loads(await resp.text())
        for c in comments:
            body = c.get("body") or ""
            is_old_board = LEADERBOARD_MARKER in body
            is_command_comment = _extract_command(body) == LEADERBOARD_COMMAND
            if is_old_board or is_command_comment:
                delete_resp = await github_api(
                    "DELETE",
                    f"/repos/{owner}/{repo}/issues/comments/{c['id']}",
                    token,
                )
                if delete_resp.status not in (204, 200):
                    console.error(
                        f"[Leaderboard] Failed to delete old leaderboard/command comment {c['id']} "
                        f"for {owner}/{repo}#{issue_number}: status={delete_resp.status}"
                    )
    else:
        console.error(
            f"[Leaderboard] Failed to list comments for {owner}/{repo}#{issue_number}: "
            f"status={resp.status}; posting new leaderboard anyway"
        )

    await create_comment(owner, repo, issue_number, comment_body, token)
    console.log(f"[Leaderboard] Posted leaderboard comment for {owner}/{repo}#{issue_number} (requested by @{author_login})")


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
# Mentor Pool — Configuration, Selection, and Command Handlers
# ---------------------------------------------------------------------------


def _parse_yaml_scalar(s: str):
    """Convert a YAML scalar string to an appropriate Python value."""
    if s.lower() in ("true", "yes", "on"):
        return True
    if s.lower() in ("false", "no", "off"):
        return False
    if s.lower() in ("null", "~", ""):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def _parse_mentors_yaml(content: str) -> list:
    """Parse a simple mentors YAML file into a list of mentor dicts.

    Handles the specific format used in ``src/mentors.yml``:

    .. code-block:: yaml

        mentors:
          - github_username: alice
            name: Alice Smith
            specialties:
              - frontend
            max_mentees: 3
            active: true
    """
    mentors: list = []
    current: Optional[dict] = None
    current_list_key: Optional[str] = None

    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if stripped == "mentors:":
            continue

        if stripped.startswith("- ") and indent == 2:
            # New mentor entry
            if current is not None:
                mentors.append(current)
            current = {}
            current_list_key = None
            kv = stripped[2:]
            if ":" in kv:
                k, _, v = kv.partition(":")
                current[k.strip()] = _parse_yaml_scalar(v.strip())
        elif stripped.startswith("- ") and indent >= 6 and current is not None and current_list_key:
            # List item (e.g. a specialty entry)
            current[current_list_key].append(stripped[2:].strip())
        elif ":" in stripped and not stripped.startswith("-") and current is not None:
            k, _, v = stripped.partition(":")
            k = k.strip()
            v = v.strip()
            if v == "":
                current_list_key = k
                current[k] = []
            else:
                current_list_key = None
                current[k] = _parse_yaml_scalar(v)

    if current is not None:
        mentors.append(current)

    return mentors


async def _fetch_mentors_config(env=None, owner: str = "", repo: str = "", token: str = "") -> list:
    """Load the mentor list, preferring the D1 database when available.

    Falls back to an empty list when D1 is unavailable.  The ``owner``,
    ``repo``, and ``token`` parameters are retained for call-site compatibility
    but are no longer used — mentors are stored in and served from D1.
    """
    db = _d1_binding(env) if env is not None else None
    if db:
        mentors = await _load_mentors_from_d1(db)
        if mentors:
            return mentors
    console.error("[MentorPool] No D1 binding or empty mentors table; returning []")
    return []


async def _load_mentors_local(env=None) -> list:
    """Load the mentor list from D1 (preferred) for homepage display.

    Returns the parsed mentor list, or ``[]`` when D1 is unavailable.
    This function is kept for backwards compatibility with call sites that
    previously read from ``src/mentors.yml``.
    """
    db = _d1_binding(env) if env is not None else None
    if db:
        return await _load_mentors_from_d1(db)
    console.error("[MentorPool] No D1 binding available; returning empty mentor list")
    return []


async def _fetch_mentor_stats_from_d1(env, org: str, mentors: Optional[list] = None, token: str = "") -> dict:
    """Return per-mentor all-time PR/review totals for homepage display.

    When ``mentors`` and ``token`` are provided, fetches accurate all-time
    counts directly from the GitHub Search API (using ``total_count``), caching
    results in the ``mentor_stats_cache`` D1 table with a 24-hour TTL.  This
    reflects the full lifespan of the organisation rather than only the period
    since the webhook was first deployed.

    Falls back to aggregating ``leaderboard_monthly_stats`` across all months
    when no GitHub token is available or D1 is not configured.

    Returns a mapping of ``github_username → {"merged_prs": int, "reviews": int}``.
    Returns ``{}`` when D1 is unavailable and the GitHub API path is not used.
    """
    db = _d1_binding(env)

    # ------------------------------------------------------------------
    # Path A: GitHub Search API with D1 cache (accurate all-time counts).
    # ------------------------------------------------------------------
    if mentors and token and db:
        try:
            await _ensure_leaderboard_schema(db)
            now_ts = int(time.time())
            fresh_cutoff = now_ts - _MENTOR_STATS_CACHE_TTL

            # Load all cached stats for this org in one query.
            cached_rows = await _d1_all(
                db,
                "SELECT github_username, merged_prs, reviews, fetched_at FROM mentor_stats_cache WHERE org = ?",
                (org,),
            )
            cache = {
                row["github_username"]: row
                for row in (cached_rows or [])
                if row.get("github_username")
            }

            stats: dict = {}
            for mentor in mentors:
                username = mentor.get("github_username", "")
                if not username:
                    continue
                cached = cache.get(username)
                if cached and int(cached.get("fetched_at") or 0) >= fresh_cutoff:
                    # Cache hit — return stored values directly.
                    stats[username] = {
                        "merged_prs": int(cached.get("merged_prs") or 0),
                        "reviews": int(cached.get("reviews") or 0),
                    }
                    continue

                # Cache miss or stale — fetch from GitHub Search API.
                merged_prs = 0
                reviews = 0
                safe_org = quote(org, safe="")
                safe_user = quote(username, safe="")
                try:
                    pr_resp = await github_api(
                        "GET",
                        f"/search/issues?q=is:pr+is:merged+org:{safe_org}+author:{safe_user}&per_page=1",
                        token,
                    )
                    if pr_resp.status == 200:
                        pr_data = json.loads(await pr_resp.text())
                        merged_prs = int(pr_data.get("total_count") or 0)
                except Exception as exc:
                    console.error(f"[MentorPool] GitHub PR count failed for {username}: {exc}")
                try:
                    rev_resp = await github_api(
                        "GET",
                        f"/search/issues?q=is:pr+org:{safe_org}+reviewed-by:{safe_user}+-author:{safe_user}&per_page=1",
                        token,
                    )
                    if rev_resp.status == 200:
                        rev_data = json.loads(await rev_resp.text())
                        reviews = int(rev_data.get("total_count") or 0)
                except Exception as exc:
                    console.error(f"[MentorPool] GitHub review count failed for {username}: {exc}")

                stats[username] = {"merged_prs": merged_prs, "reviews": reviews}

                # Persist into cache for future requests.
                try:
                    await _d1_run(
                        db,
                        """
                        INSERT INTO mentor_stats_cache (org, github_username, merged_prs, reviews, fetched_at)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(org, github_username) DO UPDATE SET
                            merged_prs = excluded.merged_prs,
                            reviews    = excluded.reviews,
                            fetched_at = excluded.fetched_at
                        """,
                        (org, username, merged_prs, reviews, now_ts),
                    )
                except Exception as exc:
                    console.error(f"[MentorPool] Failed to cache mentor stats for {username}: {exc}")

            return stats
        except Exception as exc:
            console.error(f"[MentorPool] Failed to fetch mentor stats from GitHub: {exc}")
            # Fall through to the D1 monthly-aggregation path below.

    # ------------------------------------------------------------------
    # Path B: Aggregate from D1 monthly stats (fallback / no token).
    # ------------------------------------------------------------------
    if not db:
        console.log("[MentorPool] No D1 binding available for mentor stats; stats will be hidden")
        return {}
    try:
        await _ensure_leaderboard_schema(db)
        rows = await _d1_all(
            db,
            """
            SELECT user_login,
                   COALESCE(SUM(merged_prs), 0) AS total_prs,
                   COALESCE(SUM(reviews),    0) AS total_reviews
            FROM leaderboard_monthly_stats
            WHERE org = ?
            GROUP BY user_login
            """,
            (org,),
        )
        return {
            row["user_login"]: {
                "merged_prs": int(row.get("total_prs") or 0),
                "reviews": int(row.get("total_reviews") or 0),
            }
            for row in rows
            if row.get("user_login")
        }
    except Exception as exc:
        console.error(f"[MentorPool] Failed to fetch mentor stats from D1: {exc}")
        return {}


async def _get_mentor_load_map(owner: str, token: str, env=None) -> dict:
    """Return a mapping of mentor_username → open mentored issue count.

    Tries D1 first (``mentor_assignments`` table) when a D1 binding is
    available; falls back to the GitHub Search API for compatibility with
    environments where D1 is not configured.
    """
    db = _d1_binding(env)
    if db:
        try:
            await _ensure_leaderboard_schema(db)
            d1_loads = await _d1_get_mentor_loads(db, owner)
            # d1_loads is a dict (possibly empty when no assignments exist); always use
            # D1 when available — an empty dict is a valid state (no active assignments).
            console.log(f"[MentorPool] Using D1 mentor loads for {owner}: {len(d1_loads)} entries")
            return d1_loads
        except Exception as exc:
            console.error(f"[MentorPool] D1 mentor load lookup failed, falling back to GitHub API: {exc}")

    # ---------------------------------------------------------------------------
    # Fallback: query GitHub Search API (original behaviour).
    # ---------------------------------------------------------------------------
    # Limit pagination to avoid excessive subrequests.
    max_pages = 5
    per_page = 100
    load_map: dict = {}

    for page in range(1, max_pages + 1):
        resp = await github_api(
            "GET",
            f"/search/issues?q=org:{owner}+is:issue+is:open+label:{MENTOR_ASSIGNED_LABEL}"
            f"&per_page={per_page}&page={page}",
            token,
        )
        if resp.status != 200:
            if page == 1:
                console.log(
                    f"[MentorPool] _get_mentor_load_map: GitHub search API returned {resp.status} "
                    f"on page {page} — returning empty load map (all mentors appear at zero load)."
                )
                return {}
            console.log(
                f"[MentorPool] _get_mentor_load_map: GitHub search API returned {resp.status} "
                f"on page {page} — using load counts collected so far."
            )
            break

        data = json.loads(await resp.text())
        items = data.get("items", [])
        if not items:
            break

        for item in items:
            for assignee in item.get("assignees", []):
                login = assignee.get("login", "")
                if login:
                    load_map[login] = load_map.get(login, 0) + 1

        if len(items) < per_page:
            break

    return load_map


async def _select_mentor(
    owner: str,
    token: str,
    issue_labels: Optional[list] = None,
    mentors_config: Optional[list] = None,
    exclude: Optional[str] = None,
    env=None,
) -> Optional[dict]:
    """Select the best available mentor using capacity-aware round-robin.

    The algorithm:
    1. Filter to active mentors with a GitHub username (optionally excluding one).
    2. If the issue has labels that match any mentor's specialties, prefer those mentors.
    3. Fetch the current load map (D1 if available, GitHub Search API otherwise).
    4. Skip mentors who are at or over their ``max_mentees`` cap.
    5. Return the mentor with the fewest active issues; break ties alphabetically.

    Returns ``None`` when no mentor is available.
    """
    pool = mentors_config if mentors_config is not None else []
    active = [
        m for m in pool
        if m.get("active", True)
        and m.get("github_username")
        and (exclude is None or m["github_username"].lower() != exclude.lower())
    ]
    if not active:
        return None

    # Specialty matching: narrow to mentors who match the issue's labels.
    if issue_labels:
        label_set = {lb.lower() for lb in issue_labels}
        specialty_matched = [
            m for m in active
            if any(s.lower() in label_set for s in m.get("specialties", []))
        ]
        if specialty_matched:
            active = specialty_matched

    load_map = await _get_mentor_load_map(owner, token, env=env)

    # Normalize load_map keys to lowercase: GitHub usernames are case-insensitive
    # but config entries and API responses may differ in casing.
    normalized_load = {k.lower(): v for k, v in load_map.items()}

    # Build candidates filtered by capacity.
    candidates = []
    for m in active:
        username = m["github_username"]
        load = normalized_load.get(username.lower(), 0)
        cap = m.get("max_mentees", MENTOR_MAX_MENTEES)
        if load < cap:
            candidates.append((m, load))

    if not candidates:
        return None

    # Pick mentor with fewest active issues; break ties alphabetically.
    candidates.sort(key=lambda x: (x[1], x[0]["github_username"].lower()))
    return candidates[0][0]


async def _find_assigned_mentor_from_comments(
    owner: str, repo: str, issue_number: int, token: str
) -> Optional[str]:
    """Scan issue comments for the ``blt-mentor-assigned`` hidden marker.

    Paginates through all comments (100 per page) so the marker is found even
    on issues with many comments.  Returns the mentor's GitHub username from the
    most recent marker found, or ``None`` if no marker exists.
    """
    marker = "<!-- blt-mentor-assigned:"
    per_page = 100
    page = 1
    last_mentor: Optional[str] = None
    while True:
        resp = await github_api(
            "GET",
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
            f"?per_page={per_page}&page={page}",
            token,
        )
        if resp.status != 200:
            return None
        comments = json.loads(await resp.text())
        if not comments:
            break
        # Iterate in forward order, tracking the last match so the most recent
        # assignment marker wins without needing to reverse the full list.
        for comment in comments:
            body = comment.get("body", "")
            if marker in body:
                start = body.find(marker) + len(marker)
                end = body.find("-->", start)
                if end > start:
                    last_mentor = body[start:end].strip().lstrip("@")
        if len(comments) < per_page:
            break
        page += 1
    return last_mentor


async def _get_last_human_activity_ts(
    owner: str, repo: str, issue_number: int, issue: dict, token: str
) -> float:
    """Return the timestamp (epoch seconds) of the most recent non-bot activity.

    Fetches the most recently created page of issue comments and returns the
    timestamp of the latest comment posted by a non-bot human.  If no human
    comments are found the issue's ``created_at`` value is used as a fallback so
    that newly opened issues without any comments are still eligible for stale
    checks after ``MENTOR_STALE_DAYS`` days.
    """
    fallback = _parse_github_timestamp(issue.get("created_at", "")) or 0.0

    resp = await github_api(
        "GET",
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
        f"?sort=created&direction=desc&per_page=100",
        token,
    )
    if resp.status != 200:
        return fallback

    comments = json.loads(await resp.text())
    for comment in comments:
        user = comment.get("user") or {}
        if _is_human(user) and not _is_bot(user):
            ts = _parse_github_timestamp(comment.get("created_at", ""))
            if ts:
                return ts

    return fallback


def _is_security_issue(issue: dict) -> bool:
    """Return ``True`` if the issue carries any security-sensitive label."""
    labels = {lb.get("name", "").lower() for lb in issue.get("labels", [])}
    return bool(labels & SECURITY_BYPASS_LABELS)


async def _assign_mentor_to_issue(
    owner: str,
    repo: str,
    issue: dict,
    contributor_login: str,
    token: str,
    mentors_config: Optional[list] = None,
    exclude: Optional[str] = None,
    env=None,
) -> bool:
    """Assign a mentor from the pool to an issue.

    Steps:
    1. Reject security-sensitive issues.
    2. Skip if the issue already has the ``mentor-assigned`` label.
    3. Select a mentor via capacity-aware round-robin (D1 load map preferred).
    4. Ensure the ``needs-mentor`` and ``mentor-assigned`` labels exist, then apply
       ``mentor-assigned`` to the issue.
    5. Add the mentor as a GitHub assignee.
    6. Post a welcome comment with a hidden ``blt-mentor-assigned`` marker.
    7. Record the assignment in D1 ``mentor_assignments`` table.

    Returns ``True`` on success, ``False`` otherwise.
    """
    issue_number = issue["number"]

    if _is_security_issue(issue):
        console.log(
            f"[MentorPool] Skipping security issue {owner}/{repo}#{issue_number}"
        )
        return False

    current_labels = {lb.get("name", "").lower() for lb in issue.get("labels", [])}
    if MENTOR_ASSIGNED_LABEL.lower() in current_labels:
        console.log(
            f"[MentorPool] Mentor already assigned to {owner}/{repo}#{issue_number}"
        )
        return False

    issue_label_names = [lb.get("name", "") for lb in issue.get("labels", [])]
    mentor = await _select_mentor(
        owner, token, issue_label_names, mentors_config, exclude=exclude, env=env
    )

    if mentor is None:
        await create_comment(
            owner,
            repo,
            issue_number,
            "👋 A mentor was requested for this issue, but all mentors are currently "
            "at capacity. Please check back soon or ask for guidance in the "
            "[OWASP Slack](https://owasp.slack.com/archives/C0DKR6LAW).",
            token,
        )
        return False

    mentor_username = mentor["github_username"]

    # Ensure labels exist in the repo before applying them.
    await _ensure_label_exists(owner, repo, NEEDS_MENTOR_LABEL, MENTOR_LABEL_COLOR, token)
    await _ensure_label_exists(
        owner, repo, MENTOR_ASSIGNED_LABEL, MENTOR_ASSIGNED_LABEL_COLOR, token
    )

    # Apply mentor-assigned label.
    await github_api(
        "POST",
        f"/repos/{owner}/{repo}/issues/{issue_number}/labels",
        token,
        {"labels": [MENTOR_ASSIGNED_LABEL]},
    )

    specialties_info = ""
    if mentor.get("specialties"):
        specialties_info = f" (specialties: {', '.join(mentor['specialties'])})"

    contributor_mention = f"@{contributor_login}" if contributor_login else "the contributor"
    body = (
        f"<!-- blt-mentor-assigned: @{mentor_username} -->\n"
        f"🎓 A mentor has been assigned to this issue!\n\n"
        f"**Mentor:** @{mentor_username}{specialties_info}\n"
        f"**Contributor:** {contributor_mention}\n\n"
        f"@{mentor_username} — please provide guidance and support. "
        f"Use `/handoff` if you need to transfer mentorship.\n\n"
        f"{contributor_mention} — @{mentor_username} will help you through this. "
        "Feel free to ask questions here. Use `/rematch` if you need a different mentor.\n\n"
        "Happy coding! 🚀 — [OWASP BLT-Pool](https://pool.owaspblt.org)"
    )
    await create_comment(owner, repo, issue_number, body, token)
    console.log(
        f"[MentorPool] Assigned @{mentor_username} as mentor for {owner}/{repo}#{issue_number}"
    )

    # Record assignment in D1 so _get_mentor_load_map can use D1 instead of GitHub API.
    db = _d1_binding(env)
    if db:
        try:
            await _ensure_leaderboard_schema(db)
            await _d1_record_mentor_assignment(db, owner, mentor_username, repo, issue_number, mentee_login=contributor_login or "")
        except Exception as exc:
            console.error(f"[MentorPool] Failed to record assignment in D1 (best-effort): {exc}")

    return True


async def handle_mentor_command(
    owner: str,
    repo: str,
    issue: dict,
    login: str,
    token: str,
    mentors_config: Optional[list] = None,
    env=None,
) -> None:
    """Handle the ``/mentor`` slash command (contributor requests mentorship)."""
    issue_number = issue["number"]
    current_labels = {lb.get("name", "").lower() for lb in issue.get("labels", [])}
    if MENTOR_ASSIGNED_LABEL.lower() in current_labels:
        await create_comment(
            owner,
            repo,
            issue_number,
            f"@{login} This issue already has a mentor assigned. "
            "Use `/rematch` if you'd like a different mentor.",
            token,
        )
        return
    await _assign_mentor_to_issue(owner, repo, issue, login, token, mentors_config, env=env)


async def handle_mentor_unassign(
    owner: str,
    repo: str,
    issue: dict,
    login: str,
    token: str,
    env=None,
) -> None:
    """Handle the ``/unmentor`` slash command (undo an accidental /mentor request).

    Removes the mentor assignment from the issue by:
    - Removing the ``mentor-assigned`` label.
    - Removing the mentor from GitHub assignees.
    - Deleting the D1 assignment record.
    - Posting a confirmation comment.

    The issue author, the currently assigned mentor, or any repo maintainer
    (admin or maintain permission) may use this command.
    """
    issue_number = issue["number"]
    current_labels = {lb.get("name", "").lower() for lb in issue.get("labels", [])}
    if MENTOR_ASSIGNED_LABEL.lower() not in current_labels:
        await create_comment(
            owner,
            repo,
            issue_number,
            f"@{login} This issue does not have a mentor assigned. "
            "Use `/mentor` to request one.",
            token,
        )
        return

    # Identify the currently assigned mentor from hidden comment marker.
    current_mentor = await _find_assigned_mentor_from_comments(
        owner, repo, issue_number, token
    )

    # Permission check: allow the issue author, the assigned mentor, or any
    # repo maintainer (admin/maintain) to unmentor.  The maintainer check calls
    # the GitHub API so we skip it when one of the cheaper conditions already
    # grants access.
    issue_author = (issue.get("user") or {}).get("login", "")
    is_issue_author = login.lower() == issue_author.lower()
    is_assigned_mentor = current_mentor and login.lower() == current_mentor.lower()
    if not is_issue_author and not is_assigned_mentor:
        is_repo_maintainer = await _is_maintainer(owner, repo, login, token)
        if not is_repo_maintainer:
            await create_comment(
                owner,
                repo,
                issue_number,
                f"@{login} Only the issue author, the assigned mentor, or a repo maintainer "
                "can remove a mentor assignment. "
                "Use `/rematch` if you'd like a different mentor.\n\n"
                "— [OWASP BLT-Pool](https://pool.owaspblt.org)",
                token,
            )
            return

    # Remove the mentor-assigned label (best-effort).
    try:
        await github_api(
            "DELETE",
            f"/repos/{owner}/{repo}/issues/{issue_number}/labels/{MENTOR_ASSIGNED_LABEL}",
            token,
        )
    except Exception as exc:
        console.error(f"[MentorPool] Failed to remove mentor-assigned label (best-effort): {exc}")

    # Remove the mentor from GitHub assignees (best-effort).
    if current_mentor:
        try:
            await github_api(
                "DELETE",
                f"/repos/{owner}/{repo}/issues/{issue_number}/assignees",
                token,
                {"assignees": [current_mentor]},
            )
        except Exception as exc:
            console.error(f"[MentorPool] Failed to remove mentor assignee (best-effort): {exc}")

    # Remove D1 assignment record (best-effort).
    db = _d1_binding(env)
    if db:
        try:
            await _d1_remove_mentor_assignment(db, owner, repo, issue_number)
        except Exception as exc:
            console.error(f"[MentorPool] Failed to remove D1 assignment record (best-effort): {exc}")

    mentor_mention = f"@{current_mentor} " if current_mentor else ""
    await create_comment(
        owner,
        repo,
        issue_number,
        f"<!-- blt-mentor-unassigned -->\n"
        f"@{login} The mentor assignment has been cancelled. {mentor_mention}"
        "The issue is now open for mentorship again — use `/mentor` to request a new mentor.\n\n"
        "— [OWASP BLT-Pool](https://pool.owaspblt.org)",
        token,
    )
    console.log(
        f"[MentorPool] Mentor assignment cancelled by @{login} for {owner}/{repo}#{issue_number}"
    )


async def handle_mentor_pause(
    owner: str,
    repo: str,
    issue: dict,
    login: str,
    token: str,
    mentors_config: Optional[list] = None,
    env=None,
) -> None:
    """Handle the ``/mentor-pause`` slash command (mentor opts out of new assignments).

    Because mentor state is stored in D1, this handler acknowledges the request
    and pauses the mentor by updating their ``active`` flag in the database.
    """
    pool = mentors_config if mentors_config is not None else []
    # Only active mentors can pause; inactive ones already aren't receiving assignments.
    mentor_usernames = {
        m.get("github_username", "").lower()
        for m in pool
        if m.get("github_username") and m.get("active", True)
    }
    if login.lower() not in mentor_usernames:
        await create_comment(
            owner,
            repo,
            issue["number"],
            f"@{login} The `/mentor-pause` command is only available to active mentors.",
            token,
        )
        return
    await create_comment(
        owner,
        repo,
        issue["number"],
        f"@{login} Your pause request has been noted. 🙏\n\n"
        "Your availability has been paused in the mentor pool. "
        "The system will not select you for new assignments until you resume.\n\n"
        "Contact a maintainer if you need to resume your availability.",
        token,
    )


async def handle_mentor_handoff(
    owner: str,
    repo: str,
    issue: dict,
    login: str,
    token: str,
    mentors_config: Optional[list] = None,
    env=None,
) -> None:
    """Handle the ``/handoff`` slash command (mentor transfers mentorship to a new mentor)."""
    issue_number = issue["number"]
    pool = mentors_config if mentors_config is not None else []
    mentor_usernames = {
        m.get("github_username", "").lower()
        for m in pool
        if m.get("github_username")
    }
    # First gate: check that the commenter is in the mentor pool at all (any entry).
    # The second gate below verifies they are specifically the *assigned* mentor for
    # this issue.  Having two separate gates gives a clearer error message to
    # non-mentor users vs. mentor-pool members who are not assigned here.
    if login.lower() not in mentor_usernames:
        await create_comment(
            owner,
            repo,
            issue_number,
            f"@{login} The `/handoff` command is only available to assigned mentors.",
            token,
        )
        return

    current_mentor = await _find_assigned_mentor_from_comments(
        owner, repo, issue_number, token
    )
    # Require a confirmed current mentor before proceeding; if the marker is missing
    # (API failure or marker never posted) we cannot safely authorize the handoff.
    if not current_mentor:
        await create_comment(
            owner,
            repo,
            issue_number,
            f"@{login} Unable to confirm the currently assigned mentor for this issue. "
            "Please contact a maintainer for assistance with the handoff.",
            token,
        )
        return
    if current_mentor.lower() != login.lower():
        await create_comment(
            owner,
            repo,
            issue_number,
            f"@{login} You are not the currently assigned mentor for this issue "
            f"(@{current_mentor} is). Only the assigned mentor can use `/handoff`.",
            token,
        )
        return

    # Determine contributor login from existing assignees (skip mentor usernames).
    contributor = None
    for assignee in issue.get("assignees", []):
        a_login = assignee.get("login", "")
        if a_login.lower() not in mentor_usernames and a_login.lower() != login.lower():
            contributor = a_login
            break

    # Build a temporary issue view with the mentor-assigned label stripped so the
    # assignment check inside _assign_mentor_to_issue does not abort early.
    updated_issue = {
        **issue,
        "labels": [
            lb for lb in issue.get("labels", [])
            if lb.get("name", "").lower() != MENTOR_ASSIGNED_LABEL.lower()
        ],
    }

    # Select and assign the replacement mentor BEFORE removing current state so
    # that if no mentor is available the issue is not left in an unmentored state.
    assigned = await _assign_mentor_to_issue(
        owner, repo, updated_issue, contributor or "", token, pool, exclude=login, env=env
    )
    if not assigned:
        await create_comment(
            owner,
            repo,
            issue_number,
            f"@{login} Handoff request noted, but no other mentor is currently available. "
            "Please reach out on [OWASP Slack](https://owasp.slack.com/archives/C0DKR6LAW) "
            "for assistance.",
            token,
        )
        return

    # Replacement assigned successfully — the outgoing mentor's label was already
    # replaced by _assign_mentor_to_issue; no assignee record to clean up.
    console.log(
        f"[MentorPool] Handoff from @{login} completed for {owner}/{repo}#{issue_number}"
    )


async def handle_mentor_rematch(
    owner: str,
    repo: str,
    issue: dict,
    login: str,
    token: str,
    mentors_config: Optional[list] = None,
    env=None,
) -> None:
    """Handle the ``/rematch`` slash command (contributor requests a different mentor)."""
    issue_number = issue["number"]
    pool = mentors_config if mentors_config is not None else []
    current_labels = {lb.get("name", "").lower() for lb in issue.get("labels", [])}
    if MENTOR_ASSIGNED_LABEL.lower() not in current_labels:
        await create_comment(
            owner,
            repo,
            issue_number,
            f"@{login} This issue does not have a mentor assigned yet. "
            "Use `/mentor` to request one.",
            token,
        )
        return

    current_mentor = await _find_assigned_mentor_from_comments(
        owner, repo, issue_number, token
    )

    # Build a temporary issue view with the mentor-assigned label stripped so the
    # assignment check inside _assign_mentor_to_issue does not abort early.
    updated_issue = {
        **issue,
        "labels": [
            lb for lb in issue.get("labels", [])
            if lb.get("name", "").lower() != MENTOR_ASSIGNED_LABEL.lower()
        ],
    }

    # Attempt to assign a replacement mentor BEFORE removing old state so that
    # if no mentor is available the issue stays in a mentored state.
    assigned = await _assign_mentor_to_issue(
        owner,
        repo,
        updated_issue,
        login,
        token,
        pool,
        exclude=current_mentor,
        env=env,
    )
    if not assigned:
        # _assign_mentor_to_issue already posted a "no mentor available" comment.
        console.log(
            f"[MentorPool] Rematch for @{login} on {owner}/{repo}#{issue_number} "
            "aborted: no replacement mentor available"
        )
        return

    # Replacement assigned — _assign_mentor_to_issue already applied the label
    # and posted the assignment comment.  No old assignee or label to clean up.
    console.log(
        f"[MentorPool] Rematch completed for @{login} on {owner}/{repo}#{issue_number}"
    )


async def _check_stale_mentor_assignments(owner: str, repo: str, token: str) -> None:
    """Unassign mentors from issues that have been inactive for MENTOR_STALE_DAYS days.

    Iterates over open issues that carry the ``mentor-assigned`` label.  When the
    issue's ``updated_at`` timestamp is older than the stale threshold the mentor is
    unassigned, the ``mentor-assigned`` label is removed, and an explanatory comment
    is posted.
    """
    try:
        stale_threshold = MENTOR_STALE_DAYS * _SECONDS_PER_DAY
        current_time = time.time()
        per_page = 100
        max_pages = 10  # Conservative limit to avoid excessive subrequests.
        page = 1

        while page <= max_pages:
            resp = await github_api(
                "GET",
                f"/repos/{owner}/{repo}/issues"
                f"?state=open&labels={MENTOR_ASSIGNED_LABEL}&per_page={per_page}&page={page}",
                token,
            )
            if resp.status != 200:
                break

            issues = json.loads(await resp.text())
            if not issues:
                break

            for issue in issues:
                if "pull_request" in issue:
                    continue
                issue_number = issue["number"]
                # Use the last human (non-bot) comment timestamp as the activity
                # signal so that bot-posted comments (e.g. mentor assignment
                # notices) don't reset the stale clock.
                last_human_ts = await _get_last_human_activity_ts(
                    owner, repo, issue_number, issue, token
                )
                if not last_human_ts:
                    continue
                if current_time - last_human_ts <= stale_threshold:
                    continue

                # Issue is stale — identify the mentor from the hidden comment marker.
                current_mentor = await _find_assigned_mentor_from_comments(
                    owner, repo, issue_number, token
                )

                # Remove the mentor-assigned label.
                await github_api(
                    "DELETE",
                    f"/repos/{owner}/{repo}/issues/{issue_number}/labels/{MENTOR_ASSIGNED_LABEL}",
                    token,
                )

                days_elapsed = int((current_time - last_human_ts) / _SECONDS_PER_DAY)
                mentor_mention = f"@{current_mentor} " if current_mentor else ""
                await create_comment(
                    owner,
                    repo,
                    issue_number,
                    f"{mentor_mention}This issue has had no activity for {days_elapsed} days "
                    f"so the mentor assignment has been automatically released. "
                    "The issue remains open — use `/mentor` to request a new mentor when work resumes.\n\n"
                    "— [OWASP BLT-Pool](https://pool.owaspblt.org)",
                    token,
                )
                console.log(
                    f"[MentorPool] Released stale mentor assignment on {owner}/{repo}#{issue_number}"
                )

            if len(issues) < per_page:
                break

            page += 1
    except Exception as exc:
        console.error(f"[MentorPool] Error checking stale mentors in {owner}/{repo}: {exc}")


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
    command = _extract_command(body)
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    login = comment["user"]["login"]
    issue_number = issue["number"]
    comment_id = comment.get("id")

    # Add eyes reaction immediately to acknowledge command receipt
    if comment_id and command:
        await create_reaction(owner, repo, comment_id, "eyes", token)

    if command == ASSIGN_COMMAND:
        await _assign(owner, repo, issue, login, token)
    elif command == UNASSIGN_COMMAND:
        await _unassign(owner, repo, issue, login, token)
    elif command == APPROVE_COMMAND:
        await _approve(owner, repo, issue, login, token)
    elif command == DENY_COMMAND:
        await _deny(owner, repo, issue, login, token)
    elif command == LEADERBOARD_COMMAND:
        console.log(f"[Leaderboard] Command received for {owner}/{repo}#{issue_number} by @{login}")
        # Best effort: remove the triggering command comment to keep threads clean.
        if env is not None and comment_id:
            delete_cmd_resp = await github_api(
                "DELETE",
                f"/repos/{owner}/{repo}/issues/comments/{comment_id}",
                token,
            )
            if delete_cmd_resp.status not in (204, 200):
                console.error(
                    f"[Leaderboard] Failed to delete triggering command comment {comment_id} "
                    f"for {owner}/{repo}#{issue_number}: status={delete_cmd_resp.status}"
                )
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
    elif command in (MENTOR_COMMAND, UNMENTOR_COMMAND, MENTOR_PAUSE_COMMAND, HANDOFF_COMMAND, REMATCH_COMMAND):
        if command == UNMENTOR_COMMAND:
            await handle_mentor_unassign(owner, repo, issue, login, token, env=env)
            return

        # Fetch mentors config once for all mentor-related commands.
        try:
            mentors_config = await _fetch_mentors_config(env=env)
        except Exception as exc:
            console.error(f"[MentorPool] Failed to fetch mentors config: {exc}")
            mentors_config = []

        if command == MENTOR_COMMAND:
            await handle_mentor_command(owner, repo, issue, login, token, mentors_config, env=env)
        elif command == MENTOR_PAUSE_COMMAND:
            await handle_mentor_pause(owner, repo, issue, login, token, mentors_config, env=env)
        elif command == HANDOFF_COMMAND:
            await handle_mentor_handoff(owner, repo, issue, login, token, mentors_config, env=env)
        elif command == REMATCH_COMMAND:
            await handle_mentor_rematch(owner, repo, issue, login, token, mentors_config, env=env)


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
    label_names = {lb.get("name", "").lower() for lb in issue.get("labels", [])}
    if HELP_WANTED_LABEL not in label_names:
        await create_comment(
            owner, repo, num,
            f"@{login} This issue is not yet ready for assignment. "
            f"A maintainer (such as @{TRIAGE_REVIEWER}) must first review it and add the "
            f'"{HELP_WANTED_LABEL}" label before `/assign` can be used.',
            token,
        )
        await _ensure_label_exists(owner, repo, NEEDS_APPROVAL_LABEL, NEEDS_APPROVAL_LABEL_COLOR, token)
        await github_api(
            "POST",
            f"/repos/{owner}/{repo}/issues/{num}/labels",
            token,
            {"labels": [NEEDS_APPROVAL_LABEL]},
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
        "Happy coding! 🚀 — [OWASP BLT-Pool](https://pool.owaspblt.org)",
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


async def _approve(
    owner: str, repo: str, issue: dict, login: str, token: str
) -> None:
    """Handle the ``/approve`` command (triage reviewer approves an issue for assignment).

    Only :data:`TRIAGE_REVIEWER` is authorised to use this command.  When
    approved the ``help wanted`` label is added and the issue opener is
    assigned so they can start work immediately.
    """
    num = issue["number"]
    if login.lower() != TRIAGE_REVIEWER.lower():
        await create_comment(
            owner, repo, num,
            f"@{login} Only @{TRIAGE_REVIEWER} can approve issues.",
            token,
        )
        return
    # Do not process /approve on pull requests or closed issues.
    if issue.get("pull_request") or issue.get("state") == "closed":
        return
    # Add the "help wanted" label — this is the prerequisite checked by the
    # /assign command; without it users cannot self-assign via /assign.
    await github_api(
        "POST",
        f"/repos/{owner}/{repo}/issues/{num}/labels",
        token,
        {"labels": [HELP_WANTED_LABEL]},
    )
    # Assign the issue to the person who opened it, respecting existing assignees
    # and the global MAX_ASSIGNEES limit enforced by the /assign workflow.
    opener = issue.get("user", {}).get("login", "")
    opener_assigned = False
    assignment_note = ""
    if opener:
        assignees = issue.get("assignees") or []
        assignee_logins = {
            a.get("login")
            for a in assignees
            if isinstance(a, dict) and a.get("login")
        }
        # If the opener is already assigned, we don't need to call the API again.
        if opener in assignee_logins:
            opener_assigned = True
        # If we've reached the maximum number of assignees, do not add another.
        elif len(assignee_logins) >= MAX_ASSIGNEES:
            assignment_note = (
                "However, this issue already has the maximum number of assignees, "
                "so the opener was not additionally assigned."
            )
        # If someone else has already claimed the issue, avoid assigning the opener.
        elif assignee_logins:
            assignment_note = (
                "Note: this issue already has an assignee, so the opener was not "
                "automatically assigned."
            )
        else:
            await github_api(
                "POST",
                f"/repos/{owner}/{repo}/issues/{num}/assignees",
                token,
                {"assignees": [opener]},
            )
            opener_assigned = True
    if opener and opener_assigned:
        assignment_text = f"@{opener} You have been assigned — good luck! 🚀\n\n"
    elif assignment_note:
        assignment_text = assignment_note + "\n\n"
    else:
        assignment_text = ""
    await create_comment(
        owner, repo, num,
        f"✅ This issue has been approved by @{login}!\n\n"
        + assignment_text
        + f'The `"{HELP_WANTED_LABEL}"` label has been added so others can also use '
        f"`/assign` to claim this issue.",
        token,
    )


async def _deny(
    owner: str, repo: str, issue: dict, login: str, token: str
) -> None:
    """Handle the ``/deny`` command (triage reviewer rejects an issue).

    Only :data:`TRIAGE_REVIEWER` is authorised to use this command.  When
    denied the issue is closed with an explanatory comment.
    """
    num = issue["number"]
    if login.lower() != TRIAGE_REVIEWER.lower():
        await create_comment(
            owner, repo, num,
            f"@{login} Only @{TRIAGE_REVIEWER} can deny issues.",
            token,
        )
        return
    # /deny should only operate on issues, not pull requests.
    if issue.get("pull_request"):
        await create_comment(
            owner,
            repo,
            num,
            f"@{login} The `/deny` command only works on issues, not pull requests.",
            token,
        )
        return
    if issue["state"] == "closed":
        await create_comment(
            owner, repo, num,
            f"@{login} This issue is already closed.",
            token,
        )
        return
    await create_comment(
        owner, repo, num,
        f"❌ This issue has been denied by @{login} and will be closed.\n\n"
        "If you believe this was a mistake, please open a new issue with more details.",
        token,
    )
    await github_api(
        "PATCH",
        f"/repos/{owner}/{repo}/issues/{num}",
        token,
        {"state": "closed"},
    )


_NO_WELCOME_REPOS_YML_PATH = os.path.join(os.path.dirname(__file__), "no_welcome_repos.yml")
_NO_WELCOME_REPOS_CACHE: Optional[list] = None


def _load_no_welcome_repos(path: str = _NO_WELCOME_REPOS_YML_PATH) -> list:
    """Return the list of repository names that should not receive the new-issue welcome message.

    Reads ``src/no_welcome_repos.yml`` which has the format::

        repos:
          - RepoName
          - AnotherRepo

    The result is cached in memory after the first read.
    """
    global _NO_WELCOME_REPOS_CACHE
    if path == _NO_WELCOME_REPOS_YML_PATH and _NO_WELCOME_REPOS_CACHE is not None:
        return _NO_WELCOME_REPOS_CACHE
    try:
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        if path == _NO_WELCOME_REPOS_YML_PATH:
            _NO_WELCOME_REPOS_CACHE = []
        return []
    repos: list = []
    in_repos_section = False
    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "repos:":
            in_repos_section = True
            continue
        # If we hit another top-level key (non-indented line ending with ":"),
        # we are no longer in the "repos" section.
        if not line.startswith(" ") and stripped.endswith(":"):
            in_repos_section = False
            continue
        if in_repos_section and stripped.startswith("- "):
            repos.append(stripped[2:].strip())
    if path == _NO_WELCOME_REPOS_YML_PATH:
        _NO_WELCOME_REPOS_CACHE = repos
    return repos


async def handle_issue_opened(
    payload: dict, token: str, blt_api_url: str
) -> None:
    issue = payload["issue"]
    sender = payload["sender"]
    if not _is_human(sender):
        return
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    no_welcome_repos = {r.lower() for r in _load_no_welcome_repos()}
    if repo.lower() in no_welcome_repos:
        return
    labels = [lb["name"].lower() for lb in issue.get("labels", [])]
    is_bug = any(lb in BUG_LABELS for lb in labels)
    msg = (
        f"👋 Thanks for opening this issue, @{sender['login']}!\n\n"
        "Our team will review it shortly. In the meantime:\n"
        "- If you'd like to work on this issue, comment `/assign` to get assigned.\n"
        "- Visit [OWASP BLT-Pool](https://pool.owaspblt.org) for more information about "
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
                "[OWASP BLT-Pool](https://pool.owaspblt.org) "
                f"(Bug ID: #{bug_data['id']}). "
                "Thank you for helping improve security!\n"
            )
    await create_comment(owner, repo, issue["number"], msg, token)


async def handle_issue_labeled(
    payload: dict, token: str, blt_api_url: str, env=None
) -> None:
    issue = payload["issue"]
    label = payload.get("label") or {}
    label_name = label.get("name", "").lower()
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]

    # --- needs-mentor label: trigger mentor pool assignment ---
    if label_name == NEEDS_MENTOR_LABEL:
        # The contributor is the first assignee if set, otherwise the issue author.
        # Avoid using payload['sender'] because for labeled events the sender is the
        # labeler (often a maintainer or bot), not the person working on the issue.
        assignees = issue.get("assignees", [])
        contributor_login = (
            assignees[0]["login"] if assignees else (issue.get("user") or {}).get("login", "")
        )
        try:
            mentors_config = await _fetch_mentors_config(env=env)
        except Exception as exc:
            console.error(f"[MentorPool] Failed to fetch mentors config on label event: {exc}")
            mentors_config = []
        await _assign_mentor_to_issue(
            owner, repo, issue, contributor_login, token, mentors_config, env=env
        )
        return

    # --- Bug labels: report to BLT ---
    if label_name not in BUG_LABELS:
        return
    all_labels = [lb["name"].lower() for lb in issue.get("labels", [])]
    # Only report the first time a bug label is added (avoid duplicates)
    if any(lb in BUG_LABELS for lb in all_labels if lb != label_name):
        return
    bug_data = await report_bug_to_blt(blt_api_url, {
        "url": issue["html_url"],
        "description": issue["title"],
        "github_url": issue["html_url"],
        "label": label.get("name", "bug"),
    })
    if bug_data and bug_data.get("id"):
        await create_comment(
            owner, repo, issue["number"],
            f"🐛 This issue has been reported to [OWASP BLT-Pool](https://pool.owaspblt.org) "
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

    # Post leaderboard
    if env is None:
        await _post_or_update_leaderboard(owner, repo, pr_number, author_login, token)
    else:
        await _post_or_update_leaderboard(owner, repo, pr_number, author_login, token, env)

    # If this PR is linked to a mentored issue, request the mentor as a reviewer.
    try:
        await _request_mentor_reviewer_for_pr(owner, repo, pr, token)
    except Exception as exc:
        console.error(f"[MentorPool] Mentor reviewer request failed (best-effort): {exc}")

    # When MENTOR_AUTO_PR_REVIEWER_ENABLED is True (either via the module
    # constant or the env var), also request a round-robin mentor as a reviewer
    # for every newly opened PR regardless of linked issues.
    auto_reviewer_enabled = MENTOR_AUTO_PR_REVIEWER_ENABLED or (
        env is not None
        and getattr(env, "MENTOR_AUTO_PR_REVIEWER_ENABLED", "").lower() == "true"
    )
    if auto_reviewer_enabled:
        try:
            mentors_config = await _fetch_mentors_config(env=env)
        except Exception:
            mentors_config = []
        try:
            await _assign_round_robin_mentor_reviewer(owner, repo, pr, mentors_config, token)
        except Exception as exc:
            console.error(f"[MentorPool] Round-robin reviewer failed (best-effort): {exc}")

    # Check for unresolved review conversations
    try:
        await check_unresolved_conversations(payload, token)
    except Exception as exc:
        console.error(f"[BLT] check_unresolved_conversations failed (best-effort, ignored): {exc}")

    # Label PR with number of pending checks (queued/waiting/action_required)
    await _try_label_pending_checks(owner, repo, pr, token)


async def _request_mentor_reviewer_for_pr(
    owner: str, repo: str, pr: dict, token: str
) -> None:
    """Request the assigned mentor as a reviewer if the PR is linked to a mentored issue.

    Parses the PR body for "Closes/Fixes/Resolves #N" references, fetches each linked
    issue, and — when the issue carries the ``mentor-assigned`` label — adds the mentor
    as a requested reviewer on the PR.
    """
    pr_number = pr["number"]
    pr_body = pr.get("body") or ""
    pr_author = (pr.get("user") or {}).get("login", "")

    # Extract issue numbers from common closing keywords.
    linked_issues = re.findall(
        r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*#(\d+)",
        pr_body,
        re.IGNORECASE,
    )
    if not linked_issues:
        return

    already_requested: set = set()
    for issue_num_str in linked_issues:
        issue_number = int(issue_num_str)
        resp = await github_api(
            "GET",
            f"/repos/{owner}/{repo}/issues/{issue_number}",
            token,
        )
        if resp.status != 200:
            continue
        issue = json.loads(await resp.text())
        labels = {lb.get("name", "").lower() for lb in issue.get("labels", [])}
        if MENTOR_ASSIGNED_LABEL.lower() not in labels:
            continue

        # Find the mentor from issue comments.
        mentor_username = await _find_assigned_mentor_from_comments(
            owner, repo, issue_number, token
        )
        if not mentor_username or mentor_username.lower() == pr_author.lower():
            continue
        # Skip if this mentor was already requested for this PR (multiple linked issues
        # may reference the same mentor; avoid duplicate reviewer-request API calls).
        if mentor_username.lower() in already_requested:
            continue
        already_requested.add(mentor_username.lower())

        # Request the mentor as a reviewer on the PR.
        review_resp = await github_api(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers",
            token,
            {"reviewers": [mentor_username]},
        )
        if review_resp.status in (200, 201):
            console.log(
                f"[MentorPool] Requested @{mentor_username} as reviewer "
                f"for PR {owner}/{repo}#{pr_number} (linked issue #{issue_number})"
            )
        else:
            console.error(
                f"[MentorPool] Failed to request reviewer @{mentor_username} "
                f"for PR #{pr_number}: status={review_resp.status}"
            )


async def _assign_round_robin_mentor_reviewer(
    owner: str,
    repo: str,
    pr: dict,
    mentors_config: Optional[list],
    token: str,
) -> None:
    """Auto-request one mentor as a reviewer on a newly opened PR (round-robin).

    Enabled only when ``MENTOR_AUTO_PR_REVIEWER_ENABLED`` is ``True``.
    Picks one active mentor using ``(pr_number - 1) mod pool_size`` so the
    assignment cycles predictably across consecutive PRs.  The PR author is
    never chosen as their own reviewer.
    """
    if not MENTOR_AUTO_PR_REVIEWER_ENABLED:
        return

    pool = mentors_config if mentors_config is not None else []
    active = [
        m for m in pool
        if m.get("active", True) and m.get("github_username")
    ]
    if not active:
        return

    pr_number = pr["number"]
    pr_author = (pr.get("user") or {}).get("login", "").lower()

    # Sort by username for a stable, deterministic order.
    active.sort(key=lambda m: m["github_username"].lower())

    # Try each slot in order starting at the round-robin position until we find
    # a mentor who is not the PR author.
    for offset in range(len(active)):
        index = (pr_number - 1 + offset) % len(active)
        mentor = active[index]
        username = mentor["github_username"]
        if username.lower() == pr_author:
            continue
        # Candidate found — request this mentor and stop regardless of outcome
        # so only one reviewer is assigned per PR.
        resp = await github_api(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers",
            token,
            {"reviewers": [username]},
        )
        if resp.status in (200, 201):
            console.log(
                f"[MentorPool] Auto round-robin reviewer: requested @{username} "
                f"for {owner}/{repo}#{pr_number}"
            )
        else:
            console.error(
                f"[MentorPool] Auto round-robin reviewer: failed to request @{username} "
                f"for PR #{pr_number}: status={resp.status}"
            )
        break  # Only assign one reviewer per PR.


async def _post_merged_pr_combined_comment(
    owner: str,
    repo: str,
    pr_number: int,
    author_login: str,
    token: str,
    env=None,
    pr_reviewers: list = None,
) -> None:
    """Post a single combined comment on a merged PR containing thanks, contributor
    leaderboard, reviewer leaderboard, and a link to the BLT Pool website."""

    # ---------------------------------------------------------------------------
    # 1. Fetch leaderboard data via shared helper
    # ---------------------------------------------------------------------------
    leaderboard_data, leaderboard_note, _is_org = await _fetch_leaderboard_data(owner, repo, token, env)

    # ---------------------------------------------------------------------------
    # 2. Build the combined comment body
    # ---------------------------------------------------------------------------
    thanks_section = (
        f"🎉 PR merged! Thanks for your contribution, @{author_login}!\n\n"
        "Your work is now part of the project. Keep contributing to "
        "[OWASP BLT-Pool](https://pool.owaspblt.org) and help make the web a safer place! 🛡️\n\n"
        "Visit [pool.owaspblt.org](https://pool.owaspblt.org) to explore the mentor pool and connect with contributors."
    )

    contributor_section = _format_leaderboard_comment(author_login, leaderboard_data, owner, leaderboard_note)
    # Strip the marker from the inner section — the combined comment has its own marker.
    contributor_section = contributor_section.replace(LEADERBOARD_MARKER + "\n", "")

    reviewer_section = _format_reviewer_leaderboard_comment(leaderboard_data, owner, pr_reviewers or [])
    reviewer_section = reviewer_section.replace(REVIEWER_LEADERBOARD_MARKER + "\n", "")

    combined_body = (
        MERGED_PR_COMMENT_MARKER + "\n"
        + thanks_section + "\n\n"
        + "---\n\n"
        + contributor_section + "\n\n"
        + "---\n\n"
        + reviewer_section
    )

    # ---------------------------------------------------------------------------
    # 3. Delete any old separate or combined comment(s), then post the new one
    # ---------------------------------------------------------------------------
    resp = await github_api("GET", f"/repos/{owner}/{repo}/issues/{pr_number}/comments?per_page=100", token)
    if resp.status == 200:
        old_comments = json.loads(await resp.text())
        for c in old_comments:
            body = c.get("body") or ""
            if any(
                marker in body
                for marker in (MERGED_PR_COMMENT_MARKER, LEADERBOARD_MARKER, REVIEWER_LEADERBOARD_MARKER)
            ):
                delete_resp = await github_api("DELETE", f"/repos/{owner}/{repo}/issues/comments/{c['id']}", token)
                if delete_resp.status not in (204, 200):
                    console.error(
                        f"[MergedPR] Failed to delete old comment {c['id']} "
                        f"for {owner}/{repo}#{pr_number}: status={delete_resp.status}"
                    )
    else:
        console.error(
            f"[MergedPR] Failed to list comments for {owner}/{repo}#{pr_number}: "
            f"status={resp.status}; posting new comment anyway"
        )

    await create_comment(owner, repo, pr_number, combined_body, token)
    console.log(f"[MergedPR] Posted combined merge comment for {owner}/{repo}#{pr_number}")


async def handle_pull_request_closed(payload: dict, token: str, env=None) -> None:
    pr = payload["pull_request"]
    author = pr.get("user", {})
    if _is_bot(author):
        return

    # Track close/merge counters for both merged and unmerged PRs.
    await _track_pr_closed_in_d1(payload, env)

    if not pr.get("merged"):
        return

    sender = payload["sender"]
    if not _is_human(sender) or _is_bot(sender):
        return

    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pr_number = pr["number"]
    author_login = pr["user"]["login"]

    # Post a single combined comment: thanks + contributor leaderboard + reviewer leaderboard
    pr_reviewers = await get_valid_reviewers(owner, repo, pr_number, author_login, token)
    await _post_merged_pr_combined_comment(owner, repo, pr_number, author_login, token, env, pr_reviewers)


async def handle_pull_request_review_submitted(payload: dict, env=None) -> None:
    """Track review credits in D1 (first two unique reviewers per PR per month)."""
    await _track_review_in_d1(payload, env)


async def _ensure_label_exists(
    owner: str, repo: str, name: str, color: str, token: str
) -> None:
    """Create a label if it does not already exist, or update its colour."""
    resp = await github_api(
        "GET",
        f"/repos/{owner}/{repo}/labels/{quote(name, safe='')}",
        token,
    )
    if resp.status == 404:
        await github_api(
            "POST",
            f"/repos/{owner}/{repo}/labels",
            token,
            {"name": name, "color": color},
        )
    elif resp.status == 200:
        data = json.loads(await resp.text())
        if data.get("color") != color:
            await github_api(
                "PATCH",
                f"/repos/{owner}/{repo}/labels/{quote(name, safe='')}",
                token,
                {"color": color},
            )

async def check_unresolved_conversations(payload, token):
    """Add label if PR has unresolved review conversations"""
    pr = payload.get("pull_request")
    if not pr:
        return

    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    number = pr["number"]

    query = """
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $number) {
          reviewThreads(first: 100) {
            nodes {
              isResolved
            }
          }
        }
      }
    }
    """

    resp = await fetch(
        "https://api.github.com/graphql",
        method="POST",
        headers=_gh_headers(token),
        body=json.dumps({
            "query": query,
            "variables": {"owner": owner, "repo": repo, "number": number},
        }),
    )

    if resp.status != 200:
        console.error(f"[BLT] GraphQL query failed: {resp.status}")
        return

    result = json.loads(await resp.text())
    pull_request = (
        result.get("data", {})
        .get("repository", {})
        .get("pullRequest")
    )
    if result.get("errors") or pull_request is None:
        console.error(f"[BLT] GraphQL reviewThreads query returned errors: {result.get('errors')}")
        return
    threads = (
        pull_request
        .get("reviewThreads", {})
        .get("nodes", [])
    )

    unresolved = any(not t.get("isResolved", True) for t in threads)

    unresolved_count = sum(not t.get("isResolved", True) for t in threads)

    # Remove any existing unresolved-conversations labels
    resp_labels = await github_api(
        "GET",
        f"/repos/{owner}/{repo}/issues/{number}/labels",
        token,
    )
    if resp_labels.status == 200:
        current_labels = json.loads(await resp_labels.text())
        for lb in current_labels:
            if lb["name"].startswith("unresolved-conversations"):
                await github_api(
                    "DELETE",
                    f"/repos/{owner}/{repo}/issues/{number}/labels/{quote(lb['name'], safe='')}",
                    token,
                )

    label = f"unresolved-conversations: {unresolved_count}"

    if unresolved:
        await _ensure_label_exists(owner, repo, label, "e74c3c", token)
    else:
        await _ensure_label_exists(owner, repo, label, "5cb85c", token)

    await github_api(
        "POST",
        f"/repos/{owner}/{repo}/issues/{number}/labels",
        token,
        {"labels": [label]},
    )


# ---------------------------------------------------------------------------
# Workflow approval labels
# ---------------------------------------------------------------------------


# Pending checks labels
# ---------------------------------------------------------------------------


async def label_pending_checks(
    owner: str, repo: str, pr_number: int, head_sha: str, token: str
) -> None:
    """Update the 'N checks pending' label on a PR.

    Counts workflow runs for *head_sha* across the ``queued``, ``waiting``,
    and ``action_required`` statuses (all mean "waiting to be run") and
    applies a yellow label with the combined count.  Removes any pre-existing
    ``"* checks pending"`` or legacy ``"* workflow* awaiting approval"`` labels
    before adding the fresh one.  When all status queries fail the label is
    left unchanged to avoid spurious removals during API outages.
    """
    pending_count = 0
    any_succeeded = False
    for status in ("queued", "waiting", "action_required"):
        resp = await github_api(
            "GET",
            f"/repos/{owner}/{repo}/actions/runs?head_sha={head_sha}&status={status}&per_page=100",
            token,
        )
        if resp.status == 200:
            any_succeeded = True
            data = json.loads(await resp.text())
            pending_count += data.get("total_count", 0)

    if not any_succeeded:
        # Can't determine state; leave existing labels untouched.
        return

    # Remove any existing pending-checks labels (both new and legacy formats).
    resp_labels = await github_api(
        "GET",
        f"/repos/{owner}/{repo}/issues/{pr_number}/labels",
        token,
    )
    if resp_labels.status == 200:
        current_labels = json.loads(await resp_labels.text())
        for lb in current_labels:
            name = lb.get("name", "")
            is_pending = "check" in name and "pending" in name
            is_legacy = "workflow" in name and "awaiting approval" in name
            if is_pending or is_legacy:
                await github_api(
                    "DELETE",
                    f"/repos/{owner}/{repo}/issues/{pr_number}/labels/{quote(name, safe='')}",
                    token,
                )

    if pending_count > 0:
        noun = "check" if pending_count == 1 else "checks"
        label = f"{pending_count} {noun} pending"
        await _ensure_label_exists(owner, repo, label, "e4c84b", token)
        await github_api(
            "POST",
            f"/repos/{owner}/{repo}/issues/{pr_number}/labels",
            token,
            {"labels": [label]},
        )


# Keep old name as an alias so any external callers remain compatible.
check_workflows_awaiting_approval = label_pending_checks


async def _try_label_pending_checks(
    owner: str, repo: str, pr: dict, token: str
) -> None:
    """Best-effort wrapper: extract the head SHA from *pr* and call
    :func:`label_pending_checks`, logging any exception instead of raising.
    """
    head_sha = pr.get("head", {}).get("sha", "")
    if not head_sha:
        return
    try:
        await label_pending_checks(owner, repo, pr["number"], head_sha, token)
    except Exception as exc:
        console.error(f"[BLT] label_pending_checks failed (best-effort, ignored): {exc}")


async def handle_workflow_run(payload: dict, token: str) -> None:
    """Handle workflow_run events to update 'checks pending' labels on PRs.

    Resolves the PR(s) associated with the workflow run and calls
    :func:`label_pending_checks` for each one.  Falls back to searching open
    PRs by head SHA when the payload's ``pull_requests`` array is empty
    (e.g. fork PRs).
    """
    workflow_run = payload.get("workflow_run", {})
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    head_sha = workflow_run.get("head_sha", "")

    pr_numbers: set[int] = set()
    for pr in workflow_run.get("pull_requests", []):
        pr_numbers.add(pr["number"])

    # For fork PRs the pull_requests array is empty; fall back to a lookup
    if not pr_numbers and head_sha:
        resp = await github_api(
            "GET",
            f"/repos/{owner}/{repo}/pulls?state=open&per_page=100",
            token,
        )
        if resp.status == 200:
            pulls = json.loads(await resp.text())
            for pull in pulls:
                if pull.get("head", {}).get("sha") == head_sha:
                    pr_numbers.add(pull["number"])

    for pr_number in pr_numbers:
        await label_pending_checks(owner, repo, pr_number, head_sha, token)


async def handle_check_run(payload: dict, token: str) -> None:
    """Handle check_run events to keep 'N checks pending' labels accurate.

    Called for ``check_run.created`` and ``check_run.completed`` actions.
    Resolves the PR(s) linked to the check run's head SHA and updates the
    pending-checks label for each one.
    """
    check_run = payload.get("check_run", {})
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    head_sha = check_run.get("head_sha", "")

    pr_numbers: set[int] = set()
    for pr in check_run.get("pull_requests", []):
        pr_numbers.add(pr["number"])

    # For fork PRs the pull_requests array is empty; look up by head SHA.
    if not pr_numbers and head_sha:
        resp = await github_api(
            "GET",
            f"/repos/{owner}/{repo}/pulls?state=open&per_page=100",
            token,
        )
        if resp.status == 200:
            pulls = json.loads(await resp.text())
            for pull in pulls:
                if pull.get("head", {}).get("sha") == head_sha:
                    pr_numbers.add(pull["number"])

    for pr_number in pr_numbers:
        await label_pending_checks(owner, repo, pr_number, head_sha, token)


# ---------------------------------------------------------------------------
# Peer review enforcement
# ---------------------------------------------------------------------------

# Common bot account patterns that should not count as peer reviews
def _is_excluded_reviewer(login: str) -> bool:
    """Return True if the reviewer is a bot or automated account."""
    if not login:
        return True
    login_lower = login.lower()
    # Exact matches
    excluded_exact = {
        "coderabbitai[bot]",
        "dependabot[bot]",
        "dependabot-preview[bot]",
        "dependabot",
        "github-actions[bot]",
    }
    if login_lower in excluded_exact:
        return True
    # Pattern matches (substrings that indicate bots)
    bot_patterns = [
        "[bot]",
        "bot]",
        "copilot",
        "renovate",
        "actions-user",
        "sentry",
        "snyk",
        "sonarcloud",
        "codecov",
    ]
    return any(pattern in login_lower for pattern in bot_patterns)


async def get_valid_reviewers(owner: str, repo: str, pr_number: int, pr_author: str, token: str) -> list[str]:
    """Get list of valid approved reviewers for a PR (excluding bots and the PR author).
    
    Paginates through all reviews and tracks the latest state per reviewer.
    Only reviewers with latest state == "APPROVED" count as valid.
    """
    # Track latest state per reviewer (chronological order, last event wins)
    reviewer_latest_state = {}
    page = 1
    
    while True:
        resp = await github_api("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews?per_page=100&page={page}", token)
        if resp.status != 200:
            console.error(f"[BLT] Failed to fetch reviews for PR #{pr_number}: {resp.status}")
            break
        
        reviews = json.loads(await resp.text())
        if not reviews:
            break
        
        # Process reviews in chronological order; overwrite each reviewer's state
        for review in reviews:
            reviewer_login = review.get("user", {}).get("login", "")
            state = review.get("state", "")
            if reviewer_login:
                reviewer_latest_state[reviewer_login] = state
        
        page += 1
    
    # Filter to only valid, approved reviewers
    valid_reviewers = set()
    for reviewer_login, state in reviewer_latest_state.items():
        if state != "APPROVED":
            continue
        if reviewer_login == pr_author:
            continue
        if _is_excluded_reviewer(reviewer_login):
            continue
        valid_reviewers.add(reviewer_login)
    
    return list(valid_reviewers)


async def ensure_label_exists(owner: str, repo: str, label_name: str, color: str, description: str, token: str) -> None:
    """Create or update a label to ensure it exists with the correct color/description."""
    resp = await github_api("GET", f"/repos/{owner}/{repo}/labels/{label_name}", token)
    
    if resp.status == 200:
        # Label exists, check if it needs update
        data = json.loads(await resp.text())
        if data.get("color") != color or data.get("description") != description:
            update_resp = await github_api("PATCH", f"/repos/{owner}/{repo}/labels/{label_name}", token, {
                "color": color,
                "description": description,
            })
            if update_resp.status not in (200, 201):
                error_text = await update_resp.text() if update_resp.status >= 400 else ""
                console.error(f"[BLT] Failed to update label {label_name}: {update_resp.status} {error_text}")
    elif resp.status == 404:
        # Label doesn't exist, create it
        create_resp = await github_api("POST", f"/repos/{owner}/{repo}/labels", token, {
            "name": label_name,
            "color": color,
            "description": description,
        })
        if create_resp.status not in (200, 201):
            error_text = await create_resp.text() if create_resp.status >= 400 else ""
            console.error(f"[BLT] Failed to create label {label_name}: {create_resp.status} {error_text}")


async def update_peer_review_labels(owner: str, repo: str, pr_number: int, has_review: bool, token: str) -> None:
    """Add/remove peer review labels based on whether the PR has a valid review."""
    new_label = "has-peer-review" if has_review else "needs-peer-review"
    old_label = "needs-peer-review" if has_review else "has-peer-review"
    color = "0e8a16" if has_review else "e74c3c"  # Green or Red
    description = "PR has received peer review" if has_review else "PR needs peer review"
    
    # Ensure the new label exists
    await ensure_label_exists(owner, repo, new_label, color, description, token)
    
    # Get current labels
    resp = await github_api("GET", f"/repos/{owner}/{repo}/issues/{pr_number}/labels", token)
    if resp.status != 200:
        return
    
    current_labels = json.loads(await resp.text())
    current_label_names = {label.get("name") for label in current_labels}
    
    # Remove old label if present
    if old_label in current_label_names:
        await github_api("DELETE", f"/repos/{owner}/{repo}/issues/{pr_number}/labels/{old_label}", token)
    
    # Add new label if not present
    if new_label not in current_label_names:
        await github_api("POST", f"/repos/{owner}/{repo}/issues/{pr_number}/labels", token, {"labels": [new_label]})


async def check_peer_review_and_comment(owner: str, repo: str, pr_number: int, pr_author: str, token: str) -> None:
    """Check if a PR has peer review, update labels, and post a comment if needed."""
    # Skip for excluded accounts
    if _is_excluded_reviewer(pr_author):
        return
    
    reviewers = await get_valid_reviewers(owner, repo, pr_number, pr_author, token)
    has_review = len(reviewers) > 0
    
    # Update labels
    await update_peer_review_labels(owner, repo, pr_number, has_review, token)
    
    # If no review, post a reminder comment (only once)
    if not has_review:
        # Check if we already posted the reminder (with pagination support)
        marker = "<!-- peer-review-check -->"
        already_commented = False
        page = 1
        while True:
            resp = await github_api("GET", f"/repos/{owner}/{repo}/issues/{pr_number}/comments?per_page=100&page={page}", token)
            if resp.status != 200:
                break
            comments = json.loads(await resp.text())
            if not comments:
                break
            if any(marker in comment.get("body", "") for comment in comments):
                already_commented = True
                break
            page += 1
        
        # Post comment only after searching all pages
        if not already_commented:
            body = f"""{marker}
👋 Hi @{pr_author}!

This pull request needs a peer review before it can be merged. Please request a review from a team member who is not:
- The PR author
- coderabbitai
- copilot

Once a valid peer review is submitted, this check will pass automatically. Thank you!

> ⚠️ Peer review enforcement is active."""
            await create_comment(owner, repo, pr_number, body, token)


async def handle_pull_request_review(payload: dict, token: str) -> None:
    """Handle pull_request_review events (submitted/dismissed) to check peer review status."""
    pr = payload["pull_request"]
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pr_author = pr["user"]["login"]
    
    await check_peer_review_and_comment(owner, repo, pr["number"], pr_author, token)


async def handle_pull_request_for_review(payload: dict, token: str) -> None:
    """Handle pull_request events (opened/synchronize/reopened) to check peer review status."""
    pr = payload["pull_request"]
    sender = payload["sender"]
    if not _is_human(sender):
        return
    
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pr_author = pr["user"]["login"]
    
    await check_peer_review_and_comment(owner, repo, pr["number"], pr_author, token)

    # Label PR with number of pending checks (queued/waiting/action_required)
    await _try_label_pending_checks(owner, repo, pr, token)


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
    secret = (getattr(env, "WEBHOOK_SECRET", "") or "").strip()
    if not secret:
        console.error(
            "[BLT][webhook] "
            f"delivery={delivery_id or '-'} event={event or '-'} action={action or '-'} "
            f"repo={repo_full_name or '-'} sender={sender_login or '-'} item={item_number or '-'} "
            f"installation={installation_id or '-'} method={request.method} "
            "status=rejected_missing_webhook_secret"
        )
        return _json(
            {
                "error": "Webhook authentication is not configured (missing WEBHOOK_SECRET)",
                "code": "webhook_secret_missing",
            },
            503,
        )
    if not verify_signature(payload_bytes, signature, secret):
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
                await handle_issue_labeled(payload, token, blt_api_url, env=env)
        elif event == "pull_request":
            if action == "opened":
                await handle_pull_request_opened(payload, token, env)
                await handle_pull_request_for_review(payload, token)
            elif action == "synchronize":
                await handle_pull_request_for_review(payload, token)
            elif action == "reopened":
                await _track_pr_reopened_in_d1(payload, env)
                await handle_pull_request_for_review(payload, token)
            elif action == "closed":
                await handle_pull_request_closed(payload, token, env)
        elif event == "pull_request_review":
            if action == "submitted":
                # Preserve existing D1 review-credit tracking
                await handle_pull_request_review_submitted(payload, env)
                # Also check peer review status
                await handle_pull_request_review(payload, token)
            elif action == "dismissed":
                await handle_pull_request_review(payload, token)
        elif event == "pull_request_review_comment":
            await check_unresolved_conversations(payload, token)
        elif event == "pull_request_review_thread":
            await check_unresolved_conversations(payload, token)
        elif event == "workflow_run":
            await handle_workflow_run(payload, token)
        elif event == "check_run" and action in ("created", "completed"):
            await handle_check_run(payload, token)

    except Exception as exc:
        console.error(f"[BLT] Webhook handler error: {exc}")
        return _json({"error": "Internal server error"}, 500)

    return _json({"ok": True})


# ---------------------------------------------------------------------------
# Landing page HTML — separated into src/index_template.py for maintainability.
# Edit templates/index.html and regenerate src/index_template.py before deploying.
# ---------------------------------------------------------------------------

_CALLBACK_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BLT-Pool GitHub App — Installed!</title>
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
      The BLT-Pool GitHub App has been successfully installed on your organization.<br />
      GitHub automation is now active inside BLT-Pool.
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
        '<span class="inline-flex items-center gap-1.5 font-semibold" style="color:#4ade80">'
        '<i class="fa-solid fa-circle-check" aria-hidden="true"></i> Set'
        "</span>"
    )
    _MISSING_BADGE = (
        '<span class="inline-flex items-center gap-1.5 font-semibold" style="color:#f87171">'
        '<i class="fa-solid fa-circle-xmark" aria-hidden="true"></i> Not set'
        "</span>"
    )
    _OPTIONAL_BADGE = (
        '<span class="inline-flex items-center gap-1.5 font-semibold" style="color:#9ca3af">'
        '<i class="fa-solid fa-circle-minus" aria-hidden="true"></i> Not configured'
        "</span>"
    )

    required_vars = ["APP_ID", "PRIVATE_KEY", "WEBHOOK_SECRET"]
    optional_vars = ["GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET"]

    rows = [
        '        <div class="mt-4 border-t border-[#E5E5E5] pt-3">',
        '          <p class="mb-1 text-xs font-semibold uppercase tracking-wider text-gray-500">Secret Variables</p>',
        "        </div>",
    ]
    for name in required_vars:
        is_set = bool(getattr(env, name, ""))
        badge = _SET_BADGE if is_set else _MISSING_BADGE
        rows.append(
            f'        <div class="flex items-center justify-between border-b border-[#E5E5E5] py-3 text-sm">'
            f'<span class="text-gray-700"><code class="text-xs">{name}</code></span>'
            f"{badge}</div>"
        )
    for name in optional_vars:
        is_set = bool(getattr(env, name, ""))
        badge = _SET_BADGE if is_set else _OPTIONAL_BADGE
        rows.append(
            f'        <div class="flex items-center justify-between border-b border-[#E5E5E5] py-3 text-sm">'
            f'<span class="text-gray-700"><code class="text-xs">{name}</code>'
            f' <span class="text-[0.7rem] text-gray-500">(optional)</span></span>'
            f"{badge}</div>"
        )
    return "\n".join(rows)


def _github_app_html(app_slug: str, env=None) -> str:
    install_url = (
        f"https://github.com/apps/{app_slug}/installations/new"
        if app_slug
        else "https://github.com/apps/blt-github-app/installations/new"
    )
    year = time.gmtime().tm_year
    secret_vars_html = _secret_vars_status_html(env) if env is not None else ""
    return (
        GITHUB_PAGE_HTML
        .replace("{{INSTALL_URL}}", install_url)
        .replace("{{YEAR}}", str(year))
        .replace("{{SECRET_VARS_STATUS}}", secret_vars_html)
    )


def _landing_html(app_slug: str, env=None) -> str:
    """Alias for _github_app_html; renders the landing page with secret-var status."""
    return _github_app_html(app_slug, env)


def _callback_html() -> str:
    return _CALLBACK_HTML


def _webhook_security_status(env) -> dict:
    """Return webhook security readiness and per-secret config checks.

    Webhook processing is secure-ready only when all auth-related secrets are
    present: ``APP_ID``, ``PRIVATE_KEY``, and ``WEBHOOK_SECRET``.
    """
    app_id_set = bool((getattr(env, "APP_ID", "") or "").strip()) if env else False
    private_key_set = bool((getattr(env, "PRIVATE_KEY", "") or "").strip()) if env else False
    webhook_secret_set = bool((getattr(env, "WEBHOOK_SECRET", "") or "").strip()) if env else False

    missing = []
    if not app_id_set:
        missing.append("APP_ID")
    if not private_key_set:
        missing.append("PRIVATE_KEY")
    if not webhook_secret_set:
        missing.append("WEBHOOK_SECRET")

    return {
        "ready": app_id_set and private_key_set and webhook_secret_set,
        "checks": {
            "app_id_configured": app_id_set,
            "private_key_configured": private_key_set,
            "webhook_secret_configured": webhook_secret_set,
        },
        "missing": missing,
    }


def _generate_mentor_row(mentor: dict, stats: Optional[dict] = None) -> str:
    """Generate HTML for a single mentor list row.

    Args:
        mentor: Mentor entry dict (loaded from D1).
        stats:  Optional dict with ``merged_prs`` and ``reviews`` keys from D1.
                When provided, totals are shown on the card.
    """
    name = _html_mod.escape(mentor.get("name", "Unknown"))
    github = mentor.get("github_username", "")
    specialties = mentor.get("specialties", [])
    max_mentees = mentor.get("max_mentees", 3)
    timezone = mentor.get("timezone", "")
    status = mentor.get("status", "available")
    active = mentor.get("active", True)

    avatar_url = (
        f"https://github.com/{github}.png"
        if github
        else "https://api.dicebear.com/7.x/initials/svg?seed=" + quote(name)
    )

    if not active or status == "inactive":
        status_badge = '<span class="inline-flex items-center gap-1 rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs font-semibold text-gray-500">Inactive</span>'
    elif status == "assigned":
        status_badge = '<span class="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700">Mentoring</span>'
    else:
        status_badge = '<span class="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">Available</span>'

    specialty_chips = " ".join(
        f'<span class="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">{s}</span>'
        for s in specialties
    ) if specialties else '<span class="text-xs text-gray-400">—</span>'

    github_link = (
        f'<a href="https://github.com/{github}" target="_blank" rel="noopener" '
        f'class="text-gray-500 hover:text-[#E10101]" aria-label="{name} GitHub profile">'
        '<i class="fa-brands fa-github" aria-hidden="true"></i></a>'
        if github
        else '<span class="text-gray-300"><i class="fa-brands fa-github" aria-hidden="true"></i></span>'
    )

    tz_cell = f'<span class="text-xs text-gray-500">{_html_mod.escape(timezone)}</span>' if timezone else '<span class="text-xs text-gray-400">—</span>'

    # Stats cells — shown when D1 data is available.
    if stats:
        merged_prs = int(stats.get("merged_prs") or 0)
        reviews = int(stats.get("reviews") or 0)
        stats_desktop = (
            f'<div class="text-center">'
            f'  <p class="text-xs text-gray-400 leading-none">PRs</p>'
            f'  <p class="text-sm font-semibold text-gray-700">{merged_prs}</p>'
            f'</div>'
            f'<div class="text-center">'
            f'  <p class="text-xs text-gray-400 leading-none">Reviews</p>'
            f'  <p class="text-sm font-semibold text-gray-700">{reviews}</p>'
            f'</div>'
        )
        stats_mobile = (
            f'<span class="text-xs text-gray-500">'
            f'<i class="fa-solid fa-code-pull-request text-gray-400" aria-hidden="true"></i> {merged_prs} PRs</span>'
            f'<span class="text-xs text-gray-500">'
            f'<i class="fa-solid fa-magnifying-glass-chart text-gray-400" aria-hidden="true"></i> {reviews} reviews</span>'
        )
        desktop_cols = "sm:grid-cols-[1fr_auto_auto_auto_auto_auto_auto]"
    else:
        stats_desktop = ""
        stats_mobile = ""
        desktop_cols = "sm:grid-cols-[1fr_auto_auto_auto_auto]"

    return f'''
    <li class="flex items-start gap-3 rounded-xl border border-[#E5E5E5] bg-white px-4 py-3 transition hover:shadow-sm sm:items-center sm:gap-4">
      <img src="{avatar_url}" alt="{name}" class="mt-0.5 h-9 w-9 shrink-0 rounded-full border border-[#E5E5E5] bg-white object-cover sm:mt-0 sm:h-10 sm:w-10">
      <div class="min-w-0 flex-1">
        <!-- Desktop: grid layout with separate columns -->
        <div class="hidden sm:grid {desktop_cols} sm:items-center sm:gap-4">
          <div class="min-w-0">
            <p class="truncate font-semibold text-[#111827] text-sm">{name}</p>
            <div class="mt-0.5 flex flex-wrap gap-1">{specialty_chips}</div>
          </div>
          <div>{status_badge}</div>
          <div class="text-center">
            <p class="text-xs text-gray-400 leading-none">Cap</p>
            <p class="text-sm font-semibold text-gray-700">{max_mentees}</p>
          </div>
          {stats_desktop}
          <div>{tz_cell}</div>
          <div>{github_link}</div>
        </div>
        <!-- Mobile: compact card layout -->
        <div class="sm:hidden">
          <div class="flex items-start justify-between gap-2">
            <p class="truncate font-semibold text-[#111827] text-sm">{name}</p>
            <div class="shrink-0">{github_link}</div>
          </div>
          <div class="mt-0.5 flex flex-wrap gap-1">{specialty_chips}</div>
          <div class="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
            {status_badge}
            <span class="text-xs text-gray-500">Cap: {max_mentees}</span>
            {stats_mobile}
            {tz_cell}
          </div>
        </div>
      </div>
    </li>
    '''


def _build_referral_leaderboard(mentors: list) -> list:
    """Return a sorted list of (referrer_username, count) tuples."""
    counts: dict = {}
    for m in mentors:
        ref = m.get("referred_by", "").strip()
        if ref:
            counts[ref] = counts.get(ref, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)


def _index_html(mentors: list = None, mentor_stats: Optional[dict] = None, active_assignments: Optional[list] = None, assignment_comment_stats: Optional[dict] = None) -> str:
    """Generate the BLT-Pool mentor directory homepage.

    Args:
        mentors:                  Mentor list loaded from D1.
                                  Defaults to an empty list when omitted or ``None``.
        mentor_stats:             Optional mapping of ``github_username → {"merged_prs", "reviews"}``
                                  from D1, used to show activity stats on each mentor card.
                                  When ``None`` or empty, stats columns are hidden.
        active_assignments:       Optional list of active mentor-issue assignment dicts from D1.
                                  Each dict has keys: org, mentor_login, mentee_login, issue_repo,
                                  issue_number, assigned_at.
                                  When ``None`` or empty, the section is hidden.
        assignment_comment_stats: Optional mapping of ``github_username → total_comments`` used to
                                  show comment-point badges on each assignment card.
    """
    if mentors is None:
        mentors = []
    if mentor_stats is None:
        mentor_stats = {}
    if active_assignments is None:
        active_assignments = []
    if assignment_comment_stats is None:
        assignment_comment_stats = {}
    # Normalize mentor_stats keys to lowercase for case-insensitive lookup.
    mentor_stats_lower = {k.lower(): v for k, v in mentor_stats.items()}
    year = time.gmtime().tm_year
    mentor_count = len(mentors)
    available_count = len([m for m in mentors if m.get("active", True) and m.get("status", "available") == "available"])

    mentor_rows_html = "\n".join(
        _generate_mentor_row(m, mentor_stats_lower.get(m.get("github_username", "").lower()))
        for m in mentors
    )

    # Build active assignments section HTML.
    if active_assignments:
        def _assignment_item(a: dict) -> str:
            mentor = _html_mod.escape(a["mentor_login"])
            mentee_raw = a.get("mentee_login", "")
            mentee = _html_mod.escape(mentee_raw)
            org = _html_mod.escape(a["org"])
            repo = _html_mod.escape(a["issue_repo"])
            number = _html_mod.escape(str(a["issue_number"]))
            time_ago = _html_mod.escape(_time_ago(a["assigned_at"]))
            mentor_comments = assignment_comment_stats.get(a["mentor_login"], 0)
            mentee_comments = assignment_comment_stats.get(mentee_raw, 0) if mentee_raw else 0

            mentee_html = ""
            if mentee:
                mentee_html = f'''
              <div class="flex items-center gap-2 min-w-0">
                <img src="https://github.com/{mentee}.png"
                     alt="{mentee}"
                     class="h-7 w-7 shrink-0 rounded-full border border-[#E5E5E5]">
                <div class="min-w-0">
                  <p class="text-xs text-gray-400 leading-none">Mentee</p>
                  <a href="https://github.com/{mentee}" target="_blank" rel="noopener"
                     class="text-sm font-semibold text-[#111827] hover:text-[#E10101] truncate block">
                    @{mentee}
                  </a>
                </div>
                <span class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-600" title="Total comments">{mentee_comments} pts</span>
              </div>'''

            return f'''<li class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-4">
              <div class="flex flex-wrap items-center justify-between gap-3">
                <div class="flex items-center gap-2 min-w-0">
                  <img src="https://github.com/{mentor}.png"
                       alt="{mentor}"
                       class="h-7 w-7 shrink-0 rounded-full border border-[#E5E5E5]">
                  <div class="min-w-0">
                    <p class="text-xs text-gray-400 leading-none">Mentor</p>
                    <a href="https://github.com/{mentor}" target="_blank" rel="noopener"
                       class="text-sm font-semibold text-[#111827] hover:text-[#E10101] truncate block">
                      @{mentor}
                    </a>
                  </div>
                  <span class="shrink-0 rounded-full bg-[#feeae9] px-2 py-0.5 text-xs font-semibold text-[#E10101]" title="Total comments">{mentor_comments} pts</span>
                </div>
                {mentee_html}
                <a href="https://github.com/{org}/{repo}/issues/{number}"
                   target="_blank" rel="noopener"
                   class="inline-flex items-center gap-1.5 rounded-full bg-[#feeae9] px-3 py-1 text-xs font-semibold text-[#E10101] hover:bg-red-100 transition shrink-0">
                  <i class="fa-brands fa-github text-xs" aria-hidden="true"></i>
                  {org}/{repo}#{number}
                </a>
              </div>
              <p class="mt-2 text-xs text-gray-400">
                <i class="fa-regular fa-clock mr-1" aria-hidden="true"></i>Assigned {time_ago}
              </p>
            </li>'''

        assignment_items = "\n".join(_assignment_item(a) for a in active_assignments)
        active_assignments_html = f'''
    <section id="active-assignments" class="rounded-2xl border border-[#E5E5E5] bg-white p-7 sm:p-9">
      <div class="mb-5 flex items-center gap-3">
        <div class="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#feeae9] text-[#E10101]">
          <i class="fa-solid fa-link" aria-hidden="true"></i>
        </div>
        <div>
          <h3 class="text-2xl font-bold text-[#111827]">Active Mentor Assignments</h3>
          <p class="mt-0.5 text-sm text-gray-500">{len(active_assignments)} active assignment{"s" if len(active_assignments) != 1 else ""}</p>
        </div>
      </div>
      <ul class="space-y-3">
        {assignment_items}
      </ul>
    </section>'''
    else:
        active_assignments_html = ""

    leaderboard_rows = _build_referral_leaderboard(mentors)
    if leaderboard_rows:
        lb_items = "\n".join(
            f'''<li class="flex items-center justify-between gap-2 py-1.5 border-b border-[#E5E5E5] last:border-0">
              <a href="https://github.com/{ref}" target="_blank" rel="noopener"
                 class="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-[#E10101] truncate">
                <img src="https://github.com/{ref}.png" alt="{ref}" class="h-6 w-6 rounded-full border border-[#E5E5E5]">
                @{ref}
              </a>
              <span class="shrink-0 rounded-full bg-[#feeae9] px-2 py-0.5 text-xs font-bold text-[#E10101]">{cnt}</span>
            </li>'''
            for ref, cnt in leaderboard_rows[:10]
        )
        leaderboard_html = f'''
        <section class="rounded-2xl border border-[#E5E5E5] bg-white p-6 h-fit sticky top-24">
          <div class="mb-4 flex items-center gap-2">
            <div class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[#feeae9] text-[#E10101]">
              <i class="fa-solid fa-trophy text-sm" aria-hidden="true"></i>
            </div>
            <h3 class="text-lg font-bold text-[#111827]">Referral Leaderboard</h3>
          </div>
          <p class="mb-4 text-xs text-gray-500">GitHub users who have referred the most mentors to the pool.</p>
          <ol class="space-y-0">
            {lb_items}
          </ol>
        </section>'''
    else:
        leaderboard_html = '''
        <section class="rounded-2xl border border-[#E5E5E5] bg-white p-6 h-fit sticky top-24">
          <div class="mb-4 flex items-center gap-2">
            <div class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[#feeae9] text-[#E10101]">
              <i class="fa-solid fa-trophy text-sm" aria-hidden="true"></i>
            </div>
            <h3 class="text-lg font-bold text-[#111827]">Referral Leaderboard</h3>
          </div>
          <p class="text-sm text-gray-500">No referrals yet — be the first to invite a mentor!</p>
        </section>'''

    return f'''<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="BLT-Pool for OWASP BLT. Connect with mentors and install the BLT GitHub extension.">
  <title>BLT-Pool | OWASP BLT Mentor Directory</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" crossorigin="anonymous" referrerpolicy="no-referrer">
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          colors: {{
            'blt-primary': '#E10101',
            'blt-primary-hover': '#b91c1c',
            'blt-border': '#E5E5E5'
          }},
          fontFamily: {{
            sans: ['Plus Jakarta Sans', 'ui-sans-serif', 'system-ui', 'sans-serif']
          }}
        }}
      }}
    }}
  </script>
  <style>
    body {{
      background:
        radial-gradient(circle at 0% 0%, rgba(225, 1, 1, 0.09), transparent 32%),
        radial-gradient(circle at 95% 4%, rgba(225, 1, 1, 0.05), transparent 28%),
        #f8fafc;
    }}
  </style>
</head>
<body class="min-h-screen font-sans text-gray-900 antialiased">

  <header class="sticky top-0 z-40 border-b border-[#E5E5E5] bg-white/90 backdrop-blur">
    <div class="mx-auto flex w-full max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
      <a href="/" class="flex items-center gap-3" aria-label="BLT-Pool home">
        <img src="/logo-sm.png" alt="OWASP BLT logo" class="h-10 w-10 rounded-xl border border-[#E5E5E5] bg-white object-contain p-1">
        <div>
          <p class="text-sm font-semibold uppercase tracking-wide text-gray-500">OWASP BLT</p>
          <h1 class="text-lg font-extrabold text-[#111827]">BLT-Pool</h1>
        </div>
      </a>
     <nav class="order-3 flex w-full items-center justify-center gap-0.5 rounded-xl border border-[#E5E5E5] bg-white p-1 sm:order-none sm:w-auto sm:justify-start" aria-label="Primary">
        <a href="/" class="rounded-lg bg-[#feeae9] px-2 py-1.5 text-xs font-semibold text-[#E10101] sm:px-3 sm:py-2 sm:text-sm">Mentors</a>
        <a href="/github-app" class="rounded-lg px-2 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 sm:px-3 sm:py-2 sm:text-sm">GitHub App</a>
        <a href="https://owaspblt.org" target="_blank" rel="noopener" class="rounded-lg px-2 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 sm:px-3 sm:py-2 sm:text-sm">
          OWASP BLT <i class="fa-solid fa-arrow-up-right-from-square text-xs" aria-hidden="true"></i>
        </a>
      </nav>
      <div class="order-2 flex items-center gap-2 sm:order-none">
        <span role="status" aria-label="Service status: Operational"
              class="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700">
          <i class="fa-solid fa-circle text-[0.4rem]" aria-hidden="true"></i>
          Live
        </span>
        <a href="/admin/login"
           class="inline-flex items-center gap-1.5 rounded-md border border-[#E5E5E5] px-3 py-2 text-xs font-semibold text-gray-700 transition hover:border-[#E10101] hover:bg-[#feeae9] hover:text-[#E10101] focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2">
          <i class="fa-solid fa-shield-halved text-[#E10101]" aria-hidden="true"></i>
          Admin
        </a>
      </div>
    </div>
  </header>

  <main class="mx-auto flex-1 w-full max-w-7xl space-y-10 px-4 py-10 sm:px-6 lg:px-8">

    <section class="overflow-hidden rounded-3xl border border-[#E5E5E5] bg-white p-7 shadow-[0_14px_40px_rgba(225,1,1,0.10)] sm:p-10">
      <div class="grid gap-8 lg:grid-cols-2 lg:items-center">
        <div>
          <span class="mb-4 inline-flex items-center gap-2 rounded-full border border-[#E5E5E5] bg-gray-50 px-3 py-1 text-xs font-semibold text-gray-700">
            <i class="fa-solid fa-users text-[#E10101]" aria-hidden="true"></i>
            Mentor directory for BLT contributors
          </span>
          <h2 class="text-3xl font-extrabold leading-tight text-[#111827] sm:text-5xl">
            Find your guide inside
            <span class="text-[#E10101]">OWASP BLT-Pool</span>
          </h2>
          <p class="mt-4 max-w-2xl text-base leading-relaxed text-gray-600 sm:text-lg">
            Connect with mentors, get support for your first pull request, and keep contribution quality high with a practical community workflow.
          </p>
          <div class="mt-7 flex flex-wrap gap-3">
            <a href="https://owasp.slack.com/signup" target="_blank" rel="noopener"
               class="inline-flex items-center gap-2 rounded-md bg-[#E10101] px-5 py-3 text-sm font-semibold text-white transition hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2">
              <i class="fa-brands fa-slack" aria-hidden="true"></i>
              Join OWASP Slack
            </a>
            <a href="/github-app"
               class="inline-flex items-center gap-2 rounded-md border border-[#E10101] px-5 py-3 text-sm font-semibold text-[#E10101] transition hover:bg-[#E10101] hover:text-white focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2">
              <i class="fa-brands fa-github" aria-hidden="true"></i>
              Open GitHub App
            </a>
          </div>
        </div>
        <div class="grid gap-3 sm:grid-cols-2">
          <article class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Mentors</p>
            <p class="mt-1 text-2xl font-extrabold text-[#111827]">{mentor_count}</p>
          </article>
          <article class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Available Now</p>
            <p class="mt-1 text-2xl font-extrabold text-[#111827]">{available_count}</p>
          </article>
          <article class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-4 sm:col-span-2">
            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Why It Works</p>
            <p class="mt-1 text-sm font-semibold text-gray-700">Round-robin assignment prevents overload and keeps responses timely.</p>
          </article>
        </div>
      </div>
    </section>

    <!-- Two-column layout: mentor list (2/3) + referral leaderboard (1/3) -->
    <div class="grid grid-cols-1 gap-8 lg:grid-cols-[2fr_1fr] lg:items-start">

      <!-- Mentor list -->
      <section class="space-y-4">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h3 class="text-2xl font-bold text-[#111827]">
            Mentor Pool <span class="text-base font-medium text-gray-500">({mentor_count} total, {available_count} available)</span>
          </h3>
        </div>
        <ul class="space-y-2" aria-label="Mentor list">
          <!-- Header row (desktop) -->
          <li class="hidden sm:grid sm:grid-cols-[1fr_auto_auto_auto_auto] sm:items-center sm:gap-4 sm:px-4 sm:py-1 text-xs font-semibold uppercase tracking-wide text-gray-400">
            <span>Mentor</span>
            <span>Status</span>
            <span class="text-center">Cap</span>
            <span>Timezone</span>
            <span>Link</span>
          </li>
          {mentor_rows_html}
        </ul>
      </section>

      <!-- Referral leaderboard -->
      {leaderboard_html}

    </div>

    {active_assignments_html}

    <section class="rounded-2xl border border-[#E5E5E5] bg-white p-7 sm:p-9">
      <h3 class="text-2xl font-bold text-[#111827]">How Mentor Matching Works</h3>
      <div class="mt-6 grid gap-5 md:grid-cols-3">
        <article class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-5">
          <div class="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-[#feeae9] text-[#E10101]">
            <i class="fa-solid fa-user-plus" aria-hidden="true"></i>
          </div>
          <h4 class="text-base font-bold text-[#111827]">1. Pick an issue</h4>
          <p class="mt-2 text-sm text-gray-600">Start with an issue tagged for contribution or mentor support.</p>
        </article>
        <article class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-5">
          <div class="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-[#feeae9] text-[#E10101]">
            <i class="fa-solid fa-arrows-rotate" aria-hidden="true"></i>
          </div>
          <h4 class="text-base font-bold text-[#111827]">2. Get assigned</h4>
          <p class="mt-2 text-sm text-gray-600">Mentors are matched with healthy load balancing to avoid bottlenecks.</p>
        </article>
        <article class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-5">
          <div class="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-[#feeae9] text-[#E10101]">
            <i class="fa-solid fa-comments" aria-hidden="true"></i>
          </div>
          <h4 class="text-base font-bold text-[#111827]">3. Build and review</h4>
          <p class="mt-2 text-sm text-gray-600">Work with your mentor on review quality, security checks, and merge confidence.</p>
        </article>
      </div>
    </section>

    <section id="mentor-commands" class="rounded-2xl border border-[#E5E5E5] bg-white p-7 sm:p-9">
      <h3 class="text-2xl font-bold text-[#111827]">Mentor Slash Commands</h3>
      <p class="mt-3 text-sm leading-relaxed text-gray-600">
        Use these commands directly in GitHub issue comments to interact with the mentor system.
      </p>
      <div class="mt-5 grid gap-4 sm:grid-cols-2">
        <article class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-4">
          <p class="font-mono text-sm font-bold text-[#E10101]">/mentor</p>
          <p class="mt-2 text-sm text-gray-600">Request a mentor for this issue. The bot auto-assigns the best available mentor from the pool.</p>
        </article>
        <article class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-4">
          <p class="font-mono text-sm font-bold text-[#E10101]">/unmentor</p>
          <p class="mt-2 text-sm text-gray-600">Cancel a mentor assignment. Use this to undo an accidental <code class="font-mono">/mentor</code> request. Available to the issue author or the assigned mentor.</p>
        </article>
        <article class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-4">
          <p class="font-mono text-sm font-bold text-[#E10101]">/mentor-pause</p>
          <p class="mt-2 text-sm text-gray-600">Pause your mentor availability. Use this when you need a break from accepting new mentees.</p>
        </article>
        <article class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-4">
          <p class="font-mono text-sm font-bold text-[#E10101]">/handoff</p>
          <p class="mt-2 text-sm text-gray-600">Transfer this issue to another available mentor. The current mentor uses this to hand off cleanly.</p>
        </article>
        <article class="rounded-xl border border-[#E5E5E5] bg-gray-50 p-4">
          <p class="font-mono text-sm font-bold text-[#E10101]">/rematch</p>
          <p class="mt-2 text-sm text-gray-600">Request a different mentor for this issue. The bot re-runs matching to find a fresh assignment.</p>
        </article>
      </div>
    </section>

    <section id="join-mentor" class="rounded-2xl border border-[#E5E5E5] bg-white p-7 sm:p-9">
      <div class="mb-6 flex items-start gap-4">
        <div class="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#feeae9] text-[#E10101]">
          <i class="fa-solid fa-user-plus" aria-hidden="true"></i>
        </div>
        <div>
          <h3 class="text-2xl font-bold text-[#111827]">Become a Mentor</h3>
          <p class="mt-1 text-sm leading-relaxed text-gray-600">
            Fill in the form and submit — you are added to the mentor pool immediately.
          </p>
        </div>
      </div>
      <form id="mentor-form" class="grid gap-4 sm:grid-cols-2" novalidate>
        <div>
          <label for="mf-name" class="mb-1 block text-sm font-semibold text-gray-700">
            Display Name <span class="text-[#E10101]">*</span>
          </label>
          <input id="mf-name" type="text" required autocomplete="name" placeholder="Jane Doe"
                 maxlength="100"
                 class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-[#E10101] focus:ring-1 focus:ring-[#E10101] focus:outline-none">
        </div>
        <div>
          <label for="mf-github" class="mb-1 block text-sm font-semibold text-gray-700">
            GitHub Username <span class="text-[#E10101]">*</span>
          </label>
          <input id="mf-github" type="text" required autocomplete="username" placeholder="janedoe"
                 maxlength="39" pattern="[a-zA-Z0-9]([a-zA-Z0-9\\-]{{0,37}}[a-zA-Z0-9])?"
                 class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-[#E10101] focus:ring-1 focus:ring-[#E10101] focus:outline-none">
        </div>
        <div class="sm:col-span-2">
          <label for="mf-specialties" class="mb-1 block text-sm font-semibold text-gray-700">
            Specialties <span class="text-xs font-normal text-gray-400">(optional — comma-separated)</span>
          </label>
          <input id="mf-specialties" type="text" placeholder="e.g. frontend, python, security, docs"
                 maxlength="300"
                 class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-[#E10101] focus:ring-1 focus:ring-[#E10101] focus:outline-none">
        </div>
        <div>
          <label for="mf-max" class="mb-1 block text-sm font-semibold text-gray-700">
            Max concurrent mentees
          </label>
          <input id="mf-max" type="number" min="1" max="10" value="3"
                 class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-[#E10101] focus:ring-1 focus:ring-[#E10101] focus:outline-none">
        </div>
        <div>
          <label for="mf-tz" class="mb-1 block text-sm font-semibold text-gray-700">
            Timezone <span class="text-xs font-normal text-gray-400">(optional)</span>
          </label>
          <input id="mf-tz" type="text" placeholder="e.g. UTC+5:30"
                 maxlength="60"
                 class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-[#E10101] focus:ring-1 focus:ring-[#E10101] focus:outline-none">
        </div>
        <div class="sm:col-span-2">
          <label for="mf-referral" class="mb-1 block text-sm font-semibold text-gray-700">
            Referred By <span class="text-xs font-normal text-gray-400">(optional — GitHub username of who invited you)</span>
          </label>
          <input id="mf-referral" type="text" placeholder="e.g. janedoe"
                 maxlength="39" pattern="[a-zA-Z0-9]([a-zA-Z0-9\\-]{{0,37}}[a-zA-Z0-9])?"
                 class="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-[#E10101] focus:ring-1 focus:ring-[#E10101] focus:outline-none">
        </div>
        <div id="mf-error" role="alert" class="hidden sm:col-span-2 text-sm font-semibold text-[#E10101]"></div>
        <div id="mf-success" role="status" class="hidden sm:col-span-2 text-sm font-semibold text-green-600"></div>
        <div class="sm:col-span-2">
          <button id="mf-submit" type="submit"
                  class="inline-flex items-center gap-2 rounded-md bg-[#E10101] px-5 py-3 text-sm font-semibold text-white transition hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed">
            <i class="fa-solid fa-user-plus" aria-hidden="true"></i>
            Join the Mentor Pool
          </button>
        </div>
      </form>
      <script>
        (function () {{
          // Regex matching GitHub's username rules (identical to server-side _GH_USERNAME_RE).
          var GH_USERNAME_RE = /^[a-zA-Z0-9](?:[a-zA-Z0-9\\-]{{0,37}}[a-zA-Z0-9])?$/;
          // Regex matching each specialty tag (identical to server-side _SPECIALTY_RE).
          var SPECIALTY_RE = /^[a-z0-9][a-z0-9+#.\\-]{{0,29}}$/;

          /**
           * Return true if the value contains HTML angle brackets, raw ampersands,
           * double-quotes, or common scripting injection patterns.
           */
          function containsScripting(val) {{
            if (/[<>"&]/.test(val)) return true;
            if (/javascript\\s*:/i.test(val)) return true;
            if (/on\\w+\\s*=/i.test(val)) return true;
            return false;
          }}

          document.getElementById('mentor-form').addEventListener('submit', function (e) {{
            e.preventDefault();
            var name     = document.getElementById('mf-name').value.trim();
            var github   = document.getElementById('mf-github').value.trim().replace(/^@/, '');
            var specs    = document.getElementById('mf-specialties').value.trim();
            var maxM     = parseInt(document.getElementById('mf-max').value.trim(), 10);
            var tz       = document.getElementById('mf-tz').value.trim();
            var referral = document.getElementById('mf-referral').value.trim().replace(/^@/, '');
            var errEl    = document.getElementById('mf-error');
            var okEl     = document.getElementById('mf-success');
            var btn      = document.getElementById('mf-submit');
            errEl.classList.add('hidden');
            okEl.classList.add('hidden');

            // Required fields.
            if (!name) {{
              errEl.textContent = 'Display name is required.';
              errEl.classList.remove('hidden');
              return;
            }}
            if (!github) {{
              errEl.textContent = 'GitHub username is required.';
              errEl.classList.remove('hidden');
              return;
            }}

            // Length guards (mirrors maxlength attributes).
            if (name.length > 100) {{
              errEl.textContent = 'Display name must be 100 characters or fewer.';
              errEl.classList.remove('hidden');
              return;
            }}
            if (tz.length > 60) {{
              errEl.textContent = 'Timezone must be 60 characters or fewer.';
              errEl.classList.remove('hidden');
              return;
            }}

            // Script / HTML injection checks on free-text fields.
            if (containsScripting(name)) {{
              errEl.textContent = 'Display name contains invalid characters. HTML and scripting are not allowed.';
              errEl.classList.remove('hidden');
              return;
            }}
            if (containsScripting(tz)) {{
              errEl.textContent = 'Timezone contains invalid characters. HTML and scripting are not allowed.';
              errEl.classList.remove('hidden');
              return;
            }}
            if (containsScripting(specs)) {{
              errEl.textContent = 'Specialties contain invalid characters. HTML and scripting are not allowed.';
              errEl.classList.remove('hidden');
              return;
            }}

            // GitHub username format validation.
            if (!GH_USERNAME_RE.test(github)) {{
              errEl.textContent = 'GitHub username may only contain letters, digits, and single hyphens, and cannot begin or end with a hyphen (max 39 characters).';
              errEl.classList.remove('hidden');
              return;
            }}
            if (referral && !GH_USERNAME_RE.test(referral)) {{
              errEl.textContent = 'Referred-by username may only contain letters, digits, and single hyphens, and cannot begin or end with a hyphen (max 39 characters).';
              errEl.classList.remove('hidden');
              return;
            }}

            // Validate each specialty tag format.
            var specialties = specs ? specs.split(',').map(function(s) {{ return s.trim(); }}).filter(Boolean) : [];
            for (var i = 0; i < specialties.length; i++) {{
              if (!SPECIALTY_RE.test(specialties[i])) {{
                errEl.textContent = 'Invalid specialty tag "' + specialties[i] + '". Tags must be 1-30 lowercase alphanumeric characters (also +, #, ., -).';
                errEl.classList.remove('hidden');
                return;
              }}
            }}

            // max_mentees range guard.
            if (isNaN(maxM) || maxM < 1 || maxM > 10) {{
              errEl.textContent = 'Max concurrent mentees must be a number between 1 and 10.';
              errEl.classList.remove('hidden');
              return;
            }}

            btn.disabled = true;
            fetch('/api/mentors', {{
              method: 'POST',
              headers: {{'Content-Type': 'application/json'}},
              body: JSON.stringify({{
                name: name,
                github_username: github,
                specialties: specialties,
                max_mentees: maxM,
                timezone: tz,
                referred_by: referral
              }})
            }})
            .then(function(res) {{
              return res.json().then(function(data) {{ return {{ok: res.ok, data: data}}; }});
            }})
            .then(function(result) {{
              btn.disabled = false;
              if (result.ok) {{
                if (result.data && result.data.active) {{
                  okEl.textContent = 'Welcome to the mentor pool, @' + github + '! Your mentor profile is now published.';
                }} else {{
                  okEl.textContent = 'Thanks, @' + github + '! Your mentor profile was saved and is waiting for admin publishing.';
                }}
                okEl.classList.remove('hidden');
                document.getElementById('mentor-form').reset();
              }} else {{
                errEl.textContent = result.data.error || 'An error occurred. Please try again.';
                errEl.classList.remove('hidden');
              }}
            }})
            .catch(function() {{
              btn.disabled = false;
              errEl.textContent = 'Network error. Please try again.';
              errEl.classList.remove('hidden');
            }});
          }});
        }}());
      </script>
    </section>

  </main>

  <footer class="border-t border-[#E5E5E5] bg-white">
    <div class="mx-auto max-w-7xl px-4 py-6 text-center text-sm text-gray-600 sm:px-6 lg:px-8">
      Built by the <a href="https://owaspblt.org" target="_blank" rel="noopener" class="text-red-600 hover:underline">OWASP BLT community</a>
      <span aria-hidden="true"> • </span>
      <a href="/github-app" class="text-red-600 hover:underline">GitHub App</a>
      <span aria-hidden="true"> • </span>
      <a href="https://github.com/OWASP-BLT/BLT-Pool" target="_blank" rel="noopener" class="text-red-600 hover:underline">BLT-Pool Repo</a>
      <p class="mt-2 text-xs text-gray-500">&copy; {year} OWASP Foundation. All rights reserved.</p>
    </div>
  </footer>

</body>
</html>'''


# ---------------------------------------------------------------------------
# Mentor API handler
# ---------------------------------------------------------------------------

# GitHub username: 1-39 alphanumeric/hyphen characters, cannot start or end with a hyphen.
_GH_USERNAME_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,37}[a-zA-Z0-9])?$")
# Specialty tag: 1-30 chars; lowercase letters, digits, +, #, dot, hyphen allowed.
_SPECIALTY_RE = re.compile(r"^[a-z0-9][a-z0-9+#.\-]{0,29}$")
# Display name: 1-100 printable characters, no HTML angle brackets, ampersands,
# double quotes, or ASCII control characters (prevents script injection).
_NAME_RE = re.compile(r"^[^<>&\"\x00-\x1f]{1,100}$")
# Timezone: optional free-form label, same restrictions as name but max 60 chars.
_TIMEZONE_RE = re.compile(r"^[^<>&\"\x00-\x1f]{1,60}$")
# Bounds for the max_mentees field in the mentor form.
_MENTOR_MIN_MENTEES_CAP = 1
_MENTOR_MAX_MENTEES_CAP = 10


async def _verify_gh_user_exists(username: str, env=None) -> bool:
    """Return True if the GitHub username exists on GitHub.

    Uses GITHUB_TOKEN from env if available (5,000 req/h); falls back to
    unauthenticated requests (60 req/h per IP) when no token is set.
    Returns True on network/API error so a transient outage does not block
    legitimate submissions (fail-open policy).
    """
    token = getattr(env, "GITHUB_TOKEN", "") if env else ""
    try:
        resp = await github_api("GET", f"/users/{username}", token)
        return resp.status == 200
    except Exception:
        return True  # Fail open: don't block when GitHub API is temporarily unavailable


async def _handle_add_mentor(request, env) -> "Response":
    """POST /api/mentors — insert a new mentor into the D1 mentors table.

    Expected JSON body::

        {
            "name": "Jane Doe",
            "github_username": "janedoe",
            "specialties": ["frontend", "python"],   // optional
            "max_mentees": 3,                         // optional, 1-10
            "timezone": "UTC+5:30",                   // optional
            "referred_by": "referrer"                 // optional
        }

    Returns 201 on success, 400 on validation failure, 500 on DB error.
    """
    try:
        body = json.loads(await request.text())
    except Exception:
        return _json({"error": "Invalid JSON body"}, 400)

    name = (body.get("name") or "").strip()
    github_username = (body.get("github_username") or "").strip().lstrip("@")
    specialties_raw = body.get("specialties") or []
    max_mentees = body.get("max_mentees", 3)
    timezone = (body.get("timezone") or "").strip()
    referred_by = (body.get("referred_by") or "").strip().lstrip("@")

    if not name:
        return _json({"error": "Field 'name' is required"}, 400)
    if not _NAME_RE.match(name):
        return _json({"error": "Display name contains invalid characters (HTML and scripting are not allowed)"}, 400)
    if not github_username:
        return _json({"error": "Field 'github_username' is required"}, 400)
    if not _GH_USERNAME_RE.match(github_username):
        return _json({"error": "Invalid GitHub username format"}, 400)

    # Verify the GitHub username actually exists.
    if not await _verify_gh_user_exists(github_username, env):
        return _json({"error": f"GitHub username '{github_username}' was not found on GitHub"}, 400)

    # Normalise specialties — accept a list or a comma-separated string.
    if isinstance(specialties_raw, str):
        specialties = [s.strip() for s in specialties_raw.split(",") if s.strip()]
    elif isinstance(specialties_raw, list):
        specialties = [str(s).strip() for s in specialties_raw if str(s).strip()]
    else:
        specialties = []
    # Validate each specialty tag.
    for spec in specialties:
        if not _SPECIALTY_RE.match(spec):
            return _json({"error": f"Invalid specialty tag: {spec!r}"}, 400)

    try:
        max_mentees = max(_MENTOR_MIN_MENTEES_CAP, min(_MENTOR_MAX_MENTEES_CAP, int(max_mentees)))
    except (TypeError, ValueError):
        max_mentees = 3

    if timezone and not _TIMEZONE_RE.match(timezone):
        return _json({"error": "Timezone contains invalid characters (HTML and scripting are not allowed)"}, 400)

    if referred_by and not _GH_USERNAME_RE.match(referred_by):
        return _json({"error": "Invalid referred_by username format"}, 400)

    # Verify the referrer's GitHub username exists (if provided).
    if referred_by and not await _verify_gh_user_exists(referred_by, env):
        return _json({"error": f"Referred-by username '{referred_by}' was not found on GitHub"}, 400)

    db = _d1_binding(env)
    if not db:
        return _json({"error": "Database not available"}, 500)

    mentor_is_active = await has_merged_pr_in_org(
        env,
        github_username,
        getattr(env, "GITHUB_ORG", "OWASP-BLT"),
    )

    try:
        existing = await _d1_all(
            db,
            "SELECT github_username FROM mentors WHERE github_username = ?",
            (github_username,),
        )
        if existing:
            return _json({"error": f"GitHub user '{github_username}' is already in the mentor pool"}, 409)
    except Exception as exc:
        console.error(f"[MentorPool] Failed to check duplicate mentor {github_username}: {exc}")
        return _json({"error": "Failed to validate mentor. Please try again later."}, 500)

    try:
        await _ensure_leaderboard_schema(db)
        await _d1_add_mentor(
            db,
            github_username=github_username,
            name=name,
            specialties=specialties,
            max_mentees=max_mentees,
            active=mentor_is_active,
            timezone=timezone,
            referred_by=referred_by,
        )
    except Exception as exc:
        console.error(f"[MentorPool] Failed to add mentor {github_username}: {exc}")
        return _json({"error": "Failed to save mentor"}, 500)

    console.log(
        f"[MentorPool] Added mentor {github_username} via API active={mentor_is_active}"
    )
    return _json(
        {"ok": True, "github_username": github_username, "active": mentor_is_active},
        201,
    )


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

    admin_response = await AdminService(env).handle(request)
    if admin_response is not None:
        return admin_response

    if method == "GET" and path == "/":
        # Load mentors from D1.
        org = getattr(env, "GITHUB_ORG", "OWASP-BLT")
        mentors: list = []
        try:
            mentors = await _load_mentors_local(env)
        except Exception as exc:
            console.error(f"[MentorPool] Failed to load mentors for homepage: {exc}")
        # Fetch per-mentor activity stats from D1 (best-effort; no stats if D1 unavailable).
        mentor_stats: dict = {}
        try:
            token = getattr(env, "GITHUB_TOKEN", "")
            mentor_stats = await _fetch_mentor_stats_from_d1(env, org, mentors=mentors, token=token)
        except Exception as exc:
            console.error(f"[MentorPool] Failed to fetch mentor stats for homepage: {exc}")
        # Fetch active mentor assignments from D1 (best-effort).
        active_assignments: list = []
        assignment_comment_stats: dict = {}
        db = _d1_binding(env)
        if db:
            try:
                await _ensure_leaderboard_schema(db)
                active_assignments = await _d1_get_active_assignments(db, org)
            except Exception as exc:
                console.error(f"[MentorPool] Failed to fetch active assignments for homepage: {exc}")
            if active_assignments:
                try:
                    all_logins = list({
                        login
                        for a in active_assignments
                        for login in (a["mentor_login"], a.get("mentee_login", ""))
                        if login
                    })
                    assignment_comment_stats = await _d1_get_user_comment_totals(db, org, all_logins)
                except Exception as exc:
                    console.error(f"[MentorPool] Failed to fetch assignment comment stats: {exc}")
        return _html(_index_html(mentors, mentor_stats, active_assignments, assignment_comment_stats))

    if method == "GET" and path == "/github-app":
        app_slug = getattr(env, "GITHUB_APP_SLUG", "")
        return _html(_github_app_html(app_slug, env))

    if method == "GET" and path == "/health":
        webhook_security = _webhook_security_status(env)
        return _json(
            {
                "status": "ok" if webhook_security["ready"] else "degraded",
                "service": "BLT-Pool",
                "checks": {
                    "webhook_security": webhook_security,
                },
            }
        )

    if method == "POST" and path == "/api/mentors":
        return await _handle_add_mentor(request, env)

    if method == "POST" and path == "/api/github/webhooks":
        return await handle_webhook(request, env)

    # GitHub redirects here after a successful installation
    if method == "GET" and path == "/callback":
        return _html(_callback_html())

    # Admin: reset corrupted leaderboard data for a given org/month so a fresh
    # backfill can re-populate it.  Requires ADMIN_SECRET env variable.
    if method == "POST" and path == "/admin/reset-leaderboard-month":
        admin_secret = getattr(env, "ADMIN_SECRET", "")
        if not admin_secret:
            return _json({"error": "Admin endpoint not configured"}, 403)
        auth_header = (request.headers.get("Authorization") or "").strip()
        if auth_header != f"Bearer {admin_secret}":
            return _json({"error": "Unauthorized"}, 401)
        try:
            body = json.loads(await request.text())
        except Exception:
            return _json({"error": "Invalid JSON body"}, 400)
        org = (body.get("org") or "").strip()
        if not org:
            return _json({"error": "Missing required field: org"}, 400)
        month_key = (body.get("month_key") or "").strip()
        if not month_key:
            return _json(
                {"error": "Missing required field: month_key (e.g. '2026-03'). "
                 "Provide an explicit month to prevent accidental resets."},
                400,
            )
        if not re.fullmatch(r"\d{4}-\d{2}", month_key):
            return _json({"error": "month_key must be in YYYY-MM format (e.g. '2026-03')"}, 400)
        db = _d1_binding(env)
        if not db:
            return _json({"error": "No D1 binding available"}, 500)
        deleted = await _reset_leaderboard_month(org, month_key, db)
        return _json({"ok": True, "org": org, "month_key": month_key, "tables_cleared": deleted})

    return _json({"error": "Not found"}, 404)


# ---------------------------------------------------------------------------
# Scheduled event handler — runs on cron triggers
# ---------------------------------------------------------------------------


async def _run_scheduled(env):
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
                await _check_stale_mentor_assignments(owner, repo_name, token)
        
        console.log("[CRON] Stale assignment check complete")
        
    except Exception as e:
        console.error(f"[CRON] Error during scheduled task: {e}")


async def on_scheduled(controller, env, ctx=None):
    """Cloudflare Python Workers cron entrypoint."""
    await _run_scheduled(env)


async def scheduled(event, env):
    """Backward-compatible alias for runtimes expecting scheduled()."""
    await _run_scheduled(env)


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
                    "Thank you for your interest! 🙏 — [OWASP BLT-Pool](https://pool.owaspblt.org)",
                    token
                )
    
    except Exception as e:
        console.error(f"[CRON] Error checking {owner}/{repo}: {e}")
