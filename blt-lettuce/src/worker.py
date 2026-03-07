"""
Cloudflare Python Worker for BLT-Lettuce Slack Bot.

This worker handles webhook events, sends welcome messages,
tracks stats, serves the homepage and dashboard, manages
Slack OAuth (sign-in + workspace installation), stores data
in Cloudflare D1, and handles all Slack interactions.
"""

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote_plus, urlencode, urlparse

from js import Headers, Response
from js import fetch as js_fetch

try:
    from workers import WorkerEntrypoint
except ImportError:
    # Local tooling may not provide the workers runtime package.
    class WorkerEntrypoint:
        env = None


from lettuce.html_templates import (
    get_404_html,
    get_500_html,
    get_dashboard_html,
    get_homepage_html,
    get_login_page_html,
    get_status_html,
)
from lettuce.sentry import get_sentry, init_sentry

# ---------------------------------------------------------------------------
# Channel IDs - configure via environment variables
# ---------------------------------------------------------------------------
DEFAULT_DEPLOYS_CHANNEL = None
DEFAULT_JOINS_CHANNEL_ID = None
DEFAULT_CONTRIBUTE_ID = None


def get_utc_now():
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _make_oauth_state(intent):
    """Generate a random CSRF state token with the intent embedded as a prefix."""
    return f"{intent}:{secrets.token_hex(16)}"


def _verify_oauth_state(stored_state, received_state):
    """Validate the OAuth CSRF state and return the intent, or None on failure."""
    if not stored_state or not received_state:
        return None
    if not hmac.compare_digest(stored_state, received_state):
        return None
    parts = stored_state.split(":", 1)
    return parts[0] if len(parts) == 2 else None


def _row(result):
    """Safely convert a D1 single-row result to a plain dict."""
    if result is None:
        return None
    try:
        return _js_to_python(dict(result))
    except Exception:
        converted = _js_to_python(result)
        return converted if isinstance(converted, dict) else result


def _rows(result):
    """Safely convert a D1 multi-row result to a list of plain dicts."""
    if result is None:
        return []
    rows = getattr(result, "results", None)
    if rows is None:
        return []

    rows = _js_to_python(rows)
    if not isinstance(rows, list):
        rows = [rows]

    out = []
    for r in rows:
        try:
            out.append(_js_to_python(dict(r)))
        except Exception:
            converted = _js_to_python(r)
            if isinstance(converted, dict):
                out.append(converted)
            else:
                out.append(r)
    return out


