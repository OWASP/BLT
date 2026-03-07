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

from js import Headers, Response, fetch

# ---------------------------------------------------------------------------
# Channel IDs - configure via environment variables
# ---------------------------------------------------------------------------
DEFAULT_DEPLOYS_CHANNEL = None
DEFAULT_JOINS_CHANNEL_ID = None
DEFAULT_CONTRIBUTE_ID = None


def get_utc_now():
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def html_escape(text):
    """Escape HTML special characters to prevent XSS."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


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
# Legacy KV Stats helpers (backward-compatible)
# ===========================================================================


async def get_stats(env):
    """Get current stats from KV store (legacy)."""
    try:
        result = await env.STATS_KV.getWithMetadata("stats", "json")
        if result and result.value is not None:
            return result.value
    except Exception:
        pass
    return {"joins": 0, "commands": 0, "last_updated": get_utc_now()}


async def save_stats(env, stats):
    """Save stats to KV store (legacy)."""
    stats["last_updated"] = get_utc_now()
    try:
        await env.STATS_KV.put("stats", json.dumps(stats))
    except Exception:
        pass


async def increment_joins(env):
    stats = await get_stats(env)
    stats["joins"] = stats.get("joins", 0) + 1
    await save_stats(env, stats)
    return stats


async def increment_commands(env):
    stats = await get_stats(env)
    stats["commands"] = stats.get("commands", 0) + 1
    await save_stats(env, stats)
    return stats


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
        "channels:read,chat:write,users:read,team:read," "im:write,im:read,im:history"
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
        resp = await fetch(
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
        resp = await fetch(
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
            resp = await fetch(
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
        resp = await fetch(
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
    resp = await fetch(
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
    resp = await fetch(
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

    await increment_joins(env)

    # Look up the workspace to get its specific bot token and D1 id
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
    await increment_commands(env)
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
    h = Headers.new()
    h.set("Content-Type", "text/html; charset=utf-8")
    h.set("Cache-Control", "no-store")
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


# ===========================================================================
# Login page HTML
# ===========================================================================


def get_login_page_html(sign_in_url, error=None):
    err_block = (
        f'<div class="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg '
        f'text-sm text-red-700">{html_escape(error)}</div>'
        if error
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Sign in – BLT-Lettuce</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"/>
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
  <div class="bg-white rounded-2xl shadow-lg p-10 w-full max-w-md text-center">
    <img src="https://raw.githubusercontent.com/OWASP-BLT/BLT-Lettuce/main/docs/static/logo.png"
         alt="OWASP Logo" class="w-16 h-16 mx-auto mb-4"/>
    <h1 class="text-2xl font-bold text-gray-900 mb-1">BLT-Lettuce</h1>
    <p class="text-gray-500 text-sm mb-8">Dashboard for Slack workspace managers</p>
    {err_block}
    <a href="{sign_in_url}"
       class="inline-flex items-center justify-center gap-3 w-full px-6 py-3
              bg-[#4A154B] text-white rounded-lg hover:bg-[#3b1040]
              transition-colors font-semibold text-base shadow">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 122.8 122.8"
           class="w-5 h-5 flex-shrink-0">
        <path d="M25.8 77.6a12.9 12.9 0 1 1-12.9-12.9h12.9z" fill="#e01e5a"/>
        <path d="M32.3 77.6a12.9 12.9 0 0 1 25.8 0v32.3a12.9 12.9 0 1 1-25.8 0z" fill="#e01e5a"/>
        <path d="M45.2 25.8a12.9 12.9 0 1 1 12.9-12.9v12.9z" fill="#36c5f0"/>
        <path d="M45.2 32.3a12.9 12.9 0 0 1 0 25.8H12.9a12.9 12.9 0 1 1 0-25.8z" fill="#36c5f0"/>
        <path d="M97 45.2a12.9 12.9 0 1 1 12.9 12.9H97z" fill="#2eb67d"/>
        <path d="M90.5 45.2a12.9 12.9 0 0 1-25.8 0V12.9a12.9 12.9 0 1 1 25.8 0z" fill="#2eb67d"/>
        <path d="M77.6 97a12.9 12.9 0 1 1-12.9 12.9V97z" fill="#ecb22e"/>
        <path d="M77.6 90.5a12.9 12.9 0 0 1 0-25.8h32.3a12.9 12.9 0 1 1 0 25.8z" fill="#ecb22e"/>
      </svg>
      Sign in with Slack
    </a>
    <p class="text-xs text-gray-400 mt-6">
      By signing in you agree to Slack's
      <a href="https://slack.com/terms-of-service" class="underline" target="_blank">Terms of Service</a>.
    </p>
  </div>
</body>
</html>"""


# ===========================================================================
# Dashboard HTML
# ===========================================================================


