"""OWASP community welcome bot: welcome DMs, join history, channel stats and health.

Lettuce welcomes new members of the workspaces in WELCOME_TEAM_IDS (default: the OWASP
Slack, T04T40NHX). Other workspaces keep worker.py's older handle_team_join path.

Reliability design (ported from blt-sammich, which sent these welcomes before):

* /webhook checks the Slack signature before anything here runs.
* One team_joins row per join. Its INSERT is also the event claim: the partial unique index
  on event_id makes a Slack retry (or two racing deliveries) insert nothing, so only the
  first delivery welcomes. No separate claims table, no prune job.
* The webhook answers at once and the DM is sent after the response (ctx.waitUntil). Slack
  retries a delivery that isn't answered within 3 seconds.
* Each Slack call is retried once on a transient error (rate limit, 5xx, network).
* Logs are one JSON line with ids and Slack error codes, never a token or message text.
* WELCOME_ENABLED (default off) is the kill switch: when off, joins are still recorded but
  nobody is DMed. blt-sammich has the mirror switch, so exactly one bot welcomes.

D1 cost (the account shares 100k row writes a day): a welcomed join is one INSERT (about 5
row writes with its indexes) and one UPDATE; the first logo load is one more UPDATE. The
hourly cron writes one welcome_state row (auth.test) and once a day one more (channel stats).
Reads use the (team_id, joined_at), (team_id, user_id) and tracking_id indexes.
"""

import asyncio
import base64
import hmac
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from html import escape as _html_escape
from pathlib import Path
from urllib.parse import parse_qs, urlencode

OWASP_TEAM_ID = "T04T40NHX"
DEFAULT_WELCOME_TEAM_IDS = (OWASP_TEAM_ID,)
MESSAGES_DIR = Path(__file__).resolve().parent / "messages"
FALLBACK_WELCOME = (
    ":tada: *Welcome to the OWASP Slack Community, <@{user_id}>!* :tada:\n\n"
    "We're glad you're here. Introduce yourself and say hello!"
)
BLT_LOGO_PATH = "/docs/static/blt-logo.png"
WELCOME_LOGO_PATH = "/welcome-logo"
TRACKING_ID_PATTERN = re.compile(r"[0-9a-f]{24}")
SLACK_API_BASE = "https://slack.com/api/"
TRANSIENT_SLACK_ERRORS = frozenset(
    {"ratelimited", "internal_error", "fatal_error", "service_unavailable", "request_timeout"}
)
RETRY_DELAY_SECONDS = 1.0
RETRY_DELAY_MAX_SECONDS = 3.0
# A user already welcomed (delivered) within this window isn't welcomed again.
REWELCOME_AFTER_DAYS = 30
# Health: a join younger than this may still be sending, so it doesn't count as missed yet.
HEALTH_GRACE_MINUTES = 10
# Health: the hourly cron's auth.test must be this fresh, or the cron has stopped.
AUTH_CHECK_MAX_AGE_HOURS = 3
# Health: with at least this many eligible joins in 24 h, under this % delivered is a failure.
LOW_RATE_MIN_JOINS = 5
LOW_RATE_PCT = 50.0
CHANNEL_STATS_MAX_AGE_HOURS = 23
CHANNEL_STATS_TOP = 25
CHANNEL_LIST_MAX_PAGES = 8
WELCOME_TOP_CHANNELS = 5
HEALTH_OK = "welcome-healthy"
HEALTH_DISABLED = "welcome-disabled"
HEALTH_FAILING = "welcome-unhealthy"
PUBLIC_STATS_TTL_SECONDS = 300
_public_stats_cache = {}

# Overridable in tests: async (url, method, headers, body) -> (status, text, retry_after)
_http_request = None
_sleep = asyncio.sleep


# --------------------------------------------------------------------------- config


def env_str(env, name, default=""):
    try:
        value = getattr(env, name)
    except Exception:
        return default
    if value is None:
        return default
    return str(value)


def welcome_enabled(env):
    """WELCOME_ENABLED: on only for an explicit true value. Unset means off."""
    return env_str(env, "WELCOME_ENABLED").strip().lower() in ("1", "true", "yes", "on")


def welcome_team_ids(env):
    raw = env_str(env, "WELCOME_TEAM_IDS").strip()
    if not raw:
        return DEFAULT_WELCOME_TEAM_IDS
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def is_welcome_team(env, team_id):
    return bool(team_id) and str(team_id) in welcome_team_ids(env)


def base_url(env):
    return env_str(env, "BASE_URL").strip().rstrip("/") or "https://lettuce.owaspblt.org"


def utc_now():
    return datetime.now(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).isoformat()