def _js_to_python(value):
    """Best-effort conversion of JS proxy objects to native Python values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {k: _js_to_python(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_js_to_python(v) for v in value]

    # Pyodide JSProxy objects often expose to_py().
    try:
        to_py = getattr(value, "to_py", None)
        if callable(to_py):
            return _js_to_python(to_py())
    except Exception:
        pass

    # Fallback for plain JS objects.
    try:
        from js import Object

        out = {}
        keys = Object.keys(value)
        for idx in range(len(keys)):
            key = str(keys[idx])
            out[key] = _js_to_python(getattr(value, key, None))
        if out:
            return out
    except Exception:
        pass

    return value


def _obj_get(obj, key, default=None):
    """Read key from dict/JSProxy-like object without assuming subscriptability."""
    if obj is None:
        return default
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
    except Exception:
        pass
    try:
        val = getattr(obj, key)
        if val is not None:
            return val
    except Exception:
        pass
    return default


# One-time schema bootstrap guard for the active worker instance.
_schema_initialized = False


async def ensure_d1_schema(env):
    """Create required D1 tables/indexes if they do not exist."""
    global _schema_initialized
    if _schema_initialized:
        return True

    statements = [
        (
            "CREATE TABLE IF NOT EXISTS users ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "slack_user_id TEXT UNIQUE NOT NULL,"
            "team_id TEXT NOT NULL,"
            "name TEXT DEFAULT '',"
            "email TEXT DEFAULT '',"
            "access_token TEXT DEFAULT '',"
            "created_at TEXT NOT NULL,"
            "updated_at TEXT NOT NULL"
            ")"
        ),
        (
            "CREATE TABLE IF NOT EXISTS sessions ("
            "id TEXT PRIMARY KEY,"
            "user_id INTEGER NOT NULL,"
            "created_at TEXT NOT NULL,"
            "expires_at TEXT NOT NULL,"
            "FOREIGN KEY (user_id) REFERENCES users(id)"
            ")"
        ),
        (
            "CREATE TABLE IF NOT EXISTS workspaces ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "team_id TEXT UNIQUE NOT NULL,"
            "team_name TEXT NOT NULL,"
            "access_token TEXT NOT NULL,"
            "bot_user_id TEXT DEFAULT '',"
            "created_at TEXT NOT NULL,"
            "updated_at TEXT NOT NULL"
            ")"
        ),
        (
            "CREATE TABLE IF NOT EXISTS user_workspaces ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "user_id INTEGER NOT NULL,"
            "workspace_id INTEGER NOT NULL,"
            "role TEXT DEFAULT 'owner',"
            "created_at TEXT NOT NULL,"
            "FOREIGN KEY (user_id) REFERENCES users(id),"
            "FOREIGN KEY (workspace_id) REFERENCES workspaces(id),"
            "UNIQUE(user_id, workspace_id)"
            ")"
        ),
        (
            "CREATE TABLE IF NOT EXISTS channels ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "workspace_id INTEGER NOT NULL,"
            "channel_id TEXT NOT NULL,"
            "channel_name TEXT NOT NULL,"
            "member_count INTEGER DEFAULT 0,"
            "topic TEXT DEFAULT '',"
            "purpose TEXT DEFAULT '',"
            "is_private INTEGER DEFAULT 0,"
            "created_at TEXT NOT NULL,"
            "updated_at TEXT NOT NULL,"
            "FOREIGN KEY (workspace_id) REFERENCES workspaces(id),"
            "UNIQUE(workspace_id, channel_id)"
            ")"
        ),
        (
            "CREATE TABLE IF NOT EXISTS repositories ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "workspace_id INTEGER NOT NULL,"
            "repo_url TEXT NOT NULL,"
            "repo_name TEXT DEFAULT '',"
            "description TEXT DEFAULT '',"
            "language TEXT DEFAULT '',"
            "stars INTEGER DEFAULT 0,"
            "created_at TEXT NOT NULL,"
            "FOREIGN KEY (workspace_id) REFERENCES workspaces(id),"
            "UNIQUE(workspace_id, repo_url)"
            ")"
        ),
        (
            "CREATE TABLE IF NOT EXISTS events ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "workspace_id INTEGER,"
            "event_type TEXT NOT NULL,"
            "user_slack_id TEXT DEFAULT '',"
            "status TEXT DEFAULT 'success',"
            "created_at TEXT NOT NULL"
            ")"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_events_workspace_created "
            "ON events(workspace_id, created_at DESC)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_channels_workspace "
            "ON channels(workspace_id, member_count DESC)"
        ),
        "CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)",
        (
            "CREATE INDEX IF NOT EXISTS idx_user_workspaces_user "
            "ON user_workspaces(user_id)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_user_workspaces_workspace "
            "ON user_workspaces(workspace_id)"
        ),
    ]

    try:
        for sql in statements:
            await env.DB.prepare(sql).run()
        _schema_initialized = True
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Welcome message template
# ---------------------------------------------------------------------------
WELCOME_MESSAGE = (
    ":tada: *Welcome to the OWASP Slack Community, <@{user_id}>!* :tada:\n\n"
    "We're thrilled to have you here! Whether you're new to OWASP or a "
    "long-time contributor, this Slack workspace is the perfect place to "
    "connect, collaborate, and stay informed about all things OWASP.\n\n"
    ":small_blue_diamond: *Get Involved:*\n"
    "• Check out the *#contribute* channel to find ways to get involved "
    "with OWASP projects and initiatives.\n"
    "• Explore individual project channels, which are named *#project-name*, "
    "to dive into specific projects that interest you.\n"
    "• Join our chapter channels, named *#chapter-name*, to connect with "
    "local OWASP members in your area.\n\n"
    ":small_blue_diamond: *Stay Updated:*\n"
    "• Visit *#newsroom* for the latest updates and announcements.\n"
    "• Follow *#external-activities* for news about OWASP's engagement "
    "with the wider security community.\n\n"
    ":small_blue_diamond: *Connect and Learn:*\n"
    "• *#jobs*: Looking for new opportunities? Check out the latest "
    "job postings here.\n"
    "• *#leaders*: Connect with OWASP leaders and stay informed about "
    "leadership activities.\n"
    "• *#project-committee*: Engage with the committee overseeing "
    "OWASP projects.\n"
    "• *#gsoc*: Stay updated on Google Summer of Code initiatives.\n"
    "• *#github-admins*: Get support and discuss issues related to "
    "OWASP's GitHub repositories.\n"
    "• *#learning*: Share and find resources to expand your knowledge "
    "in the field of application security.\n\n"
    "We're excited to see the amazing contributions you'll make. If you "
    "have any questions or need assistance, don't hesitate to ask. Let's "
    "work together to make software security visible and improve the "
    "security of the software we all rely on.\n\n"
    "Welcome aboard! :rocket:"
)


# ===========================================================================
# D1 — Workspace helpers
# ===========================================================================


async def db_get_workspace_by_team(env, team_id):
    try:
        return _row(
            await env.DB.prepare("SELECT * FROM workspaces WHERE team_id = ?")
            .bind(team_id)
            .first()
        )
    except Exception:
        return None


async def db_upsert_workspace(env, team_id, team_name, access_token, bot_user_id=""):
    now = get_utc_now()
    try:
        await ensure_d1_schema(env)
        existing = await db_get_workspace_by_team(env, team_id)
        if existing:
            result = await (
                env.DB.prepare(
                    "UPDATE workspaces SET team_name=?, access_token=?, bot_user_id=?, "
                    "updated_at=? WHERE team_id=?"
                )
                .bind(team_name, access_token, bot_user_id, now, team_id)
                .run()
            )
            print(f"[db_upsert_workspace] Updated workspace {team_id}, result: {result}")
        else:
            result = await (
                env.DB.prepare(
                    "INSERT INTO workspaces "
                    "(team_id, team_name, access_token, bot_user_id, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)"
                )
                .bind(team_id, team_name, access_token, bot_user_id, now, now)
                .run()
            )
            print(f"[db_upsert_workspace] Inserted workspace {team_id}, result: {result}")
        ws = await db_get_workspace_by_team(env, team_id)
        print(f"[db_upsert_workspace] Retrieved workspace: {ws}")
        return ws
    except Exception as e:
        print(f"[db_upsert_workspace] ERROR: {e}")
        capture_exception_to_sentry(env, e, {"team_id": team_id, "team_name": team_name})
        return None


async def db_get_workspace_by_id(env, workspace_id):
    try:
        return _row(
            await env.DB.prepare("SELECT * FROM workspaces WHERE id = ?")
            .bind(workspace_id)
            .first()
        )
    except Exception:
        return None


# ===========================================================================
# D1 — user_workspaces junction (many-to-many)
# ===========================================================================


async def db_link_user_workspace(env, user_id, workspace_id, role="owner"):
    """Associate a user with a workspace (idempotent)."""
    now = get_utc_now()
    print(f"[db_link_user_workspace] Linking user {user_id} to workspace {workspace_id}")
    try:
        await ensure_d1_schema(env)
        result = await (
            env.DB.prepare(
                "INSERT INTO user_workspaces (user_id, workspace_id, role, created_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(user_id, workspace_id) DO NOTHING"
            )
            .bind(user_id, workspace_id, role, now)
            .run()
        )
        print(f"[db_link_user_workspace] Link created successfully, result: {result}")
        return True
    except Exception as e:
        print(f"[db_link_user_workspace] ERROR linking user {user_id} to workspace {workspace_id}: {e}")
        capture_exception_to_sentry(env, e, {"user_id": user_id, "workspace_id": workspace_id})
async def db_get_user_workspaces(env, user_id):
    """Return all workspaces accessible by this user."""
    try:
        result = (
            await env.DB.prepare(
                "SELECT w.* FROM workspaces w "
                "JOIN user_workspaces uw ON w.id = uw.workspace_id "
                "WHERE uw.user_id = ? "
                "ORDER BY w.team_name ASC"
            )
            .bind(user_id)
            .all()
        )
        return _rows(result)
    except Exception:
        return []


async def db_user_owns_workspace(env, user_id, workspace_id):
    """Return True if the user has access to the given workspace."""
    try:
        row = _row(
            await env.DB.prepare(
                "SELECT id FROM user_workspaces WHERE user_id = ? AND workspace_id = ?"
            )
            .bind(user_id, workspace_id)
            .first()
        )
        return row is not None
    except Exception:
        return False


# ===========================================================================
# D1 — Channel helpers
# ===========================================================================


async def db_upsert_channel(
    env,
    workspace_id,
    channel_id,
    channel_name,
    member_count,
    topic,
    purpose,
    is_private,
):
    now = get_utc_now()
    try:
        await ensure_d1_schema(env)
        result = await (
            env.DB.prepare(
                "INSERT INTO channels "
                "(workspace_id, channel_id, channel_name, member_count, topic, purpose, "
                "is_private, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(workspace_id, channel_id) DO UPDATE SET "
                "channel_name=excluded.channel_name, member_count=excluded.member_count, "
                "topic=excluded.topic, purpose=excluded.purpose, "
                "updated_at=excluded.updated_at"
            )
            .bind(
                workspace_id,
                channel_id,
                channel_name,
                member_count,
                topic,
                purpose,
                is_private,
                now,
                now,
            )
            .run()
        )
        print(f"[db_upsert_channel] Saved channel {channel_name} (ID: {channel_id}), result: {result}")
        return True
    except Exception as e:
        print(f"[db_upsert_channel] ERROR saving channel {channel_id}: {e}")
        capture_exception_to_sentry(env, e, {"workspace_id": workspace_id, "channel_id": channel_id})
        return False


async def db_get_channels(env, workspace_id):
    try:
        return _rows(
            await env.DB.prepare(
                "SELECT * FROM channels WHERE workspace_id = ? "
                "ORDER BY member_count DESC"
            )
            .bind(workspace_id)
            .all()
        )
    except Exception:
        return []


# ===========================================================================
# D1 — User & Session helpers
# ===========================================================================


async def db_get_or_create_user(env, slack_user_id, team_id, name, email, access_token):
    now = get_utc_now()
    print(f"[db_get_or_create_user] Called with slack_user_id={slack_user_id}, team_id={team_id}, name={name}")
    try:
        await ensure_d1_schema(env)

        # Ensure required columns are never NULL for inserts/updates.
        slack_user_id = slack_user_id or ""
        team_id = team_id or "unknown"
        name = name or ""
        email = email or ""
        access_token = access_token or ""

        if not slack_user_id:
            print(f"[db_get_or_create_user] ERROR: slack_user_id is empty, returning None")
            return None

        existing = _row(
            await env.DB.prepare("SELECT * FROM users WHERE slack_user_id = ?")
            .bind(slack_user_id)
            .first()
        )
        if existing:
            print(f"[db_get_or_create_user] User exists, updating...")
            result = await (
                env.DB.prepare(
                    "UPDATE users SET name=?, email=?, access_token=?, team_id=?, updated_at=? "
                    "WHERE slack_user_id=?"
                )
                .bind(name, email, access_token, team_id, now, slack_user_id)
                .run()
            )
            print(f"[db_get_or_create_user] Update result: {result}")
        else:
            print(f"[db_get_or_create_user] Creating new user...")
            result = await (
                env.DB.prepare(
                    "INSERT INTO users "
                    "(slack_user_id, team_id, name, email, access_token, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)"
                )
                .bind(slack_user_id, team_id, name, email, access_token, now, now)
                .run()
            )
            print(f"[db_get_or_create_user] Insert result: {result}")
        user = _row(
            await env.DB.prepare("SELECT * FROM users WHERE slack_user_id = ?")
            .bind(slack_user_id)
            .first()
        )
        print(f"[db_get_or_create_user] Retrieved user: {user}")
        return user
    except Exception as e:
        print(f"[db_get_or_create_user] ERROR: {e}")
        capture_exception_to_sentry(env, e, {"slack_user_id": slack_user_id})
        return None


async def db_create_session(env, user_id, token):
    now = get_utc_now()
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    print(f"[db_create_session] Creating session for user_id={user_id}")
    try:
        await ensure_d1_schema(env)
        result = await (
            env.DB.prepare(
                "INSERT INTO sessions (id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)"
            )
            .bind(token, user_id, now, expires)
            .run()
        )
        print(f"[db_create_session] Session created successfully, result: {result}")
        return True
    except Exception as e:
        print(f"[db_create_session] ERROR: {e}")
        capture_exception_to_sentry(env, e, {"user_id": user_id})
        return False


async def db_get_session(env, token):
    """Return session + user data if valid and not expired."""
    try:
        return _row(
            await env.DB.prepare(
                "SELECT s.id as session_id, s.user_id, s.expires_at, "
                "u.slack_user_id, u.team_id, u.name, u.email "
                "FROM sessions s JOIN users u ON s.user_id = u.id "
                "WHERE s.id = ? AND s.expires_at > ?"
            )
            .bind(token, get_utc_now())
            .first()
        )
    except Exception:
        return None


async def db_delete_session(env, token):
    try:
        await env.DB.prepare("DELETE FROM sessions WHERE id = ?").bind(token).run()
        return True
    except Exception:
        return False


# ===========================================================================
# D1 — Repository helpers
# ===========================================================================


async def db_add_repository(
    env, workspace_id, repo_url, repo_name="", description="", language="", stars=0
):
    now = get_utc_now()
    try:
        await (
            env.DB.prepare(
                "INSERT INTO repositories "
                "(workspace_id, repo_url, repo_name, description, language, stars, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(workspace_id, repo_url) DO UPDATE SET "
                "repo_name=excluded.repo_name, description=excluded.description, "
                "language=excluded.language, stars=excluded.stars"
            )
            .bind(workspace_id, repo_url, repo_name, description, language, stars, now)
            .run()
        )
        return True
    except Exception:
        return False


async def db_delete_repository(env, repo_id, workspace_id):
    """Delete a repository by id, scoped to the workspace for safety."""
    try:
        await (
            env.DB.prepare("DELETE FROM repositories WHERE id = ? AND workspace_id = ?")
            .bind(repo_id, workspace_id)
            .run()
        )
        return True
    except Exception:
        return False


async def db_get_repositories(env, workspace_id):
    try:
        return _rows(
            await env.DB.prepare(
                "SELECT * FROM repositories WHERE workspace_id = ? ORDER BY stars DESC"
            )
            .bind(workspace_id)
            .all()
        )
    except Exception:
        return []


# ===========================================================================
# D1 — Event helpers
# ===========================================================================


async def db_log_event(
    env, workspace_id, event_type, user_slack_id="", status="success"
):
    now = get_utc_now()
    try:
        await (
            env.DB.prepare(
                "INSERT INTO events (workspace_id, event_type, user_slack_id, status, created_at) "
                "VALUES (?, ?, ?, ?, ?)"
            )
            .bind(workspace_id, event_type, user_slack_id, status, now)
            .run()
        )
        return True
    except Exception:
        return False


async def db_get_events(env, workspace_id, limit=20):
    try:
        return _rows(
            await env.DB.prepare(
                "SELECT * FROM events WHERE workspace_id = ? "
                "ORDER BY created_at DESC LIMIT ?"
            )
            .bind(workspace_id, limit)
            .all()
        )
    except Exception:
        return []


async def db_get_daily_stats(env, workspace_id, days=30):
    """Return [{date, event_type, count}] for the last N days."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        return _rows(
            await env.DB.prepare(
                "SELECT substr(created_at, 1, 10) as date, event_type, COUNT(*) as count "
                "FROM events WHERE workspace_id = ? AND created_at >= ? "
                "GROUP BY date, event_type ORDER BY date ASC"
            )
            .bind(workspace_id, since)
            .all()
        )
    except Exception:
        return []


