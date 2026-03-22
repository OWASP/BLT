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
    get_homepage_html,
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


def get_blt_base_url(env):
    """Return canonical BLT base URL for links and branding."""
    base_url = str(getattr(env, "BASE_URL", "") or "").strip().rstrip("/")
    if not base_url:
        base_url = "https://lettuce.owaspblt.org"
    return base_url


def get_blt_logo_url(env):
    """Build logo URL from BASE_URL so verification is tied to deployment domain."""
    return f"{get_blt_base_url(env)}/docs/static/logo.png"


def build_blt_branding_block(env, channel="", user_id="", tracking_id=""):
    """Build a footer block that includes the BLT logo and homepage link.

    The logo URL includes cache-busting/tracking query params so image loads
    register a hit in the deployment logs.
    """
    tid = str(tracking_id or "").strip() or secrets.token_hex(12)
    tracking_query = urlencode(
        {
            "src": "slack",
            "tid": tid,
            "ts": int(datetime.now(timezone.utc).timestamp()),
            "ch": str(channel or "")[:80],
            "u": str(user_id or "")[:80],
        }
    )
    logo_url = f"{get_blt_base_url(env)}/logo-hit?{tracking_query}"
    return {
        "type": "context",
        "elements": [
            {"type": "image", "image_url": logo_url, "alt_text": "BLT-Lettuce"},
            {
                "type": "mrkdwn",
                "text": f"Sent by <{get_blt_base_url(env)}|BLT-Lettuce>",
            },
        ],
    }


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

    try:
        to_py = getattr(value, "to_py", None)
        if callable(to_py):
            return _js_to_python(to_py())
    except Exception:
        pass

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


async def db_update_workspace_icon(env, workspace_id, icon_url):
    """Persist a workspace icon URL."""
    try:
        await (
            env.DB.prepare(
                "UPDATE workspaces SET icon_url = ?, updated_at = ? WHERE id = ?"
            )
            .bind(icon_url or "", get_utc_now(), workspace_id)
            .run()
        )
        return True
    except Exception:
        return False


async def db_update_workspace_manifest(env, workspace_id, manifest_yaml):
    """Persist manifest YAML for a specific workspace/app entry."""
    now = get_utc_now()
    try:
        await (
            env.DB.prepare(
                "UPDATE workspaces SET manifest_yaml = ?, updated_at = ? WHERE id = ?"
            )
            .bind(str(manifest_yaml or ""), now, workspace_id)
            .run()
        )
        return True
    except Exception:
        return False


async def db_update_workspace_app_metadata(
    env, workspace_id, app_name="", app_icon_url="", app_id=""
):
    """Persist app metadata for a workspace/app row."""
    now = get_utc_now()
    try:
        await (
            env.DB.prepare(
                "UPDATE workspaces SET app_name = ?, app_icon_url = ?, app_id = ?, updated_at = ? WHERE id = ?"
            )
            .bind(
                str(app_name or ""),
                str(app_icon_url or ""),
                str(app_id or ""),
                now,
                workspace_id,
            )
            .run()
        )
        return True
    except Exception:
        return False


async def db_update_workspace_installer(
    env, workspace_id, installer_slack_user_id="", installer_name=""
):
    """Persist the Slack installer/admin identity on the workspace row."""
    now = get_utc_now()
    try:
        await (
            env.DB.prepare(
                "UPDATE workspaces SET installer_slack_user_id = ?, installer_name = ?, updated_at = ? WHERE id = ?"
            )
            .bind(
                str(installer_slack_user_id or ""),
                str(installer_name or ""),
                now,
                workspace_id,
            )
            .run()
        )
        return True
    except Exception:
        return False


async def db_update_workspace_channel_member_counts(
    env, workspace_id, channel_count=0, member_count=0
):
    """Persist cached workspace channel/member totals."""
    now = get_utc_now()
    try:
        await (
            env.DB.prepare(
                "UPDATE workspaces SET channel_count = ?, member_count = ?, updated_at = ? WHERE id = ?"
            )
            .bind(
                int(channel_count or 0),
                int(member_count or 0),
                now,
                workspace_id,
            )
            .run()
        )
        return True
    except Exception:
        # Older databases may not have the aggregate columns yet.
        return False


async def db_get_workspace_admin_identity(env, workspace):
    """Return the installer/admin Slack identity for a workspace."""
    ws = workspace or {}
    installer_slack_user_id = str(ws.get("installer_slack_user_id") or "").strip()
    installer_name = str(ws.get("installer_name") or "").strip()
    if installer_slack_user_id:
        return {
            "slack_user_id": installer_slack_user_id,
            "name": installer_name or installer_slack_user_id,
        }

    workspace_id = ws.get("id")
    if not workspace_id:
        return None

    installers = await db_get_workspace_installers(env, workspace_id)
    target = next(
        (row for row in installers if str(row.get("slack_user_id") or "").strip()),
        None,
    )
    if not target:
        return None

    installer_slack_user_id = str(target.get("slack_user_id") or "").strip()
    installer_name = str(target.get("name") or installer_slack_user_id).strip()
    if installer_slack_user_id:
        await db_update_workspace_installer(
            env,
            workspace_id,
            installer_slack_user_id=installer_slack_user_id,
            installer_name=installer_name,
        )
        return {
            "slack_user_id": installer_slack_user_id,
            "name": installer_name,
        }
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
    except Exception as e:
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
        return workspaces
    except Exception as e:
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


def _parse_iso_datetime(value):
    """Parse ISO timestamp strings into UTC-aware datetime values."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    normalized = raw.replace(" ", "T")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


async def db_get_workspaces_with_activity_markers(env):
    """Return workspaces with last non-alert activity and last inactivity alert time."""
    try:
        rows = _rows(
            await env.DB.prepare(
                "SELECT "
                "w.id, w.team_name, w.access_token, w.created_at, "
                "(SELECT MAX(e.created_at) FROM events e "
                " WHERE e.workspace_id = w.id AND e.event_type != 'Inactivity_Alert') AS last_activity_at, "
                "(SELECT MAX(e2.created_at) FROM events e2 "
                " WHERE e2.workspace_id = w.id AND e2.event_type = 'Inactivity_Alert') AS last_alert_at "
                "FROM workspaces w"
            ).all()
        )
        return rows
    except Exception:
        return []


async def run_inactivity_monitor(env):
    """Notify workspace installer/admin when no activity has been received for 1 day."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=1)
    checked = 0
    alerted = 0

    workspaces = await db_get_workspaces_with_activity_markers(env)
    for ws in workspaces:
        ws_id = ws.get("id")
        if not ws_id:
            continue
        checked += 1

        last_activity_dt = _parse_iso_datetime(
            ws.get("last_activity_at") or ws.get("created_at")
        )
        last_alert_dt = _parse_iso_datetime(ws.get("last_alert_at"))

        # Skip active workspaces.
        if last_activity_dt and last_activity_dt > cutoff:
            continue

        # Deduplicate: only one alert per inactivity period.
        if last_alert_dt and last_activity_dt and last_alert_dt >= last_activity_dt:
            continue

        alert_result = await send_inactivity_alert_for_workspace(
            env,
            ws,
            last_activity_at=(ws.get("last_activity_at") or ws.get("created_at")),
            is_test=False,
        )
        if alert_result.get("ok"):
            alerted += 1

    return {"checked": checked, "alerted": alerted}


async def send_inactivity_alert_for_workspace(
    env, ws, last_activity_at="", is_test=False
):
    """Send inactivity alert DM to installer/admin for a workspace."""
    ws_id = ws.get("id")
    if not ws_id:
        return {"ok": False, "error": "missing_workspace_id"}

    target_user = await db_get_workspace_admin_identity(env, ws)
    if not target_user:
        return {"ok": False, "error": "no_workspace_installer"}

    slack_user_id = str(target_user.get("slack_user_id") or "").strip()
    ws_token = ws.get("access_token") or getattr(env, "SLACK_TOKEN", None)
    if not ws_token:
        return {"ok": False, "error": "missing_workspace_token"}

    conv_result = await open_conversation(env, slack_user_id, token=ws_token)
    dm_channel = (
        (conv_result.get("channel") or {}).get("id")
        if isinstance(conv_result.get("channel"), dict)
        else conv_result.get("channel")
    )
    if not conv_result.get("ok") or not dm_channel:
        return {
            "ok": False,
            "error": conv_result.get("error") or "dm_open_failed",
        }

    dashboard_link = f"{get_blt_base_url(env)}/dashboard?ws={ws_id}&tab=overview"
    ws_name = ws.get("team_name") or f"Workspace {ws_id}"
    prefix = ":test_tube: *Test Inactivity Alert*\n" if is_test else ""
    msg = (
        f"{prefix}:warning: No activity received in one day for *{ws_name}*.\n"
        f"Open dashboard: {dashboard_link}"
    )
    send_result = await send_slack_message(env, dm_channel, msg, token=ws_token)
    if send_result.get("ok"):
        await db_log_event(
            env,
            ws_id,
            "Inactivity_Alert",
            slack_user_id,
            "success",
            channel_name="Direct Message",
            request_data=json.dumps(
                {
                    "workspace_id": ws_id,
                    "workspace_name": ws_name,
                    "last_activity_at": last_activity_at,
                    "dashboard_link": dashboard_link,
                    "is_test": bool(is_test),
                }
            ),
            verified=True,
        )
        return {"ok": True}

    await db_log_event(
        env,
        ws_id,
        "Inactivity_Alert",
        slack_user_id,
        "failed",
        channel_name="Direct Message",
        request_data=json.dumps(
            {
                "workspace_id": ws_id,
                "workspace_name": ws_name,
                "error": send_result.get("error") or "send_failed",
                "is_test": bool(is_test),
            }
        ),
        verified=False,
    )
    return {"ok": False, "error": send_result.get("error") or "send_failed"}


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
    except Exception as e:
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


async def db_get_channel_by_slack_id(env, workspace_id, channel_id):
    """Return a channel row by workspace and Slack channel ID."""
    try:
        return _row(
            await env.DB.prepare(
                "SELECT * FROM channels WHERE workspace_id = ? AND channel_id = ?"
            )
            .bind(workspace_id, channel_id)
            .first()
        )
    except Exception:
        return None