def log(event, **fields):
    """One JSON line. Callers pass ids and Slack error codes only, never tokens or text."""
    payload = {"event": event}
    payload.update({k: v for k, v in fields.items() if v not in (None, "")})
    try:
        print("[welcome]", json.dumps(payload, separators=(",", ":"), sort_keys=True))
    except Exception:
        pass


# --------------------------------------------------------------------------- D1


def _to_py(value):
    try:
        return value.to_py()
    except Exception:
        return value


def _param(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return 1 if value else 0
    return value


def _statement(env, sql, params):
    statement = env.DB.prepare(sql)
    if params:
        statement = statement.bind(*[_param(p) for p in params])
    return statement


async def d1_all(env, sql, params=()):
    """Rows as a list of dicts. Never uses .first(): Pyodide returns jsnull, not None,
    for "no row", which is how worker.py's old team_join dedupe skipped every join."""
    result = _to_py(await _statement(env, sql, params).all())
    rows = result.get("results") if isinstance(result, dict) else getattr(result, "results", None)
    rows = _to_py(rows) or []
    return [dict(_to_py(row)) for row in rows]


async def d1_run(env, sql, params=()):
    """Run a write; return the number of rows changed."""
    result = _to_py(await _statement(env, sql, params).run())
    meta = result.get("meta") if isinstance(result, dict) else getattr(result, "meta", None)
    meta = _to_py(meta) or {}
    try:
        return int(meta.get("changes") or 0)
    except Exception:
        return 0


async def state_get(env, key):
    rows = await d1_all(env, "SELECT value, updated_at FROM welcome_state WHERE key = ?", [key])
    if not rows:
        return None
    try:
        value = json.loads(rows[0].get("value") or "null")
    except ValueError:
        value = None
    return {"value": value, "updated_at": str(rows[0].get("updated_at") or "")}


async def state_put(env, key, value, now=None):
    await d1_run(
        env,
        (
            "INSERT INTO welcome_state (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at"
        ),
        [key, json.dumps(value, separators=(",", ":"), sort_keys=True), iso(now or utc_now())],
    )


# --------------------------------------------------------------------------- Slack


async def _default_http_request(url, method, headers, body):
    from js import Object, fetch
    from pyodide.ffi import to_js

    options = {"method": method, "headers": headers}
    if body is not None:
        options["body"] = body
    response = await fetch(url, to_js(options, dict_converter=Object.fromEntries))
    text = str(await response.text() or "")
    retry_after = ""
    try:
        retry_after = str(response.headers.get("retry-after") or "")
    except Exception:
        retry_after = ""
    return int(response.status), text, retry_after


def _is_transient(status, payload):
    if status == 429 or status >= 500:
        return True
    return str((payload or {}).get("error") or "") in TRANSIENT_SLACK_ERRORS


async def slack_call(token, api_method, payload=None, http_method="POST", query=None):
    """Call a Slack Web API method, retrying once on a transient failure.

    Returns Slack's JSON (always a dict with "ok"). Transport failures come back as
    {"ok": False, "error": "http_<status>" | "network_error"}.
    """
    if not token:
        return {"ok": False, "error": "missing_token"}
    request = _http_request or _default_http_request
    url = SLACK_API_BASE + api_method
    if query:
        url += "?" + urlencode(query)
    headers = {"Authorization": "Bearer " + token}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        body = json.dumps(payload)
    result = {"ok": False, "error": "not_called"}
    for attempt in (1, 2):
        retry_after = ""
        try:
            status, text, retry_after = await request(url, http_method, headers, body)
            try:
                result = json.loads(text) if text else {}
            except ValueError:
                result = {}
            if not isinstance(result, dict):
                result = {}
            if status >= 400 and not result.get("error"):
                result = {"ok": False, "error": "http_{0}".format(status)}
            result.setdefault("ok", False)
            if result.get("ok") or not _is_transient(status, result):
                break
        except Exception as error:
            status = 0
            result = {"ok": False, "error": "network_error", "detail": type(error).__name__}
        if attempt == 1:
            log("slack_retry", method=api_method, error=result.get("error"), status=status)
            try:
                delay = float(retry_after or RETRY_DELAY_SECONDS)
            except ValueError:
                delay = RETRY_DELAY_SECONDS
            await _sleep(max(0.0, min(delay, RETRY_DELAY_MAX_SECONDS)))
    result["attempts"] = attempt
    return result


async def welcome_token(env, team_id):
    """The bot token for a welcome team: the workspaces row lettuce's OAuth install wrote,
    else the WELCOME_SLACK_TOKEN secret (for an install made from the Slack app settings)."""
    try:
        rows = await d1_all(
            env,
            (
                "SELECT access_token FROM workspaces WHERE team_id = ? AND access_token != '' "
                "ORDER BY updated_at DESC LIMIT 1"
            ),
            [team_id],
        )
    except Exception as error:
        log("token_lookup_failed", team_id=team_id, error=type(error).__name__)
        rows = []
    token = str((rows[0] if rows else {}).get("access_token") or "").strip()
    return token or env_str(env, "WELCOME_SLACK_TOKEN").strip()


# --------------------------------------------------------------------------- message


def load_welcome_template(team_id):
    """The welcome text for a team from messages/<team_id>-team_join.txt, or None.

    The file is .txt inside src/ so Wrangler bundles it as a text module (it doesn't bundle
    .md files, or anything outside src/)."""
    if not re.fullmatch(r"[A-Z0-9]{5,20}", str(team_id or "")):
        return None
    try:
        text = (MESSAGES_DIR / "{0}-team_join.txt".format(team_id)).read_text(encoding="utf-8")
    except Exception:
        return None
    return text.strip() or None


def render_welcome(team_id, user_id, top_channels=None):
    """(text, template_loaded). Fills {user_id}, {user_mention}; appends the top channels."""
    template = load_welcome_template(team_id)
    loaded = template is not None
    text = (template or FALLBACK_WELCOME).replace("{user_id}", user_id).replace(
        "{user_mention}", "<@{0}>".format(user_id)
    )
    links = [
        "*<#{0}|{1}>*".format(ch["id"], ch["name"])
        for ch in (top_channels or [])[:WELCOME_TOP_CHANNELS]
        if ch.get("id") and ch.get("name")
    ]
    if links:
        text += "\n\n:bar_chart: *Most Active Channels:* " + ", ".join(links)
    return text, loaded


def new_tracking_id():
    """96 random bits: a logo hit can't be forged by guessing another message's id."""
    return secrets.token_hex(12)


def build_welcome_blocks(env, text, tracking_id):
    """The welcome with the BLT logo beside it and a tracked logo in the footer.

    The visible logo is the plain PNG: Slack may fetch a section's image when the message is
    posted, which would mark every welcome opened. The footer's small context image carries
    the per-message id; Slack loads it lazily when a client renders the message."""
    root = base_url(env)
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text.strip()},
            "accessory": {
                "type": "image",
                "image_url": root + BLT_LOGO_PATH,
                "alt_text": "OWASP BLT logo",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "image",
                    "image_url": "{0}{1}?{2}".format(
                        root, WELCOME_LOGO_PATH, urlencode({"tid": tracking_id})
                    ),
                    "alt_text": "OWASP BLT",
                },
                {"type": "mrkdwn", "text": "Sent by <{0}|BLT Lettuce>".format(root)},
            ],
        },
    ]