async def db_get_workspace_stats(env, workspace_id):
    """Return aggregate stats for a workspace."""
    zero = {
        "total_activities": 0,
        "last_24h_activities": 0,
        "success_rate": 100.0,
        "last_event_time": None,
        "joins": 0,
        "commands": 0,
    }
    try:
        since_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        total_row = _row(
            await env.DB.prepare(
                "SELECT COUNT(*) as n FROM events WHERE workspace_id = ?"
            )
            .bind(workspace_id)
            .first()
        )
        last24_row = _row(
            await env.DB.prepare(
                "SELECT COUNT(*) as n FROM events WHERE workspace_id = ? AND created_at >= ?"
            )
            .bind(workspace_id, since_24h)
            .first()
        )
        success_row = _row(
            await env.DB.prepare(
                "SELECT COUNT(*) as n FROM events WHERE workspace_id = ? AND status='success'"
            )
            .bind(workspace_id)
            .first()
        )
        last_event_row = _row(
            await env.DB.prepare(
                "SELECT created_at FROM events WHERE workspace_id = ? "
                "ORDER BY created_at DESC LIMIT 1"
            )
            .bind(workspace_id)
            .first()
        )
        joins_row = _row(
            await env.DB.prepare(
                "SELECT COUNT(*) as n FROM events WHERE workspace_id = ? "
                "AND event_type='Team_Join'"
            )
            .bind(workspace_id)
            .first()
        )
        cmd_row = _row(
            await env.DB.prepare(
                "SELECT COUNT(*) as n FROM events WHERE workspace_id = ? "
                "AND event_type='Command'"
            )
            .bind(workspace_id)
            .first()
        )
        total = (total_row or {}).get("n", 0) or 0
        last24 = (last24_row or {}).get("n", 0) or 0
        success = (success_row or {}).get("n", 0) or 0
        last_time = (last_event_row or {}).get("created_at")
        joins = (joins_row or {}).get("n", 0) or 0
        commands = (cmd_row or {}).get("n", 0) or 0
        rate = round(success / total * 100, 1) if total > 0 else 100.0
        return {
            "total_activities": total,
            "last_24h_activities": last24,
            "success_rate": rate,
            "last_event_time": last_time,
            "joins": joins,
            "commands": commands,
        }
    except Exception:
        return zero


# ===========================================================================
# OAuth / session helpers
# ===========================================================================


def parse_cookies(request):
    cookies = {}
    header = request.headers.get("Cookie") or ""
    for part in header.split(";"):
        kv = part.strip().split("=", 1)
        if len(kv) == 2:
            cookies[kv[0].strip()] = kv[1].strip()
    return cookies


async def get_current_user(env, request):
    """Return session dict (with user info) or None if not authenticated."""
    try:
        token = parse_cookies(request).get("session_id")
        if not token:
            return None
        return await db_get_session(env, token)
    except Exception:
        return None


def generate_session_token():
    return secrets.token_hex(32)


def get_base_url(env, request):
    """Derive the worker base URL for redirect URIs."""
    configured = getattr(env, "BASE_URL", None)
    if configured:
        return configured.rstrip("/")
    # Fall back to origin from the incoming request
    try:
        parts = request.url.split("/")
        return f"{parts[0]}//{parts[2]}"
    except Exception:
        return "https://blt-lettuce.workers.dev"


def get_slack_sign_in_url(client_id, redirect_uri, state="signin"):
    """OAuth URL for 'Sign in with Slack' (identity only)."""
    return (
        "https://slack.com/oauth/v2/authorize"
        f"?client_id={client_id}"
        "&scope="  # no bot scopes for pure sign-in
        "&user_scope=identity.basic,identity.email,identity.team"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
    )


