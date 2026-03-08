"""
Cloudflare Python Worker for BLT-Lettuce Slack Bot.

This worker handles webhook events, sends welcome messages,
tracks stats, serves the homepage and dashboard, manages
Slack OAuth (sign-in + workspace installation), stores data
in Cloudflare D1, and handles all Slack interactions.
"""

import csv
import hashlib
import hmac
import io
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
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
    html_escape,
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
            "avatar_url TEXT DEFAULT '',"
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
            "app_id TEXT DEFAULT '',"
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
            "channel_name TEXT DEFAULT '',"
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

    # Migration metadata for conditional, idempotent schema changes.
    migrations = [
        {
            "table": "users",
            "column": "avatar_url",
            "sql": "ALTER TABLE users ADD COLUMN avatar_url TEXT DEFAULT ''",
        },
        {
            "table": "workspaces",
            "column": "app_id",
            "sql": "ALTER TABLE workspaces ADD COLUMN app_id TEXT DEFAULT ''",
        },
        {
            "table": "events",
            "column": "channel_name",
            "sql": "ALTER TABLE events ADD COLUMN channel_name TEXT DEFAULT ''",
        },
    ]

    try:
        print(
            f"[ensure_d1_schema] Initializing schema with {len(statements)} statements..."
        )
        for idx, sql in enumerate(statements, 1):
            await env.DB.prepare(sql).run()
            print(f"[ensure_d1_schema] Statement {idx}/{len(statements)} executed")

        # Run migrations only when the target column is missing.
        print(f"[ensure_d1_schema] Running {len(migrations)} migration(s)...")
        for idx, migration in enumerate(migrations, 1):
            try:
                table_name = migration["table"]
                column_name = migration["column"]
                migration_sql = migration["sql"]

                pragma_result = await env.DB.prepare(
                    f"PRAGMA table_info({table_name})"
                ).all()
                columns = _rows(pragma_result)
                existing_column_names = {
                    (col.get("name") or "") for col in columns if isinstance(col, dict)
                }

                if column_name in existing_column_names:
                    print(
                        f"[ensure_d1_schema] Migration {idx}/{len(migrations)} skipped: column {table_name}.{column_name} already exists"
                    )
                    continue

                await env.DB.prepare(migration_sql).run()
                print(
                    f"[ensure_d1_schema] Migration {idx}/{len(migrations)} executed successfully"
                )
            except Exception as migration_error:
                print(f"[ensure_d1_schema] Migration {idx} failed: {migration_error}")
                try:
                    sentry = get_sentry()
                    sentry.capture_exception_nowait(
                        migration_error,
                        level="error",
                        extra={
                            "context": "schema_migration",
                            "migration_index": idx,
                            "migration_sql": migration_sql,
                        },
                    )
                except Exception:
                    pass

        _schema_initialized = True
        print("[ensure_d1_schema] Schema initialization complete")
        return True
    except Exception as e:
        print(f"[ensure_d1_schema] ERROR: {e}")
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e, level="error", extra={"context": "schema_initialization"}
            )
        except Exception:
            pass
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
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={"context": "db_get_workspace_by_team", "team_id": team_id},
            )
        except Exception:
            pass
        return None


async def db_upsert_workspace(
    env, team_id, team_name, access_token, bot_user_id="", app_id=""
):
    now = get_utc_now()
    try:
        await ensure_d1_schema(env)
        existing = await db_get_workspace_by_team(env, team_id)
        if existing:
            result = await (
                env.DB.prepare(
                    "UPDATE workspaces SET team_name=?, app_id=?, access_token=?, bot_user_id=?, "
                    "updated_at=? WHERE team_id=?"
                )
                .bind(team_name, app_id, access_token, bot_user_id, now, team_id)
                .run()
            )
            print(
                f"[db_upsert_workspace] Updated workspace {team_id}, result: {result}"
            )
        else:
            result = await (
                env.DB.prepare(
                    "INSERT INTO workspaces "
                    "(team_id, team_name, app_id, access_token, bot_user_id, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)"
                )
                .bind(team_id, team_name, app_id, access_token, bot_user_id, now, now)
                .run()
            )
            print(
                f"[db_upsert_workspace] Inserted workspace {team_id}, result: {result}"
            )
        ws = await db_get_workspace_by_team(env, team_id)
        print(f"[db_upsert_workspace] Retrieved workspace: {ws}")
        return ws
    except Exception as e:
        print(f"[db_upsert_workspace] ERROR: {e}")
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e, level="error", extra={"team_id": team_id, "team_name": team_name}
            )
        except Exception:
            pass
        return None


async def db_get_workspace_by_id(env, workspace_id):
    try:
        return _row(
            await env.DB.prepare("SELECT * FROM workspaces WHERE id = ?")
            .bind(workspace_id)
            .first()
        )
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={
                    "context": "db_get_workspace_by_id",
                    "workspace_id": workspace_id,
                },
            )
        except Exception:
            pass
        return None


# ===========================================================================
# D1 — user_workspaces junction (many-to-many)
# ===========================================================================


async def db_link_user_workspace(env, user_id, workspace_id, role="owner"):
    """Associate a user with a workspace (idempotent)."""
    now = get_utc_now()
    print(
        f"[db_link_user_workspace] Linking user {user_id} to workspace {workspace_id}"
    )
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
        print(
            f"[db_link_user_workspace] ERROR linking user {user_id} to workspace {workspace_id}: {e}"
        )
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={"user_id": user_id, "workspace_id": workspace_id},
            )
        except Exception:
            pass
        return False


async def db_get_user_workspaces(env, user_id):
    """Return all workspaces accessible by this user."""
    print(f"[db_get_user_workspaces] Fetching workspaces for user_id={user_id}")
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
        workspaces = _rows(result)
        print(
            f"[db_get_user_workspaces] Found {len(workspaces)} workspace(s) for user {user_id}"
        )
        if workspaces:
            print(
                f"[db_get_user_workspaces] Workspaces: {[ws.get('team_name') for ws in workspaces]}"
            )
        return workspaces
    except Exception as e:
        print(f"[db_get_user_workspaces] ERROR: {e}")
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e, level="error", extra={"user_id": user_id}
            )
        except Exception:
            pass
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


async def db_get_user_workspace_role(env, user_id, workspace_id):
    """Return role for a user's workspace membership, or empty string."""
    try:
        row = _row(
            await env.DB.prepare(
                "SELECT role FROM user_workspaces WHERE user_id = ? AND workspace_id = ?"
            )
            .bind(user_id, workspace_id)
            .first()
        )
        return str((row or {}).get("role") or "")
    except Exception:
        return ""