def join_skip_reason(user_obj, bot_user_id=""):
    def flag(name):
        value = (user_obj or {}).get(name)
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes")
        return bool(value)

    if flag("deleted"):
        return "deleted_user"
    if flag("is_bot"):
        return "bot_user"
    if flag("is_app_user"):
        return "app_user"
    if bot_user_id and str((user_obj or {}).get("id") or "") == bot_user_id:
        return "bot_user"
    return ""


# --------------------------------------------------------------------------- team_join


async def run_after_response(ctx, deferred):
    """Run `deferred` after the response (ctx.waitUntil), or now when there's no ctx."""
    wait_until = getattr(ctx, "waitUntil", None) if ctx is not None else None
    if wait_until is not None:
        wait_until(asyncio.ensure_future(deferred()))
    else:
        await deferred()


async def accept_team_join(env, ctx, body, team_id, retry_num=""):
    """Record a team_join, claim it, answer Slack at once, and welcome after the response.

    Returns the JSON for the webhook's 200 response.
    """
    event = body.get("event") or {}
    user_obj = event.get("user") if isinstance(event.get("user"), dict) else {"id": event.get("user")}
    user_id = str((user_obj or {}).get("id") or "").strip()
    event_id = str(body.get("event_id") or "").strip()
    if not user_id:
        log("team_join_without_user", team_id=team_id, event_id=event_id)
        return {"ok": True, "action": "ignored_no_user"}

    enabled = welcome_enabled(env)
    skip_reason = join_skip_reason(user_obj)
    if skip_reason:
        status = "skipped"
    elif not enabled:
        status = "disabled"
    else:
        status = "pending"
    tracking_id = new_tracking_id() if status == "pending" else ""
    now = iso(utc_now())
    try:
        claimed = await d1_run(
            env,
            (
                "INSERT INTO team_joins (team_id, user_id, event_id, joined_at, welcome_status, "
                "detail, tracking_id) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING"
            ),
            [team_id, user_id, event_id, now, status, skip_reason, tracking_id],
        ) > 0
        recorded = claimed
    except Exception as error:
        # D1 down or the migration missing. A welcome matters more than the record, so
        # send anyway on a first delivery; a Slack retry of it is assumed already handled.
        log("team_join_record_failed", team_id=team_id, event_id=event_id, error=type(error).__name__)
        claimed = not retry_num
        recorded = False
    if not claimed:
        log("team_join_duplicate", team_id=team_id, event_id=event_id, retry_num=retry_num)
        return {"ok": True, "action": "duplicate"}
    if status != "pending":
        log("team_join_recorded", team_id=team_id, event_id=event_id, status=status, reason=skip_reason)
        return {"ok": True, "action": "recorded", "welcome": status}

    async def deferred():
        row_tracking_id = tracking_id if recorded else ""
        try:
            await deliver_welcome(env, team_id, user_id, event_id, row_tracking_id, now)
        except Exception as error:
            # Nothing above should raise; if it does, leave an honest record, not "pending".
            log("welcome_crashed", team_id=team_id, user_id=user_id, event_id=event_id,
                error=type(error).__name__)
            await _finish(env, row_tracking_id,
                          {"welcome_status": "failed", "detail": "crash:" + type(error).__name__})

    await run_after_response(ctx, deferred)
    return {"ok": True, "action": "accepted"}