def get_slack_add_workspace_url(client_id, redirect_uri, state="add_workspace"):
    """OAuth URL for installing the bot into a workspace."""
    bot_scopes = (
        "channels:read,chat:write,users:read,team:read,im:write,im:read,im:history"
    )
    return (
        "https://slack.com/oauth/v2/authorize"
        f"?client_id={client_id}"
        f"&scope={bot_scopes}"
        "&user_scope=identity.basic,identity.email,identity.team"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
    )


async def exchange_code_for_token(client_id, client_secret, code, redirect_uri):
    try:
        body = urlencode(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            }
        )
        headers = Headers.new()
        headers.set("Content-Type", "application/x-www-form-urlencoded")
        resp = await js_fetch(
            "https://slack.com/api/oauth.v2.access",
            {
                "method": "POST",
                "headers": headers,
                "body": body,
            },
        )
        
        # Check HTTP status
        status = getattr(resp, "status", 0)
        if status >= 400:
            return {"ok": False, "error": f"http_error_{status}"}
        
        result = _js_to_python(await resp.json())
        if not isinstance(result, dict):
            return {"ok": False, "error": "invalid_response_format"}
        
        # If Slack returns an error, include details
        ok_status = result.get("ok", False)
        if not ok_status:
            error_detail = result.get("error", "unknown_error")
            return {"ok": False, "error": error_detail}
        
        return result
    except Exception as e:
        # Try to get meaningful error info
        error_msg = str(e) if str(e) else type(e).__name__
        return {"ok": False, "error": f"exception: {error_msg}"}


async def fetch_user_identity(user_token):
    """Call identity.basic to get user profile from a user token."""
    try:
        headers = Headers.new()
        headers.set("Authorization", f"Bearer {user_token}")
        resp = await js_fetch(
            "https://slack.com/api/users.identity",
            {
                "method": "GET",
                "headers": headers,
            },
        )
        result = _js_to_python(await resp.json())
        return result if isinstance(result, dict) else {"ok": False}
    except Exception:
        return {"ok": False}


async def get_db_table_counts(env):
    """Return counts for key D1 tables used by dashboard and bot commands."""
    await ensure_d1_schema(env)

    tables = [
        "users",
        "sessions",
        "workspaces",
        "user_workspaces",
        "channels",
        "repositories",
        "events",
    ]
    counts = {}
    for table in tables:
        try:
            row = await env.DB.prepare(f"SELECT COUNT(*) as count FROM {table}").first()
            counts[table] = (row or {}).get("count", 0)
        except Exception:
            counts[table] = 0
    return counts


def _format_db_stats_for_slack(counts):
    """Format table counts as a readable Slack markdown message."""
    lines = ["*BLT Lettuce DB Stats* :bar_chart:"]
    ordered = [
        ("users", "Users"),
        ("sessions", "Sessions"),
        ("workspaces", "Workspaces"),
        ("user_workspaces", "User Workspaces"),
        ("channels", "Channels"),
        ("repositories", "Repositories"),
        ("events", "Events"),
    ]
    for key, label in ordered:
        lines.append(f"- *{label}:* {counts.get(key, 0)}")
    return "\n".join(lines)


# ===========================================================================
# Channel scanning
# ===========================================================================


async def scan_workspace_channels(env, workspace_id, access_token):
    """Scan all public channels in the workspace and persist them in D1."""
    print(f"[scan_workspace_channels] Starting scan for workspace {workspace_id}")
    print(f"[scan_workspace_channels] Access token present: {bool(access_token)}")
    scanned = 0
    cursor = None
    while True:
        url = "https://slack.com/api/conversations.list?limit=200&types=public_channel"
        if cursor:
            url += f"&cursor={cursor}"
        try:
            headers = Headers.new()
            headers.set("Authorization", f"Bearer {access_token}")
            resp = await js_fetch(
                url,
                {
                    "method": "GET",
                    "headers": headers,
                },
            )
            data = _js_to_python(await resp.json())
            print(f"[scan_workspace_channels] Slack API response ok: {data.get('ok')}, error: {data.get('error')}")
            if not data.get("ok"):
                print(f"[scan_workspace_channels] Slack API error: {data.get('error')}")
                break
            channels = data.get("channels", [])
            print(f"[scan_workspace_channels] Found {len(channels)} channels in this batch")
            for ch in channels:
                cid = ch.get("id", "")
                cname = ch.get("name", "")
                if cid and cname:
                    success = await db_upsert_channel(
                        env,
                        workspace_id,
                        cid,
                        cname,
                        ch.get("num_members", 0),
                        (ch.get("topic") or {}).get("value", ""),
                        (ch.get("purpose") or {}).get("value", ""),
                        1 if ch.get("is_private") else 0,
                    )
                    if success:
                        scanned += 1
            cursor = (data.get("response_metadata") or {}).get("next_cursor", "")
            if not cursor:
                break
        except Exception as e:
            print(f"[scan_workspace_channels] ERROR during scan: {e}")
            capture_exception_to_sentry(env, e, {"workspace_id": workspace_id})
            break
    print(f"[scan_workspace_channels] Scan complete: {scanned} channels saved")
    return scanned


# ===========================================================================
# Slack API helpers
# ===========================================================================


async def get_bot_user_id(env):
    slack_token = getattr(env, "SLACK_TOKEN", None)
    if not slack_token:
        return None
    try:
        headers = Headers.new()
        headers.set("Authorization", f"Bearer {slack_token}")
        resp = await js_fetch(
            "https://slack.com/api/auth.test",
            {"method": "POST", "headers": headers},
        )
        result = _js_to_python(await resp.json())
        if not isinstance(result, dict):
            return None
        if result.get("ok"):
            return result.get("user_id")
    except Exception:
        pass
    return None


async def send_slack_message(env, channel, text, blocks=None, token=None):
    slack_token = token or getattr(env, "SLACK_TOKEN", None)
    if not slack_token:
        return {"ok": False, "error": "SLACK_TOKEN not configured"}
    payload = {"channel": channel, "text": text}
    if blocks:
        payload["blocks"] = blocks
    headers = Headers.new()
    headers.set("Content-Type", "application/json")
    headers.set("Authorization", f"Bearer {slack_token}")
    resp = await js_fetch(
        "https://slack.com/api/chat.postMessage",
        {
            "method": "POST",
            "headers": headers,
            "body": json.dumps(payload),
        },
    )
    result = _js_to_python(await resp.json())
    return result if isinstance(result, dict) else {"ok": False, "error": "invalid_response"}


async def open_conversation(env, user_id, token=None):
    slack_token = token or getattr(env, "SLACK_TOKEN", None)
    if not slack_token:
        return {"ok": False, "error": "SLACK_TOKEN not configured"}
    headers = Headers.new()
    headers.set("Content-Type", "application/json")
    headers.set("Authorization", f"Bearer {slack_token}")
    resp = await js_fetch(
        "https://slack.com/api/conversations.open",
        {
            "method": "POST",
            "headers": headers,
            "body": json.dumps({"users": user_id}),
        },
    )
    result = _js_to_python(await resp.json())
    return result if isinstance(result, dict) else {"ok": False, "error": "invalid_response"}


# ===========================================================================
# Webhook event handlers
# ===========================================================================