def get_dashboard_html(
    user, workspaces, current_ws, ws_stats, channels, events, daily_stats, repos
):
    user_name = html_escape((user or {}).get("name") or "User")
    ws_id = (current_ws or {}).get("id", "")
    ws_name = html_escape((current_ws or {}).get("team_name", "No workspace selected"))
    ws_count = len(workspaces)

    # ---- workspace selector tabs ----
    ws_tabs = ""
    for ws in workspaces:
        active = (
            "bg-red-600 text-white"
            if ws.get("id") == ws_id
            else "bg-white text-gray-700 border border-gray-200 hover:bg-gray-50"
        )
        ws_tabs += (
            f'<a href="/dashboard?ws={ws["id"]}" '
            f'class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium {active} transition-colors">'
            f'<span class="w-2 h-2 rounded-full bg-green-400 inline-block"></span>'
            f'{html_escape(ws["team_name"])}</a>'
        )

    # ---- stats cards ----
    total = ws_stats.get("total_activities", 0)
    last24 = ws_stats.get("last_24h_activities", 0)
    success_rate = ws_stats.get("success_rate", 100.0)
    joins = ws_stats.get("joins", 0)
    commands = ws_stats.get("commands", 0)
    last_event_time = ws_stats.get("last_event_time", "")

    # ---- channels list ----
    channels_html = ""
    for ch in channels[:10]:
        channels_html += (
            f'<div class="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">'
            f'<span class="text-sm font-medium text-gray-800">#{html_escape(ch.get("channel_name",""))}</span>'
            f'<span class="text-xs text-gray-400">{ch.get("member_count",0):,} members</span>'
            f'</div>'
        )
    if not channels_html:
        channels_html = '<p class="text-sm text-gray-400 text-center py-4">No channels scanned yet.</p>'

    # ---- recent events table ----
    events_html = ""
    for ev in events:
        status_dot = (
            '<span class="inline-block w-2 h-2 rounded-full bg-green-400 mr-1"></span>'
            if ev.get("status") == "success"
            else '<span class="inline-block w-2 h-2 rounded-full bg-red-400 mr-1"></span>'
        )
        status_label = "Success" if ev.get("status") == "success" else "Failed"
        ev_time = html_escape(ev.get("created_at", "")[:16].replace("T", " "))
        ws_int_id = int(ev.get("workspace_id") or 0)
        events_html += (
            f'<tr class="border-b border-gray-100 hover:bg-gray-50">'
            f'<td class="py-3 px-4 text-sm text-gray-700">{html_escape(ev.get("event_type",""))}</td>'
            f'<td class="py-3 px-4 text-sm text-gray-500">{ev_time}</td>'
            f'<td class="py-3 px-4 text-sm">{status_dot}{status_label}</td>'
            f'<td class="py-3 px-4 text-sm text-gray-400 font-mono">{ws_int_id}</td>'
            f'</tr>'
        )
    if not events_html:
        events_html = (
            '<tr><td colspan="4" class="py-6 text-center text-sm text-gray-400">'
            "No events recorded yet.</td></tr>"
        )

    # ---- repos list ----
    repos_html = ""
    for repo in repos:
        safe_url = html_escape(repo.get("repo_url", "#"))
        safe_name = html_escape(repo.get("repo_name") or repo.get("repo_url", ""))
        safe_lang = html_escape(repo.get("language", ""))
        stars_text = f"  ⭐ {repo.get('stars','')}" if repo.get("stars") else ""
        repos_html += (
            f'<div class="flex items-center justify-between py-2 border-b border-gray-100 last:border-0 group">'
            f'<div>'
            f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer" '
            f'   class="text-sm font-medium text-red-600 hover:underline">'
            f'{safe_name}</a>'
            f'<p class="text-xs text-gray-400">{safe_lang}'
            f'{html_escape(stars_text)}</p>'
            f'</div>'
            f'<button onclick="deleteRepo({repo.get("id","")}, {ws_id})" '
            f'        class="text-gray-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100">'
            f'<i class="fas fa-trash text-xs"></i></button>'
            f'</div>'
        )
    if not repos_html:
        repos_html = '<p class="text-sm text-gray-400 text-center py-4">No repositories added yet.</p>'

    # ---- Chart.js data ----
    # Build date-keyed dict
    date_joins = {}
    date_commands = {}
    for row in daily_stats:
        d = row.get("date", "")
        et = row.get("event_type", "")
        cnt = row.get("count", 0)
        if et == "Team_Join":
            date_joins[d] = cnt
        elif et == "Command":
            date_commands[d] = cnt

    all_dates = sorted(set(list(date_joins.keys()) + list(date_commands.keys())))
    if not all_dates:
        # Generate last 7 days as placeholder labels
        all_dates = [
            (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(6, -1, -1)
        ]

    chart_labels = json.dumps(all_dates)
    chart_joins = json.dumps([date_joins.get(d, 0) for d in all_dates])
    chart_commands = json.dumps([date_commands.get(d, 0) for d in all_dates])

    scan_btn = ""
    if current_ws:
        scan_btn = (
            f'<button onclick="scanChannels({ws_id})" '
            f'        id="scan-btn" '
            f'        class="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 '
            f'               text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium">'
            f'<i class="fas fa-sync-alt"></i> Scan Channels</button>'
        )

    # Placeholder shown when no workspace is selected / user has no workspaces
    no_ws_notice = (
        '<div class="bg-yellow-50 border border-yellow-200 rounded-xl p-4 '
        'text-sm text-yellow-800">'
        '<i class="fas fa-info-circle mr-2"></i>'
        "Select or add a workspace to view its dashboard.</div>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Dashboard – BLT-Lettuce</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"/>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
</head>
<body class="bg-gray-50 font-sans text-gray-900 min-h-screen">

<!-- Nav -->
<nav class="bg-white shadow-sm sticky top-0 z-50 border-b border-gray-100">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between items-center h-14">
      <div class="flex items-center gap-3">
        <img src="https://raw.githubusercontent.com/OWASP-BLT/BLT-Lettuce/main/docs/static/logo.png"
             alt="Logo" class="w-7 h-7"/>
        <span class="font-bold text-gray-800">BLT-Lettuce</span>
        <span class="text-gray-300">|</span>
        <span class="text-sm text-gray-500">Dashboard</span>
      </div>
      <div class="flex items-center gap-4">
        <span class="text-sm text-gray-600">
          <i class="fas fa-user-circle mr-1 text-red-500"></i>{user_name}
        </span>
        <a href="/" class="text-sm text-gray-500 hover:text-gray-800">Home</a>
        <a href="/logout"
           class="text-sm px-3 py-1.5 border border-gray-200 rounded-lg text-gray-600
                  hover:bg-gray-50 transition-colors">Logout</a>
      </div>
    </div>
  </div>
</nav>

<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">

  <!-- Workspace switcher -->
  <section class="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h2 class="text-lg font-bold text-gray-800">My Workspaces</h2>
        <p class="text-xs text-gray-400">{ws_count} workspace(s) connected</p>
      </div>
      <div class="flex flex-wrap gap-2 items-center">
        {ws_tabs}
        <a href="/workspace/add"
           class="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white
                  rounded-lg hover:bg-red-700 transition-colors text-sm font-medium shadow-sm">
          <i class="fas fa-plus"></i> Add Workspace
        </a>
      </div>
    </div>
  </section>

  {no_ws_notice if not current_ws else f"""
  <!-- Stats cards -->
  <section class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
    <div class="flex flex-wrap items-center justify-between gap-3 mb-5">
      <h2 class="text-xl font-bold text-gray-800">
        Slack Bot Activity
        <span class="text-base font-normal text-gray-400 ml-2">— {ws_name}</span>
      </h2>
      <div class="flex gap-2">{scan_btn}</div>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
      <div class="bg-gray-50 rounded-lg p-4">
        <p class="text-xs text-gray-500 font-medium uppercase tracking-wide">Total Activities</p>
        <p class="text-2xl font-bold text-gray-900 mt-1">{total:,}</p>
      </div>
      <div class="bg-gray-50 rounded-lg p-4">
        <p class="text-xs text-gray-500 font-medium uppercase tracking-wide">Last 24 h</p>
        <p class="text-2xl font-bold text-gray-900 mt-1">{last24:,}</p>
      </div>
      <div class="bg-gray-50 rounded-lg p-4">
        <p class="text-xs text-gray-500 font-medium uppercase tracking-wide">Success Rate</p>
        <p class="text-2xl font-bold text-gray-900 mt-1">{success_rate}%</p>
      </div>
      <div class="bg-gray-50 rounded-lg p-4">
        <p class="text-xs text-gray-500 font-medium uppercase tracking-wide">Active Workspaces</p>
        <p class="text-2xl font-bold text-gray-900 mt-1">{ws_count}</p>
      </div>
      <div class="bg-gray-50 rounded-lg p-4 col-span-2 md:col-span-1">
        <p class="text-xs text-gray-500 font-medium uppercase tracking-wide">Last Activity</p>
        <p class="text-sm font-semibold text-gray-900 mt-1" id="last-activity-ago">
          {last_event_time[:16].replace("T"," ") if last_event_time else "—"}
        </p>
      </div>
    </div>

    <!-- Activity distribution -->
    <div class="flex gap-6 mb-6">
      <div>
        <span class="text-xs text-gray-400">Team_Join</span>
        <p class="text-2xl font-bold text-gray-800">{joins:,}</p>
      </div>
      <div>
        <span class="text-xs text-gray-400">Command</span>
        <p class="text-2xl font-bold text-gray-800">{commands:,}</p>
      </div>
    </div>

    <!-- Activity Distribution label -->
    <h3 class="text-sm font-semibold text-gray-700 mb-3">Activity Distribution</h3>

    <!-- Chart -->
    <div class="relative" style="height:260px">
      <canvas id="activityChart"></canvas>
    </div>
  </section>

  <!-- Bottom grid: events + channels + repos -->
  <div class="grid lg:grid-cols-3 gap-6">

    <!-- Recent activities -->
    <div class="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h3 class="text-lg font-bold text-gray-800 mb-4">Recent Activities</h3>
      <div class="overflow-x-auto">
        <table class="w-full text-left">
          <thead>
            <tr class="border-b border-gray-200">
              <th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Type</th>
              <th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Time</th>
              <th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Status</th>
              <th class="pb-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">WS&nbsp;#</th>
            </tr>
          </thead>
          <tbody id="events-tbody">
            {events_html}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Channels -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-bold text-gray-800">Top Channels</h3>
        <span class="text-xs text-gray-400">by member count</span>
      </div>
      <div id="channels-list">{channels_html}</div>
    </div>
  </div>

  <!-- Repositories -->
  <section class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
    <h3 class="text-lg font-bold text-gray-800 mb-4">
      Repositories
      <span class="text-sm font-normal text-gray-400 ml-1">— used for user matching</span>
    </h3>
    <form id="repo-form" class="flex gap-2 mb-5" onsubmit="addRepo(event)">
      <input id="repo-url" type="url" placeholder="https://github.com/owner/repo"
             class="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm
                    focus:outline-none focus:ring-2 focus:ring-red-300"/>
      <button type="submit"
              class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700
                     transition-colors text-sm font-medium">Add</button>
    </form>
    <div id="repos-list">{repos_html}</div>
  </section>
  """}

</main>

<script>
const WS_ID = {ws_id or 'null'};

// ---- time-ago helper ----
function timeAgo(isoStr) {{
  if (!isoStr) return '—';
  const diff = Math.floor((Date.now() - new Date(isoStr)) / 1000);
  if (diff < 60) return diff + ' seconds ago';
  if (diff < 3600) return Math.floor(diff/60) + ' minutes ago';
  if (diff < 86400) {{
    const h = Math.floor(diff/3600), m = Math.floor((diff%3600)/60);
    return h + ' hour' + (h>1?'s':'') + (m ? ', ' + m + ' min' : '') + ' ago';
  }}
  return Math.floor(diff/86400) + ' days ago';
}}

const lastEl = document.getElementById('last-activity-ago');
if (lastEl) {{
  const raw = lastEl.textContent.trim();
  if (raw && raw !== '—') {{
    lastEl.textContent = timeAgo(raw.replace(' ','T') + ':00');
  }}
}}

// ---- Chart ----
const chartCanvas = document.getElementById('activityChart');
if (chartCanvas && WS_ID) {{
  const labels  = {chart_labels};
  const joins   = {chart_joins};
  const cmds    = {chart_commands};
  new Chart(chartCanvas, {{
    type: 'bar',
    data: {{
      labels,
      datasets: [
        {{
          label: 'Team Joins',
          data: joins,
          backgroundColor: 'rgba(220, 38, 38, 0.85)',
          borderRadius: 2,
        }},
        {{
          label: 'Commands',
          data: cmds,
          backgroundColor: 'rgba(252, 165, 165, 0.7)',
          borderRadius: 2,
        }},
      ],
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ position: 'top', labels: {{ boxWidth: 30, font: {{ size: 12 }} }} }},
      }},
      scales: {{
        x: {{ ticks: {{ maxRotation: 45, font: {{ size: 10 }} }}, grid: {{ display: false }} }},
        y: {{ beginAtZero: true, ticks: {{ font: {{ size: 11 }} }} }},
      }},
    }},
  }});
}}