async def _finish(env, tracking_id, fields):
    """Write the outcome onto the join's row (found by its tracking id)."""
    if not tracking_id:
        return
    columns = sorted(fields)
    try:
        await d1_run(
            env,
            "UPDATE team_joins SET {0} WHERE tracking_id = ?".format(
                ", ".join("{0} = ?".format(c) for c in columns)
            ),
            [fields[c] for c in columns] + [tracking_id],
        )
    except Exception as error:
        log("team_join_update_failed", error=type(error).__name__)


async def deliver_welcome(env, team_id, user_id, event_id, tracking_id, joined_at):
    """Open the DM and post the welcome; record failed/sent/delivered on the join's row."""
    attempts = 0
    try:
        since = iso(utc_now() - timedelta(days=REWELCOME_AFTER_DAYS))
        earlier = await d1_all(
            env,
            (
                "SELECT id FROM team_joins WHERE team_id = ? AND user_id = ? AND delivered_at != '' "
                "AND joined_at >= ? LIMIT 1"
            ),
            [team_id, user_id, since],
        )
        if earlier:
            log("welcome_skipped_already_welcomed", team_id=team_id, user_id=user_id, event_id=event_id)
            await _finish(env, tracking_id, {"welcome_status": "skipped", "detail": "already_welcomed"})
            return {"ok": True, "action": "already_welcomed"}
    except Exception as error:
        log("welcome_history_lookup_failed", team_id=team_id, error=type(error).__name__)

    token = await welcome_token(env, team_id)
    if not token:
        log("welcome_failed", team_id=team_id, user_id=user_id, event_id=event_id, error="missing_token")
        await _finish(env, tracking_id, {"welcome_status": "failed", "detail": "missing_token"})
        return {"ok": False, "error": "missing_token"}

    top = []
    try:
        stats = await state_get(env, "channels:" + team_id)
        top = list(((stats or {}).get("value") or {}).get("top") or [])
    except Exception as error:
        log("welcome_channel_stats_failed", team_id=team_id, error=type(error).__name__)
    text, template_loaded = render_welcome(team_id, user_id, top)
    if not template_loaded:
        log("welcome_template_missing", team_id=team_id)

    opened = await slack_call(token, "conversations.open", {"users": user_id})
    attempts += int(opened.get("attempts") or 1)
    channel = opened.get("channel")
    dm_channel = str((channel or {}).get("id") if isinstance(channel, dict) else channel or "")
    if not opened.get("ok") or not dm_channel:
        error_code = str(opened.get("error") or "dm_open_failed")
        log("welcome_failed", team_id=team_id, user_id=user_id, event_id=event_id,
            stage="conversations.open", error=error_code)
        await _finish(env, tracking_id, {
            "welcome_status": "failed", "detail": "conversations.open:" + error_code, "attempts": attempts,
        })
        return {"ok": False, "error": error_code}

    sent_at = iso(utc_now())
    posted = await slack_call(token, "chat.postMessage", {
        "channel": dm_channel,
        "text": "Welcome to the OWASP Slack Community!",
        "blocks": build_welcome_blocks(env, text, tracking_id or new_tracking_id()),
        "unfurl_links": False,
        "unfurl_media": False,
    })
    attempts += int(posted.get("attempts") or 1)
    message_ts = str(posted.get("ts") or "")
    delivered = bool(posted.get("ok") and message_ts and posted.get("channel"))
    if not posted.get("ok"):
        error_code = str(posted.get("error") or "post_failed")
        log("welcome_failed", team_id=team_id, user_id=user_id, event_id=event_id,
            stage="chat.postMessage", error=error_code)
        await _finish(env, tracking_id, {
            "welcome_status": "failed", "detail": "chat.postMessage:" + error_code,
            "dm_channel": dm_channel, "sent_at": sent_at, "attempts": attempts,
        })
        return {"ok": False, "error": error_code}
    log("welcome_sent", team_id=team_id, user_id=user_id, event_id=event_id, delivered=delivered,
        template=("file" if template_loaded else "fallback"))
    await _finish(env, tracking_id, {
        "welcome_status": "sent",
        "detail": "" if template_loaded else "fallback_template",
        "dm_channel": dm_channel,
        "message_ts": message_ts,
        "sent_at": sent_at,
        "delivered_at": iso(utc_now()) if delivered else "",
        "attempts": attempts,
    })
    return {"ok": True, "delivered": delivered}