async def db_get_workspace_installers(env, workspace_id):
    """Return users linked to a workspace (owners first) for install attribution."""
    try:
        rows = _rows(
            await env.DB.prepare(
                "SELECT u.name, u.slack_user_id, uw.role, uw.created_at "
                "FROM user_workspaces uw "
                "JOIN users u ON u.id = uw.user_id "
                "WHERE uw.workspace_id = ? "
                "ORDER BY CASE WHEN uw.role = 'owner' THEN 0 ELSE 1 END, uw.created_at ASC"
            )
            .bind(workspace_id)
            .all()
        )
        return rows
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={
                    "context": "db_get_workspace_installers",
                    "workspace_id": workspace_id,
                },
            )
        except Exception:
            pass
        return []


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
        print(
            f"[db_upsert_channel] Saved channel {channel_name} (ID: {channel_id}), result: {result}"
        )
        return True
    except Exception as e:
        print(f"[db_upsert_channel] ERROR saving channel {channel_id}: {e}")
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={"workspace_id": workspace_id, "channel_id": channel_id},
            )
        except Exception:
            pass
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


async def db_get_or_create_user(
    env, slack_user_id, team_id, name, email, access_token, avatar_url=""
):
    now = get_utc_now()
    print(
        f"[db_get_or_create_user] Called with slack_user_id={slack_user_id}, team_id={team_id}, name={name}"
    )
    try:
        await ensure_d1_schema(env)

        # Ensure required columns are never NULL for inserts/updates.
        slack_user_id = slack_user_id or ""
        team_id = team_id or "unknown"
        name = name or ""
        email = email or ""
        access_token = access_token or ""
        avatar_url = avatar_url or ""

        if not slack_user_id:
            print(
                "[db_get_or_create_user] ERROR: slack_user_id is empty, returning None"
            )
            return None

        existing = _row(
            await env.DB.prepare("SELECT * FROM users WHERE slack_user_id = ?")
            .bind(slack_user_id)
            .first()
        )
        if existing:
            print("[db_get_or_create_user] User exists, updating...")
            result = await (
                env.DB.prepare(
                    "UPDATE users SET name=?, email=?, access_token=?, avatar_url=?, team_id=?, updated_at=? "
                    "WHERE slack_user_id=?"
                )
                .bind(
                    name, email, access_token, avatar_url, team_id, now, slack_user_id
                )
                .run()
            )
            print(f"[db_get_or_create_user] Update result: {result}")
        else:
            print("[db_get_or_create_user] Creating new user...")
            result = await (
                env.DB.prepare(
                    "INSERT INTO users "
                    "(slack_user_id, team_id, name, email, access_token, avatar_url, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                )
                .bind(
                    slack_user_id,
                    team_id,
                    name,
                    email,
                    access_token,
                    avatar_url,
                    now,
                    now,
                )
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
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e, level="error", extra={"slack_user_id": slack_user_id}
            )
        except Exception:
            pass
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
        return token
    except Exception as e:
        print(f"[db_create_session] ERROR: {e}")
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e, level="error", extra={"user_id": user_id}
            )
        except Exception:
            pass
        return None


async def db_get_session(env, token):
    """Return session + user data if valid and not expired."""
    try:
        return _row(
            await env.DB.prepare(
                "SELECT s.id as session_id, s.user_id, s.expires_at, "
                "u.slack_user_id, u.team_id, u.name, u.email, u.avatar_url "
                "FROM sessions s JOIN users u ON s.user_id = u.id "
                "WHERE s.id = ? AND s.expires_at > ?"
            )
            .bind(token, get_utc_now())
            .first()
        )
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e, level="error", extra={"context": "db_get_session"}
            )
        except Exception:
            pass
        return None


async def db_delete_session(env, token):
    try:
        await env.DB.prepare("DELETE FROM sessions WHERE id = ?").bind(token).run()
        return True
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e, level="error", extra={"context": "db_delete_session"}
            )
        except Exception:
            pass
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
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={
                    "context": "db_add_repository",
                    "workspace_id": workspace_id,
                    "repo_url": repo_url,
                },
            )
        except Exception:
            pass
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
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={
                    "context": "db_delete_repository",
                    "repo_id": repo_id,
                    "workspace_id": workspace_id,
                },
            )
        except Exception:
            pass
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
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={"context": "db_get_repositories", "workspace_id": workspace_id},
            )
        except Exception:
            pass
        return []


# ===========================================================================
# D1 — Event helpers
# ===========================================================================


async def db_log_event(
    env,
    workspace_id,
    event_type,
    user_slack_id="",
    status="success",
    channel_name="",
):
    now = get_utc_now()
    try:
        await (
            env.DB.prepare(
                "INSERT INTO events (workspace_id, event_type, user_slack_id, channel_name, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)"
            )
            .bind(workspace_id, event_type, user_slack_id, channel_name, status, now)
            .run()
        )
        return True
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={
                    "context": "db_log_event",
                    "workspace_id": workspace_id,
                    "event_type": event_type,
                },
            )
        except Exception:
            pass
        return False


async def db_insert_event(
    env,
    workspace_id,
    event_type,
    user_slack_id="",
    status="success",
    created_at=None,
    channel_name="",
):
    """Insert a single event row with an explicit timestamp when provided."""
    event_time = created_at or get_utc_now()
    try:
        await (
            env.DB.prepare(
                "INSERT INTO events (workspace_id, event_type, user_slack_id, channel_name, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)"
            )
            .bind(
                workspace_id,
                event_type,
                user_slack_id,
                channel_name,
                status,
                event_time,
            )
            .run()
        )
        return True
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={
                    "context": "db_insert_event",
                    "workspace_id": workspace_id,
                    "event_type": event_type,
                },
            )
        except Exception:
            pass
        return False


def _normalize_event_timestamp(value):
    """Normalize user-provided timestamp values to ISO-8601 UTC strings."""
    if value is None:
        return get_utc_now()
    raw = str(value).strip()
    if not raw:
        return get_utc_now()
    cleaned = raw.replace(" ", "T")
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(cleaned)
    except ValueError:
        return get_utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