async def handle_team_join(env, event, team_id=None):
    user_data = event.get("user") or {}
    if isinstance(user_data, dict):
        user_id = user_data.get("id")
    else:
        user_id = user_data
    if not user_id:
        return {"error": "No user ID in event"}

    # Ignore if the bot is welcoming itself
    bot_user_id = await get_bot_user_id(env)
    if user_id == bot_user_id:
        return {"ok": True, "message": "Ignoring bot's own team_join event"}

    # Look up the workspace
    ws = None
    ws_token = getattr(env, "SLACK_TOKEN", None)
    if team_id:
        ws = await db_get_workspace_by_team(env, team_id)
        if ws:
            await db_log_event(env, ws["id"], "Team_Join", user_id, "success")
            if ws.get("access_token"):
                ws_token = ws["access_token"]

    joins_channel = getattr(env, "JOINS_CHANNEL_ID", DEFAULT_JOINS_CHANNEL_ID)
    if joins_channel:
        try:
            await send_slack_message(
                env, joins_channel, f"<@{user_id}> joined the team.", token=ws_token
            )
        except Exception:
            pass

    dm_response = await open_conversation(env, user_id, token=ws_token)
    if not dm_response.get("ok"):
        return {"error": f"Failed to open DM: {dm_response.get('error')}"}

    dm_channel = (dm_response.get("channel") or {}).get("id")
    if not dm_channel:
        return {"error": "Failed to get DM channel ID"}

    # Build suggested channels from D1 if available
    channel_suggestions = ""
    if ws:
        top_channels = await db_get_channels(env, ws["id"])
        top5 = [c for c in top_channels[:5] if c.get("channel_name")]
        if top5:
            names = ", ".join(f"*#{c['channel_name']}*" for c in top5)
            channel_suggestions = f"\n\n:bar_chart: *Most Active Channels:* {names}"

    welcome_text = WELCOME_MESSAGE.format(user_id=user_id) + channel_suggestions
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": welcome_text.strip()}}
    ]

    result = await send_slack_message(
        env, dm_channel, "Welcome to the OWASP Slack Community!", blocks, token=ws_token
    )
    return {"ok": result.get("ok"), "user_id": user_id}


async def handle_message_event(env, event, team_id=None):
    original_text = (event.get("text") or "").strip()
    message_text = original_text.lower()
    user = event.get("user")
    channel = event.get("channel")
    channel_type = event.get("channel_type")
    subtype = event.get("subtype")
    
    # Ignore bot messages (check both bot_id field and user field)
    if event.get("bot_id") or event.get("bot_profile"):
        return {"ok": True, "message": "Ignoring bot message (bot_id present)"}
    
    # Ignore message subtypes that shouldn't trigger responses
    if subtype in ("message_changed", "message_deleted", "bot_message", "channel_join", "channel_leave"):
        return {"ok": True, "message": f"Ignoring message subtype: {subtype}"}

    # Look up workspace-specific bot token
    ws_token = getattr(env, "SLACK_TOKEN", None)
    if team_id:
        ws = await db_get_workspace_by_team(env, team_id)
        if ws and ws.get("access_token"):
            ws_token = ws["access_token"]

    bot_user_id = await get_bot_user_id(env)
    if user == bot_user_id:
        return {"ok": True, "message": "Ignoring bot message"}

    contribute_id = getattr(env, "CONTRIBUTE_ID", DEFAULT_CONTRIBUTE_ID)
    joins_channel = getattr(env, "JOINS_CHANNEL_ID", DEFAULT_JOINS_CHANNEL_ID)

    if (
        subtype is None
        and "#contribute" not in message_text
        and any(
            kw in message_text for kw in ("contribute", "contributing", "contributes")
        )
    ):
        text = (
            f"Hello <@{user}>! Please check this channel "
            f"<#{contribute_id}> for contributing guidelines today!"
        )
        result = await send_slack_message(env, channel, text, token=ws_token)
        return {"ok": result.get("ok"), "action": "contribute_response"}

    if channel_type == "im":
        if joins_channel:
            try:
                await send_slack_message(
                    env,
                    joins_channel,
                    f"<@{user}> said {message_text}",
                    token=ws_token,
                )
            except Exception:
                pass

        if any(word in message_text for word in ("stats", "health", "tables", "db")):
            counts = await get_db_table_counts(env)
            stats_text = _format_db_stats_for_slack(counts)
            result = await send_slack_message(env, channel, stats_text, token=ws_token)
            return {"ok": result.get("ok"), "action": "dm_stats"}

        if any(greet in message_text for greet in ("hello", "hi", "hey")):
            counts = await get_db_table_counts(env)
            stats_text = _format_db_stats_for_slack(counts)
            greet_text = (
                f"Hello <@{user}>! Here are the latest stats.\n\n{stats_text}\n\n"
                "Try commands: `stats`, `help`, `health`"
            )
            result = await send_slack_message(env, channel, greet_text, token=ws_token)
            return {"ok": result.get("ok"), "action": "dm_greeting_stats"}

        if any(word in message_text for word in ("help", "commands", "cmd")):
            help_text = (
                "*Lettuce Bot Commands*\n"
                "- `stats` or `health`: Show DB table counts\n"
                "- `hello` / `hi` / `hey`: Greeting + DB stats\n"
                "- `help`: Show this command list"
            )
            result = await send_slack_message(env, channel, help_text, token=ws_token)
            return {"ok": result.get("ok"), "action": "dm_help"}

        # Default DM response with quick guidance + current stats.
        counts = await get_db_table_counts(env)
        stats_text = _format_db_stats_for_slack(counts)
        default_text = (
            f"Hi <@{user}>! I can help with stats.\n\n{stats_text}\n\n"
            "Try: `stats`, `hello`, or `help`."
        )
        result = await send_slack_message(env, channel, default_text, token=ws_token)
        return {"ok": result.get("ok"), "action": "dm_default"}

    return {"ok": True, "message": "No action taken"}


async def handle_command(env, event, team_id=None):
    user_id = event.get("user") or event.get("user_id") or ""
    if team_id:
        ws = await db_get_workspace_by_team(env, team_id)
        if ws:
            await db_log_event(env, ws["id"], "Command", user_id, "success")
    return {"ok": True, "message": "Command tracked"}


# ===========================================================================
# Signature verification
# ===========================================================================


