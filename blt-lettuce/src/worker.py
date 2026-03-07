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

from js import Headers, Response, fetch as js_fetch

try:
    from workers import WorkerEntrypoint
except ImportError:
    # Local tooling may not provide the workers runtime package.
    class WorkerEntrypoint:
        env = None

from lettuce.html_templates import (
    get_dashboard_html,
    get_homepage_html,
    get_login_page_html,
    html_escape,
)

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
        return dict(result)
    except Exception:
        return result


def _rows(result):
    """Safely convert a D1 multi-row result to a list of plain dicts."""
    if result is None:
        return []
    rows = getattr(result, "results", None)
    if rows is None:
        return []
    out = []
    for r in rows:
        try:
            out.append(dict(r))
        except Exception:
            out.append(r)
    return out


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
        existing = await db_get_workspace_by_team(env, team_id)
        if existing:
            await (
                env.DB.prepare(
                    "UPDATE workspaces SET team_name=?, access_token=?, bot_user_id=?, "
                    "updated_at=? WHERE team_id=?"
                )
                .bind(team_name, access_token, bot_user_id, now, team_id)
                .run()
            )
        else:
            await (
                env.DB.prepare(
                    "INSERT INTO workspaces "
                    "(team_id, team_name, access_token, bot_user_id, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)"
                )
                .bind(team_id, team_name, access_token, bot_user_id, now, now)
                .run()
            )
        return await db_get_workspace_by_team(env, team_id)
    except Exception:
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
    try:
        await (
            env.DB.prepare(
                "INSERT INTO user_workspaces (user_id, workspace_id, role, created_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(user_id, workspace_id) DO NOTHING"
            )
            .bind(user_id, workspace_id, role, now)
            .run()
        )
        return True
    except Exception:
        return False


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
        await (
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
        return True
    except Exception:
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
    try:
        existing = _row(
            await env.DB.prepare("SELECT * FROM users WHERE slack_user_id = ?")
            .bind(slack_user_id)
            .first()
        )
        if existing:
            await (
                env.DB.prepare(
                    "UPDATE users SET name=?, email=?, access_token=?, team_id=?, updated_at=? "
                    "WHERE slack_user_id=?"
                )
                .bind(name, email, access_token, team_id, now, slack_user_id)
                .run()
            )
        else:
            await (
                env.DB.prepare(
                    "INSERT INTO users "
                    "(slack_user_id, team_id, name, email, access_token, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)"
                )
                .bind(slack_user_id, team_id, name, email, access_token, now, now)
                .run()
            )
        return _row(
            await env.DB.prepare("SELECT * FROM users WHERE slack_user_id = ?")
            .bind(slack_user_id)
            .first()
        )
    except Exception:
        return None


async def db_create_session(env, user_id, token):
    now = get_utc_now()
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    try:
        await (
            env.DB.prepare(
                "INSERT INTO sessions (id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)"
            )
            .bind(token, user_id, now, expires)
            .run()
        )
        return True
    except Exception:
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
        resp = await js_fetch(
            "https://slack.com/api/oauth.v2.access",
            {
                "method": "POST",
                "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                "body": body,
            },
        )
        return await resp.json()
    except Exception:
        return {"ok": False, "error": "token_exchange_failed"}


async def fetch_user_identity(user_token):
    """Call identity.basic to get user profile from a user token."""
    try:
        resp = await js_fetch(
            "https://slack.com/api/users.identity",
            {
                "method": "GET",
                "headers": {"Authorization": f"Bearer {user_token}"},
            },
        )
        return await resp.json()
    except Exception:
        return {"ok": False}


# ===========================================================================
# Channel scanning
# ===========================================================================


async def scan_workspace_channels(env, workspace_id, access_token):
    """Scan all public channels in the workspace and persist them in D1."""
    scanned = 0
    cursor = None
    while True:
        url = "https://slack.com/api/conversations.list?limit=200&types=public_channel"
        if cursor:
            url += f"&cursor={cursor}"
        try:
            resp = await js_fetch(
                url,
                {
                    "method": "GET",
                    "headers": {"Authorization": f"Bearer {access_token}"},
                },
            )
            data = await resp.json()
            if not data.get("ok"):
                break
            for ch in data.get("channels", []):
                cid = ch.get("id", "")
                cname = ch.get("name", "")
                if cid and cname:
                    await db_upsert_channel(
                        env,
                        workspace_id,
                        cid,
                        cname,
                        ch.get("num_members", 0),
                        (ch.get("topic") or {}).get("value", ""),
                        (ch.get("purpose") or {}).get("value", ""),
                        1 if ch.get("is_private") else 0,
                    )
                    scanned += 1
            cursor = (data.get("response_metadata") or {}).get("next_cursor", "")
            if not cursor:
                break
        except Exception:
            break
    return scanned


# ===========================================================================
# Slack API helpers
# ===========================================================================


async def get_bot_user_id(env):
    slack_token = getattr(env, "SLACK_TOKEN", None)
    if not slack_token:
        return None
    try:
        resp = await js_fetch(
            "https://slack.com/api/auth.test",
            {"method": "POST", "headers": {"Authorization": f"Bearer {slack_token}"}},
        )
        result = await resp.json()
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
    resp = await js_fetch(
        "https://slack.com/api/chat.postMessage",
        {
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {slack_token}",
            },
            "body": json.dumps(payload),
        },
    )
    return await resp.json()