# --------------------------------------------------------------------------- logo hit


def logo_hit_agent(user_agent):
    agent = str(user_agent or "")
    if "Slack-ImgProxy" in agent:
        return "slack-imgproxy"
    if "Slack/" in agent or "Slack_SSB" in agent or "chatlyio" in agent:
        return "slack-client"
    return "other"


async def record_logo_hit(env, tracking_id, user_agent):
    """First load of a welcome's tracked logo sets opened_at; later loads change nothing.
    The IP address isn't stored."""
    tracking_id = str(tracking_id or "").strip()
    if not TRACKING_ID_PATTERN.fullmatch(tracking_id):
        return False
    agent = str(user_agent or "")[:160]
    try:
        return await d1_run(
            env,
            (
                "UPDATE team_joins SET opened_at = ?, opened_via = ? "
                "WHERE tracking_id = ? AND opened_at = ''"
            ),
            [iso(utc_now()), "{0}: {1}".format(logo_hit_agent(agent), agent), tracking_id],
        ) > 0
    except Exception as error:
        log("logo_hit_failed", error=type(error).__name__)
        return False


def logo_redirect_target(env):
    return base_url(env) + BLT_LOGO_PATH


# --------------------------------------------------------------------------- reports


def _pct(part, whole):
    return round(part * 100.0 / whole, 1) if whole else 0.0


def summarize_joins(rows, now=None, grace_minutes=HEALTH_GRACE_MINUTES):
    """Counts over team_joins rows: joins, eligible (not skipped), attempted, delivered…

    A row younger than the grace period that is still pending isn't counted as eligible:
    its welcome may still be on the way."""
    current = now or utc_now()
    grace_cutoff = iso(current - timedelta(minutes=grace_minutes))
    out = {"joins": 0, "eligible": 0, "attempted": 0, "delivered": 0, "opened": 0,
           "failed": 0, "skipped": 0, "disabled": 0, "pending": 0}
    for row in rows:
        out["joins"] += 1
        status = str(row.get("welcome_status") or "")
        if status in ("skipped", "disabled"):
            out[status] += 1
            continue
        if status == "pending":
            out["pending"] += 1
            if str(row.get("joined_at") or "") > grace_cutoff:
                continue
        out["eligible"] += 1
        if row.get("sent_at"):
            out["attempted"] += 1
        if row.get("delivered_at"):
            out["delivered"] += 1
            if row.get("opened_at"):
                out["opened"] += 1
        if status == "failed":
            out["failed"] += 1
    out["delivered_pct"] = _pct(out["delivered"], out["eligible"])
    out["opened_pct"] = _pct(out["opened"], out["delivered"])
    return out


REPORT_COLUMNS = (
    "id, user_id, event_id, joined_at, welcome_status, detail, attempts, sent_at, "
    "delivered_at, opened_at, opened_via"
)


async def joins_since(env, team_id, since):
    return await d1_all(
        env,
        "SELECT {0} FROM team_joins WHERE team_id = ? AND joined_at >= ? ORDER BY joined_at DESC".format(
            REPORT_COLUMNS
        ),
        [team_id, iso(since)],
    )


async def welcome_report(env, team_id, now=None, limit=100):
    """7- and 30-day totals and the latest `limit` joins, for the admin page."""
    current = now or utc_now()
    rows_30 = await joins_since(env, team_id, current - timedelta(days=30))
    cutoff_7 = iso(current - timedelta(days=7))
    rows_7 = [r for r in rows_30 if str(r.get("joined_at") or "") >= cutoff_7]
    return {
        "team_id": team_id,
        "enabled": welcome_enabled(env),
        "generated_at": iso(current),
        "last_7_days": summarize_joins(rows_7, current),
        "last_30_days": summarize_joins(rows_30, current),
        "joins": rows_30[: int(limit)],
    }