async def db_update_channel_join_config(
    env, workspace_id, channel_id, join_message_id, join_delivery_mode="dm"
):
    """Update per-channel join message template selection.

    Sending is enabled whenever join_message_id is set, disabled when NULL.
    """
    try:
        send_join_message = 1 if join_message_id else 0
        await (
            env.DB.prepare(
                "UPDATE channels SET send_join_message = ?, join_message_id = ?, join_delivery_mode = ?, updated_at = ? "
                "WHERE workspace_id = ? AND channel_id = ?"
            )
            .bind(
                1 if send_join_message else 0,
                join_message_id,
                join_delivery_mode,
                get_utc_now(),
                workspace_id,
                channel_id,
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
                    "context": "db_update_channel_join_config",
                    "workspace_id": workspace_id,
                    "channel_id": channel_id,
                    "join_message_id": join_message_id,
                    "join_delivery_mode": join_delivery_mode,
                },
            )
        except Exception:
            pass
        return False


async def db_get_channel_join_message_sent_counts(env, workspace_id):
    """Return a map of channel_id -> successful Channel_Join_Message send count."""
    try:
        rows = _rows(
            await env.DB.prepare(
                "SELECT request_data FROM events "
                "WHERE workspace_id = ? AND event_type = 'Channel_Join_Message' AND status = 'success' "
                "ORDER BY id DESC LIMIT 10000"
            )
            .bind(workspace_id)
            .all()
        )
        counts = {}
        for row in rows:
            try:
                payload = json.loads(row.get("request_data") or "{}")
            except Exception:
                payload = {}
            channel_id = str(payload.get("channel") or "").strip()
            if not channel_id:
                continue
            counts[channel_id] = counts.get(channel_id, 0) + 1
        return counts
    except Exception:
        return {}


async def db_mark_join_message_verified_by_tracking(
    env, tracking_id, ip_address, user_agent
):
    """Mark the latest tracked Channel_Join_Message event as verified with hit metadata."""
    tid = str(tracking_id or "").strip()
    if not tid:
        return False
    try:
        row = _row(
            await env.DB.prepare(
                "SELECT id, request_data FROM events "
                "WHERE event_type = 'Channel_Join_Message' "
                "AND request_data LIKE ? "
                "ORDER BY id DESC LIMIT 1"
            )
            .bind(f'%"logo_tracking_id": "{tid}"%')
            .first()
        )
        if not row:
            return False

        payload = {}
        try:
            payload = json.loads(row.get("request_data") or "{}")
            if not isinstance(payload, dict):
                payload = {}
        except Exception:
            payload = {}

        payload["verification_ip"] = str(ip_address or "")
        payload["verification_user_agent"] = str(user_agent or "")[:512]
        payload["verified_at"] = get_utc_now()

        await (
            env.DB.prepare(
                "UPDATE events SET request_data = ?, verified = 1 WHERE id = ?"
            )
            .bind(json.dumps(payload), int(row.get("id") or 0))
            .run()
        )
        return True
    except Exception:
        return False


async def db_get_join_messages(env, workspace_id):
    """List saved join message templates for a workspace."""
    try:
        return _rows(
            await env.DB.prepare(
                "SELECT * FROM join_messages WHERE workspace_id = ? "
                "ORDER BY created_at DESC"
            )
            .bind(workspace_id)
            .all()
        )
    except Exception:
        return []


async def db_get_join_message_by_id(env, workspace_id, message_id):
    """Fetch one join message template by id."""
    try:
        return _row(
            await env.DB.prepare(
                "SELECT * FROM join_messages WHERE id = ? AND workspace_id = ?"
            )
            .bind(message_id, workspace_id)
            .first()
        )
    except Exception:
        return None


async def db_add_join_message(env, workspace_id, name, message_text):
    """Create a join message template."""
    now = get_utc_now()
    try:
        await (
            env.DB.prepare(
                "INSERT INTO join_messages "
                "(workspace_id, name, message_text, is_active, created_at, updated_at) "
                "VALUES (?, ?, ?, 1, ?, ?)"
            )
            .bind(workspace_id, name, message_text, now, now)
            .run()
        )
        return True
    except Exception:
        return False


async def db_delete_join_message(env, workspace_id, message_id):
    """Delete a join message template and unset channel references."""
    try:
        await (
            env.DB.prepare(
                "UPDATE channels SET join_message_id = NULL, send_join_message = 0, updated_at = ? "
                "WHERE workspace_id = ? AND join_message_id = ?"
            )
            .bind(get_utc_now(), workspace_id, message_id)
            .run()
        )
        await (
            env.DB.prepare(
                "DELETE FROM join_messages WHERE id = ? AND workspace_id = ?"
            )
            .bind(message_id, workspace_id)
            .run()
        )
        return True
    except Exception:
        return False


# ===========================================================================
# D1 — User & Session helpers
# ===========================================================================


async def db_get_or_create_user(
    env, slack_user_id, team_id, name, email, access_token, avatar_url=""
):
    now = get_utc_now()
    try:
        # Ensure required columns are never NULL for inserts/updates.
        slack_user_id = slack_user_id or ""
        team_id = team_id or "unknown"
        name = name or ""
        email = email or ""
        access_token = access_token or ""
        avatar_url = avatar_url or ""

        if not slack_user_id:
            return None

        existing = _row(
            await env.DB.prepare("SELECT * FROM users WHERE slack_user_id = ?")
            .bind(slack_user_id)
            .first()
        )
        if existing:
            # Preserve existing name when the caller provides no name (e.g. identity
            # fetch failed), so we never overwrite a real display name with an empty
            # string or the raw Slack user ID.
            # Fallback precedence: new name → existing DB name → slack_user_id
            existing_name = existing.get("name") or ""
            effective_name = name or existing_name or slack_user_id
            await (
                env.DB.prepare(
                    "UPDATE users SET name=?, email=?, access_token=?, avatar_url=?, team_id=?, updated_at=? "
                    "WHERE slack_user_id=?"
                )
                .bind(
                    effective_name,
                    email,
                    access_token,
                    avatar_url,
                    team_id,
                    now,
                    slack_user_id,
                )
                .run()
            )
        else:
            # For new users, fall back to slack_user_id when no display name is available.
            insert_name = name or slack_user_id
            await (
                env.DB.prepare(
                    "INSERT INTO users "
                    "(slack_user_id, team_id, name, email, access_token, avatar_url, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                )
                .bind(
                    slack_user_id,
                    team_id,
                    insert_name,
                    email,
                    access_token,
                    avatar_url,
                    now,
                    now,
                )
                .run()
            )
        user = _row(
            await env.DB.prepare("SELECT * FROM users WHERE slack_user_id = ?")
            .bind(slack_user_id)
            .first()
        )
        return user
    except Exception as e:
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
    try:
        await (
            env.DB.prepare(
                "INSERT INTO sessions (id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)"
            )
            .bind(token, user_id, now, expires)
            .run()
        )
        return token
    except Exception as e:
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
    env,
    workspace_id,
    repo_url,
    repo_name="",
    description="",
    language="",
    stars=0,
    source_type="repo",
    metadata_json="",
):
    now = get_utc_now()
    try:
        await (
            env.DB.prepare(
                "INSERT INTO repositories "
                "(workspace_id, repo_url, repo_name, description, language, stars, source_type, metadata_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(workspace_id, repo_url) DO UPDATE SET "
                "repo_name=excluded.repo_name, description=excluded.description, "
                "language=excluded.language, stars=excluded.stars, "
                "source_type=excluded.source_type, metadata_json=excluded.metadata_json"
            )
            .bind(
                workspace_id,
                repo_url,
                repo_name,
                description,
                language,
                stars,
                source_type,
                metadata_json,
                now,
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


async def db_delete_workspace(env, workspace_id):
    """Delete a workspace and all dependent workspace-scoped records."""
    try:
        # Delete children first because FKs are not configured with cascade.
        try:
            await (
                env.DB.prepare("DELETE FROM events WHERE workspace_id = ?")
                .bind(workspace_id)
                .run()
            )
        except Exception as e:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="warning",
                extra={
                    "context": "db_delete_workspace/events",
                    "workspace_id": workspace_id,
                },
            )

        try:
            await (
                env.DB.prepare("DELETE FROM channels WHERE workspace_id = ?")
                .bind(workspace_id)
                .run()
            )
        except Exception as e:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="warning",
                extra={
                    "context": "db_delete_workspace/channels",
                    "workspace_id": workspace_id,
                },
            )

        try:
            await (
                env.DB.prepare("DELETE FROM repositories WHERE workspace_id = ?")
                .bind(workspace_id)
                .run()
            )
        except Exception as e:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="warning",
                extra={
                    "context": "db_delete_workspace/repositories",
                    "workspace_id": workspace_id,
                },
            )

        try:
            await (
                env.DB.prepare(
                    "DELETE FROM github_organizations WHERE workspace_id = ?"
                )
                .bind(workspace_id)
                .run()
            )
        except Exception as e:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="warning",
                extra={
                    "context": "db_delete_workspace/github_organizations",
                    "workspace_id": workspace_id,
                },
            )

        try:
            await (
                env.DB.prepare("DELETE FROM join_messages WHERE workspace_id = ?")
                .bind(workspace_id)
                .run()
            )
        except Exception as e:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="warning",
                extra={
                    "context": "db_delete_workspace/join_messages",
                    "workspace_id": workspace_id,
                },
            )

        await (
            env.DB.prepare("DELETE FROM workspaces WHERE id = ?")
            .bind(workspace_id)
            .run()
        )
        return True
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={"context": "db_delete_workspace", "workspace_id": workspace_id},
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


async def db_upsert_github_organization(
    env,
    workspace_id,
    org_login,
    org_type="org",
    metadata_json="",
):
    """Persist a GitHub org/user source linked to a workspace."""
    now = get_utc_now()
    try:
        await (
            env.DB.prepare(
                "INSERT INTO github_organizations "
                "(workspace_id, org_login, org_type, metadata_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(workspace_id, org_login) DO UPDATE SET "
                "org_type=excluded.org_type, metadata_json=excluded.metadata_json, "
                "updated_at=excluded.updated_at"
            )
            .bind(
                workspace_id,
                str(org_login or "").strip(),
                str(org_type or "org").strip() or "org",
                str(metadata_json or ""),
                now,
                now,
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
                    "context": "db_upsert_github_organization",
                    "workspace_id": workspace_id,
                    "org_login": org_login,
                },
            )
        except Exception:
            pass
        return False