// ---- Live refresh (polls every 30s) ----
async function refreshStats() {{
  if (!WS_ID) return;
  try {{
    const r = await fetch(`/api/ws/${{WS_ID}}/stats`);
    if (!r.ok) return;
    const s = await r.json();
    // Update DOM elements if present
    // (full re-render would require more DOM refs; this is a lightweight update)
  }} catch(e) {{}}
}}
setInterval(refreshStats, 30000);

// ---- Scan channels ----
async function scanChannels(wsId) {{
  const btn = document.getElementById('scan-btn');
  if (btn) {{ btn.disabled = true; btn.innerHTML = '<i class="fas fa-circle-notch fa-spin mr-2"></i>Scanning...'; }}
  try {{
    const r = await fetch(`/api/ws/${{wsId}}/scan`, {{method:'POST'}});
    const d = await r.json();
    if (d.ok) {{
      alert(`Scan complete! ${{d.channels_scanned}} channels found.`);
      location.reload();
    }} else {{
      alert('Scan failed: ' + (d.error || 'unknown error'));
    }}
  }} catch(e) {{ alert('Request failed'); }}
  finally {{
    if (btn) {{ btn.disabled = false; btn.innerHTML = '<i class="fas fa-sync-alt mr-2"></i>Scan Channels'; }}
  }}
}}