async def import_workspace_history_csv(env, workspace_id, csv_text):
    """Import event rows from CSV text into the events table."""
    if not csv_text or not str(csv_text).strip():
        return {"ok": False, "error": "CSV file is empty"}

    imported = 0
    skipped = 0
    sample_errors = []

    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        return {"ok": False, "error": "CSV must include a header row"}

    # Normalize header names to lowercase for flexible CSV imports.
    normalized_fieldnames = [
        str(name or "").strip().lower() for name in reader.fieldnames
    ]

    max_rows = 5000
    for row_index, row in enumerate(reader, start=2):
        if row_index > max_rows + 1:
            skipped += 1
            continue

        normalized_row = {}
        for idx, key in enumerate(reader.fieldnames or []):
            norm_key = (
                normalized_fieldnames[idx]
                if idx < len(normalized_fieldnames)
                else str(key or "").strip().lower()
            )
            normalized_row[norm_key] = row.get(key)

        event_type = (
            normalized_row.get("event_type") or normalized_row.get("type") or ""
        ).strip()
        if not event_type:
            skipped += 1
            if len(sample_errors) < 5:
                sample_errors.append(f"Line {row_index}: missing event_type")
            continue

        user_slack_id = (
            normalized_row.get("user_slack_id") or normalized_row.get("user") or ""
        ).strip()
        status = (normalized_row.get("status") or "success").strip() or "success"
        created_at = _normalize_event_timestamp(
            normalized_row.get("created_at")
            or normalized_row.get("time")
            or normalized_row.get("timestamp")
        )

        ok = await db_insert_event(
            env,
            workspace_id,
            event_type,
            user_slack_id=user_slack_id,
            status=status,
            created_at=created_at,
            channel_name=(normalized_row.get("channel_name") or "").strip(),
        )
        if ok:
            imported += 1
        else:
            skipped += 1
            if len(sample_errors) < 5:
                sample_errors.append(f"Line {row_index}: failed to insert event")

    return {
        "ok": imported > 0,
        "events_imported": imported,
        "rows_skipped": skipped,
        "errors": sample_errors,
    }


async def db_get_events(env, workspace_id, limit=20):
    try:
        return _rows(
            await env.DB.prepare(
                "SELECT e.*, u.name AS user_name "
                "FROM events e "
                "LEFT JOIN users u ON u.slack_user_id = e.user_slack_id "
                "WHERE e.workspace_id = ? "
                "ORDER BY e.created_at DESC LIMIT ?"
            )
            .bind(workspace_id, limit)
            .all()
        )
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={"context": "db_get_events", "workspace_id": workspace_id},
            )
        except Exception:
            pass
        return []


async def db_purge_events(env, workspace_id):
    """Delete all events for a workspace and return the number of deleted rows."""
    try:
        result = await (
            env.DB.prepare("DELETE FROM events WHERE workspace_id = ?")
            .bind(workspace_id)
            .run()
        )
        meta = _js_to_python(getattr(result, "meta", None)) or {}
        changes = int(meta.get("changes") or 0)
        return {"ok": True, "deleted": changes}
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={"context": "db_purge_events", "workspace_id": workspace_id},
            )
        except Exception:
            pass
        return {"ok": False, "deleted": 0, "error": "Failed to purge events"}


async def db_get_channel_name(env, workspace_id, channel_id):
    """Resolve a Slack channel ID to a stored channel name when available."""
    if not channel_id:
        return ""
    try:
        row = _row(
            await env.DB.prepare(
                "SELECT channel_name FROM channels WHERE workspace_id = ? AND channel_id = ?"
            )
            .bind(workspace_id, channel_id)
            .first()
        )
        return (row or {}).get("channel_name") or ""
    except Exception:
        return ""


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
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={"context": "db_get_daily_stats", "workspace_id": workspace_id},
            )
        except Exception:
            pass
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
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={
                    "context": "db_get_workspace_stats",
                    "workspace_id": workspace_id,
                },
            )
        except Exception:
            pass
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
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e, level="error", extra={"context": "get_current_user"}
            )
        except Exception:
            pass
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
            result = await env.DB.prepare(
                f"SELECT COUNT(*) as count FROM {table}"
            ).first()
            row = _row(result)
            count_val = row.get("count", 0) if row else 0
            counts[table] = count_val
            print(f"[get_db_table_counts] Table {table}: {count_val} rows")
        except Exception as e:
            print(f"[get_db_table_counts] ERROR querying table {table}: {e}")
            try:
                sentry = get_sentry()
                sentry.capture_exception_nowait(
                    e,
                    level="error",
                    extra={"table": table, "context": "get_db_table_counts"},
                )
            except Exception:
                pass
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


def _create_quick_action_buttons():
    """Create Slack Block Kit buttons for quick commands."""
    return [
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📊 Stats", "emoji": True},
                    "value": "stats",
                    "action_id": "quick_stats",
                    "style": "primary",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "👋 Hello", "emoji": True},
                    "value": "hello",
                    "action_id": "quick_hello",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "❓ Help", "emoji": True},
                    "value": "help",
                    "action_id": "quick_help",
                },
            ],
        }
    ]


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
            print(
                f"[scan_workspace_channels] Slack API response ok: {data.get('ok')}, error: {data.get('error')}"
            )
            if not data.get("ok"):
                print(f"[scan_workspace_channels] Slack API error: {data.get('error')}")
                break
            channels = data.get("channels", [])
            print(
                f"[scan_workspace_channels] Found {len(channels)} channels in this batch"
            )
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
            try:
                sentry = get_sentry()
                sentry.capture_exception_nowait(
                    e, level="error", extra={"workspace_id": workspace_id}
                )
            except Exception:
                pass
            break
    print(f"[scan_workspace_channels] Scan complete: {scanned} channels saved")
    return scanned


async def import_workspace_history(env, workspace_id, access_token):
    """Import historical channel activity from Slack to populate events table."""
    print(f"[import_workspace_history] Starting import for workspace {workspace_id}")

    # Get all channels for this workspace
    channels = await db_get_channels(env, workspace_id)
    if not channels:
        print("[import_workspace_history] No channels found. Run scan first.")
        return {"ok": False, "error": "No channels found. Please scan channels first."}

    total_events = 0
    # Get last 7 days of history from each channel
    import time

    oldest = str(int(time.time()) - (7 * 24 * 60 * 60))  # 7 days ago

    for ch in channels[:10]:  # Limit to first 10 channels to avoid timeout
        channel_id = ch.get("channel_id")
        print(
            f"[import_workspace_history] Importing history from #{ch.get('channel_name')}"
        )

        try:
            headers = Headers.new()
            headers.set("Authorization", f"Bearer {access_token}")
            headers.set("Content-Type", "application/json")

            url = f"https://slack.com/api/conversations.history?channel={channel_id}&oldest={oldest}&limit=100"
            resp = await js_fetch(url, {"method": "GET", "headers": headers})
            data = await resp.json()
            data = _js_to_python(data)

            if not data.get("ok"):
                print(
                    f"[import_workspace_history] Error fetching history: {data.get('error')}"
                )
                continue

            messages = _js_to_python(data.get("messages") or [])
            for msg in messages:
                user_id = _obj_get(msg, "user", "")
                msg_type = _obj_get(msg, "type", "message")
                await db_log_event(
                    env,
                    workspace_id,
                    f"message_{msg_type}",
                    user_id,
                    "success",
                    channel_name=ch.get("channel_name", "") or "",
                )
                total_events += 1

        except Exception as e:
            print(f"[import_workspace_history] ERROR importing from {channel_id}: {e}")
            try:
                sentry = get_sentry()
                sentry.capture_exception_nowait(
                    e,
                    level="error",
                    extra={
                        "workspace_id": workspace_id,
                        "channel_id": channel_id,
                        "context": "import_workspace_history",
                    },
                )
            except Exception:
                pass
            continue

    print(f"[import_workspace_history] Import complete: {total_events} events added")
    return {
        "ok": True,
        "events_imported": total_events,
        "channels_processed": min(len(channels), 10),
    }