def daily_join_history(rows, now=None, days=30):
    current = (now or utc_now()).astimezone(timezone.utc).date()
    joins, delivered = {}, {}
    for row in rows:
        day = str(row.get("joined_at") or "")[:10]
        joins[day] = joins.get(day, 0) + 1
        if row.get("delivered_at"):
            delivered[day] = delivered.get(day, 0) + 1
    history = []
    for offset in range(days - 1, -1, -1):
        day = (current - timedelta(days=offset)).isoformat()
        history.append({"date": day, "joins": joins.get(day, 0), "welcomed": delivered.get(day, 0)})
    return history


async def community_stats(env, team_id, now=None):
    """Public OWASP community numbers: daily joins for 30 days and the biggest channels."""
    current = now or utc_now()
    cached = _public_stats_cache.get(team_id)
    if cached and (current - cached[0]).total_seconds() < PUBLIC_STATS_TTL_SECONDS:
        return cached[1]
    rows = await d1_all(
        env,
        "SELECT joined_at, delivered_at FROM team_joins WHERE team_id = ? AND joined_at >= ?",
        [team_id, iso(current - timedelta(days=30))],
    )
    history = daily_join_history(rows, current)
    stats = await state_get(env, "channels:" + team_id)
    channels = (stats or {}).get("value") or {}
    payload = {
        "ok": True,
        "team_id": team_id,
        "joins_last_7_days": sum(day["joins"] for day in history[-7:]),
        "joins_last_30_days": sum(day["joins"] for day in history),
        "welcomed_last_30_days": sum(day["welcomed"] for day in history),
        "team_join_history": history,
        "channels_with_most_members": [
            {"id": ch.get("id"), "name": ch.get("name"), "members": ch.get("members")}
            for ch in (channels.get("top") or [])
        ],
        "public_channel_count": channels.get("channel_count") or 0,
        "channels_updated_at": (stats or {}).get("updated_at") or "",
        "generated_at": iso(current),
    }
    _public_stats_cache[team_id] = (current, payload)
    return payload


# --------------------------------------------------------------------------- health


def _parse_time(value):
    try:
        parsed = datetime.fromisoformat(str(value or ""))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def evaluate_health(enabled, summary, auth, last_join_at, last_delivered_at, template_loaded,
                    now=None):
    """(http_status, body) for /health/welcome. Pure, so the rules are unit-tested.

    Unhealthy (503) when the welcome is on and any of:
      * joins arrived in the last 24 h (older than the grace period) and none was delivered;
      * at least LOW_RATE_MIN_JOINS eligible joins and under LOW_RATE_PCT % delivered;
      * the last auth.test failed, or the token belongs to another workspace;
      * no auth.test result in AUTH_CHECK_MAX_AGE_HOURS (the hourly cron isn't running);
      * the welcome text file didn't load (welcomes would go out with the short fallback).
    When the welcome is off (before the cut-over, or rolled back to sammich) it answers 200
    with status welcome-disabled; the problems are still listed.
    """
    current = now or utc_now()
    problems = []
    if summary["eligible"] > 0 and summary["delivered"] == 0:
        problems.append("joins_without_welcomes_24h")
    elif summary["eligible"] >= LOW_RATE_MIN_JOINS and summary["delivered_pct"] < LOW_RATE_PCT:
        problems.append("low_delivery_rate_24h")
    auth_value = (auth or {}).get("value") or {}
    checked_at = _parse_time((auth or {}).get("updated_at"))
    if not auth:
        problems.append("slack_auth_never_checked")
    else:
        if not auth_value.get("ok"):
            problems.append("slack_auth_failed:{0}".format(auth_value.get("error") or "unknown"))
        if checked_at is None or current - checked_at > timedelta(hours=AUTH_CHECK_MAX_AGE_HOURS):
            problems.append("slack_auth_check_stale")
    if not template_loaded:
        problems.append("welcome_template_missing")
    if not enabled:
        status_word, http_status = HEALTH_DISABLED, 200
    elif problems:
        status_word, http_status = HEALTH_FAILING, 503
    else:
        status_word, http_status = HEALTH_OK, 200
    return http_status, {
        "service": "blt-lettuce",
        "check": "owasp-welcome",
        "status": status_word,
        "enabled": bool(enabled),
        "problems": problems,
        "last_team_join_at": last_join_at or "",
        "last_welcome_delivered_at": last_delivered_at or "",
        "last_24h": summary,
        "slack_auth": {
            "ok": bool(auth_value.get("ok")),
            "error": auth_value.get("error") or "",
            "checked_at": (auth or {}).get("updated_at") or "",
        },
        "checked_at": iso(current),
    }