async def open_conversation(env, user_id, token=None):
    slack_token = token or getattr(env, "SLACK_TOKEN", None)
    if not slack_token:
        return {"ok": False, "error": "SLACK_TOKEN not configured"}
    resp = await js_fetch(
        "https://slack.com/api/conversations.open",
        {
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {slack_token}",
            },
            "body": json.dumps({"users": user_id}),
        },
    )
    return await resp.json()


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
    message_text = event.get("text", "").lower()
    user = event.get("user")
    channel = event.get("channel")
    channel_type = event.get("channel_type")
    subtype = event.get("subtype")

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
                    env, joins_channel, f"<@{user}> said {message_text}", token=ws_token
                )
            except Exception:
                pass
        # Use the event's channel ID (the DM channel), not the user ID
        result = await send_slack_message(
            env,
            channel,
            f"Hello <@{user}>, you said: {event.get('text', '')}",
            token=ws_token,
        )
        return {"ok": result.get("ok"), "action": "dm_response"}

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
    # Use a plain header dict for compatibility across Python Worker runtimes.
    h = {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }
    if extra_headers:
        for k, v in extra_headers.items():
            h[k] = v
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
    return Response.new(
        json.dumps(data),
        {"status": status, "headers": {"Content-Type": "application/json"}},
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
        authed_user = token_data.get("authed_user") or {}
        user_token = authed_user.get("access_token")
        user_slack_id = authed_user.get("id")

        user_name = ""
        user_email = ""
        user_team_id = (token_data.get("team") or {}).get("id", "")

        if user_token:
            identity = await fetch_user_identity(user_token)
            if identity.get("ok"):
                profile = identity.get("user") or {}
                team_info = identity.get("team") or {}
                user_name = profile.get("name", "")
                user_email = profile.get("email", "")
                if not user_team_id:
                    user_team_id = team_info.get("id", "")
                if not user_slack_id:
                    user_slack_id = profile.get("id", "")

        if not user_slack_id:
            sign_in_url = get_slack_sign_in_url(client_id or "", redirect_uri)
            return _html_response(
                get_login_page_html(
                    sign_in_url, error="Could not retrieve your Slack identity."
                ),
            )

        user = await db_get_or_create_user(
            env, user_slack_id, user_team_id, user_name, user_email, user_token or ""
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
            bot_token = token_data.get("access_token")
            team_info = token_data.get("team") or {}
            team_id = team_info.get("id", "")
            team_name = team_info.get("name", "Unknown Workspace")
            bot_user_id = token_data.get("bot_user_id") or ""

            if team_id and bot_token:
                ws = await db_upsert_workspace(
                    env, team_id, team_name, bot_token, bot_user_id
                )
                if ws:
                    await db_link_user_workspace(
                        env, user["id"], ws["id"], role="owner"
                    )
                    # Background channel scan (best-effort)
                    try:
                        await scan_workspace_channels(env, ws["id"], bot_token)
                    except Exception:
                        pass

        # ---- Create session ----
        token = generate_session_token()
        session_ok = await db_create_session(env, user["id"], token)
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
            user, workspaces, current_ws, ws_stats, channels, events, daily_stats, repos
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
            return _json_response(
                {"ok": False, "error": "Invalid workspace id"}, 400
            )

        if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
            return _json_response({"ok": False, "error": "Forbidden"}, 403)

        ws = await db_get_workspace_by_id(env, ws_id_val)
        if not ws:
            return _json_response(
                {"ok": False, "error": "Workspace not found"}, 404
            )

        scanned = await scan_workspace_channels(env, ws_id_val, ws["access_token"])
        return Response.json({"ok": True, "channels_scanned": scanned})

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
            return _json_response(
                {"ok": False, "error": "Invalid workspace id"}, 400
            )

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
                            gh_resp = await js_fetch(
                                api_url,
                                {
                                    "method": "GET",
                                    "headers": {"User-Agent": "BLT-Lettuce"},
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
            return _json_response(
                {"ok": False, "error": "Invalid workspace id"}, 400
            )

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
            return _json_response(
                {"ok": False, "error": "Invalid workspace id"}, 400
            )

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

        except Exception:
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
    #  Default API info response                                         #
    # ------------------------------------------------------------------ #
    return Response.json(
        {
            "message": "BLT-Lettuce Cloudflare Worker",
            "version": "2.0.0",
            "endpoints": {
                "GET /": "Homepage",
                "GET /login": "Sign in with Slack",
                "GET /callback": "OAuth callback",
                "GET /logout": "Sign out",
                "GET /dashboard": "Live stats dashboard (auth required)",
                "GET /workspace/add": "Add a new workspace (auth required)",
                "POST /webhook": "Slack event webhook",
                "GET /health": "Health check",
                "GET /api/ws/<id>/stats": "Workspace live stats (auth required)",
                "GET /api/ws/<id>/events": "Workspace events (auth required)",
                "POST /api/ws/<id>/scan": "Scan workspace channels (auth required)",
                "GET /api/ws/<id>/repos": "List repos (auth required)",
                "POST /api/ws/<id>/repos": "Add repo (auth required)",
                "DELETE /api/ws/<id>/repos/<repo_id>": "Remove repo (auth required)",
            },
        }
    )


class Default(WorkerEntrypoint):
    """Cloudflare Python Worker entrypoint class."""

    async def fetch(self, request):
        return await handle_request(request, self.env)