async def get_workspace_installed_apps(env, workspace):
    """Best-effort list of installed apps visible to the workspace token."""
    ws = workspace or {}
    token = ws.get("access_token") or ""
    if not token:
        return {
            "apps": [],
            "permission_warning": "No workspace token found. Reinstall the app to fetch installed apps.",
        }

    apps = []
    admin_list_success = False
    admin_errors = []

    def _append_app(item):
        app_id = str(item.get("app_id") or "").strip()
        if not app_id:
            return
        for existing in apps:
            if existing.get("app_id") == app_id:
                return
        apps.append(item)

    async def _fetch_admin_apps(endpoint, source_label, distribution_label):
        nonlocal admin_list_success
        try:
            headers = Headers.new()
            headers.set("Authorization", f"Bearer {token}")
            resp = await js_fetch(
                f"https://slack.com/api/{endpoint}?limit=200",
                {"method": "GET", "headers": headers},
            )
            data = _js_to_python(await resp.json())
            if isinstance(data, dict) and data.get("ok"):
                admin_list_success = True
                for app in _js_to_python(data.get("apps") or []):
                    if not isinstance(app, dict):
                        continue
                    _append_app(
                        {
                            "app_id": app.get("app_id") or app.get("id") or "",
                            "app_name": app.get("name")
                            or app.get("app_name")
                            or "Unknown App",
                            "is_installed": True,
                            "source": source_label,
                            "distribution": distribution_label,
                        }
                    )
            elif isinstance(data, dict):
                admin_errors.append(str(data.get("error") or "unknown_error"))
        except Exception:
            admin_errors.append("request_failed")

    # Admin APIs can list more than one app in a workspace when permissions allow it.
    await _fetch_admin_apps(
        "admin.apps.approved.list",
        "admin.apps.approved.list",
        "Publicly Distributed",
    )
    await _fetch_admin_apps(
        "admin.apps.restricted.list",
        "admin.apps.restricted.list",
        "Not distributed",
    )

    try:
        headers = Headers.new()
        headers.set("Authorization", f"Bearer {token}")

        # Fallback to metadata for the currently installed app.
        app_info_resp = await js_fetch(
            "https://slack.com/api/apps.permissions.info",
            {"method": "GET", "headers": headers},
        )
        app_info = _js_to_python(await app_info_resp.json())
        if isinstance(app_info, dict) and app_info.get("ok"):
            info = _js_to_python(app_info.get("info") or {})
            app_obj = _js_to_python(info.get("app") or app_info.get("app") or {})
            scopes_obj = _js_to_python(info.get("scopes") or {})
            bot_scopes = _js_to_python(scopes_obj.get("bot") or [])
            if isinstance(bot_scopes, list):
                bot_scopes_text = ", ".join(str(s) for s in bot_scopes[:12])
            else:
                bot_scopes_text = ""
            _append_app(
                {
                    "app_id": ws.get("app_id") or app_obj.get("id") or "",
                    "app_name": app_obj.get("name") or "BLT Lettuce",
                    "is_installed": True,
                    "source": "apps.permissions.info",
                    "scopes": bot_scopes_text,
                    "distribution": "Modern",
                }
            )
    except Exception:
        pass

    # Final fallback: always show the app currently linked in our workspace table.
    _append_app(
        {
            "app_id": ws.get("app_id") or "",
            "app_name": "BLT Lettuce",
            "is_installed": True,
            "source": "workspace_record",
            "scopes": "",
            "distribution": "Modern",
        }
    )

    permission_warning = ""
    if not admin_list_success:
        unique_errors = sorted({e for e in admin_errors if e})
        hint = ""
        if any(
            e
            in ("missing_scope", "not_allowed_token_type", "not_authed", "invalid_auth")
            for e in unique_errors
        ):
            hint = (
                "To list all workspace apps, reinstall with an admin token that has "
                "`admin.apps:read` scope (and org/workspace admin privileges)."
            )
        elif unique_errors:
            hint = f"Admin app listing failed with: {', '.join(unique_errors)}"
        else:
            hint = (
                "Admin app listing is unavailable for this token. "
                "Use an admin token with `admin.apps:read` to see all installed apps."
            )
        permission_warning = hint

    return {
        "apps": [a for a in apps if a.get("app_id")],
        "permission_warning": permission_warning,
    }


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
    return (
        result
        if isinstance(result, dict)
        else {"ok": False, "error": "invalid_response"}
    )