async def health(env, team_id, now=None):
    current = now or utc_now()
    try:
        rows = await joins_since(env, team_id, current - timedelta(hours=24))
        last_join = await d1_all(
            env,
            "SELECT joined_at FROM team_joins WHERE team_id = ? ORDER BY joined_at DESC LIMIT 1",
            [team_id],
        )
        last_delivered = max((str(r.get("delivered_at") or "") for r in rows), default="")
        if not last_delivered:
            older = await d1_all(
                env,
                (
                    "SELECT delivered_at FROM team_joins WHERE team_id = ? AND delivered_at != '' "
                    "ORDER BY joined_at DESC LIMIT 1"
                ),
                [team_id],
            )
            last_delivered = (older[0] if older else {}).get("delivered_at") or ""
        auth = await state_get(env, "auth:" + team_id)
    except Exception as error:
        log("health_query_failed", team_id=team_id, error=type(error).__name__)
        body = {"service": "blt-lettuce", "check": "owasp-welcome", "status": HEALTH_FAILING,
                "enabled": welcome_enabled(env), "problems": ["database_error"],
                "checked_at": iso(current)}
        return (503 if welcome_enabled(env) else 200), body
    return evaluate_health(
        welcome_enabled(env),
        summarize_joins(rows, current),
        auth,
        (last_join[0] if last_join else {}).get("joined_at") or "",
        last_delivered or "",
        load_welcome_template(team_id) is not None,
        current,
    )


# --------------------------------------------------------------------------- cron


async def check_slack_auth(env, team_id, now=None):
    """auth.test with the team's token, stored for /health/welcome (one write)."""
    token = await welcome_token(env, team_id)
    result = await slack_call(token, "auth.test", {}) if token else {"ok": False, "error": "missing_token"}
    value = {"ok": bool(result.get("ok")), "error": str(result.get("error") or "")}
    if value["ok"] and str(result.get("team_id") or "") != team_id:
        value = {"ok": False, "error": "token_for_other_team"}
    if value["ok"]:
        value["bot_user_id"] = str(result.get("user_id") or "")
    await state_put(env, "auth:" + team_id, value, now)
    if not value["ok"]:
        log("slack_auth_failed", team_id=team_id, error=value["error"])
    return value


def top_channels_by_members(channels, limit=CHANNEL_STATS_TOP):
    rows = [
        {"id": str(ch.get("id") or ""), "name": str(ch.get("name") or ""),
         "members": int(ch.get("num_members") or 0)}
        for ch in channels
        if isinstance(ch, dict) and ch.get("id") and ch.get("name") and not ch.get("is_archived")
    ]
    rows.sort(key=lambda row: (-row["members"], row["name"]))
    return rows[:limit]


async def refresh_channel_stats(env, team_id, now=None):
    """Public channels by member count, from conversations.list, kept as one welcome_state
    row (the OWASP workspace has thousands of channels; a row each would cost a write each)."""
    token = await welcome_token(env, team_id)
    if not token:
        return {"ok": False, "error": "missing_token"}
    channels, cursor, pages = [], "", 0
    while pages < CHANNEL_LIST_MAX_PAGES:
        query = {"limit": "1000", "types": "public_channel", "exclude_archived": "true"}
        if cursor:
            query["cursor"] = cursor
        page = await slack_call(token, "conversations.list", None, http_method="GET", query=query)
        pages += 1
        if not page.get("ok"):
            log("channel_stats_failed", team_id=team_id, error=page.get("error"))
            return {"ok": False, "error": str(page.get("error") or "")}
        channels.extend(page.get("channels") or [])
        cursor = str((page.get("response_metadata") or {}).get("next_cursor") or "")
        if not cursor:
            break
    value = {"top": top_channels_by_members(channels), "channel_count": len(channels),
             "complete": not cursor}
    await state_put(env, "channels:" + team_id, value, now)
    return {"ok": True, "channels": len(channels)}


async def run_welcome_cron(env, now=None):
    """Each cron run (hourly): auth.test per welcome team; channel stats once a day."""
    current = now or utc_now()
    summary = {}
    for team_id in welcome_team_ids(env):
        result = {}
        try:
            result["auth_ok"] = (await check_slack_auth(env, team_id, current)).get("ok")
        except Exception as error:
            log("welcome_cron_auth_failed", team_id=team_id, error=type(error).__name__)
            result["auth_ok"] = False
        try:
            stats = await state_get(env, "channels:" + team_id)
            updated = _parse_time((stats or {}).get("updated_at"))
            if updated is None or current - updated > timedelta(hours=CHANNEL_STATS_MAX_AGE_HOURS):
                result["channel_stats"] = await refresh_channel_stats(env, team_id, current)
        except Exception as error:
            log("welcome_cron_channel_stats_failed", team_id=team_id, error=type(error).__name__)
        summary[team_id] = result
    return summary