def _extract_github_target(repo_url):
    """Return {'kind': 'repo'|'org', ...} for GitHub URLs, else None."""
    try:
        parsed = urlparse(str(repo_url or "").strip())
        if parsed.netloc not in ("github.com", "www.github.com"):
            return None
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if not parts:
            return None
        if len(parts) == 1:
            return {"kind": "org", "org": parts[0]}
        owner = parts[0]
        repo_slug = parts[1].replace(".git", "")
        return {"kind": "repo", "owner": owner, "repo": repo_slug}
    except Exception:
        return None


async def _fetch_github_json(url):
    """GET GitHub API JSON with required headers and safe conversion."""
    try:
        gh_headers = Headers.new()
        gh_headers.set("User-Agent", "BLT-Lettuce")
        gh_headers.set("Accept", "application/vnd.github+json")
        resp = await js_fetch(
            url,
            {
                "method": "GET",
                "headers": gh_headers,
            },
        )
        return _js_to_python(await resp.json())
    except Exception:
        return {}


def _repo_metadata_from_github(repo_data, source_type="repo", org_login=""):
    """Normalize GitHub API repo payload into db fields and metadata."""
    owner_obj = repo_data.get("owner") if isinstance(repo_data, dict) else {}
    owner_login = (owner_obj.get("login") if isinstance(owner_obj, dict) else "") or ""
    repo_name = str(repo_data.get("name") or "")
    html_url = str(repo_data.get("html_url") or "")
    full_name = str(repo_data.get("full_name") or "")
    description = str(repo_data.get("description") or "")
    language = str(repo_data.get("language") or "")
    stars = int(repo_data.get("stargazers_count") or 0)

    metadata = {
        "source_type": source_type,
        "org_login": org_login or owner_login,
        "full_name": full_name,
        "owner_login": owner_login,
        "topics": repo_data.get("topics") or [],
        "forks": int(repo_data.get("forks_count") or 0),
        "watchers": int(repo_data.get("watchers_count") or 0),
        "open_issues": int(repo_data.get("open_issues_count") or 0),
        "default_branch": repo_data.get("default_branch") or "",
        "visibility": repo_data.get("visibility") or "",
        "is_private": bool(repo_data.get("private")),
        "is_archived": bool(repo_data.get("archived")),
        "created_at": repo_data.get("created_at") or "",
        "updated_at": repo_data.get("updated_at") or "",
        "pushed_at": repo_data.get("pushed_at") or "",
        "license": (
            (repo_data.get("license") or {}).get("spdx_id")
            if isinstance(repo_data.get("license"), dict)
            else ""
        )
        or "",
    }
    return {
        "repo_url": html_url,
        "repo_name": repo_name,
        "description": description,
        "language": language,
        "stars": stars,
        "source_type": source_type,
        "metadata_json": json.dumps(metadata),
    }