async def send_interactive_response(response_url, text, blocks=None):
    """Send a response to Slack interactivity response_url."""
    if not response_url:
        return {"ok": False, "error": "missing_response_url"}
    payload = {
        "response_type": "ephemeral",
        "text": text,
    }
    if blocks:
        payload["blocks"] = blocks
    headers = Headers.new()
    headers.set("Content-Type", "application/json")
    resp = await js_fetch(
        response_url,
        {
            "method": "POST",
            "headers": headers,
            "body": json.dumps(payload),
        },
    )
    status = getattr(resp, "status", 0)
    return {"ok": 200 <= status < 300, "status": status}


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
    return (
        result
        if isinstance(result, dict)
        else {"ok": False, "error": "invalid_response"}
    )


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
    if subtype in (
        "message_changed",
        "message_deleted",
        "bot_message",
        "channel_leave",
    ):
        return {"ok": True, "message": f"Ignoring message subtype: {subtype}"}

    # Look up workspace-specific bot token
    ws_token = getattr(env, "SLACK_TOKEN", None)
    ws = None
    resolved_channel_name = ""
    if team_id:
        ws = await db_get_workspace_by_team(env, team_id)
        if ws and ws.get("access_token"):
            ws_token = ws["access_token"]
        if ws:
            if channel_type == "im":
                resolved_channel_name = "Direct Message"
            else:
                resolved_channel_name = await db_get_channel_name(
                    env, ws["id"], channel
                )

    bot_user_id = await get_bot_user_id(env)
    if user == bot_user_id:
        return {"ok": True, "message": "Ignoring bot message"}

    contribute_id = getattr(env, "CONTRIBUTE_ID", DEFAULT_CONTRIBUTE_ID)
    joins_channel = getattr(env, "JOINS_CHANNEL_ID", DEFAULT_JOINS_CHANNEL_ID)

    # Track channel joins in activities and notify contribute channel.
    if subtype == "channel_join":
        if ws:
            await db_log_event(
                env,
                ws["id"],
                "Channel_Join",
                user or "",
                "success",
                channel_name=resolved_channel_name,
            )
        return {"ok": True, "action": "channel_join_logged"}

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
            blocks = _create_quick_action_buttons()
            result = await send_slack_message(
                env, channel, stats_text, blocks=blocks, token=ws_token
            )
            return {"ok": result.get("ok"), "action": "dm_stats"}

        if any(greet in message_text for greet in ("hello", "hi", "hey")):
            counts = await get_db_table_counts(env)
            stats_text = _format_db_stats_for_slack(counts)
            greet_text = (
                f"Hello <@{user}>! Here are the latest stats.\n\n{stats_text}\n\n"
                "Try commands: `stats`, `help`, `health`"
            )
            blocks = _create_quick_action_buttons()
            result = await send_slack_message(
                env, channel, greet_text, blocks=blocks, token=ws_token
            )
            return {"ok": result.get("ok"), "action": "dm_greeting_stats"}

        if any(word in message_text for word in ("help", "commands", "cmd")):
            help_text = (
                "*Lettuce Bot Commands*\n"
                "- `stats` or `health`: Show DB table counts\n"
                "- `hello` / `hi` / `hey`: Greeting + DB stats\n"
                "- `help`: Show this command list\n\n"
                "Or use the quick action buttons below!"
            )
            blocks = _create_quick_action_buttons()
            result = await send_slack_message(
                env, channel, help_text, blocks=blocks, token=ws_token
            )
            return {"ok": result.get("ok"), "action": "dm_help"}

        # Default DM response with quick guidance + current stats.
        counts = await get_db_table_counts(env)
        stats_text = _format_db_stats_for_slack(counts)
        default_text = (
            f"Hi <@{user}>! I can help with stats.\n\n{stats_text}\n\n"
            "Try: `stats`, `hello`, or `help` - or use the buttons below!"
        )
        blocks = _create_quick_action_buttons()
        result = await send_slack_message(
            env, channel, default_text, blocks=blocks, token=ws_token
        )
        return {"ok": result.get("ok"), "action": "dm_default"}

    return {"ok": True, "message": "No action taken"}


async def handle_command(env, event, team_id=None):
    user_id = event.get("user") or event.get("user_id") or ""
    channel_id = event.get("channel") or event.get("channel_id") or ""
    channel_name = event.get("channel_name") or ""
    if team_id:
        ws = await db_get_workspace_by_team(env, team_id)
        if ws:
            if not channel_name and channel_id:
                channel_name = await db_get_channel_name(env, ws["id"], channel_id)
            await db_log_event(
                env,
                ws["id"],
                "Command",
                user_id,
                "success",
                channel_name=channel_name,
            )
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


def _manifest_get(data, path):
    """Safely read nested dict values by path list."""
    cur = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _manifest_read_data(manifest_path):
    """Read YAML manifest content and parse to dict when possible."""
    text = manifest_path.read_text(encoding="utf-8")
    parsed = None
    try:
        import yaml  # type: ignore

        parsed = yaml.safe_load(text)
    except Exception:
        parsed = None
    return text, parsed if isinstance(parsed, dict) else None


def _contains_manifest_line(text, snippet):
    return snippet in text