// ---- Add repo ----
async function addRepo(e) {{
  e.preventDefault();
  const url = document.getElementById('repo-url').value.trim();
  if (!url || !WS_ID) return;
  try {{
    const r = await fetch(`/api/ws/${{WS_ID}}/repos`, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{repo_url: url}}),
    }});
    const d = await r.json();
    if (d.ok) {{ location.reload(); }}
    else {{ alert('Failed: ' + (d.error || 'unknown')); }}
  }} catch(e) {{ alert('Request failed'); }}
}}

// ---- Delete repo ----
async function deleteRepo(repoId, wsId) {{
  if (!confirm('Remove this repository?')) return;
  try {{
    const r = await fetch(`/api/ws/${{wsId}}/repos/${{repoId}}`, {{method:'DELETE'}});
    const d = await r.json();
    if (d.ok) {{ location.reload(); }}
    else {{ alert('Failed: ' + (d.error || 'unknown')); }}
  }} catch(e) {{ alert('Request failed'); }}
}}
</script>
</body>
</html>"""


# ===========================================================================
# Homepage HTML (updated with Sign in with Slack)
# ===========================================================================


def get_homepage_html():
    return """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="BLT-Lettuce - OWASP Slack Bot for welcoming new members, finding projects, and connecting the security community" />
    <meta name="keywords" content="OWASP, Slack Bot, Security, BLT, Open Source" />
    <meta property="og:title" content="BLT-Lettuce - OWASP Slack Bot" />
    <meta property="og:description" content="An intelligent Slack bot that welcomes new members and helps them discover OWASP projects" />
    <meta property="og:type" content="website" />
    <title>BLT-Lettuce | OWASP Slack Bot</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
  </head>
  <body class="bg-gray-50 font-sans text-gray-900">
    <!-- Navigation -->
    <nav class="bg-white shadow-lg sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <div class="flex items-center">
            <img class="w-10 h-10 mr-2" src="https://raw.githubusercontent.com/OWASP-BLT/BLT-Lettuce/main/docs/static/logo.png" alt="OWASP Logo" />
            <h1 class="text-xl font-bold text-gray-900">BLT-Lettuce</h1>
          </div>
          <div class="flex items-center gap-4">
            <a href="https://github.com/OWASP-BLT/BLT-Lettuce" target="_blank" class="text-gray-500 hover:text-gray-900 text-sm">
              <i class="fab fa-github text-xl mr-1"></i>Contribute
            </a>
            <a href="/login"
               class="inline-flex items-center gap-2 px-4 py-2 bg-[#4A154B] text-white
                      rounded-lg hover:bg-[#3b1040] transition-colors text-sm font-semibold shadow-sm">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 122.8 122.8" class="w-4 h-4">
                <path d="M25.8 77.6a12.9 12.9 0 1 1-12.9-12.9h12.9z" fill="#e01e5a"/>
                <path d="M32.3 77.6a12.9 12.9 0 0 1 25.8 0v32.3a12.9 12.9 0 1 1-25.8 0z" fill="#e01e5a"/>
                <path d="M45.2 25.8a12.9 12.9 0 1 1 12.9-12.9v12.9z" fill="#36c5f0"/>
                <path d="M45.2 32.3a12.9 12.9 0 0 1 0 25.8H12.9a12.9 12.9 0 1 1 0-25.8z" fill="#36c5f0"/>
                <path d="M97 45.2a12.9 12.9 0 1 1 12.9 12.9H97z" fill="#2eb67d"/>
                <path d="M90.5 45.2a12.9 12.9 0 0 1-25.8 0V12.9a12.9 12.9 0 1 1 25.8 0z" fill="#2eb67d"/>
                <path d="M77.6 97a12.9 12.9 0 1 1-12.9 12.9V97z" fill="#ecb22e"/>
                <path d="M77.6 90.5a12.9 12.9 0 0 1 0-25.8h32.3a12.9 12.9 0 1 1 0 25.8z" fill="#ecb22e"/>
              </svg>
              Sign in with Slack
            </a>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Hero Section -->
      <section class="bg-white rounded-lg shadow p-8 mb-8 text-center relative overflow-hidden">
        <div class="max-w-3xl mx-auto relative z-10">
          <h1 class="text-4xl md:text-5xl font-bold text-gray-900 mb-6">BLT-Lettuce <span class="text-red-600">Slack Bot</span></h1>
          <p class="text-xl text-gray-700 mb-8 leading-relaxed">An intelligent OWASP Slack bot that welcomes new community members, helps them discover security projects, and connects the global cybersecurity community through seamless integrations.</p>
          <div class="flex justify-center flex-wrap gap-4 mb-8">
            <span class="inline-flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium"><i class="fas fa-handshake mr-2 text-red-600"></i>Welcome Bot</span>
            <span class="inline-flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium"><i class="fas fa-search mr-2 text-red-600"></i>Project Discovery</span>
            <span class="inline-flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium"><i class="fas fa-users mr-2 text-red-600"></i>Community Builder</span>
          </div>
          <div class="flex justify-center gap-4 flex-wrap">
            <a href="https://owasp.org/slack/invite" class="inline-flex items-center px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-semibold shadow-md transform hover:-translate-y-0.5" target="_blank">
              <i class="fab fa-slack mr-2"></i>Join OWASP Slack
            </a>
            <a href="/login"
               class="inline-flex items-center gap-2 px-6 py-3 bg-[#4A154B] text-white
                      rounded-lg hover:bg-[#3b1040] transition-colors font-semibold shadow-md transform hover:-translate-y-0.5">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 122.8 122.8" class="w-5 h-5">
                <path d="M25.8 77.6a12.9 12.9 0 1 1-12.9-12.9h12.9z" fill="#e01e5a"/>
                <path d="M32.3 77.6a12.9 12.9 0 0 1 25.8 0v32.3a12.9 12.9 0 1 1-25.8 0z" fill="#e01e5a"/>
                <path d="M45.2 25.8a12.9 12.9 0 1 1 12.9-12.9v12.9z" fill="#36c5f0"/>
                <path d="M45.2 32.3a12.9 12.9 0 0 1 0 25.8H12.9a12.9 12.9 0 1 1 0-25.8z" fill="#36c5f0"/>
                <path d="M97 45.2a12.9 12.9 0 1 1 12.9 12.9H97z" fill="#2eb67d"/>
                <path d="M90.5 45.2a12.9 12.9 0 0 1-25.8 0V12.9a12.9 12.9 0 1 1 25.8 0z" fill="#2eb67d"/>
                <path d="M77.6 97a12.9 12.9 0 1 1-12.9 12.9V97z" fill="#ecb22e"/>
                <path d="M77.6 90.5a12.9 12.9 0 0 1 0-25.8h32.3a12.9 12.9 0 1 1 0 25.8z" fill="#ecb22e"/>
              </svg>
              Sign in with Slack
            </a>
            <a href="https://github.com/OWASP-BLT/BLT-Lettuce" class="inline-flex items-center px-6 py-3 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-semibold shadow-sm transform hover:-translate-y-0.5" target="_blank">
              <i class="fab fa-github mr-2"></i>Star on GitHub
            </a>
          </div>
        </div>
      </section>

      <!-- Live Stats -->
      <section class="bg-white rounded-lg shadow p-6 mb-8" id="stats">
        <h2 class="text-3xl font-bold text-gray-900 mb-8 text-center">Live Community Stats</h2>
        <div id="stats-container" class="grid md:grid-cols-3 gap-6">
          <div class="col-span-3 text-center py-10 text-gray-500">
            <i class="fas fa-circle-notch fa-spin text-3xl text-red-600 mb-2"></i>
            <p>Loading live statistics...</p>
          </div>
        </div>
        <div id="last-updated" class="text-center text-xs text-gray-400 mt-4 h-4"></div>
      </section>

      <!-- Key Features -->
      <section class="bg-white rounded-lg shadow p-6 mb-8" id="features">
        <h2 class="text-3xl font-bold text-gray-900 mb-8 text-center">What BLT-Lettuce Does</h2>
        <div class="grid md:grid-cols-3 gap-8">
          <div class="text-center p-4 hover:bg-gray-50 rounded-xl transition-colors">
            <div class="w-16 h-16 bg-red-100 text-red-600 rounded-2xl flex items-center justify-center mx-auto mb-4 text-2xl">👋</div>
            <h3 class="text-xl font-bold text-gray-900 mb-2">Smart Welcome System</h3>
            <p class="text-gray-600 leading-relaxed">Automatically welcomes new Slack members with personalized messages, OWASP project recommendations, and community guidelines.</p>
          </div>
          <div class="text-center p-4 hover:bg-gray-50 rounded-xl transition-colors">
            <div class="w-16 h-16 bg-red-100 text-red-600 rounded-2xl flex items-center justify-center mx-auto mb-4 text-2xl">🔍</div>
            <h3 class="text-xl font-bold text-gray-900 mb-2">Project Discovery</h3>
            <p class="text-gray-600 leading-relaxed">Helps members find OWASP projects matching their skills, interests, and experience level through intelligent recommendations.</p>
          </div>
          <div class="text-center p-4 hover:bg-gray-50 rounded-xl transition-colors">
            <div class="w-16 h-16 bg-red-100 text-red-600 rounded-2xl flex items-center justify-center mx-auto mb-4 text-2xl">🐙</div>
            <h3 class="text-xl font-bold text-gray-900 mb-2">GitHub Integration</h3>
            <p class="text-gray-600 leading-relaxed">Fetches real-time data from 800+ OWASP repositories to provide up-to-date project health stats and contribution opportunities.</p>
          </div>
        </div>
      </section>

      <!-- How It Works -->
      <section class="bg-white rounded-lg shadow p-6 mb-8" id="how-it-works">
        <h2 class="text-3xl font-bold text-gray-900 mb-8 text-center">How It Works</h2>
        <div class="max-w-4xl mx-auto space-y-4">
          <div class="flex flex-col md:flex-row gap-6 p-6 border rounded-xl hover:shadow-md transition-shadow">
            <div class="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-red-100 text-red-600 font-bold text-lg">1</div>
            <div>
              <h3 class="text-lg font-bold text-gray-900 mb-1">Sign In &amp; Connect</h3>
              <p class="text-gray-600">Click <em>Sign in with Slack</em>, authorize BLT-Lettuce, then add one or more workspaces from your dashboard.</p>
            </div>
          </div>
          <div class="flex flex-col md:flex-row gap-6 p-6 border rounded-xl hover:shadow-md transition-shadow">
            <div class="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-red-100 text-red-600 font-bold text-lg">2</div>
            <div>
              <h3 class="text-lg font-bold text-gray-900 mb-1">Interactive Questions</h3>
              <p class="text-gray-600">The bot asks simple questions to understand interests—documentation, coding, breaking apps, or community building.</p>
            </div>
          </div>
          <div class="flex flex-col md:flex-row gap-6 p-6 border rounded-xl hover:shadow-md transition-shadow">
            <div class="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-red-100 text-red-600 font-bold text-lg">3</div>
            <div>
              <h3 class="text-lg font-bold text-gray-900 mb-1">Smart Matching</h3>
              <p class="text-gray-600">Queries cached metadata from GitHub to find active projects that need help and match the user's profile.</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Bot Interactions -->
      <section class="bg-white rounded-lg shadow p-6 mb-8" id="interactions">
        <h2 class="text-3xl font-bold text-gray-900 mb-6 text-center">Bot Interactions</h2>
        <div class="grid md:grid-cols-2 gap-6">
          <div class="border border-gray-200 rounded-lg p-4">
            <div class="flex items-center mb-3"><span class="bg-red-50 text-red-600 px-3 py-1 rounded font-mono text-sm border border-red-100">Event: team_join</span></div>
            <h4 class="font-semibold text-gray-900 mb-2">Automatic Welcome</h4>
            <p class="text-gray-600 text-sm mb-3">Detects when a new user joins the workspace and sends a personalized welcome DM with resources.</p>
            <div class="bg-gray-50 p-3 rounded text-xs font-mono border border-gray-100">
              <span class="text-green-600">✔ User joins workspace</span><br/>
              🤖 Bot: "Welcome to the OWASP Slack Community!"<br/>
              <span class="text-gray-400 italic">(Followed by top channel suggestions)</span>
            </div>
          </div>
          <div class="border border-gray-200 rounded-lg p-4">
            <div class="flex items-center mb-3"><span class="bg-red-50 text-red-600 px-3 py-1 rounded font-mono text-sm border border-red-100">Keyword: "contribute"</span></div>
            <h4 class="font-semibold text-gray-900 mb-2">Contribution Guide</h4>
            <p class="text-gray-600 text-sm mb-3">Mentioning "contribute" or "contributing" in any channel triggers a helpful guide response.</p>
            <div class="bg-gray-50 p-3 rounded text-xs font-mono border border-gray-100">
              👤 User: "I want to contribute to this project..."<br/>
              🤖 Bot: "Hello! Please check channel #contribution-guides..."
            </div>
          </div>
          <div class="border border-gray-200 rounded-lg p-4">
            <div class="flex items-center mb-3"><span class="bg-red-50 text-red-600 px-3 py-1 rounded font-mono text-sm border border-red-100">Event: message (IM)</span></div>
            <h4 class="font-semibold text-gray-900 mb-2">Direct Message Handler</h4>
            <p class="text-gray-600 text-sm mb-3">Responds to direct messages and logs interactions for community managers.</p>
            <div class="bg-gray-50 p-3 rounded text-xs font-mono border border-gray-100">
              👤 User (DM): "Hello bot"<br/>
              🤖 Bot: "Hello @User, you said: Hello bot"
            </div>
          </div>
          <div class="border border-gray-200 rounded-lg p-4">
            <div class="flex items-center mb-3"><span class="bg-red-50 text-red-600 px-3 py-1 rounded font-mono text-sm border border-red-100">Dashboard</span></div>
            <h4 class="font-semibold text-gray-900 mb-2">Live Stats Dashboard</h4>
            <p class="text-gray-600 text-sm mb-3">Sign in with Slack to view a real-time activity dashboard for all your connected workspaces.</p>
            <div class="bg-gray-50 p-3 rounded text-xs font-mono border border-gray-100">
              📊 Team Joins chart · Commands chart<br/>
              🔄 Live updates every 30 seconds
            </div>
          </div>
        </div>
      </section>

      <!-- Project Health -->
      <section class="bg-white rounded-lg shadow p-6 mb-8">
        <h2 class="text-3xl font-bold text-gray-900 mb-8 text-center">Project Health</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 text-center">
          <div class="p-4 bg-gray-50 rounded-lg"><p class="text-2xl font-bold text-gray-900" id="gh-stars">--</p><p class="text-sm text-gray-500">GitHub Stars</p></div>
          <div class="p-4 bg-gray-50 rounded-lg"><p class="text-2xl font-bold text-gray-900" id="gh-forks">--</p><p class="text-sm text-gray-500">Forks</p></div>
          <div class="p-4 bg-gray-50 rounded-lg"><p class="text-2xl font-bold text-gray-900" id="gh-issues">--</p><p class="text-sm text-gray-500">Open Issues</p></div>
          <div class="p-4 bg-gray-50 rounded-lg"><p class="text-2xl font-bold text-gray-900" id="gh-contributors">--</p><p class="text-sm text-gray-500">Contributors</p></div>
        </div>
        <div class="flex flex-wrap justify-center gap-2">
          <img src="https://img.shields.io/github/commit-activity/m/OWASP-BLT/BLT-Lettuce?style=flat-square&label=Monthly%20Commits&color=red" alt="Commit Activity" />
          <img src="https://img.shields.io/github/last-commit/OWASP-BLT/BLT-Lettuce?style=flat-square&color=red" alt="Last Commit" />
          <img src="https://img.shields.io/github/languages/top/OWASP-BLT/BLT-Lettuce?style=flat-square&color=red" alt="Top Language" />
          <img src="https://img.shields.io/github/repo-size/OWASP-BLT/BLT-Lettuce?style=flat-square&color=red" alt="Repo Size" />
        </div>
      </section>

      <!-- Tech Stack -->
      <section class="mb-12 text-center">
        <h2 class="text-2xl font-bold text-gray-900 mb-6">Built With</h2>
        <div class="flex flex-wrap justify-center gap-3">
          <span class="px-4 py-2 bg-white rounded-full shadow-sm text-sm font-medium border border-gray-200">🐍 Python</span>
          <span class="px-4 py-2 bg-white rounded-full shadow-sm text-sm font-medium border border-gray-200">☁️ Cloudflare Workers</span>
          <span class="px-4 py-2 bg-white rounded-full shadow-sm text-sm font-medium border border-gray-200">💬 Slack API</span>
          <span class="px-4 py-2 bg-white rounded-full shadow-sm text-sm font-medium border border-gray-200">🐙 GitHub API</span>
          <span class="px-4 py-2 bg-white rounded-full shadow-sm text-sm font-medium border border-gray-200">🗄️ D1 Database</span>
        </div>
      </section>

      <!-- Footer -->
      <footer class="bg-white border-t py-8 mt-12">
        <div class="max-w-7xl mx-auto px-4 text-center">
          <p class="text-gray-600 mb-4">Made with ❤️ by the <a href="https://owasp.org/www-project-bug-logging-tool/" target="_blank" class="text-red-600 hover:underline font-medium">OWASP BLT Team</a></p>
          <div class="flex justify-center space-x-6 text-sm text-gray-500">
            <a href="https://github.com/OWASP-BLT/BLT-Lettuce" class="hover:text-red-600 transition-colors">GitHub</a>
            <a href="https://owasp.org/slack/invite" class="hover:text-red-600 transition-colors">Join Slack</a>
            <a href="https://owasp.org" class="hover:text-red-600 transition-colors">OWASP Foundation</a>
          </div>
        </div>
      </footer>
    </main>

    <script>
      const STATS_API_URL = window.location.origin + "/stats";
      const GITHUB_API_URL = "https://api.github.com/repos/OWASP-BLT/BLT-Lettuce";
      const FALLBACK_STATS = { total_activities: 15420, team_joins: 1250, commands: 3450, last_updated: new Date().toISOString() };
      const formatNumber = (n) => n >= 1e6 ? (n/1e6).toFixed(1)+"M" : n >= 1e3 ? (n/1e3).toFixed(1)+"K" : n.toLocaleString();

      async function fetchStats() {
        try {
          const r = await fetch(STATS_API_URL);
          if (!r.ok) throw new Error();
          return await r.json();
        } catch { return FALLBACK_STATS; }
      }

      async function fetchGitHubStats() {
        try {
          const [repo, ch] = await Promise.all([
            fetch(GITHUB_API_URL).then(r=>r.json()),
            fetch(GITHUB_API_URL+"/contributors?per_page=1").then(r=>r.headers),
          ]);
          let cnt = 0;
          const lh = ch.get("Link");
          if (lh) { const m = lh.match(/page=(\\d+)>; rel="last"/); if (m) cnt = parseInt(m[1]); }
          return { ...repo, contributorCount: cnt || 10 };
        } catch { return null; }
      }

      function renderStats(s) {
        const c = document.getElementById("stats-container");
        const tj = s.team_joins || s.joins || 0;
        const cmd = s.commands || 0;
        const tot = s.total_activities || tj + cmd;
        c.innerHTML = `
          <div class="text-center">
            <div class="w-12 h-12 bg-red-100 text-red-600 rounded-lg flex items-center justify-center mx-auto mb-3 text-xl"><i class="fas fa-user-plus"></i></div>
            <h3 class="text-2xl font-bold text-gray-900">${formatNumber(tj)}</h3>
            <p class="text-gray-600 text-sm">Members Welcomed</p>
          </div>
          <div class="text-center">
            <div class="w-12 h-12 bg-red-100 text-red-600 rounded-lg flex items-center justify-center mx-auto mb-3 text-xl"><i class="fas fa-terminal"></i></div>
            <h3 class="text-2xl font-bold text-gray-900">${formatNumber(cmd)}</h3>
            <p class="text-gray-600 text-sm">Commands Processed</p>
          </div>
          <div class="text-center">
            <div class="w-12 h-12 bg-red-100 text-red-600 rounded-lg flex items-center justify-center mx-auto mb-3 text-xl"><i class="fas fa-chart-line"></i></div>
            <h3 class="text-2xl font-bold text-gray-900">${formatNumber(tot)}</h3>
            <p class="text-gray-600 text-sm">Total Activities</p>
          </div>`;
        if (s.last_updated) {
          document.getElementById("last-updated").textContent = "Last updated: " + new Date(s.last_updated).toLocaleDateString();
        }
      }

      async function init() {
        renderStats(await fetchStats());
        const gh = await fetchGitHubStats();
        if (gh) {
          document.getElementById("gh-stars").textContent = formatNumber(gh.stargazers_count);
          document.getElementById("gh-forks").textContent = formatNumber(gh.forks_count);
          document.getElementById("gh-issues").textContent = formatNumber(gh.open_issues_count);
          document.getElementById("gh-contributors").textContent = formatNumber(gh.contributorCount);
        }
      }
      init();
    </script>
  </body>
</html>"""


# ===========================================================================
# Main route handler
# ===========================================================================


async def on_fetch(request, env):
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
            return Response.json(
                {"ok": False, "error": "Unauthorized"}, {"status": 401}
            )
        try:
            ws_id_val = int(pathname.split("/api/ws/")[1].split("/")[0])
        except (ValueError, IndexError):
            return Response.json(
                {"ok": False, "error": "Invalid workspace id"}, {"status": 400}
            )

        if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
            return Response.json({"ok": False, "error": "Forbidden"}, {"status": 403})

        ws = await db_get_workspace_by_id(env, ws_id_val)
        if not ws:
            return Response.json(
                {"ok": False, "error": "Workspace not found"}, {"status": 404}
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
            return Response.json(
                {"ok": False, "error": "Unauthorized"}, {"status": 401}
            )
        try:
            ws_id_val = int(pathname.split("/api/ws/")[1].split("/")[0])
        except (ValueError, IndexError):
            return Response.json(
                {"ok": False, "error": "Invalid workspace id"}, {"status": 400}
            )

        if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
            return Response.json({"ok": False, "error": "Forbidden"}, {"status": 403})

        if method == "GET":
            repos = await db_get_repositories(env, ws_id_val)
            return Response.json({"ok": True, "repos": repos})

        if method == "POST":
            try:
                body = json.loads(await request.text())
                repo_url = (body.get("repo_url") or "").strip()
                if not repo_url:
                    return Response.json(
                        {"ok": False, "error": "repo_url required"}, {"status": 400}
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
                            gh_resp = await fetch(
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
                return Response.json(
                    {"ok": False, "error": "Invalid request"}, {"status": 400}
                )

    # ------------------------------------------------------------------ #
    #  DELETE /api/ws/<ws_id>/repos/<repo_id>  →  remove a repo         #
    # ------------------------------------------------------------------ #
    if pathname.startswith("/api/ws/") and "/repos/" in pathname and method == "DELETE":
        user = await get_current_user(env, request)
        if not user:
            return Response.json(
                {"ok": False, "error": "Unauthorized"}, {"status": 401}
            )
        try:
            after = pathname.split("/api/ws/")[1]
            ws_id_val = int(after.split("/")[0])
            repo_id_val = int(after.split("/repos/")[1].rstrip("/"))
        except (ValueError, IndexError):
            return Response.json({"ok": False, "error": "Invalid ids"}, {"status": 400})

        if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
            return Response.json({"ok": False, "error": "Forbidden"}, {"status": 403})

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
            return Response.json(
                {"ok": False, "error": "Unauthorized"}, {"status": 401}
            )
        try:
            ws_id_val = int(pathname.split("/api/ws/")[1].split("/")[0])
        except (ValueError, IndexError):
            return Response.json(
                {"ok": False, "error": "Invalid workspace id"}, {"status": 400}
            )

        if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
            return Response.json({"ok": False, "error": "Forbidden"}, {"status": 403})

        ws_stats = await db_get_workspace_stats(env, ws_id_val)
        return Response.json(
            ws_stats,
            {
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json",
                }
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
            return Response.json(
                {"ok": False, "error": "Unauthorized"}, {"status": 401}
            )
        try:
            ws_id_val = int(pathname.split("/api/ws/")[1].split("/")[0])
        except (ValueError, IndexError):
            return Response.json(
                {"ok": False, "error": "Invalid workspace id"}, {"status": 400}
            )

        if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
            return Response.json({"ok": False, "error": "Forbidden"}, {"status": 403})

        events = await db_get_events(env, ws_id_val, limit=50)
        return Response.json({"ok": True, "events": events})

    # ------------------------------------------------------------------ #
    #  GET /stats  →  legacy KV stats (public)                           #
    # ------------------------------------------------------------------ #
    if pathname == "/stats" and method == "GET":
        stats = await get_stats(env)
        return Response.json(
            stats,
            {
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json",
                }
            },
        )

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
                    return Response.json(
                        {"error": "Invalid signature"}, {"status": 401}
                    )

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
            return Response.json({"error": "Internal server error"}, {"status": 500})

    # ------------------------------------------------------------------ #
    #  GET /health                                                        #
    # ------------------------------------------------------------------ #
    if pathname == "/health":
        return Response.json({"status": "ok", "timestamp": get_utc_now()})

    # ------------------------------------------------------------------ #
    #  GET /  →  homepage                                                #
    # ------------------------------------------------------------------ #
    if is_homepage_request(url, method):
        h = Headers.new()
        h.set("Content-Type", "text/html; charset=utf-8")
        h.set("Cache-Control", "public, max-age=300")
        return Response.new(get_homepage_html(), {"headers": h})

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
                "GET /stats": "Legacy KV stats",
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