async def _import_github_org_repositories(env, workspace_id, org_login, max_repos=150):
    """Import repositories for a GitHub organization/user URL."""
    org_login = str(org_login or "").strip()
    if not org_login:
        return {"imported": 0, "failed": 0, "organization": "", "org_type": "org"}

    imported = 0
    failed = 0
    page = 1
    per_page = 100
    org_type = "org"

    org_profile = await _fetch_github_json(f"https://api.github.com/orgs/{org_login}")
    if isinstance(org_profile, dict) and org_profile.get("message") == "Not Found":
        org_type = "user"
        org_profile = await _fetch_github_json(
            f"https://api.github.com/users/{org_login}"
        )

    if isinstance(org_profile, dict) and org_profile.get("login"):
        org_login = str(org_profile.get("login") or org_login)

    while imported + failed < max_repos:
        api_url = f"https://api.github.com/orgs/{org_login}/repos?per_page={per_page}&page={page}&type=all"
        data = await _fetch_github_json(api_url)

        # Fallback for user account URLs that are not orgs.
        if isinstance(data, dict) and data.get("message") == "Not Found":
            api_url = f"https://api.github.com/users/{org_login}/repos?per_page={per_page}&page={page}&type=owner"
            data = await _fetch_github_json(api_url)

        repos = data if isinstance(data, list) else []
        if not repos:
            break

        for item in repos:
            if imported + failed >= max_repos:
                break
            if not isinstance(item, dict):
                failed += 1
                continue

            normalized = _repo_metadata_from_github(
                item,
                source_type="org",
                org_login=org_login,
            )
            ok = await db_add_repository(
                env,
                workspace_id,
                normalized["repo_url"],
                normalized["repo_name"],
                normalized["description"],
                normalized["language"],
                normalized["stars"],
                source_type=normalized["source_type"],
                metadata_json=normalized["metadata_json"],
            )
            if ok:
                imported += 1
            else:
                failed += 1

        if len(repos) < per_page:
            break
        page += 1

    public_repos = 0
    followers = 0
    if isinstance(org_profile, dict):
        try:
            public_repos = int(org_profile.get("public_repos") or 0)
        except Exception:
            public_repos = 0
        try:
            followers = int(org_profile.get("followers") or 0)
        except Exception:
            followers = 0

    org_metadata = {
        "login": org_login,
        "type": org_type,
        "name": org_profile.get("name") if isinstance(org_profile, dict) else "",
        "avatar_url": (
            org_profile.get("avatar_url") if isinstance(org_profile, dict) else ""
        ),
        "html_url": (
            org_profile.get("html_url") if isinstance(org_profile, dict) else ""
        ),
        "public_repos": public_repos,
        "followers": followers,
        "repos_imported": imported,
        "repos_failed": failed,
        "last_imported_at": get_utc_now(),
    }
    await db_upsert_github_organization(
        env,
        workspace_id,
        org_login,
        org_type=org_type,
        metadata_json=json.dumps(org_metadata),
    )

    return {
        "imported": imported,
        "failed": failed,
        "organization": org_login,
        "org_type": org_type,
    }


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
    request_data="",
    verified=0,
):
    now = get_utc_now()
    try:
        await (
            env.DB.prepare(
                "INSERT INTO events (workspace_id, event_type, user_slack_id, channel_name, request_data, verified, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            )
            .bind(
                workspace_id,
                event_type,
                user_slack_id,
                channel_name,
                request_data,
                1 if verified else 0,
                status,
                now,
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
    request_data="",
    verified=0,
):
    """Insert a single event row with an explicit timestamp when provided."""
    event_time = created_at or get_utc_now()
    try:
        await (
            env.DB.prepare(
                "INSERT INTO events (workspace_id, event_type, user_slack_id, channel_name, request_data, verified, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            )
            .bind(
                workspace_id,
                event_type,
                user_slack_id,
                channel_name,
                request_data,
                1 if verified else 0,
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
        request_data = (normalized_row.get("request_data") or "").strip()
        verified_raw = str(normalized_row.get("verified") or "").strip().lower()
        verified = verified_raw in ("1", "true", "yes", "y", "verified")
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
            request_data=request_data,
            verified=verified,
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
                "SELECT e.*, e.user_slack_id AS user_name "
                "FROM events e "
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


async def db_list_workspaces_public(env):
    """Return all workspaces with public stats (no access tokens)."""
    try:
        rows = _rows(
            await env.DB.prepare(
                "SELECT "
                "w.id, w.team_name, w.icon_url, w.created_at, "
                "(SELECT COUNT(*) FROM events e WHERE e.workspace_id = w.id) AS total_activities, "
                "(SELECT COUNT(*) FROM events e WHERE e.workspace_id = w.id AND e.event_type = 'Team_Join') AS joins, "
                "(SELECT MAX(e2.created_at) FROM events e2 WHERE e2.workspace_id = w.id) AS last_event_time, "
                "(SELECT COUNT(*) FROM repositories r WHERE r.workspace_id = w.id) AS repo_count, "
                "(SELECT COUNT(*) FROM channels c WHERE c.workspace_id = w.id) AS channel_count, "
                "(SELECT SUM(c.member_count) FROM channels c WHERE c.workspace_id = w.id) AS member_count "
                "FROM workspaces w ORDER BY w.created_at DESC"
            ).all()
        )

        if not rows:
            return []

        # Attach a 7-day activity timeline to each workspace for homepage charts.
        since = (datetime.now(timezone.utc) - timedelta(days=6)).isoformat()
        timeline_rows = _rows(
            await env.DB.prepare(
                "SELECT workspace_id, substr(created_at, 1, 10) AS day, COUNT(*) AS count "
                "FROM events WHERE workspace_id IS NOT NULL AND created_at >= ? "
                "GROUP BY workspace_id, day"
            )
            .bind(since)
            .all()
        )

        day_labels = [
            (datetime.now(timezone.utc) - timedelta(days=offset)).strftime("%Y-%m-%d")
            for offset in range(6, -1, -1)
        ]

        timeline_by_workspace = {}
        for row in timeline_rows:
            ws_id = int(row.get("workspace_id") or 0)
            if not ws_id:
                continue
            day = str(row.get("day") or "")
            count = int(row.get("count") or 0)
            if ws_id not in timeline_by_workspace:
                timeline_by_workspace[ws_id] = {}
            timeline_by_workspace[ws_id][day] = count

        for ws in rows:
            ws_id = int(ws.get("id") or 0)
            day_counts = timeline_by_workspace.get(ws_id, {})
            ws["activity_timeline"] = [
                int(day_counts.get(day, 0)) for day in day_labels
            ]
            # Normalize nulls to 0 for channel/member counts
            ws["channel_count"] = ws.get("channel_count") or 0
            ws["member_count"] = ws.get("member_count") or 0

        return rows
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
    tables = [
        "workspaces",
        "channels",
        "repositories",
        "events",
        "github_organizations",
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
        except Exception as e:
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
        ("workspaces", "Workspaces"),
        ("channels", "Channels"),
        ("repositories", "Repositories"),
        ("events", "Events"),
        ("github_organizations", "GitHub Orgs"),
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


def _create_quick_response_blocks(message_text):
    """Create blocks that include message text and quick action buttons."""
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": message_text},
        },
        *_create_quick_action_buttons(),
    ]


# ==========================================================================
# D1 - Workspace helpers
# ==========================================================================

WELCOME_MESSAGE = (
    "Hello <@{user_id}>! Welcome to the OWASP Slack Community. "
    "We are glad you are here."
)


async def db_get_workspace_by_team(env, team_id):
    """Return the newest workspace row for a Slack team ID."""
    try:
        return _row(
            await env.DB.prepare(
                "SELECT * FROM workspaces WHERE team_id = ? "
                "ORDER BY updated_at DESC, id DESC LIMIT 1"
            )
            .bind(str(team_id or ""))
            .first()
        )
    except Exception:
        return None


async def db_get_workspace_by_id(env, workspace_id):
    """Return one workspace row by primary key ID."""
    try:
        return _row(
            await env.DB.prepare("SELECT * FROM workspaces WHERE id = ?")
            .bind(workspace_id)
            .first()
        )
    except Exception:
        return None


async def db_get_workspace_by_team_and_app(env, team_id, app_id):
    """Return workspace by team/app pair, or latest team workspace when app ID is empty."""
    team_id = str(team_id or "").strip()
    app_id = str(app_id or "").strip()
    if not team_id:
        return None

    try:
        if app_id:
            row = _row(
                await env.DB.prepare(
                    "SELECT * FROM workspaces WHERE team_id = ? AND app_id = ? LIMIT 1"
                )
                .bind(team_id, app_id)
                .first()
            )
            if row:
                return row
        return await db_get_workspace_by_team(env, team_id)
    except Exception:
        return None


async def db_upsert_workspace(
    env,
    team_id,
    team_name,
    access_token,
    bot_user_id,
    app_id="",
    icon_url="",
    app_name="",
    app_icon_url="",
    installer_slack_user_id="",
    installer_name="",
):
    """Create or update a workspace row and return the stored record."""
    now = get_utc_now()
    team_id = str(team_id or "").strip()
    team_name = str(team_name or "Unknown Workspace").strip() or "Unknown Workspace"
    access_token = str(access_token or "").strip()
    bot_user_id = str(bot_user_id or "").strip()
    app_id = str(app_id or "").strip()
    icon_url = str(icon_url or "").strip()
    app_name = str(app_name or "").strip()
    app_icon_url = str(app_icon_url or "").strip()
    installer_slack_user_id = str(installer_slack_user_id or "").strip()
    installer_name = str(installer_name or "").strip()

    if not team_id or not access_token:
        return None

    # Prefer full schema (icon + installer metadata), then gracefully fallback.
    try:
        await (
            env.DB.prepare(
                "INSERT INTO workspaces "
                "(team_id, team_name, app_id, app_name, app_icon_url, icon_url, access_token, bot_user_id, installer_slack_user_id, installer_name, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(team_id, app_id) DO UPDATE SET "
                "team_name=excluded.team_name, app_name=excluded.app_name, app_icon_url=excluded.app_icon_url, "
                "icon_url=excluded.icon_url, access_token=excluded.access_token, bot_user_id=excluded.bot_user_id, "
                "installer_slack_user_id=excluded.installer_slack_user_id, installer_name=excluded.installer_name, "
                "updated_at=excluded.updated_at"
            )
            .bind(
                team_id,
                team_name,
                app_id,
                app_name,
                app_icon_url,
                icon_url,
                access_token,
                bot_user_id,
                installer_slack_user_id,
                installer_name,
                now,
                now,
            )
            .run()
        )
    except Exception:
        await (
            env.DB.prepare(
                "INSERT INTO workspaces "
                "(team_id, team_name, app_id, app_name, app_icon_url, access_token, bot_user_id, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(team_id, app_id) DO UPDATE SET "
                "team_name=excluded.team_name, app_name=excluded.app_name, app_icon_url=excluded.app_icon_url, "
                "access_token=excluded.access_token, bot_user_id=excluded.bot_user_id, updated_at=excluded.updated_at"
            )
            .bind(
                team_id,
                team_name,
                app_id,
                app_name,
                app_icon_url,
                access_token,
                bot_user_id,
                now,
                now,
            )
            .run()
        )

    return await db_get_workspace_by_team_and_app(env, team_id, app_id)


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
            if not data.get("ok"):
                break
            channels = data.get("channels", [])
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
            try:
                sentry = get_sentry()
                sentry.capture_exception_nowait(
                    e, level="error", extra={"workspace_id": workspace_id}
                )
            except Exception:
                pass
            break
    return scanned


async def import_workspace_history(env, workspace_id, access_token):
    """Import historical channel activity from Slack to populate events table."""

    # Get all channels for this workspace
    channels = await db_get_channels(env, workspace_id)
    if not channels:
        return {"ok": False, "error": "No channels found. Please scan channels first."}

    total_events = 0
    # Get last 7 days of history from each channel
    import time

    oldest = str(int(time.time()) - (7 * 24 * 60 * 60))  # 7 days ago

    for ch in channels[:10]:  # Limit to first 10 channels to avoid timeout
        channel_id = ch.get("channel_id")

        try:
            headers = Headers.new()
            headers.set("Authorization", f"Bearer {access_token}")
            headers.set("Content-Type", "application/json")

            url = f"https://slack.com/api/conversations.history?channel={channel_id}&oldest={oldest}&limit=100"
            resp = await js_fetch(url, {"method": "GET", "headers": headers})
            data = await resp.json()
            data = _js_to_python(data)

            if not data.get("ok"):
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

    return {
        "ok": True,
        "events_imported": total_events,
        "channels_processed": min(len(channels), 10),
    }


def _extract_app_icon_url(app_obj):
    """Return best available app icon URL from Slack app object."""
    if not isinstance(app_obj, dict):
        return ""
    icons = _js_to_python(app_obj.get("icons") or {})
    if isinstance(icons, dict):
        for key in (
            "image_68",
            "image_64",
            "image_48",
            "image_44",
            "image_36",
            "image_32",
        ):
            val = str(icons.get(key) or "").strip()
            if val:
                return val
    for key in ("icon", "image_68", "image_64", "image_48", "image_36"):
        val = str(app_obj.get(key) or "").strip()
        if val:
            return val
    return ""


async def fetch_app_metadata(access_token, fallback_app_id=""):
    """Fetch app id/name/icon from Slack using the provided token."""
    if not access_token:
        return {
            "app_id": str(fallback_app_id or ""),
            "app_name": "",
            "app_icon_url": "",
        }
    try:
        headers = Headers.new()
        headers.set("Authorization", f"Bearer {access_token}")
        resp = await js_fetch(
            "https://slack.com/api/apps.permissions.info",
            {"method": "GET", "headers": headers},
        )
        data = _js_to_python(await resp.json())
        if isinstance(data, dict) and data.get("ok"):
            info = _js_to_python(data.get("info") or {})
            app_obj = _js_to_python(info.get("app") or data.get("app") or {})
            app_id = str(
                app_obj.get("id")
                or info.get("app_id")
                or data.get("app_id")
                or fallback_app_id
                or ""
            )
            app_name = str(app_obj.get("name") or "").strip()
            app_icon_url = _extract_app_icon_url(app_obj)
            return {
                "app_id": app_id,
                "app_name": app_name,
                "app_icon_url": app_icon_url,
            }
    except Exception:
        pass
    return {
        "app_id": str(fallback_app_id or ""),
        "app_name": "",
        "app_icon_url": "",
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
                            "app_icon_url": _extract_app_icon_url(app),
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
                    "app_name": app_obj.get("name") or "Bot App",
                    "app_icon_url": _extract_app_icon_url(app_obj)
                    or str(ws.get("app_icon_url") or ""),
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
            "app_name": str(ws.get("app_name") or "Bot App"),
            "app_icon_url": str(ws.get("app_icon_url") or ""),
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


async def validate_slack_token(token):
    """
    Validate a Slack token and return workspace info.
    Returns dict with keys: ok, team_id, team_name, bot_user_id, app_id, error
    """
    if not token or not isinstance(token, str):
        return {"ok": False, "error": "Invalid token format"}

    token = token.strip()
    if not token.startswith(("xoxb-", "xoxp-")):
        return {"ok": False, "error": "Token must start with xoxb- or xoxp-"}

    try:
        headers = Headers.new()
        headers.set("Authorization", f"Bearer {token}")
        headers.set("Content-Type", "application/json")

        resp = await js_fetch(
            "https://slack.com/api/auth.test",
            {"method": "POST", "headers": headers},
        )
        result = _js_to_python(await resp.json())

        if not isinstance(result, dict):
            return {"ok": False, "error": "Invalid Slack API response"}

        if not result.get("ok"):
            error_msg = result.get("error", "unknown_error")
            return {"ok": False, "error": f"Slack API error: {error_msg}"}

        # Extract workspace information
        team_id = result.get("team_id", "")
        team_name = result.get("team", "")
        bot_user_id = result.get("user_id", "")

        # Get team info including icon
        try:
            team_resp = await js_fetch(
                "https://slack.com/api/team.info",
                {"method": "POST", "headers": headers},
            )
            team_result = _js_to_python(await team_resp.json())
            if team_result.get("ok") and team_result.get("team"):
                team_data = team_result["team"]
                if not team_name:
                    team_name = team_data.get("name", "")
                icon_url = (team_data.get("icon") or {}).get("image_132", "")
            else:
                icon_url = ""
        except Exception:
            icon_url = ""

        return {
            "ok": True,
            "team_id": team_id,
            "team_name": team_name or "Unknown Workspace",
            "bot_user_id": bot_user_id,
            "icon_url": icon_url,
            "app_id": "",  # Can't easily get this from auth.test
        }
    except Exception as e:
        return {"ok": False, "error": f"Failed to validate token: {str(e)}"}


async def send_slack_message(
    env,
    channel,
    text,
    blocks=None,
    token=None,
    include_branding=True,
    branding_tracking_id="",
):
    slack_token = token or getattr(env, "SLACK_TOKEN", None)
    if not slack_token:
        return {"ok": False, "error": "SLACK_TOKEN not configured"}
    payload = {"channel": channel, "text": text}
    payload_blocks = list(blocks) if isinstance(blocks, list) else []
    if include_branding and len(payload_blocks) < 50:
        payload_blocks.append(
            build_blt_branding_block(
                env,
                channel=channel,
                tracking_id=branding_tracking_id,
            )
        )
    if payload_blocks:
        payload["blocks"] = payload_blocks
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


async def send_slack_ephemeral_message(
    env,
    channel,
    user_id,
    text,
    blocks=None,
    token=None,
    include_branding=True,
    branding_tracking_id="",
):
    """Send an ephemeral message visible only to one user in a channel."""
    slack_token = token or getattr(env, "SLACK_TOKEN", None)
    if not slack_token:
        return {"ok": False, "error": "SLACK_TOKEN not configured"}
    payload = {"channel": channel, "user": user_id, "text": text}
    payload_blocks = list(blocks) if isinstance(blocks, list) else []
    if include_branding and len(payload_blocks) < 50:
        payload_blocks.append(
            build_blt_branding_block(
                env,
                channel=channel,
                user_id=user_id,
                tracking_id=branding_tracking_id,
            )
        )
    if payload_blocks:
        payload["blocks"] = payload_blocks
    headers = Headers.new()
    headers.set("Content-Type", "application/json")
    headers.set("Authorization", f"Bearer {slack_token}")
    resp = await js_fetch(
        "https://slack.com/api/chat.postEphemeral",
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


async def fetch_workspace_icon_url(access_token):
    """Fetch workspace icon URL from Slack team.info API."""
    if not access_token:
        return ""
    try:
        headers = Headers.new()
        headers.set("Authorization", f"Bearer {access_token}")
        resp = await js_fetch(
            "https://slack.com/api/team.info",
            {
                "method": "GET",
                "headers": headers,
            },
        )
        result = _js_to_python(await resp.json())
        if not isinstance(result, dict) or not result.get("ok"):
            return ""

        team = _js_to_python(result.get("team") or {})
        icon = _js_to_python((team or {}).get("icon") or {})
        if not isinstance(icon, dict):
            return ""
        return (
            icon.get("image_230")
            or icon.get("image_132")
            or icon.get("image_88")
            or icon.get("image_68")
            or icon.get("image_44")
            or icon.get("image_34")
            or ""
        )
    except Exception:
        return ""


async def fetch_workspace_member_count(access_token):
    """Fetch best-effort workspace member count from Slack APIs."""
    if not access_token:
        return 0

    headers = Headers.new()
    headers.set("Authorization", f"Bearer {access_token}")

    # Prefer team.info because it is a single lightweight request.
    try:
        resp = await js_fetch(
            "https://slack.com/api/team.info",
            {
                "method": "GET",
                "headers": headers,
            },
        )
        result = _js_to_python(await resp.json())
        if isinstance(result, dict) and result.get("ok"):
            team = _js_to_python(result.get("team") or {})
            count = int((team or {}).get("num_members") or 0)
            if count > 0:
                return count
    except Exception:
        pass

    # Fallback to users.list pagination when team.info lacks member totals.
    try:
        total = 0
        cursor = ""
        while True:
            url = "https://slack.com/api/users.list?limit=200"
            if cursor:
                url += f"&cursor={cursor}"

            resp = await js_fetch(
                url,
                {
                    "method": "GET",
                    "headers": headers,
                },
            )
            data = _js_to_python(await resp.json())
            if not isinstance(data, dict) or not data.get("ok"):
                break

            members = data.get("members") or []
            if isinstance(members, list):
                for member in members:
                    if not isinstance(member, dict):
                        continue
                    if member.get("deleted"):
                        continue
                    if member.get("is_bot"):
                        continue
                    if member.get("is_app_user"):
                        continue
                    total += 1

            cursor = str((data.get("response_metadata") or {}).get("next_cursor") or "")
            if not cursor:
                break

        return total
    except Exception:
        return 0


async def is_image_url_reachable(url):
    """Best-effort URL check used for verified image status."""
    if not url:
        return False
    try:
        resp = await js_fetch(url, {"method": "GET"})
        status = int(getattr(resp, "status", 0) or 0)
        return 200 <= status < 400
    except Exception:
        return False


def render_join_message_template(template_text, context):
    """Render join message variables in both {var} and {{var}} forms."""
    output = str(template_text or "")
    for key, value in (context or {}).items():
        safe_value = str(value or "")
        output = output.replace("{" + key + "}", safe_value)
        output = output.replace("{{" + key + "}}", safe_value)
    return output


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
            # Send configured join message when a template is selected for this channel.
            channel_row = await db_get_channel_by_slack_id(env, ws["id"], channel)
            if channel_row:
                message_id = channel_row.get("join_message_id")
                if message_id:
                    template = await db_get_join_message_by_id(
                        env, ws["id"], message_id
                    )
                    if template and (template.get("message_text") or "").strip():
                        rendered = render_join_message_template(
                            template.get("message_text") or "",
                            {
                                "user_id": user or "",
                                "user_mention": f"<@{user}>" if user else "",
                                "channel_id": channel or "",
                                "channel_name": resolved_channel_name or "",
                                "workspace_id": ws.get("id") or "",
                                "workspace_name": ws.get("team_name") or "",
                                "event_type": "channel_join",
                                "timestamp": get_utc_now(),
                            },
                        )
                        if rendered.strip():
                            logo_tracking_id = secrets.token_hex(12)
                            join_blocks = [
                                {
                                    "type": "section",
                                    "text": {"type": "mrkdwn", "text": rendered},
                                }
                            ]

                            request_payload = {
                                "channel": channel,
                                "channel_name": resolved_channel_name,
                                "template_id": message_id,
                                "template_name": template.get("name") or "",
                                "user_id": user or "",
                                "logo_url": get_blt_logo_url(env),
                                "logo_tracking_id": logo_tracking_id,
                                "delivery_mode": str(
                                    channel_row.get("join_delivery_mode") or "dm"
                                ).lower(),
                            }
                            try:
                                delivery_mode = (
                                    str(channel_row.get("join_delivery_mode") or "dm")
                                    .strip()
                                    .lower()
                                )
                                if delivery_mode == "ephemeral":
                                    send_result = await send_slack_ephemeral_message(
                                        env,
                                        channel,
                                        user,
                                        rendered,
                                        blocks=join_blocks,
                                        token=ws_token,
                                        branding_tracking_id=logo_tracking_id,
                                    )
                                else:
                                    dm_response = await open_conversation(
                                        env, user, token=ws_token
                                    )
                                    dm_channel = (
                                        (dm_response.get("channel") or {}).get("id")
                                        if isinstance(dm_response.get("channel"), dict)
                                        else dm_response.get("channel")
                                    )
                                    if not dm_response.get("ok") or not dm_channel:
                                        raise ValueError(
                                            f"Failed to open DM channel: {dm_response.get('error', 'unknown')}"
                                        )
                                    send_result = await send_slack_message(
                                        env,
                                        dm_channel,
                                        rendered,
                                        blocks=join_blocks,
                                        token=ws_token,
                                        branding_tracking_id=logo_tracking_id,
                                    )
                                await db_log_event(
                                    env,
                                    ws["id"],
                                    "Channel_Join_Message",
                                    user or "",
                                    "success" if send_result.get("ok") else "failed",
                                    channel_name=resolved_channel_name,
                                    request_data=json.dumps(request_payload),
                                    verified=False,
                                )
                            except Exception:
                                await db_log_event(
                                    env,
                                    ws["id"],
                                    "Channel_Join_Message",
                                    user or "",
                                    "failed",
                                    channel_name=resolved_channel_name,
                                    request_data=json.dumps(request_payload),
                                    verified=False,
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


def is_valid_slack_url(url):
    """Return True for trusted Slack endpoints over HTTPS."""
    try:
        parsed = urlparse(str(url or "").strip())
    except Exception:
        return False
    if parsed.scheme != "https":
        return False
    hostname = (parsed.netloc or "").split(":", 1)[0].lower()
    return hostname == "slack.com" or hostname.endswith(".slack.com")


async def _is_workspace_admin_user(env, workspace, user_id):
    """Return True when the Slack user is the recorded installer/admin."""
    if not workspace or not user_id:
        return False
    admin_identity = await db_get_workspace_admin_identity(env, workspace)
    if not admin_identity:
        return False
    return hmac.compare_digest(
        str(admin_identity.get("slack_user_id") or ""), str(user_id or "")
    )


async def _handle_disconnect_command(env, body_json):
    """Handle /lettuce-disconnect: remove all bot data for this workspace.

    Only the original installer (admin) may run this command.
    """
    team_id = body_json.get("team_id") or ""
    user_id = str(body_json.get("user_id") or "").strip()

    workspace = await db_get_workspace_by_team(env, team_id) if team_id else None
    if not workspace:
        return {
            "response_type": "ephemeral",
            "text": "No workspace data found for this Slack team — nothing to remove.",
        }

    if not await _is_workspace_admin_user(env, workspace, user_id):
        return {
            "response_type": "ephemeral",
            "text": "Only the user who originally installed the bot can run `/lettuce-disconnect`.",
        }

    workspace_id = workspace.get("id")
    team_name = str(workspace.get("team_name") or team_id)

    try:
        deleted = await db_delete_workspace(env, workspace_id)
    except Exception as e:
        try:
            sentry = get_sentry()
            sentry.capture_exception_nowait(
                e,
                level="error",
                extra={
                    "context": "_handle_disconnect_command",
                    "workspace_id": workspace_id,
                },
            )
        except Exception:
            pass
        return {
            "response_type": "ephemeral",
            "text": f"An error occurred while removing workspace data: {str(e)[:100]}",
        }

    if not deleted:
        return {
            "response_type": "ephemeral",
            "text": "An error occurred while removing workspace data. Please try again.",
        }

    return {
        "response_type": "ephemeral",
        "text": (
            f":wave: All data for workspace *{html_escape(team_name)}* has been removed from the database. "
            "You can uninstall the app from your Slack workspace settings to complete the disconnection."
        ),
    }


async def _handle_org_add_command(env, body_json):
    """Handle /lettuce-org-add: connect a GitHub org to this workspace."""
    team_id = body_json.get("team_id") or ""
    cmd_text = str(body_json.get("text") or "").strip()

    workspace = await db_get_workspace_by_team(env, team_id) if team_id else None
    if not workspace:
        return {
            "response_type": "ephemeral",
            "text": "No workspace connection was found for this Slack team. Install the app to this workspace first.",
        }

    if not cmd_text:
        return {
            "response_type": "ephemeral",
            "text": "Usage: `/lettuce-org-add <github-org-url-or-name>`\nExample: `/lettuce-org-add https://github.com/OWASP-BLT`",
        }

    # Accept either a full GitHub URL or a plain org name
    gh_target = _extract_github_target(cmd_text)
    if gh_target and gh_target.get("kind") == "org":
        org_login = gh_target.get("org") or ""
    elif gh_target is None and "/" not in cmd_text:
        # Treat bare word as org name
        org_login = cmd_text
    else:
        return {
            "response_type": "ephemeral",
            "text": "Provide a valid GitHub organization URL or name.",
        }

    ws_id = workspace.get("id")
    result = await _import_github_org_repositories(env, ws_id, org_login)
    canonical_org = str(result.get("organization") or org_login)
    return {
        "response_type": "ephemeral",
        "text": (
            f"Connected GitHub org *{canonical_org}*: "
            f"{int(result.get('imported') or 0)} repositories imported, "
            f"{int(result.get('failed') or 0)} failed."
        ),
    }


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


def _is_same_origin_request(request):
    """Best-effort same-origin check for browser-initiated state-changing requests."""
    req_url = urlparse(request.url)
    expected_origin = f"{req_url.scheme}://{req_url.netloc}".lower()

    origin = str(request.headers.get("Origin") or "").strip().lower()
    if origin:
        return origin == expected_origin

    referer = str(request.headers.get("Referer") or "").strip()
    if referer:
        try:
            referer_url = urlparse(referer)
            referer_origin = (
                f"{referer_url.scheme}://{referer_url.netloc}".strip().lower()
            )
            return referer_origin == expected_origin
        except Exception:
            return False

    sec_fetch_site = str(request.headers.get("Sec-Fetch-Site") or "").strip().lower()
    if sec_fetch_site and sec_fetch_site not in ("same-origin", "none"):
        return False

    # If no browser provenance headers are present (e.g. non-browser callers),
    # let auth/ownership checks decide.
    return True


def _attach_security_headers(response):
    """Attach security headers to every response if not already set."""
    if response is None:
        return response

    headers = response.headers
    if not headers.get("X-Content-Type-Options"):
        headers.set("X-Content-Type-Options", "nosniff")
    if not headers.get("X-Frame-Options"):
        headers.set("X-Frame-Options", "DENY")
    if not headers.get("Referrer-Policy"):
        headers.set("Referrer-Policy", "strict-origin-when-cross-origin")
    if not headers.get("Permissions-Policy"):
        headers.set(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )
    if not headers.get("Cross-Origin-Resource-Policy"):
        headers.set("Cross-Origin-Resource-Policy", "same-origin")
    if not headers.get("Cross-Origin-Opener-Policy"):
        headers.set("Cross-Origin-Opener-Policy", "same-origin")
    if not headers.get("Strict-Transport-Security"):
        headers.set(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains; preload",
        )
    if not headers.get("Content-Security-Policy"):
        headers.set(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "img-src 'self' https: data:; "
            "font-src 'self' https: data:; "
            "connect-src 'self' https:; "
            "base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
        )
    return response


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


def _manifest_parse_text(text):
    """Parse YAML text to dict when possible."""
    parsed = None
    try:
        import yaml  # type: ignore

        parsed = yaml.safe_load(text)
    except Exception:
        parsed = None
    return parsed if isinstance(parsed, dict) else None


def _contains_manifest_line(text, snippet):
    return snippet in text


def _check_manifest_requirements_from_data(text, parsed, manifest_label):
    """Validate manifest data from either file text or pasted YAML text."""
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
        "manifest_path": manifest_label,
        "summary": summary,
        "checks": checks,
    }


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
    return _check_manifest_requirements_from_data(text, parsed, str(manifest_path))


def check_manifest_requirements_from_text(
    manifest_text, manifest_label="pasted manifest"
):
    """Validate pasted manifest YAML text."""
    text = str(manifest_text or "")
    parsed = _manifest_parse_text(text)
    return _check_manifest_requirements_from_data(text, parsed, manifest_label)


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

    # Reject cross-origin browser requests for mutating workspace API calls.
    if pathname.startswith("/api/ws/") and method in ("POST", "DELETE"):
        if not _is_same_origin_request(request):
            return _json_response({"ok": False, "error": "Forbidden origin"}, 403)

    # ------------------------------------------------------------------ #
    #  GET /login  →  legacy alias for connect workspace flow             #
    # ------------------------------------------------------------------ #
    if pathname == "/login" and method == "GET":
        return _redirect("/workspace/add")

    # ------------------------------------------------------------------ #
    #  GET /workspace/add  →  redirect to Slack OAuth (bot installation) #
    # ------------------------------------------------------------------ #
    if pathname == "/workspace/add" and method == "GET":
        client_id = getattr(env, "SLACK_CLIENT_ID", None)
        if not client_id:
            return _html_response("SLACK_CLIENT_ID is not configured.", status=500)
        base = get_base_url(env, request)
        redirect_uri = f"{base}/callback"
        state_token = _make_oauth_state("add_workspace")
        sign_in_url = get_slack_add_workspace_url(
            client_id, redirect_uri, state=state_token
        )
        oauth_cookie = (
            f"oauth_state={state_token}; HttpOnly; Secure; SameSite=Lax; "
            "Max-Age=600; Path=/"
        )
        return _redirect(sign_in_url, extra_headers={"Set-Cookie": oauth_cookie})

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
                return _redirect("/")

            # Reject if CSRF state is invalid (missing or tampered)
            if intent is None:
                return _redirect("/")

            client_id = getattr(env, "SLACK_CLIENT_ID", None)
            client_secret = getattr(env, "SLACK_CLIENT_SECRET", None)
            base = get_base_url(env, request)
            redirect_uri = f"{base}/callback"

            token_data = await exchange_code_for_token(
                client_id, client_secret, code, redirect_uri
            )

            if not token_data.get("ok"):
                return _redirect("/")

            # ---- Identify the installing workspace admin ----
            authed_user = _js_to_python(token_data.get("authed_user") or {})
            user_token = _obj_get(authed_user, "access_token", "")
            installer_slack_user_id = _obj_get(authed_user, "id", "")
            installer_name = ""

            if user_token:
                identity = await fetch_user_identity(user_token)
                if identity.get("ok"):
                    profile = _js_to_python(identity.get("user") or {})
                    installer_name = _obj_get(profile, "name", "")
                    if not installer_slack_user_id:
                        installer_slack_user_id = _obj_get(profile, "id", "")

            if not installer_slack_user_id:
                return _redirect("/")

            bot_token = token_data.get("access_token")
            team_info = _js_to_python(token_data.get("team") or {})
            team_id = _obj_get(team_info, "id", "")
            team_name = _obj_get(team_info, "name", "Unknown Workspace")
            bot_user_id = token_data.get("bot_user_id") or ""
            app_id = token_data.get("app_id") or ""
            app_name = f"Bot App ({app_id[:8]})" if app_id else "Bot App"
            app_icon_url = ""
            icon_url = ""

            if not team_id or not bot_token:
                return _redirect("/")

            app_meta = await fetch_app_metadata(bot_token, fallback_app_id=app_id)
            app_id = app_meta.get("app_id") or app_id
            app_name = app_meta.get("app_name") or app_name
            app_icon_url = app_meta.get("app_icon_url") or ""
            icon_url = await fetch_workspace_icon_url(bot_token)
            ws = await db_upsert_workspace(
                env,
                team_id,
                team_name,
                bot_token,
                bot_user_id,
                app_id,
                icon_url,
                app_name,
                app_icon_url,
                installer_slack_user_id=installer_slack_user_id,
                installer_name=installer_name or installer_slack_user_id,
            )
            channels_scanned = 0
            total_members = 0
            if ws:
                ws_id_val = ws.get("id") if isinstance(ws, dict) else None
                try:
                    if ws_id_val and bot_token:
                        channels_scanned = int(
                            await scan_workspace_channels(env, ws_id_val, bot_token)
                            or 0
                        )
                        channel_rows = await db_get_channels(env, ws_id_val)
                        total_members = int(
                            await fetch_workspace_member_count(bot_token) or 0
                        )
                        await db_update_workspace_channel_member_counts(
                            env,
                            ws_id_val,
                            channel_count=len(channel_rows),
                            member_count=total_members,
                        )
                except Exception:
                    pass

                try:
                    conv_result = await open_conversation(
                        env,
                        installer_slack_user_id,
                        token=bot_token,
                    )
                    dm_channel = (
                        (conv_result.get("channel") or {}).get("id")
                        if isinstance(conv_result.get("channel"), dict)
                        else conv_result.get("channel")
                    )
                    if conv_result.get("ok") and dm_channel:
                        await send_slack_message(
                            env,
                            dm_channel,
                            (
                                f":white_check_mark: BLT-Lettuce is now connected to *{team_name}*\n"
                                f"Channels synced: *{channels_scanned}*\n"
                                f"Members tracked: *{total_members}*"
                            ),
                            token=bot_token,
                        )
                except Exception:
                    pass

            clear_oauth_cookie = (
                "oauth_state=; HttpOnly; Secure; SameSite=Lax; Max-Age=0; Path=/"
            )
            resp_h = Headers.new()
            resp_h.set("Location", "/")
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

            return _html_response(
                "Internal server error during workspace connection. Please retry.",
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

    # -------------------------------------------------------------------------- #
    #  POST /api/workspace/manual-add  →  manually add workspace with token     #
    # -------------------------------------------------------------------------- #
    if pathname == "/api/workspace/manual-add" and method == "POST":
        user = await get_current_user(env, request)
        if not user:
            return _json_response({"ok": False, "error": "Unauthorized"}, 401)

        try:
            body = json.loads(await request.text())
            token = (body.get("token") or "").strip()
            custom_name = (body.get("team_name") or "").strip()

            if not token:
                return _json_response(
                    {"ok": False, "error": "Bot token is required"}, 400
                )

            # Validate token and get workspace info
            validation = await validate_slack_token(token)

            if not validation.get("ok"):
                error_msg = validation.get("error", "Invalid token")
                return _json_response({"ok": False, "error": error_msg}, 400)

            team_id = validation.get("team_id")
            team_name = custom_name or validation.get("team_name", "Unknown Workspace")
            bot_user_id = validation.get("bot_user_id", "")
            icon_url = validation.get("icon_url", "")
            app_id = validation.get("app_id", "")
            app_icon_url = ""
            app_name = (
                custom_name or f"Bot App ({bot_user_id[:8]})"
                if bot_user_id
                else "Bot App"
            )

            app_meta = await fetch_app_metadata(token, fallback_app_id=app_id)
            app_id = app_meta.get("app_id") or app_id
            app_name = app_meta.get("app_name") or app_name
            app_icon_url = app_meta.get("app_icon_url") or ""

            # Check if workspace already exists for another user
            existing_ws = await db_get_workspace_by_team_and_app(env, team_id, app_id)
            if existing_ws:
                # Check if current user already has access
                has_access = await db_user_owns_workspace(
                    env, user["user_id"], existing_ws["id"]
                )
                if not has_access:
                    # Link the user to existing workspace
                    await db_link_user_workspace(
                        env, user["user_id"], existing_ws["id"], role="admin"
                    )

                # Update token if provided
                ws = await db_upsert_workspace(
                    env,
                    team_id,
                    team_name,
                    token,
                    bot_user_id,
                    app_id,
                    icon_url,
                    app_name,
                    app_icon_url,
                )
            else:
                # Create new workspace
                ws = await db_upsert_workspace(
                    env,
                    team_id,
                    team_name,
                    token,
                    bot_user_id,
                    app_id,
                    icon_url,
                    app_name,
                    app_icon_url,
                )

                if ws:
                    # Link user as owner
                    await db_link_user_workspace(
                        env, user["user_id"], ws["id"], role="owner"
                    )

            if not ws:
                return _json_response(
                    {"ok": False, "error": "Failed to create workspace"}, 500
                )

            channels_scanned = 0
            total_members = 0
            try:
                ws_id_val = ws.get("id") if isinstance(ws, dict) else None
                if ws_id_val and token:
                    channels_scanned = int(
                        await scan_workspace_channels(env, ws_id_val, token) or 0
                    )
                    channel_rows = await db_get_channels(env, ws_id_val)
                    total_members = int(await fetch_workspace_member_count(token) or 0)
                    await db_update_workspace_channel_member_counts(
                        env,
                        ws_id_val,
                        channel_count=len(channel_rows),
                        member_count=total_members,
                    )

                user_slack_id = str(user.get("slack_user_id") or "").strip()
                if user_slack_id:
                    conv_result = await open_conversation(
                        env,
                        user_slack_id,
                        token=token,
                    )
                    dm_channel = (
                        (conv_result.get("channel") or {}).get("id")
                        if isinstance(conv_result.get("channel"), dict)
                        else conv_result.get("channel")
                    )
                    if conv_result.get("ok") and dm_channel:
                        await send_slack_message(
                            env,
                            dm_channel,
                            (
                                f":white_check_mark: BLT-Lettuce is now connected to *{team_name}*\n"
                                f"Channels synced: *{channels_scanned}*\n"
                                f"Members tracked: *{total_members}*"
                            ),
                            token=token,
                        )
            except Exception:
                pass

            try:
                sentry = get_sentry()
                sentry.capture_message_nowait(
                    f"Manual workspace added: {team_name} (team_id={team_id})",
                    level="info",
                )
            except Exception:
                pass

            return _json_response(
                {
                    "ok": True,
                    "workspace": {
                        "id": ws.get("id"),
                        "team_id": team_id,
                        "team_name": team_name,
                    },
                },
                200,
            )

        except Exception as e:
            try:
                sentry = get_sentry()
                sentry.capture_exception_nowait(
                    e, level="error", extra={"user_id": user.get("user_id")}
                )
            except Exception:
                pass
            return _json_response({"ok": False, "error": "Internal server error"}, 500)

    # ------------------------------------------------------------------ #
    #  POST /api/ws/<id>/scan  →  trigger channel scan for a workspace   #
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    #  DELETE /api/ws/<id>  →  delete a workspace and its workspace data #
    # ------------------------------------------------------------------ #
    if pathname.startswith("/api/ws/") and method == "DELETE":
        suffix = pathname.split("/api/ws/")[1].strip("/")
        if suffix and "/" not in suffix:
            user = await get_current_user(env, request)
            if not user:
                return _json_response({"ok": False, "error": "Unauthorized"}, 401)
            try:
                ws_id_val = int(suffix)
            except (ValueError, TypeError):
                return _json_response(
                    {"ok": False, "error": "Invalid workspace id"},
                    400,
                )

            if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
                return _json_response({"ok": False, "error": "Forbidden"}, 403)

            user_role = await db_get_user_workspace_role(
                env, user["user_id"], ws_id_val
            )
            if user_role not in ("owner", "admin"):
                return _json_response(
                    {
                        "ok": False,
                        "error": "Only workspace admins/owners can delete a workspace.",
                    },
                    403,
                )

            ws = await db_get_workspace_by_id(env, ws_id_val)
            if not ws:
                return _json_response(
                    {"ok": False, "error": "Workspace not found"},
                    404,
                )

            deleted = await db_delete_workspace(env, ws_id_val)
            if not deleted:
                return _json_response(
                    {"ok": False, "error": "Failed to delete workspace"},
                    500,
                )

            return _json_response(
                {
                    "ok": True,
                    "deleted_workspace_id": ws_id_val,
                    "deleted_workspace_name": ws.get("team_name") or "Workspace",
                },
                200,
            )

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
        channel_rows = await db_get_channels(env, ws_id_val)
        total_members = int(
            await fetch_workspace_member_count(ws.get("access_token") or "") or 0
        )
        await db_update_workspace_channel_member_counts(
            env,
            ws_id_val,
            channel_count=len(channel_rows),
            member_count=total_members,
        )
        return Response.json(
            {
                "ok": True,
                "channels_scanned": scanned,
                "channel_count": len(channel_rows),
                "member_count": total_members,
            }
        )

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
    #  GET/POST /api/ws/<id>/join-messages  →  list/create templates      #
    # ------------------------------------------------------------------ #
    if pathname.startswith("/api/ws/") and pathname.endswith("/join-messages"):
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
            rows = await db_get_join_messages(env, ws_id_val)
            return _json_response({"ok": True, "join_messages": rows}, 200)

        if method == "POST":
            user_role = await db_get_user_workspace_role(
                env, user["user_id"], ws_id_val
            )
            if user_role not in ("owner", "admin"):
                return _json_response(
                    {
                        "ok": False,
                        "error": "Only workspace admins/owners can manage join messages.",
                    },
                    403,
                )
            try:
                body = json.loads(await request.text())
            except Exception:
                body = {}

            name = str((body or {}).get("name") or "").strip()
            message_text = str((body or {}).get("message_text") or "").strip()
            if not name:
                return _json_response({"ok": False, "error": "name is required"}, 400)
            if not message_text:
                return _json_response(
                    {"ok": False, "error": "message_text is required"},
                    400,
                )

            ok = await db_add_join_message(env, ws_id_val, name, message_text)
            if not ok:
                return _json_response(
                    {"ok": False, "error": "Failed to create join message"},
                    500,
                )
            return _json_response({"ok": True}, 200)

    # ------------------------------------------------------------------ #
    #  DELETE /api/ws/<id>/join-messages/<msg_id>  →  delete template    #
    # ------------------------------------------------------------------ #
    if (
        pathname.startswith("/api/ws/")
        and "/join-messages/" in pathname
        and method == "DELETE"
    ):
        user = await get_current_user(env, request)
        if not user:
            return _json_response({"ok": False, "error": "Unauthorized"}, 401)
        try:
            after = pathname.split("/api/ws/")[1]
            ws_id_val = int(after.split("/")[0])
            msg_id_val = int(after.split("/join-messages/")[1].rstrip("/"))
        except (ValueError, IndexError):
            return _json_response({"ok": False, "error": "Invalid ids"}, 400)

        if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
            return _json_response({"ok": False, "error": "Forbidden"}, 403)

        user_role = await db_get_user_workspace_role(env, user["user_id"], ws_id_val)
        if user_role not in ("owner", "admin"):
            return _json_response(
                {
                    "ok": False,
                    "error": "Only workspace admins/owners can manage join messages.",
                },
                403,
            )

        ok = await db_delete_join_message(env, ws_id_val, msg_id_val)
        if not ok:
            return _json_response(
                {"ok": False, "error": "Failed to delete join message"},
                500,
            )
        return _json_response({"ok": True}, 200)

    # ------------------------------------------------------------------ #
    #  POST /api/ws/<id>/join-messages/<msg_id>/test  →  test template  #
    # ------------------------------------------------------------------ #
    if (
        pathname.startswith("/api/ws/")
        and "/join-messages/" in pathname
        and pathname.endswith("/test")
        and method == "POST"
    ):
        user = await get_current_user(env, request)
        if not user:
            return _json_response({"ok": False, "error": "Unauthorized"}, 401)
        try:
            after = pathname.split("/api/ws/")[1]
            ws_id_val = int(after.split("/")[0])
            msg_id_val = int(after.split("/join-messages/")[1].split("/")[0])
        except (ValueError, IndexError):
            return _json_response({"ok": False, "error": "Invalid ids"}, 400)

        if not await db_user_owns_workspace(env, user["user_id"], ws_id_val):
            return _json_response({"ok": False, "error": "Forbidden"}, 403)

        user_role = await db_get_user_workspace_role(env, user["user_id"], ws_id_val)
        if user_role not in ("owner", "admin"):
            return _json_response(
                {
                    "ok": False,
                    "error": "Only workspace admins/owners can test join messages.",
                },
                403,
            )

        ws = await db_get_workspace_by_id(env, ws_id_val)
        if not ws:
            await report_404_to_sentry(env, pathname, method, "workspace_not_found")
            return _json_response({"ok": False, "error": "Workspace not found"}, 404)

        template = await db_get_join_message_by_id(env, ws_id_val, msg_id_val)
        if not template:
            return _json_response(
                {"ok": False, "error": "Join message template not found"}, 404
            )

        user_slack_id = user.get("slack_user_id")
        if not user_slack_id:
            return _json_response(
                {"ok": False, "error": "User Slack ID not found"}, 400
            )

        ws_token = ws.get("access_token") or getattr(env, "SLACK_TOKEN", None)
        dm_response = await open_conversation(env, user_slack_id, token=ws_token)
        dm_channel = (
            (dm_response.get("channel") or {}).get("id")
            if isinstance(dm_response.get("channel"), dict)
            else dm_response.get("channel")
        )
        if not dm_response.get("ok") or not dm_channel:
            return _json_response(
                {
                    "ok": False,
                    "error": f"Failed to open DM: {dm_response.get('error', 'unknown')}",
                },
                500,
            )

        rendered = render_join_message_template(
            template.get("message_text") or "",
            {
                "user_id": user_slack_id,
                "user_mention": f"<@{user_slack_id}>",
                "channel_id": "test-channel",
                "channel_name": "test-channel",
                "workspace_id": ws.get("id") or "",
                "workspace_name": ws.get("team_name") or "",
                "event_type": "join_message_test",
                "timestamp": get_utc_now(),
            },
        )
        test_text = (
            f":test_tube: Join message test for *{template.get('name') or 'Template'}*\n\n"
            f"{rendered}"
        )
        send_result = await send_slack_message(
            env,
            dm_channel,
            test_text,
            token=ws_token,
        )
        if not send_result.get("ok"):
            return _json_response(
                {
                    "ok": False,
                    "error": f"Failed to send test: {send_result.get('error', 'unknown')}",
                },
                500,
            )
        return _json_response({"ok": True, "message": "Test message sent"}, 200)

    # ------------------------------------------------------------------ #
    #  POST /api/ws/<id>/channels/join-config  →  update per-channel cfg #
    # ------------------------------------------------------------------ #
    if (
        pathname.startswith("/api/ws/")
        and pathname.endswith("/channels/join-config")
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
                    "error": "Only workspace admins/owners can update channel join settings.",
                },
                403,
            )

        try:
            body = json.loads(await request.text())
        except Exception:
            body = {}

        channel_id = str((body or {}).get("channel_id") or "").strip()
        join_message_id_raw = (body or {}).get("join_message_id")
        join_delivery_mode = str((body or {}).get("join_delivery_mode") or "dm").lower()
        if join_delivery_mode not in ("dm", "ephemeral"):
            return _json_response(
                {"ok": False, "error": "Invalid join_delivery_mode"}, 400
            )
        join_message_id = None
        try:
            if join_message_id_raw not in (None, "", 0, "0"):
                join_message_id = int(join_message_id_raw)
        except Exception:
            return _json_response(
                {"ok": False, "error": "Invalid join_message_id"}, 400
            )

        if not channel_id:
            return _json_response({"ok": False, "error": "channel_id is required"}, 400)

        channel_row = await db_get_channel_by_slack_id(env, ws_id_val, channel_id)
        if not channel_row:
            return _json_response(
                {
                    "ok": False,
                    "error": "Unknown channel. Run Scan Channels and try again.",
                },
                404,
            )

        if join_message_id is not None:
            join_message = await db_get_join_message_by_id(
                env, ws_id_val, join_message_id
            )
            if not join_message:
                return _json_response(
                    {
                        "ok": False,
                        "error": "Selected join message does not exist for this workspace.",
                    },
                    400,
                )

        ok = await db_update_channel_join_config(
            env,
            ws_id_val,
            channel_id,
            join_message_id,
            join_delivery_mode,
        )
        if not ok:
            return _json_response(
                {"ok": False, "error": "Failed to update channel join config"},
                500,
            )
        return _json_response({"ok": True}, 200)

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

                gh_target = _extract_github_target(repo_url)

                if gh_target and gh_target.get("kind") == "org":
                    org_login = gh_target.get("org") or ""
                    if not org_login:
                        return _json_response(
                            {"ok": False, "error": "Invalid GitHub organization URL"},
                            400,
                        )

                    org_result = await _import_github_org_repositories(
                        env,
                        ws_id_val,
                        org_login,
                    )
                    return Response.json(
                        {
                            "ok": True,
                            "mode": "org",
                            "organization": str(
                                org_result.get("organization") or org_login
                            ),
                            "organization_type": str(
                                org_result.get("org_type") or "org"
                            ),
                            "imported": int(org_result.get("imported") or 0),
                            "failed": int(org_result.get("failed") or 0),
                        }
                    )

                repo_name, description, language, stars = "", "", "", 0
                source_type = "repo"
                metadata_json = ""

                if gh_target and gh_target.get("kind") == "repo":
                    owner = gh_target.get("owner") or ""
                    repo_slug = gh_target.get("repo") or ""
                    if owner and repo_slug:
                        gh_data = await _fetch_github_json(
                            f"https://api.github.com/repos/{owner}/{repo_slug}"
                        )
                        if isinstance(gh_data, dict) and gh_data.get("full_name"):
                            normalized = _repo_metadata_from_github(
                                gh_data,
                                source_type="repo",
                            )
                            repo_url = normalized["repo_url"] or repo_url
                            repo_name = normalized["repo_name"]
                            description = normalized["description"]
                            language = normalized["language"]
                            stars = normalized["stars"]
                            source_type = normalized["source_type"]
                            metadata_json = normalized["metadata_json"]

                await db_add_repository(
                    env,
                    ws_id_val,
                    repo_url,
                    repo_name,
                    description,
                    language,
                    stars,
                    source_type=source_type,
                    metadata_json=metadata_json,
                )
                return Response.json({"ok": True, "mode": "repo"})
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
    #  POST /api/ws/<id>/manifest-check  →  analyze pasted manifest YAML #
    # ------------------------------------------------------------------ #
    if (
        pathname.startswith("/api/ws/")
        and pathname.endswith("/manifest-check")
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
                    "error": "Only workspace admins/owners can analyze manifests.",
                },
                403,
            )

        try:
            body = json.loads(await request.text())
        except Exception:
            body = {}

        manifest_yaml = ""
        if isinstance(body, dict):
            manifest_yaml = str(body.get("manifest_yaml") or "")
        if not manifest_yaml.strip():
            return _json_response(
                {"ok": False, "error": "manifest_yaml is required"},
                400,
            )

        result = check_manifest_requirements_from_text(
            manifest_yaml, manifest_label="pasted manifest"
        )
        return _json_response({"ok": True, "result": result}, 200)

    # ------------------------------------------------------------------ #
    #  GET/POST /api/ws/<id>/manifest  →  load/save workspace manifest   #
    # ------------------------------------------------------------------ #
    if pathname.startswith("/api/ws/") and pathname.endswith("/manifest"):
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
            ws = await db_get_workspace_by_id(env, ws_id_val)
            if not ws:
                return _json_response(
                    {"ok": False, "error": "Workspace not found"}, 404
                )
            return _json_response(
                {
                    "ok": True,
                    "manifest_yaml": str(ws.get("manifest_yaml") or ""),
                    "app_id": str(ws.get("app_id") or ""),
                    "app_name": str(ws.get("app_name") or ""),
                },
                200,
            )

        if method == "POST":
            user_role = await db_get_user_workspace_role(
                env, user["user_id"], ws_id_val
            )
            if user_role not in ("owner", "admin"):
                return _json_response(
                    {
                        "ok": False,
                        "error": "Only workspace admins/owners can save manifest data.",
                    },
                    403,
                )
            try:
                body = json.loads(await request.text())
            except Exception:
                body = {}

            manifest_yaml = str((body or {}).get("manifest_yaml") or "")
            save_ok = await db_update_workspace_manifest(env, ws_id_val, manifest_yaml)
            if not save_ok:
                return _json_response(
                    {"ok": False, "error": "Failed to save manifest"}, 500
                )

            result = check_manifest_requirements_from_text(
                manifest_yaml,
                manifest_label="saved workspace manifest",
            )
            return _json_response({"ok": True, "result": result}, 200)

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
    #  POST /api/ws/<id>/inactivity-alert/test  →  send test alert       #
    # ------------------------------------------------------------------ #
    if (
        pathname.startswith("/api/ws/")
        and pathname.endswith("/inactivity-alert/test")
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
                    "error": "Only workspace admins/owners can trigger inactivity alerts.",
                },
                403,
            )

        ws = await db_get_workspace_by_id(env, ws_id_val)
        if not ws:
            await report_404_to_sentry(env, pathname, method, "workspace_not_found")
            return _json_response({"ok": False, "error": "Workspace not found"}, 404)

        last_event_row = _row(
            await env.DB.prepare(
                "SELECT created_at FROM events WHERE workspace_id = ? AND event_type != 'Inactivity_Alert' ORDER BY created_at DESC LIMIT 1"
            )
            .bind(ws_id_val)
            .first()
        )
        last_activity_at = (last_event_row or {}).get("created_at") or ws.get(
            "created_at"
        )

        test_result = await send_inactivity_alert_for_workspace(
            env,
            ws,
            last_activity_at=last_activity_at,
            is_test=True,
        )
        if not test_result.get("ok"):
            return _json_response(
                {
                    "ok": False,
                    "error": test_result.get("error")
                    or "Failed to send inactivity alert test",
                },
                500,
            )

        return _json_response(
            {"ok": True, "message": "Test inactivity alert sent."}, 200
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
                cmd_name = (body_json.get("command") or "").strip().lower()

                if cmd_name == "/lettuce-org-add":
                    return Response.json(await _handle_org_add_command(env, body_json))

                if cmd_name == "/lettuce-disconnect":
                    return Response.json(
                        await _handle_disconnect_command(env, body_json)
                    )

                return Response.json(
                    {
                        "response_type": "ephemeral",
                        "text": "Unknown command.",
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
                        blocks = _create_quick_response_blocks(stats_text)
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
                        blocks = _create_quick_response_blocks(greet_text)
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
                        blocks = _create_quick_response_blocks(help_text)
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
    #  GET /logo-hit  →  track logo image loads for verification         #
    # ------------------------------------------------------------------ #
    if pathname == "/logo-hit" and method == "GET":
        qs = _parsed.query or ""
        tid = ""
        for part in qs.split("&"):
            kv = part.split("=", 1)
            if len(kv) == 2 and kv[0] == "tid":
                tid = unquote_plus(kv[1] or "").strip()
                break

        ip_address = (request.headers.get("CF-Connecting-IP") or "").strip() or (
            request.headers.get("X-Forwarded-For") or ""
        ).split(",")[0].strip()
        user_agent = (request.headers.get("User-Agent") or "").strip()

        if tid:
            await db_mark_join_message_verified_by_tracking(
                env,
                tid,
                ip_address,
                user_agent,
            )

        # Redirect to the actual logo asset after recording the hit.
        h = Headers.new()
        h.set("Location", get_blt_logo_url(env))
        h.set("Cache-Control", "no-store")
        return Response.new("", {"status": 302, "headers": h})

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
        return _redirect("/")

    # ------------------------------------------------------------------ #
    #  GET /api/workspaces-public  →  connected workspaces + stats       #
    # ------------------------------------------------------------------ #
    if pathname == "/api/workspaces-public" and method == "GET":
        try:
            workspaces = await db_list_workspaces_public(env)
            return _json_response({"ok": True, "workspaces": workspaces})
        except Exception as e:
            return _json_response({"ok": False, "workspaces": [], "error": str(e)})

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
            response = await handle_request(request, self.env)
            return _attach_security_headers(response)
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
                return _attach_security_headers(
                    _json_response({"error": "Internal server error"}, 500)
                )
            return _attach_security_headers(_html_response(get_500_html(), 500))

    async def scheduled(self, controller):
        """Cloudflare Cron trigger entrypoint."""
        try:
            await run_inactivity_monitor(self.env)
        except Exception as e:
            try:
                sentry = get_sentry()
                sentry.capture_exception_nowait(
                    e,
                    level="error",
                    extra={"context": "cron_inactivity_monitor"},
                )
            except Exception:
                pass