def check_manifest_requirements(manifest_path):
    """Validate manifest.yaml against required BLT-Lettuce settings."""
    if not manifest_path.exists():
        return {
            "ok": False,
            "manifest_path": str(manifest_path),
            "summary": "manifest.yaml not found",
            "checks": [
                {
                    "name": "Manifest file exists",
                    "ok": False,
                    "detail": f"Could not find: {manifest_path}",
                }
            ],
        }

    text, parsed = _manifest_read_data(manifest_path)

    checks = []

    def add_check(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    if parsed is not None:
        add_check(
            "display_information.name",
            bool(_manifest_get(parsed, ["display_information", "name"])),
            "App display name is required.",
        )
        add_check(
            "display_information.description",
            bool(_manifest_get(parsed, ["display_information", "description"])),
            "App description is required.",
        )
        add_check(
            "features.bot_user.display_name",
            bool(_manifest_get(parsed, ["features", "bot_user", "display_name"])),
            "Bot display name is required.",
        )

        request_url = _manifest_get(
            parsed, ["settings", "event_subscriptions", "request_url"]
        )
        add_check(
            "settings.event_subscriptions.request_url",
            bool(request_url)
            and "<YOUR_WORKER_URL>" not in str(request_url)
            and str(request_url).endswith("/webhook"),
            "Must be a real webhook URL ending in /webhook.",
        )

        interactivity_url = _manifest_get(
            parsed, ["settings", "interactivity", "request_url"]
        )
        interactivity_enabled = _manifest_get(
            parsed, ["settings", "interactivity", "is_enabled"]
        )
        add_check(
            "settings.interactivity",
            bool(interactivity_enabled)
            and bool(interactivity_url)
            and "<YOUR_WORKER_URL>" not in str(interactivity_url)
            and str(interactivity_url).endswith("/webhook"),
            "Interactivity must be enabled and point to /webhook.",
        )

        bot_events = _manifest_get(
            parsed, ["settings", "event_subscriptions", "bot_events"]
        )
        bot_events = bot_events if isinstance(bot_events, list) else []
        required_events = ["team_join", "message.im"]
        for evt in required_events:
            add_check(
                f"bot_event:{evt}",
                evt in bot_events,
                f"Required event subscription: {evt}",
            )

        bot_scopes = _manifest_get(parsed, ["oauth_config", "scopes", "bot"])
        bot_scopes = bot_scopes if isinstance(bot_scopes, list) else []
        required_scopes = [
            "channels:read",
            "chat:write",
            "commands",
            "im:history",
            "im:read",
            "im:write",
            "users:read",
            "team:read",
        ]
        for scope in required_scopes:
            add_check(
                f"scope:{scope}",
                scope in bot_scopes,
                f"Required bot scope: {scope}",
            )
    else:
        # Fallback text checks when YAML parser is unavailable.
        add_check(
            "Manifest YAML parse",
            False,
            "Could not parse YAML with local parser; using text checks only.",
        )
        fallback_snippets = [
            "display_information:",
            "oauth_config:",
            "settings:",
            "request_url:",
            "bot_events:",
            "commands",
            "chat:write",
            "users:read",
        ]
        for snippet in fallback_snippets:
            add_check(
                f"contains:{snippet}",
                _contains_manifest_line(text, snippet),
                f"Manifest should include: {snippet}",
            )

    passed = len([c for c in checks if c["ok"]])
    failed = len(checks) - passed
    summary = f"{passed} passed, {failed} failed"
    return {
        "ok": failed == 0,
        "manifest_path": str(manifest_path),
        "summary": summary,
        "checks": checks,
    }


async def report_404_to_sentry(env, path, method, detail=""):
    """Capture 404 responses in Sentry with request context."""
    try:
        sentry = get_sentry()
        sentry.capture_exception_nowait(
            RuntimeError(f"404 Not Found: {path}"),
            level="warning",
            extra={
                "path": path,
                "method": method,
                "detail": detail,
            },
        )
    except Exception:
        pass


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
            user_avatar = ""
            team_obj = _js_to_python(token_data.get("team") or {})
            user_team_id = _obj_get(team_obj, "id", "")

            if user_token:
                identity = await fetch_user_identity(user_token)
                if identity.get("ok"):
                    profile = _js_to_python(identity.get("user") or {})
                    team_info = _js_to_python(identity.get("team") or {})
                    user_name = _obj_get(profile, "name", "")
                    user_email = _obj_get(profile, "email", "")
                    user_avatar = (
                        _obj_get(profile, "image_192", "")
                        or _obj_get(profile, "image_72", "")
                        or _obj_get(profile, "image_48", "")
                    )
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
                user_avatar,
            )
            print(f"[OAuth callback] User object returned: {user}")
            if not user:
                sign_in_url = get_slack_sign_in_url(client_id or "", redirect_uri)
                return _html_response(
                    get_login_page_html(
                        sign_in_url, error="Database error. Please try again."
                    ),
                )

            # Validate user has an ID field
            user_id_val = user.get("id") if isinstance(user, dict) else None
            if not user_id_val:
                print(
                    f"[OAuth callback] ERROR: User object missing 'id' field. User keys: {user.keys() if isinstance(user, dict) else 'not a dict'}"
                )
                sign_in_url = get_slack_sign_in_url(client_id or "", redirect_uri)
                return _html_response(
                    get_login_page_html(
                        sign_in_url, error="User ID error. Please try again."
                    ),
                )

            # ---- If this was an "add workspace" flow, install the bot ----
            if intent == "add_workspace":
                print("[OAuth callback] Processing add_workspace flow")
                bot_token = token_data.get("access_token")
                team_info = _js_to_python(token_data.get("team") or {})
                team_id = _obj_get(team_info, "id", "")
                team_name = _obj_get(team_info, "name", "Unknown Workspace")
                bot_user_id = token_data.get("bot_user_id") or ""
                app_id = token_data.get("app_id") or ""
                print(
                    f"[OAuth callback] team_id={team_id}, team_name={team_name}, app_id={app_id}, bot_user_id={bot_user_id}, bot_token present={bool(bot_token)}"
                )

                if team_id and bot_token:
                    ws = await db_upsert_workspace(
                        env, team_id, team_name, bot_token, bot_user_id, app_id
                    )
                    print(f"[OAuth callback] Workspace upserted: {ws}")
                    if ws:
                        ws_id_val = ws.get("id") if isinstance(ws, dict) else None
                        print(
                            f"[OAuth callback] user_id_val={user_id_val}, ws_id_val={ws_id_val}"
                        )
                        print(
                            f"[OAuth callback] Workspace keys: {ws.keys() if isinstance(ws, dict) else 'not a dict'}"
                        )

                        if user_id_val and ws_id_val:
                            link_result = await db_link_user_workspace(
                                env, user_id_val, ws_id_val, role="owner"
                            )
                            print(f"[OAuth callback] Link result: {link_result}")
                            if not link_result:
                                print(
                                    "[OAuth callback] ERROR: Failed to link user to workspace"
                                )
                        else:
                            print(
                                f"[OAuth callback] WARNING: Could not link workspace - missing user_id ({user_id_val}) or ws_id ({ws_id_val})"
                            )
                        # Background channel scan (best-effort)
                        try:
                            if ws_id_val and bot_token:
                                print("[OAuth callback] Starting channel scan...")
                                scan_result = await scan_workspace_channels(
                                    env, ws_id_val, bot_token
                                )
                                print(
                                    f"[OAuth callback] Channel scan result: {scan_result}"
                                )
                        except Exception as e:
                            print(f"[OAuth callback] Channel scan failed: {e}")
                            pass
                else:
                    print(
                        "[OAuth callback] WARNING: Could not create workspace - missing team_id or bot_token"
                    )

            # ---- Create session ----
            token = generate_session_token()
            print(f"[OAuth callback] Creating session with user_id={user_id_val}")
            session_ok = (
                await db_create_session(env, user_id_val, token)
                if user_id_val
                else False
            )
            print(f"[OAuth callback] Session creation result: {session_ok}")
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
                sentry.capture_exception_nowait(
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

        print(
            f"[GET /dashboard] User: {user.get('name')} (user_id={user.get('user_id')}, slack_user_id={user.get('slack_user_id')})"
        )
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
        if selected_tab not in ("overview", "channels", "apps", "manifest"):
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
        installed_apps = []
        apps_permission_warning = ""
        workspace_installers = []
        manifest_result = None
        can_manage_manifest = False

        if current_ws:
            ws_id_val = current_ws["id"]
            user_role = await db_get_user_workspace_role(
                env, user["user_id"], ws_id_val
            )
            can_manage_manifest = user_role in ("owner", "admin")
            ws_stats = await db_get_workspace_stats(env, ws_id_val)
            channels = await db_get_channels(env, ws_id_val)
            events = await db_get_events(env, ws_id_val, limit=20)
            daily_stats = await db_get_daily_stats(env, ws_id_val, days=30)
            repos = await db_get_repositories(env, ws_id_val)
            if selected_tab == "apps":
                apps_payload = await get_workspace_installed_apps(env, current_ws)
                installed_apps = (apps_payload or {}).get("apps") or []
                apps_permission_warning = (apps_payload or {}).get(
                    "permission_warning"
                ) or ""
                workspace_installers = await db_get_workspace_installers(env, ws_id_val)

                # Attach best-effort installer attribution to each app row.
                installer_name = ""
                if workspace_installers:
                    primary = workspace_installers[0]
                    installer_name = (
                        primary.get("name") or primary.get("slack_user_id") or "Unknown"
                    )
                for app in installed_apps:
                    app["installed_by"] = installer_name or "Unknown"
            elif selected_tab == "manifest":
                if not can_manage_manifest:
                    manifest_result = {
                        "ok": False,
                        "summary": "Access denied",
                        "manifest_path": "manifest.yaml",
                        "checks": [],
                        "error": "Only workspace admins/owners can access Manifest Checker.",
                    }
                else:
                    base_dir = Path(__file__).resolve().parents[1]
                    manifest_path = base_dir / "manifest.yaml"
                    manifest_result = check_manifest_requirements(manifest_path)

        html = get_dashboard_html(
            user,
            workspaces,
            current_ws,
            ws_stats,
            channels,
            events,
            daily_stats,
            repos,
            installed_apps,
            apps_permission_warning,
            manifest_result,
            can_manage_manifest,
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
            await report_404_to_sentry(env, pathname, method, "workspace_not_found")
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
            await report_404_to_sentry(env, pathname, method, "workspace_not_found")
            return _json_response({"ok": False, "error": "Workspace not found"}, 404)

        # Send test DM to the user
        user_slack_id = user.get("slack_user_id")
        if not user_slack_id:
            return _json_response(
                {"ok": False, "error": "User Slack ID not found"}, 400
            )

        # Open DM conversation
        conv_result = await open_conversation(
            env, user_slack_id, ws.get("access_token")
        )
        if not conv_result.get("ok"):
            return _json_response(
                {
                    "ok": False,
                    "error": f"Failed to open conversation: {conv_result.get('error', 'unknown')}",
                },
                500,
            )

        channel_id = (
            conv_result.get("channel", {}).get("id")
            if isinstance(conv_result.get("channel"), dict)
            else conv_result.get("channel")
        )
        if not channel_id:
            return _json_response(
                {"ok": False, "error": "Could not retrieve DM channel ID"}, 500
            )

        # Get DB stats
        counts = await get_db_table_counts(env)
        stats_text = _format_db_stats_for_slack(counts)

        # Send test message
        test_message = (
            f":wave: *Test Message from BLT Lettuce Bot!*\n\n"
            f"This is a test message from your workspace *{html_escape(ws.get('team_name', 'Unknown'))}*.\n\n"
            f"{stats_text}\n\n"
            f":white_check_mark: Your bot is working correctly!\n\n"
            "Try the quick action buttons below:"
        )

        blocks = _create_quick_action_buttons()
        send_result = await send_slack_message(
            env, channel_id, test_message, blocks=blocks, token=ws.get("access_token")
        )

        if send_result.get("ok"):
            return Response.json(
                {"ok": True, "message": "Test message sent successfully"}
            )
        else:
            return _json_response(
                {
                    "ok": False,
                    "error": f"Failed to send message: {send_result.get('error', 'unknown')}",
                },
                500,
            )

    # ------------------------------------------------------------------ #
    #  POST /api/ws/<id>/import-history  →  import historical activities#
    # ------------------------------------------------------------------ #
    if (
        pathname.startswith("/api/ws/")
        and pathname.endswith("/import-history")
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
            await report_404_to_sentry(env, pathname, method, "workspace_not_found")
            return _json_response({"ok": False, "error": "Workspace not found"}, 404)

        try:
            body = json.loads(await request.text())
        except Exception:
            body = {}

        csv_text = (body.get("csv_text") or "") if isinstance(body, dict) else ""
        if not csv_text:
            return _json_response(
                {
                    "ok": False,
                    "error": "CSV upload required. Please choose a CSV file from the dashboard.",
                },
                400,
            )

        result = await import_workspace_history_csv(env, ws_id_val, csv_text)
        status_code = 200 if result.get("ok") else 400
        return _json_response(result, status_code)

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
        try:
            user = await get_current_user(env, request)
            if not user:
                return _json_response({"ok": False, "error": "Unauthorized"}, 401)
            try:
                ws_id_val = int(pathname.split("/api/ws/")[1].split("/")[0])
            except (ValueError, IndexError):
                return _json_response(
                    {"ok": False, "error": "Invalid workspace id"}, 400
                )

            if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
                return _json_response({"ok": False, "error": "Forbidden"}, 403)

            ws_stats = await db_get_workspace_stats(env, ws_id_val)
            return _json_response(ws_stats, 200)
        except Exception as e:
            try:
                sentry = get_sentry()
                sentry.capture_exception_nowait(
                    e,
                    level="error",
                    extra={"path": "/api/ws/<id>/stats", "workspace_id": pathname},
                )
            except Exception:
                pass
            return _json_response({"ok": False, "error": "Internal server error"}, 500)

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
    #  POST /api/ws/<id>/events/purge  →  purge workspace events         #
    # ------------------------------------------------------------------ #
    if (
        pathname.startswith("/api/ws/")
        and pathname.endswith("/events/purge")
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

        user_role = await db_get_user_workspace_role(env, user["user_id"], ws_id_val)
        if user_role not in ("owner", "admin"):
            return _json_response(
                {
                    "ok": False,
                    "error": "Only workspace admins/owners can purge recent activities.",
                },
                403,
            )

        purge_result = await db_purge_events(env, ws_id_val)
        if not purge_result.get("ok"):
            return _json_response(
                {"ok": False, "error": purge_result.get("error") or "Purge failed"},
                500,
            )

        return Response.json(
            {
                "ok": True,
                "deleted": int(purge_result.get("deleted") or 0),
                "message": "Recent activities purged.",
            }
        )

    # ------------------------------------------------------------------ #
    #  POST /webhook  →  Slack events                                    #
    # ------------------------------------------------------------------ #
    if pathname == "/webhook" and method == "POST":
        try:
            body_text = await request.text()
            content_type = (request.headers.get("Content-Type") or "").lower()
            body_json = {}

            # Slack interactivity and slash commands are form-encoded.
            if "application/x-www-form-urlencoded" in content_type:
                form_data = {}
                for pair in body_text.split("&"):
                    if not pair:
                        continue
                    kv = pair.split("=", 1)
                    key = unquote_plus(kv[0]) if len(kv) > 0 else ""
                    value = unquote_plus(kv[1]) if len(kv) > 1 else ""
                    if key:
                        form_data[key] = value

                if form_data.get("payload"):
                    body_json = json.loads(form_data.get("payload") or "{}")
                else:
                    # Slash command payload shape.
                    body_json = {
                        "type": "slash_command",
                        **form_data,
                    }
            else:
                body_json = json.loads(body_text or "{}")

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

            if body_json.get("type") == "slash_command":
                user_id = body_json.get("user_id")
                cmd_text = (body_json.get("text") or "").strip().lower()
                cmd_name = (body_json.get("command") or "").strip().lower()

                # Fast path for /demo to avoid Slack dispatch timeouts.
                if cmd_name == "/demo":
                    return Response.json(
                        {
                            "response_type": "ephemeral",
                            "text": "Demo command received successfully.",
                        }
                    )

                try:
                    counts = await get_db_table_counts(env)
                    stats_text = _format_db_stats_for_slack(counts)
                except Exception:
                    stats_text = "Stats are temporarily unavailable. Please try again."
                quick_buttons = _create_quick_action_buttons()

                # Primary behavior for slash commands: return stats immediately.
                if cmd_name in ("/project", "/repo", "/demo_jisan") or (
                    cmd_text in ("", "stats", "health", "tables", "db")
                ):
                    return Response.json(
                        {
                            "response_type": "ephemeral",
                            "text": stats_text,
                            "blocks": quick_buttons,
                        }
                    )

                if cmd_text in ("hello", "hi", "hey"):
                    return Response.json(
                        {
                            "response_type": "ephemeral",
                            "text": f"Hello <@{user_id}>! Here are the latest stats.\\n\\n{stats_text}",
                            "blocks": quick_buttons,
                        }
                    )

                return Response.json(
                    {
                        "response_type": "ephemeral",
                        "text": (
                            "Unknown command input. Try `stats`, `hello`, or `help`.\\n\\n"
                            f"{stats_text}"
                        ),
                        "blocks": quick_buttons,
                    }
                )

            # Handle interactive button clicks
            if body_json.get("type") == "block_actions":
                team_id = (
                    body_json.get("team", {}).get("id")
                    if isinstance(body_json.get("team"), dict)
                    else body_json.get("team_id")
                )
                user_id = (
                    body_json.get("user", {}).get("id")
                    if isinstance(body_json.get("user"), dict)
                    else None
                )
                channel_id = (
                    body_json.get("channel", {}).get("id")
                    if isinstance(body_json.get("channel"), dict)
                    else None
                )
                response_url = body_json.get("response_url")

                actions = body_json.get("actions", [])
                if actions and len(actions) > 0:
                    action = actions[0]
                    action_id = action.get("action_id", "")

                    # Get workspace token
                    ws = await db_get_workspace_by_team(env, team_id)
                    ws_token = ws.get("access_token") if ws else None
                    if not ws_token:
                        ws_token = getattr(env, "SLACK_TOKEN", None)

                    # Handle button actions by simulating the command
                    if action_id == "quick_stats":
                        counts = await get_db_table_counts(env)
                        stats_text = _format_db_stats_for_slack(counts)
                        blocks = _create_quick_action_buttons()
                        if ws_token and channel_id:
                            await send_slack_message(
                                env,
                                channel_id,
                                stats_text,
                                blocks=blocks,
                                token=ws_token,
                            )
                        else:
                            await send_interactive_response(
                                response_url,
                                stats_text,
                                blocks=blocks,
                            )

                    elif action_id == "quick_hello":
                        counts = await get_db_table_counts(env)
                        stats_text = _format_db_stats_for_slack(counts)
                        greet_text = (
                            f"Hello <@{user_id}>! Here are the latest stats.\\n\\n{stats_text}\\n\\n"
                            "Try commands: `stats`, `help`, `health`"
                        )
                        blocks = _create_quick_action_buttons()
                        if ws_token and channel_id:
                            await send_slack_message(
                                env,
                                channel_id,
                                greet_text,
                                blocks=blocks,
                                token=ws_token,
                            )
                        else:
                            await send_interactive_response(
                                response_url,
                                greet_text,
                                blocks=blocks,
                            )

                    elif action_id == "quick_help":
                        help_text = (
                            "*Lettuce Bot Commands*\\n"
                            "- `stats` or `health`: Show DB table counts\\n"
                            "- `hello` / `hi` / `hey`: Greeting + DB stats\\n"
                            "- `help`: Show this command list\\n\\n"
                            "Or use the quick action buttons below!"
                        )
                        blocks = _create_quick_action_buttons()
                        if ws_token and channel_id:
                            await send_slack_message(
                                env,
                                channel_id,
                                help_text,
                                blocks=blocks,
                                token=ws_token,
                            )
                        else:
                            await send_interactive_response(
                                response_url,
                                help_text,
                                blocks=blocks,
                            )

                return Response.json({"ok": True})

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
                sentry.capture_exception_nowait(
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
        user = await get_current_user(env, request)
        return _html_response(
            get_homepage_html(user),
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
    #  GET /manifest-checker  →  validate Slack app manifest             #
    # ------------------------------------------------------------------ #
    if pathname == "/manifest-checker" and method == "GET":
        return _redirect("/dashboard?tab=manifest")

    # ------------------------------------------------------------------ #
    #  GET /api/db-stats  →  database table counts                       #
    # ------------------------------------------------------------------ #
    if pathname == "/api/db-stats" and method == "GET":
        try:
            counts = await get_db_table_counts(env)
            return Response.json(
                {"ok": True, "counts": counts, "timestamp": get_utc_now()}
            )
        except Exception as e:
            print(f"[/api/db-stats] ERROR: {e}")
            try:
                sentry = get_sentry()
                sentry.capture_exception_nowait(
                    e, level="error", extra={"path": "/api/db-stats"}
                )
            except Exception:
                pass
            return Response.json({"ok": False, "error": str(e), "counts": {}})

    # ------------------------------------------------------------------ #
    #  GET /api/debug/db  →  raw database data for debugging             #
    # ------------------------------------------------------------------ #
    if pathname == "/api/debug/db" and method == "GET":
        try:
            # Check if user is logged in (only show debug to authenticated users)
            user = await get_current_user(env, request)
            if not user:
                return _json_response({"ok": False, "error": "Unauthorized"}, 401)

            counts = await get_db_table_counts(env)

            # Get sample data from each table
            users = _rows(
                await env.DB.prepare(
                    "SELECT id, slack_user_id, team_id, name, created_at FROM users LIMIT 5"
                ).all()
            )
            sessions = _rows(
                await env.DB.prepare(
                    "SELECT id, user_id, created_at, expires_at FROM sessions LIMIT 5"
                ).all()
            )
            workspaces = _rows(
                await env.DB.prepare(
                    "SELECT id, team_id, team_name, created_at FROM workspaces LIMIT 5"
                ).all()
            )

            return Response.json(
                {
                    "ok": True,
                    "counts": counts,
                    "samples": {
                        "users": users,
                        "sessions": sessions,
                        "workspaces": workspaces,
                    },
                    "current_user": {
                        "user_id": user.get("user_id"),
                        "slack_user_id": user.get("slack_user_id"),
                        "name": user.get("name"),
                    },
                }
            )
        except Exception as e:
            print(f"[/api/debug/db] ERROR: {e}")
            try:
                sentry = get_sentry()
                sentry.capture_exception_nowait(
                    e, level="error", extra={"path": "/api/debug/db"}
                )
            except Exception:
                pass
            return Response.json({"ok": False, "error": str(e)})

    # ------------------------------------------------------------------ #
    #  404 Not Found                                                     #
    # ------------------------------------------------------------------ #
    await report_404_to_sentry(env, pathname, method, "route_not_found")
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
                sentry.capture_exception_nowait(
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
            try:
                path = urlparse(request.url).path
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