def verify_slack_signature(signing_secret, timestamp, body, signature):
    if not signing_secret or not timestamp or not signature:
        return False
    try:
        request_time = int(timestamp)
        current_time = int(datetime.now(timezone.utc).timestamp())
        if abs(current_time - request_time) > 300:
            return False
    except (ValueError, TypeError):
        return False

    sig_basestring = f"v0:{timestamp}:{body}"
    expected = (
        "v0="
        + hmac.new(
            signing_secret.encode("utf-8"),
            sig_basestring.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )
    return hmac.compare_digest(expected, signature)


# ===========================================================================
# HTML helpers
# ===========================================================================


def is_homepage_request(url, method):
    if method != "GET":
        return False
    pathname = urlparse(url).path.rstrip("/") or "/"
    return pathname in ("/", "/index")


def _html_response(html, status=200, extra_headers=None):
    # Use Headers object for compatibility with Cloudflare Workers
    h = Headers.new()
    h.set("Content-Type", "text/html; charset=utf-8")
    h.set("Cache-Control", "no-store")
    h.set("X-Content-Type-Options", "nosniff")
    if extra_headers:
        for k, v in extra_headers.items():
            h.set(k, v)
    return Response.new(html, {"status": status, "headers": h})


def _redirect(location, extra_headers=None):
    h = Headers.new()
    h.set("Location", location)
    if extra_headers:
        for k, v in extra_headers.items():
            h.set(k, v)
    return Response.new("", {"status": 302, "headers": h})


def _json_response(data, status=200):
    """Return a JSON response with the given status code."""
    h = Headers.new()
    h.set("Content-Type", "application/json")
    return Response.new(
        json.dumps(data),
        {"status": status, "headers": h},
    )


# ===========================================================================
# Main route handler
# ===========================================================================


async def handle_request(request, env):
    """Main entry point for the Cloudflare Worker."""
    url = request.url
    method = request.method

    # Parse the URL into its components for exact, safe routing
    _parsed = urlparse(url)
    pathname = _parsed.path.rstrip("/") or "/"  # e.g., "/login", "/api/ws/3/scan"

    # ---- CORS preflight ----
    if method == "OPTIONS":
        h = Headers.new()
        h.set("Access-Control-Allow-Origin", "*")
        h.set("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        h.set("Access-Control-Allow-Headers", "Content-Type")
        return Response.new("", {"headers": h})

    # ------------------------------------------------------------------ #
    #  GET /login  →  redirect to Slack OAuth (sign-in, identity only)   #
    # ------------------------------------------------------------------ #
    if pathname == "/login" and method == "GET":
        client_id = getattr(env, "SLACK_CLIENT_ID", None)
        if not client_id:
            return _html_response(
                get_login_page_html("#", error="SLACK_CLIENT_ID is not configured."),
                status=500,
            )
        base = get_base_url(env, request)
        redirect_uri = f"{base}/callback"
        state_token = _make_oauth_state("signin")
        sign_in_url = get_slack_sign_in_url(client_id, redirect_uri, state=state_token)
        oauth_cookie = (
            f"oauth_state={state_token}; HttpOnly; Secure; SameSite=Lax; "
            "Max-Age=600; Path=/"
        )
        return _html_response(
            get_login_page_html(sign_in_url),
            extra_headers={"Set-Cookie": oauth_cookie},
        )

    # ------------------------------------------------------------------ #
    #  GET /callback  →  OAuth callback (handles both sign-in & add-ws)  #
    # ------------------------------------------------------------------ #
    if pathname == "/callback" and method == "GET":
        try:
            qs = url.split("?", 1)[1] if "?" in url else ""
            params = {}
            for part in qs.split("&"):
                kv = part.split("=", 1)
                if len(kv) == 2:
                    try:
                        params[kv[0]] = unquote_plus(kv[1])
                    except Exception:
                        params[kv[0]] = kv[1]

            code = params.get("code")
            received_state = params.get("state", "")
            error = params.get("error")

            # Validate CSRF state before processing
            stored_state = parse_cookies(request).get("oauth_state", "")
            intent = _verify_oauth_state(stored_state, received_state)

            if error or not code:
                base = get_base_url(env, request)
                client_id = getattr(env, "SLACK_CLIENT_ID", None)
                sign_in_url = get_slack_sign_in_url(client_id or "", f"{base}/callback")
                return _html_response(
                    get_login_page_html(
                        sign_in_url, error=f"OAuth error: {error or 'missing code'}"
                    ),
                )

            # Reject if CSRF state is invalid (missing or tampered)
            if intent is None:
                base = get_base_url(env, request)
                client_id_csrf = getattr(env, "SLACK_CLIENT_ID", None)
                sign_in_url = get_slack_sign_in_url(
                    client_id_csrf or "", f"{base}/callback"
                )
                return _html_response(
                    get_login_page_html(
                        sign_in_url,
                        error="Invalid OAuth state. Please try signing in again.",
                    ),
                )

            client_id = getattr(env, "SLACK_CLIENT_ID", None)
            client_secret = getattr(env, "SLACK_CLIENT_SECRET", None)
            base = get_base_url(env, request)
            redirect_uri = f"{base}/callback"

            token_data = await exchange_code_for_token(
                client_id, client_secret, code, redirect_uri
            )

            if not token_data.get("ok"):
                sign_in_url = get_slack_sign_in_url(client_id or "", redirect_uri)
                return _html_response(
                    get_login_page_html(
                        sign_in_url,
                        error=f"Token exchange failed: {token_data.get('error')}",
                    ),
                )

            # ---- Identify the authorizing user ----
            authed_user = _js_to_python(token_data.get("authed_user") or {})
            user_token = _obj_get(authed_user, "access_token", "")
            user_slack_id = _obj_get(authed_user, "id", "")

            user_name = ""
            user_email = ""
            team_obj = _js_to_python(token_data.get("team") or {})
            user_team_id = _obj_get(team_obj, "id", "")

            if user_token:
                identity = await fetch_user_identity(user_token)
                if identity.get("ok"):
                    profile = _js_to_python(identity.get("user") or {})
                    team_info = _js_to_python(identity.get("team") or {})
                    user_name = _obj_get(profile, "name", "")
                    user_email = _obj_get(profile, "email", "")
                    if not user_team_id:
                        user_team_id = _obj_get(team_info, "id", "")
                    if not user_slack_id:
                        user_slack_id = _obj_get(profile, "id", "")

            if not user_slack_id:
                sign_in_url = get_slack_sign_in_url(client_id or "", redirect_uri)
                return _html_response(
                    get_login_page_html(
                        sign_in_url, error="Could not retrieve your Slack identity."
                    ),
                )

            user = await db_get_or_create_user(
                env,
                user_slack_id,
                user_team_id,
                user_name,
                user_email,
                user_token or "",
            )
            if not user:
                sign_in_url = get_slack_sign_in_url(client_id or "", redirect_uri)
                return _html_response(
                    get_login_page_html(
                        sign_in_url, error="Database error. Please try again."
                    ),
                )

            # ---- If this was an "add workspace" flow, install the bot ----
            if intent == "add_workspace":
                print(f"[OAuth callback] Processing add_workspace flow")
                bot_token = token_data.get("access_token")
                team_info = _js_to_python(token_data.get("team") or {})
                team_id = _obj_get(team_info, "id", "")
                team_name = _obj_get(team_info, "name", "Unknown Workspace")
                bot_user_id = token_data.get("bot_user_id") or ""
                print(f"[OAuth callback] team_id={team_id}, team_name={team_name}, bot_user_id={bot_user_id}, bot_token present={bool(bot_token)}")

                if team_id and bot_token:
                    ws = await db_upsert_workspace(
                        env, team_id, team_name, bot_token, bot_user_id
                    )
                    print(f"[OAuth callback] Workspace upserted: {ws}")
                    if ws:
                        user_id_val = _obj_get(user, "id")
                        ws_id_val = _obj_get(ws, "id")
                        print(f"[OAuth callback] user_id_val={user_id_val}, ws_id_val={ws_id_val}")
                        if user_id_val and ws_id_val:
                            link_result = await db_link_user_workspace(
                                env, user_id_val, ws_id_val, role="owner"
                            )
                            print(f"[OAuth callback] Link result: {link_result}")
                        else:
                            print(f"[OAuth callback] WARNING: Could not link workspace - missing user_id or ws_id")
                        # Background channel scan (best-effort)
                        try:
                            if ws_id_val and bot_token:
                                print(f"[OAuth callback] Starting channel scan...")
                                scan_result = await scan_workspace_channels(env, ws_id_val, bot_token)
                                print(f"[OAuth callback] Channel scan result: {scan_result}")
                        except Exception as e:
                            print(f"[OAuth callback] Channel scan failed: {e}")
                            pass
                else:
                    print(f"[OAuth callback] WARNING: Could not create workspace - missing team_id or bot_token")

            # ---- Create session ----
            token = generate_session_token()
            user_id_val = _obj_get(user, "id")
            session_ok = await db_create_session(env, user_id_val, token) if user_id_val else False
            if not session_ok:
                sign_in_url = get_slack_sign_in_url(client_id or "", redirect_uri)
                return _html_response(
                    get_login_page_html(
                        sign_in_url,
                        error="Could not create a session. Please try again.",
                    ),
                )

            # Clear the oauth_state cookie and set the session cookie
            session_cookie = (
                f"session_id={token}; HttpOnly; Secure; SameSite=Lax; "
                "Max-Age=2592000; Path=/"
            )
            clear_oauth_cookie = (
                "oauth_state=; HttpOnly; Secure; SameSite=Lax; Max-Age=0; Path=/"
            )
            # Set both cookies in the redirect using append (Workers support multiple Set-Cookie)
            resp_h = Headers.new()
            resp_h.set("Location", "/dashboard")
            resp_h.append("Set-Cookie", session_cookie)
            resp_h.append("Set-Cookie", clear_oauth_cookie)
            return Response.new("", {"status": 302, "headers": resp_h})
        except Exception as e:
            try:
                sentry = get_sentry()
                await sentry.capture_exception(
                    e,
                    level="error",
                    extra={
                        "path": "/callback",
                        "method": "GET",
                    },
                )
            except Exception:
                pass

            base = get_base_url(env, request)
            client_id = getattr(env, "SLACK_CLIENT_ID", None)
            sign_in_url = get_slack_sign_in_url(client_id or "", f"{base}/callback")
            return _html_response(
                get_login_page_html(
                    sign_in_url,
                    error="Internal server error during Slack sign-in. Please retry.",
                ),
                status=500,
            )

    # ------------------------------------------------------------------ #
    #  GET /logout                                                        #
    # ------------------------------------------------------------------ #
    if pathname == "/logout" and method == "GET":
        cookies = parse_cookies(request)
        session_id = cookies.get("session_id")
        if session_id:
            await db_delete_session(env, session_id)
        clear_cookie = "session_id=; HttpOnly; Secure; SameSite=Lax; Max-Age=0; Path=/"
        return _redirect("/", extra_headers={"Set-Cookie": clear_cookie})

    # ------------------------------------------------------------------ #
    #  GET /workspace/add  →  redirect to Slack OAuth (bot installation) #
    # ------------------------------------------------------------------ #
    if pathname == "/workspace/add" and method == "GET":
        user = await get_current_user(env, request)
        if not user:
            return _redirect("/login")
        client_id = getattr(env, "SLACK_CLIENT_ID", None)
        if not client_id:
            return _redirect("/dashboard")
        base = get_base_url(env, request)
        redirect_uri = f"{base}/callback"
        state_token = _make_oauth_state("add_workspace")
        add_ws_url = get_slack_add_workspace_url(
            client_id, redirect_uri, state=state_token
        )
        oauth_cookie = (
            f"oauth_state={state_token}; HttpOnly; Secure; SameSite=Lax; "
            "Max-Age=600; Path=/"
        )
        resp_h = Headers.new()
        resp_h.set("Location", add_ws_url)
        resp_h.append("Set-Cookie", oauth_cookie)
        return Response.new("", {"status": 302, "headers": resp_h})

    # ------------------------------------------------------------------ #
    #  GET /dashboard  →  live stats dashboard (requires auth)           #
    # ------------------------------------------------------------------ #
    if pathname == "/dashboard" and method == "GET":
        user = await get_current_user(env, request)
        if not user:
            return _redirect("/login")

        workspaces = await db_get_user_workspaces(env, user["user_id"])

        # Determine which workspace to show (ws= query param or first)
        qs = url.split("?", 1)[1] if "?" in url else ""
        qs_params = {}
        for part in qs.split("&"):
            kv = part.split("=", 1)
            if len(kv) == 2:
                qs_params[kv[0]] = kv[1]

        current_ws = None
        selected_ws_id = qs_params.get("ws")
        selected_tab = (qs_params.get("tab") or "overview").lower()
        if selected_tab not in ("overview", "channels"):
            selected_tab = "overview"
        if selected_ws_id:
            try:
                sid = int(selected_ws_id)
                # Ensure the user actually owns this workspace
                for ws in workspaces:
                    if ws.get("id") == sid:
                        current_ws = ws
                        break
            except (ValueError, TypeError):
                pass
        if not current_ws and workspaces:
            current_ws = workspaces[0]

        ws_stats = {}
        channels = []
        events = []
        daily_stats = []
        repos = []

        if current_ws:
            ws_id_val = current_ws["id"]
            ws_stats = await db_get_workspace_stats(env, ws_id_val)
            channels = await db_get_channels(env, ws_id_val)
            events = await db_get_events(env, ws_id_val, limit=20)
            daily_stats = await db_get_daily_stats(env, ws_id_val, days=30)
            repos = await db_get_repositories(env, ws_id_val)

        html = get_dashboard_html(
            user,
            workspaces,
            current_ws,
            ws_stats,
            channels,
            events,
            daily_stats,
            repos,
            active_tab=selected_tab,
        )
        return _html_response(html)

    # ------------------------------------------------------------------ #
    #  POST /api/ws/<id>/scan  →  trigger channel scan for a workspace   #
    # ------------------------------------------------------------------ #
    if (
        pathname.startswith("/api/ws/")
        and pathname.endswith("/scan")
        and method == "POST"
    ):
        user = await get_current_user(env, request)
        if not user:
            return _json_response({"ok": False, "error": "Unauthorized"}, 401)
        try:
            ws_id_val = int(pathname.split("/api/ws/")[1].split("/")[0])
        except (ValueError, IndexError):
            return _json_response({"ok": False, "error": "Invalid workspace id"}, 400)

        if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
            return _json_response({"ok": False, "error": "Forbidden"}, 403)

        ws = await db_get_workspace_by_id(env, ws_id_val)
        if not ws:
            return _json_response({"ok": False, "error": "Workspace not found"}, 404)

        scanned = await scan_workspace_channels(env, ws_id_val, ws["access_token"])
        return Response.json({"ok": True, "channels_scanned": scanned})

    # ------------------------------------------------------------------ #
    #  POST /api/ws/<id>/test-message  →  send test DM to workspace owner#
    # ------------------------------------------------------------------ #
    if (
        pathname.startswith("/api/ws/")
        and pathname.endswith("/test-message")
        and method == "POST"
    ):
        user = await get_current_user(env, request)
        if not user:
            return _json_response({"ok": False, "error": "Unauthorized"}, 401)
        try:
            ws_id_val = int(pathname.split("/api/ws/")[1].split("/")[0])
        except (ValueError, IndexError):
            return _json_response({"ok": False, "error": "Invalid workspace id"}, 400)

        if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
            return _json_response({"ok": False, "error": "Forbidden"}, 403)

        ws = await db_get_workspace_by_id(env, ws_id_val)
        if not ws:
            return _json_response({"ok": False, "error": "Workspace not found"}, 404)

        # Send test DM to the user
        user_slack_id = user.get("slack_user_id")
        if not user_slack_id:
            return _json_response({"ok": False, "error": "User Slack ID not found"}, 400)

        # Open DM conversation
        conv_result = await open_conversation(env, user_slack_id, ws.get("access_token"))
        if not conv_result.get("ok"):
            return _json_response(
                {"ok": False, "error": f"Failed to open conversation: {conv_result.get('error', 'unknown')}"}, 500
            )

        channel_id = conv_result.get("channel", {}).get("id") if isinstance(conv_result.get("channel"), dict) else conv_result.get("channel")
        if not channel_id:
            return _json_response({"ok": False, "error": "Could not retrieve DM channel ID"}, 500)

        # Get DB stats
        counts = await get_db_table_counts(env)
        stats_text = _format_db_stats_for_slack(counts)

        # Send test message
        test_message = (
            f":wave: *Test Message from BLT Lettuce Bot!*\n\n"
            f"This is a test message from your workspace *{html_escape(ws.get('team_name', 'Unknown'))}*.\n\n"
            f"{stats_text}\n\n"
            f":white_check_mark: Your bot is working correctly!"
        )

        send_result = await send_slack_message(
            env,
            channel_id,
            test_message,
            token=ws.get("access_token")
        )

        if send_result.get("ok"):
            return Response.json({"ok": True, "message": "Test message sent successfully"})
        else:
            return _json_response(
                {"ok": False, "error": f"Failed to send message: {send_result.get('error', 'unknown')}"}, 500
            )

    # ------------------------------------------------------------------ #
    #  GET  /api/ws/<id>/repos  →  list repos                            #
    #  POST /api/ws/<id>/repos  →  add repo                              #
    # ------------------------------------------------------------------ #
    if pathname.startswith("/api/ws/") and pathname.endswith("/repos"):
        user = await get_current_user(env, request)
        if not user:
            return _json_response({"ok": False, "error": "Unauthorized"}, 401)
        try:
            ws_id_val = int(pathname.split("/api/ws/")[1].split("/")[0])
        except (ValueError, IndexError):
            return _json_response({"ok": False, "error": "Invalid workspace id"}, 400)

        if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
            return _json_response({"ok": False, "error": "Forbidden"}, 403)

        if method == "GET":
            repos = await db_get_repositories(env, ws_id_val)
            return Response.json({"ok": True, "repos": repos})

        if method == "POST":
            try:
                body = json.loads(await request.text())
                repo_url = (body.get("repo_url") or "").strip()
                if not repo_url:
                    return _json_response(
                        {"ok": False, "error": "repo_url required"}, 400
                    )

                # Fetch GitHub metadata (best-effort)
                repo_name, description, language, stars = "", "", "", 0
                try:
                    parsed_repo = urlparse(repo_url)
                    # Only call GitHub API for URLs whose host is exactly github.com
                    if parsed_repo.netloc in ("github.com", "www.github.com"):
                        path_parts = parsed_repo.path.strip("/").split("/")
                        if len(path_parts) >= 2:
                            owner, repo_slug = path_parts[0], path_parts[1]
                            api_url = (
                                f"https://api.github.com/repos/{owner}/{repo_slug}"
                            )
                            gh_headers = Headers.new()
                            gh_headers.set("User-Agent", "BLT-Lettuce")
                            gh_resp = await js_fetch(
                                api_url,
                                {
                                    "method": "GET",
                                    "headers": gh_headers,
                                },
                            )
                            gh_data = await gh_resp.json()
                            repo_name = gh_data.get("name", "")
                            description = gh_data.get("description", "") or ""
                            language = gh_data.get("language", "") or ""
                            stars = gh_data.get("stargazers_count", 0) or 0
                except Exception:
                    pass

                await db_add_repository(
                    env, ws_id_val, repo_url, repo_name, description, language, stars
                )
                return Response.json({"ok": True})
            except Exception:
                return _json_response({"ok": False, "error": "Invalid request"}, 400)

    # ------------------------------------------------------------------ #
    #  DELETE /api/ws/<ws_id>/repos/<repo_id>  →  remove a repo         #
    # ------------------------------------------------------------------ #
    if pathname.startswith("/api/ws/") and "/repos/" in pathname and method == "DELETE":
        user = await get_current_user(env, request)
        if not user:
            return _json_response({"ok": False, "error": "Unauthorized"}, 401)
        try:
            after = pathname.split("/api/ws/")[1]
            ws_id_val = int(after.split("/")[0])
            repo_id_val = int(after.split("/repos/")[1].rstrip("/"))
        except (ValueError, IndexError):
            return _json_response({"ok": False, "error": "Invalid ids"}, 400)

        if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
            return _json_response({"ok": False, "error": "Forbidden"}, 403)

        await db_delete_repository(env, repo_id_val, ws_id_val)
        return Response.json({"ok": True})

    # ------------------------------------------------------------------ #
    #  GET /api/ws/<id>/stats  →  live stats JSON (for dashboard poll)   #
    # ------------------------------------------------------------------ #
    if (
        pathname.startswith("/api/ws/")
        and pathname.endswith("/stats")
        and method == "GET"
    ):
        user = await get_current_user(env, request)
        if not user:
            return _json_response({"ok": False, "error": "Unauthorized"}, 401)
        try:
            ws_id_val = int(pathname.split("/api/ws/")[1].split("/")[0])
        except (ValueError, IndexError):
            return _json_response({"ok": False, "error": "Invalid workspace id"}, 400)

        if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
            return _json_response({"ok": False, "error": "Forbidden"}, 403)

        ws_stats = await db_get_workspace_stats(env, ws_id_val)
        return Response.new(
            json.dumps(ws_stats),
            {
                "status": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json",
                },
            },
        )

    # ------------------------------------------------------------------ #
    #  GET /api/ws/<id>/events  →  recent events JSON                    #
    # ------------------------------------------------------------------ #
    if (
        pathname.startswith("/api/ws/")
        and pathname.endswith("/events")
        and method == "GET"
    ):
        user = await get_current_user(env, request)
        if not user:
            return _json_response({"ok": False, "error": "Unauthorized"}, 401)
        try:
            ws_id_val = int(pathname.split("/api/ws/")[1].split("/")[0])
        except (ValueError, IndexError):
            return _json_response({"ok": False, "error": "Invalid workspace id"}, 400)

        if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
            return _json_response({"ok": False, "error": "Forbidden"}, 403)

        events = await db_get_events(env, ws_id_val, limit=50)
        return Response.json({"ok": True, "events": events})

    # ------------------------------------------------------------------ #
    #  POST /webhook  →  Slack events                                    #
    # ------------------------------------------------------------------ #
    if pathname == "/webhook" and method == "POST":
        try:
            body_text = await request.text()
            body_json = json.loads(body_text)

            if body_json.get("type") != "url_verification":
                signing_secret = getattr(env, "SIGNING_SECRET", None)
                timestamp = request.headers.get("X-Slack-Request-Timestamp")
                signature = request.headers.get("X-Slack-Signature")
                if not verify_slack_signature(
                    signing_secret, timestamp, body_text, signature
                ):
                    return _json_response({"error": "Invalid signature"}, 401)

            if body_json.get("type") == "url_verification":
                return Response.json({"challenge": body_json.get("challenge")})

            team_id = body_json.get("team_id")
            event = body_json.get("event", {})
            event_type = event.get("type")

            if event_type == "team_join":
                result = await handle_team_join(env, event, team_id=team_id)
                return Response.json(result)

            if event_type == "message":
                result = await handle_message_event(env, event, team_id=team_id)
                return Response.json(result)

            if event_type == "app_mention" or body_json.get("command"):
                result = await handle_command(env, event, team_id=team_id)
                return Response.json(result)

            return Response.json({"ok": True, "message": "Event received"})

        except Exception as e:
            try:
                sentry = get_sentry()
                await sentry.capture_exception(
                    e,
                    level="error",
                    extra={
                        "path": "/webhook",
                        "method": "POST",
                    },
                )
            except Exception:
                pass
            return _json_response({"error": "Internal server error"}, 500)

    # ------------------------------------------------------------------ #
    #  GET /health                                                        #
    # ------------------------------------------------------------------ #
    if pathname == "/health":
        return Response.json({"status": "ok", "timestamp": get_utc_now()})

    # ------------------------------------------------------------------ #
    #  GET /  →  homepage                                                #
    # ------------------------------------------------------------------ #
    if is_homepage_request(url, method):
        return _html_response(
            get_homepage_html(),
            extra_headers={"Cache-Control": "public, max-age=300"},
        )

    # ------------------------------------------------------------------ #
    #  GET /status  →  configuration status page                         #
    # ------------------------------------------------------------------ #
    if pathname == "/status":
        return _html_response(
            get_status_html(env),
            extra_headers={"Cache-Control": "no-cache"},
        )

    # ------------------------------------------------------------------ #
    #  GET /api/db-stats  →  database table counts                       #
    # ------------------------------------------------------------------ #
    if pathname == "/api/db-stats" and method == "GET":
        try:
            counts = await get_db_table_counts(env)
            return Response.json({
                "ok": True,
                "counts": counts,
                "timestamp": get_utc_now()
            })
        except Exception as e:
            return _json_response({"error": str(e)}, 500)

    # ------------------------------------------------------------------ #
    #  404 Not Found                                                     #
    # ------------------------------------------------------------------ #
    return _html_response(get_404_html(), 404)


# Module-level env holder for handler access
_current_env = None
_sentry_initialized = False


class Default(WorkerEntrypoint):
    """Cloudflare Python Worker entrypoint class."""

    async def fetch(self, request):
        """Main entry point for the Cloudflare Worker."""
        global _current_env
        global _sentry_initialized

        try:
            # Initialize Sentry on first request
            if not _sentry_initialized:
                try:
                    sentry_dsn = getattr(self.env, "SENTRY_DSN", None)
                    if sentry_dsn:
                        init_sentry(sentry_dsn)
                except Exception:
                    pass
                _sentry_initialized = True

            # Store env globally to avoid passing through multiple call levels
            _current_env = self.env
            # Call handler - it will access _current_env as needed
            return await handle_request(request, self.env)
        except Exception as e:
            # Report error to Sentry
            try:
                sentry = get_sentry()
                await sentry.capture_exception(
                    e,
                    level="error",
                    extra={
                        "path": request.url if hasattr(request, "url") else "unknown",
                        "method": request.method
                        if hasattr(request, "method")
                        else "unknown",
                    },
                )
            except Exception:
                pass

            # Log error cleanly to console
            import sys
            import traceback

            traceback.print_exc(file=sys.stderr)
            path = ""
            method = ""
            try:
                path = urlparse(request.url).path
                method = request.method
            except Exception:
                pass

            # API/webhook callers still expect JSON responses.
            if path.startswith("/api/") or path == "/webhook":
                h = Headers.new()
                h.set("Content-Type", "application/json")
                return Response.new(
                    json.dumps({"error": "Internal server error"}),
                    {"status": 500, "headers": h},
                )

            return _html_response(get_500_html(), status=500)