# --------------------------------------------------------------------------- admin


def admin_authorized(env, authorization_header):
    """HTTP Basic against the ADMIN_USERNAME / ADMIN_PASSWORD secrets. Fails closed."""
    expected_user = env_str(env, "ADMIN_USERNAME")
    expected_password = env_str(env, "ADMIN_PASSWORD")
    if not expected_user or not expected_password:
        return False
    header = str(authorization_header or "")
    if not header.lower().startswith("basic "):
        return False
    try:
        decoded = base64.b64decode(header.split(" ", 1)[1].strip()).decode("utf-8")
    except Exception:
        return False
    user, sep, password = decoded.partition(":")
    if not sep:
        return False
    return hmac.compare_digest(user.encode(), expected_user.encode()) and hmac.compare_digest(
        password.encode(), expected_password.encode()
    )


OPENED_EXPLANATION = (
    "Eligible: joins lettuce should welcome (not bots, not deleted, not already welcomed in "
    "the last 30 days). Sent: chat.postMessage was called. Delivered: Slack answered ok with a "
    "message ts. Opened (logo loaded): the welcome's tracked footer logo was first fetched, by "
    "a Slack app or Slack's image proxy on a client's behalf. Slack loads it lazily, so it "
    "usually means a client showed the message, but it can be a notification preview or "
    "another device, the proxy caches it so only the first load is seen, and no load doesn't "
    "prove the DM went unread."
)


REPORT_CSS = (
    "body{font:14px system-ui,sans-serif;margin:16px;color:#111;background:#fff}"
    "table{border-collapse:collapse;margin-bottom:16px}th,td{border-bottom:1px solid #ddd;"
    "padding:4px 8px;text-align:left;vertical-align:top}small{color:#555}.note{max-width:900px}"
)


def render_report_html(report):
    def stat(label, data):
        return (
            "<tr><th>{0}</th><td>{1}</td><td>{2}</td><td>{3}</td><td>{4} ({5}%)</td>"
            "<td>{6} ({7}% of delivered)</td><td>{8}</td><td>{9}</td></tr>"
        ).format(
            _html_escape(label), data["joins"], data["eligible"], data["attempted"],
            data["delivered"], data["delivered_pct"], data["opened"], data["opened_pct"],
            data["failed"], data["skipped"] + data["disabled"],
        )

    rows = "".join(
        "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td><td>{4}</td><td>{5}</td>"
        "<td><small>{6}</small></td><td>{7}</td></tr>".format(
            _html_escape(str(r.get("joined_at") or "")[:19]),
            _html_escape(str(r.get("user_id") or "")),
            _html_escape(str(r.get("welcome_status") or "")),
            _html_escape(str(r.get("sent_at") or "")[:19]),
            _html_escape(str(r.get("delivered_at") or "")[:19]),
            _html_escape(str(r.get("opened_at") or "")[:19]),
            _html_escape(str(r.get("opened_via") or "")[:80]),
            _html_escape(str(r.get("detail") or "")),
        )
        for r in report.get("joins") or []
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Welcome delivery</title><style>{6}</style></head><body>"
        "<h1>OWASP welcome DM delivery</h1>"
        "<p>Team {0}. Welcome sending is <b>{1}</b> (WELCOME_ENABLED).</p>"
        "<table><tr><th></th><th>Joins</th><th>Eligible</th><th>Sent</th><th>Delivered</th>"
        "<th>Opened (logo loaded)</th><th>Failed</th><th>Skipped / off</th></tr>{2}{3}</table>"
        "<p class='note'>{4}</p><h2>Latest joins</h2>"
        "<table><tr><th>Joined (UTC)</th><th>User</th><th>Welcome</th><th>Sent</th>"
        "<th>Delivered</th><th>Opened</th><th>Loaded by</th><th>Detail</th></tr>{5}</table>"
        "</body></html>"
    ).format(
        _html_escape(report["team_id"]),
        "on" if report["enabled"] else "off",
        stat("Last 7 days", report["last_7_days"]),
        stat("Last 30 days", report["last_30_days"]),
        _html_escape(OPENED_EXPLANATION),
        rows,
        REPORT_CSS,
    )


def query_param(query_string, name):
    return (parse_qs(query_string or "").get(name) or [""])[0]
