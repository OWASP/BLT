"""BLT Timer Web Cloudflare Python Worker.

The Worker provides cookie-authenticated account and manual work-log APIs backed by D1.
"""

import csv
import io
import json
import re
import time
import uuid
from urllib.parse import urlparse, parse_qs

from workers import Response

try:
    from .auth import (
        SESSION_COOKIE_NAME,
        build_clear_session_cookie,
        build_session_cookie,
        generate_session_token,
        hash_password,
        normalize_email,
        normalize_username,
        parse_cookie,
        session_hash,
        verify_password,
    )
except ImportError:  # pragma: no cover - Cloudflare may load src/ as worker root.
    from auth import (
        SESSION_COOKIE_NAME,
        build_clear_session_cookie,
        build_session_cookie,
        generate_session_token,
        hash_password,
        normalize_email,
        normalize_username,
        parse_cookie,
        session_hash,
        verify_password,
    )


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PATCH, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}

SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60
DEFAULT_SESSION_SECRET = "development-blt-timer-session-secret"


def json_ok(data, status=200, headers=None):
    """Return a JSON response with CORS headers."""
    response_headers = {"Content-Type": "application/json", **_CORS_HEADERS}
    if headers:
        response_headers.update(headers)
    return Response(json.dumps(data), status=status, headers=response_headers)


def json_err(message, status=400, headers=None):
    """Return a JSON error response with CORS headers."""
    response_headers = {"Content-Type": "application/json", **_CORS_HEADERS}
    if headers:
        response_headers.update(headers)
    return Response(json.dumps({"error": message}), status=status, headers=response_headers)


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def handle_root():
    return Response("", status=302, headers={"Location": "/index.html", **_CORS_HEADERS})


def handle_health():
    return json_ok({"status": "healthy", "timestamp": int(time.time() * 1000)})


def _now_ms():
    return int(time.time() * 1000)


def _env_value(env, name, default=None):
    try:
        value = getattr(env, name)
    except Exception:
        value = None
    if value is not None:
        return value
    try:
        return env[name]
    except Exception:
        return default


def js_to_py(value):
    if value is None:
        return None
    if hasattr(value, "to_py"):
        try:
            return value.to_py()
        except Exception:
            pass
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return [js_to_py(item) for item in value]
    try:
        return dict(value)
    except Exception:
        return value


def _dict(value):
    data = js_to_py(value)
    return data if isinstance(data, dict) else None


def _list(value):
    data = js_to_py(value)
    return data if isinstance(data, list) else []


def _session_secret(env):
    return _env_value(env, "SESSION_SECRET", DEFAULT_SESSION_SECRET)


def _is_secure_request(request):
    return str(getattr(request, "url", "")).startswith("https://")


async def _read_json_body(request):
    try:
        return json.loads(await request.text())
    except Exception:
        return None


def _user_public(row):
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "displayName": row.get("display_name"),
        "timezone": row.get("timezone", "UTC"),
        "createdAt": row.get("created_at"),
        "updatedAt": row.get("updated_at"),
    }


async def _create_auth_session(request, env, user_id):
    token = generate_session_token()
    now = _now_ms()
    expires_at = now + SESSION_MAX_AGE_SECONDS * 1000
    await env.DB.prepare(
        "INSERT INTO auth_sessions (id, user_id, session_token_hash, expires_at, created_at, last_seen_at)"
        " VALUES (?, ?, ?, ?, ?, ?)"
    ).bind(
        str(uuid.uuid4()),
        user_id,
        session_hash(token, _session_secret(env)),
        expires_at,
        now,
        now,
    ).run()
    cookie = build_session_cookie(
        token,
        SESSION_MAX_AGE_SECONDS,
        secure=_is_secure_request(request),
    )
    return token, cookie


async def get_current_user(request, env):
    cookie_header = request.headers.get("Cookie") if request.headers else None
    token = parse_cookie(cookie_header).get(SESSION_COOKIE_NAME)
    if not token:
        return None

    now = _now_ms()
    row = _dict(await env.DB.prepare(
        "SELECT users.id, users.username, users.email, users.display_name, users.timezone,"
        " users.created_at, users.updated_at"
        " FROM auth_sessions"
        " JOIN users ON users.id = auth_sessions.user_id"
        " WHERE auth_sessions.session_token_hash = ? AND auth_sessions.expires_at > ?"
    ).bind(session_hash(token, _session_secret(env)), now).first())
    if row is None:
        return None

    await env.DB.prepare(
        "UPDATE auth_sessions SET last_seen_at = ? WHERE session_token_hash = ?"
    ).bind(now, session_hash(token, _session_secret(env))).run()
    return row


async def handle_register(request, env):
    body = await _read_json_body(request)
    if body is None:
        return json_err("Invalid JSON body", 400)

    try:
        email = normalize_email(body.get("email"))
        username = normalize_username(body.get("username"))
        timezone = _normalize_timezone(body.get("timezone"))
    except ValueError as exc:
        return json_err(str(exc), 400)

    password = body.get("password")
    if not isinstance(password, str) or len(password) < 8:
        return json_err("Password must be at least 8 characters", 400)

    display_name = body.get("displayName") or body.get("display_name") or username
    if not isinstance(display_name, str) or not display_name.strip():
        display_name = username
    display_name = display_name.strip()[:80]

    existing = _dict(await env.DB.prepare(
        "SELECT id FROM users WHERE email = ? OR username = ? LIMIT 1"
    ).bind(email, username).first())
    if existing is not None:
        return json_err("Email or username already exists", 409)

    now = _now_ms()
    user = {
        "id": str(uuid.uuid4()),
        "username": username,
        "email": email,
        "display_name": display_name,
        "timezone": timezone,
        "created_at": now,
        "updated_at": now,
    }
    await env.DB.prepare(
        "INSERT INTO users (id, username, email, password_hash, display_name, timezone, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    ).bind(
        user["id"],
        username,
        email,
        hash_password(password),
        display_name,
        timezone,
        now,
        now,
    ).run()
    _token, cookie = await _create_auth_session(request, env, user["id"])
    return json_ok({"user": _user_public(user)}, status=201, headers={"Set-Cookie": cookie})


async def handle_login(request, env):
    body = await _read_json_body(request)
    if body is None:
        return json_err("Invalid JSON body", 400)

    login = body.get("login") or body.get("email") or body.get("username")
    password = body.get("password")
    if not isinstance(login, str) or not isinstance(password, str):
        return json_err("Invalid credentials", 401)

    normalized_login = login.strip().lower()
    row = _dict(await env.DB.prepare(
        "SELECT * FROM users WHERE email = ? OR username = ? LIMIT 1"
    ).bind(normalized_login, normalized_login).first())
    if row is None or not verify_password(password, row.get("password_hash")):
        return json_err("Invalid credentials", 401)

    _token, cookie = await _create_auth_session(request, env, row["id"])
    return json_ok({"user": _user_public(row)}, headers={"Set-Cookie": cookie})


async def handle_logout(request, env):
    cookie_header = request.headers.get("Cookie") if request.headers else None
    token = parse_cookie(cookie_header).get(SESSION_COOKIE_NAME)
    if token:
        await env.DB.prepare(
            "DELETE FROM auth_sessions WHERE session_token_hash = ?"
        ).bind(session_hash(token, _session_secret(env))).run()
    clear_cookie = build_clear_session_cookie(secure=_is_secure_request(request))
    return json_ok({"ok": True}, headers={"Set-Cookie": clear_cookie})


async def handle_me(request, env):
    user = await get_current_user(request, env)
    if user is None:
        return json_err("Not authenticated", 401)
    return json_ok({"user": _user_public(user)})


def _normalize_timezone(value):
    timezone = str(value or "UTC").strip()
    if not re.fullmatch(r"UTC|[A-Za-z][A-Za-z_+-]*(?:/[A-Za-z][A-Za-z_+-]*)+", timezone):
        raise ValueError("Timezone must be a valid IANA timezone name")
    return timezone


def _normalize_profile_payload(body):
    if not isinstance(body, dict):
        raise ValueError("Invalid JSON body")

    display_name = str(body.get("displayName") or "").strip()
    if not display_name or len(display_name) > 80:
        raise ValueError("Display name must be between 1 and 80 characters")
    timezone = _normalize_timezone(body.get("timezone"))

    return {"display_name": display_name, "timezone": timezone}


async def handle_update_me(request, env):
    user = await get_current_user(request, env)
    if user is None:
        return json_err("Not authenticated", 401)

    body = await _read_json_body(request)
    try:
        profile = _normalize_profile_payload(body)
    except ValueError as exc:
        return json_err(str(exc), 400)

    now = _now_ms()
    await env.DB.prepare(
        "UPDATE users SET display_name = ?, timezone = ?, updated_at = ? WHERE id = ?"
    ).bind(
        profile["display_name"],
        profile["timezone"],
        now,
        user["id"],
    ).run()
    user.update({
        "display_name": profile["display_name"],
        "timezone": profile["timezone"],
        "updated_at": now,
    })
    return json_ok({"user": _user_public(user)})


def _rows(result):
    data = _dict(result)
    if isinstance(data, dict):
        return data.get("results") or []
    return getattr(result, "results", []) or []


def _to_int(value, field_name):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer")


def _normalize_log_payload(body, partial=False):
    if not isinstance(body, dict):
        raise ValueError("Invalid JSON body")

    data = {}
    if "title" in body or not partial:
        title = str(body.get("title") or "").strip()
        if not title:
            raise ValueError("Title is required")
        data["title"] = title[:200]

    for field in ["notes", "project", "reference_url"]:
        if field in body:
            value = body.get(field)
            data[field] = str(value).strip() if value is not None else None

    if "referenceUrl" in body:
        value = body.get("referenceUrl")
        data["reference_url"] = str(value).strip() if value is not None else None

    if "source" in body:
        source = str(body.get("source") or "web").strip().lower()
        data["source"] = source[:32] or "web"
    elif not partial:
        data["source"] = "web"

    if "start_time" in body or "startTime" in body or not partial:
        data["start_time"] = _to_int(body.get("start_time", body.get("startTime")), "start_time")
    if "end_time" in body or "endTime" in body or not partial:
        data["end_time"] = _to_int(body.get("end_time", body.get("endTime")), "end_time")

    if "duration_seconds" in body or "durationSeconds" in body:
        data["duration_seconds"] = _to_int(
            body.get("duration_seconds", body.get("durationSeconds")),
            "duration_seconds",
        )
    elif not partial and "start_time" in data and "end_time" in data:
        data["duration_seconds"] = max(0, int((data["end_time"] - data["start_time"]) / 1000))

    if "start_time" in data and "end_time" in data and data["end_time"] < data["start_time"]:
        raise ValueError("end_time must be after start_time")
    if "duration_seconds" in data and data["duration_seconds"] < 0:
        raise ValueError("duration_seconds must be non-negative")

    return data


def _row_to_log(row):
    return {
        "id": row["id"],
        "userId": row["user_id"],
        "title": row["title"],
        "notes": row.get("notes"),
        "project": row.get("project"),
        "referenceUrl": row.get("reference_url"),
        "source": row.get("source", "web"),
        "startTime": row["start_time"],
        "endTime": row["end_time"],
        "durationSeconds": row["duration_seconds"],
        "createdAt": row.get("created_at"),
        "updatedAt": row.get("updated_at"),
    }


async def handle_create_log(request, env):
    user = await get_current_user(request, env)
    if user is None:
        return json_err("Not authenticated", 401)

    body = await _read_json_body(request)
    try:
        data = _normalize_log_payload(body)
    except ValueError as exc:
        return json_err(str(exc), 400)

    now = _now_ms()
    log_id = str(uuid.uuid4())
    await env.DB.prepare(
        "INSERT INTO work_logs (id, user_id, title, notes, project, reference_url, source, start_time, end_time, duration_seconds, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    ).bind(
        log_id,
        user["id"],
        data["title"],
        data.get("notes"),
        data.get("project"),
        data.get("reference_url"),
        data.get("source", "web"),
        data["start_time"],
        data["end_time"],
        data["duration_seconds"],
        now,
        now,
    ).run()
    row = _dict(await env.DB.prepare(
        "SELECT * FROM work_logs WHERE id = ? AND user_id = ?"
    ).bind(log_id, user["id"]).first())
    return json_ok({"log": _row_to_log(row)}, 201)


async def handle_list_logs(request, env, query_string):
    user = await get_current_user(request, env)
    if user is None:
        return json_err("Not authenticated", 401)

    params = parse_qs(query_string or "")
    limit = min(max(int(params.get("limit", ["50"])[0] or 50), 1), 100)
    where = ["user_id = ?"]
    binds = [user["id"]]

    if params.get("project", [""])[0]:
        where.append("project = ?")
        binds.append(params["project"][0])
    if params.get("start", [""])[0]:
        where.append("start_time >= ?")
        binds.append(int(params["start"][0]))
    if params.get("end", [""])[0]:
        where.append("start_time <= ?")
        binds.append(int(params["end"][0]))
    if params.get("q", [""])[0]:
        where.append("(title LIKE ? OR notes LIKE ?)")
        search = f"%{params['q'][0]}%"
        binds.extend([search, search])

    sql = "SELECT * FROM work_logs WHERE " + " AND ".join(where) + " ORDER BY start_time DESC LIMIT ?"
    result = await env.DB.prepare(sql).bind(*binds, limit).all()
    return json_ok({"logs": [_row_to_log(row) for row in _rows(result)]})


async def handle_get_log(request, env, log_id):
    user = await get_current_user(request, env)
    if user is None:
        return json_err("Not authenticated", 401)

    row = _dict(await env.DB.prepare(
        "SELECT * FROM work_logs WHERE id = ? AND user_id = ?"
    ).bind(log_id, user["id"]).first())
    if row is None:
        return json_err("Log not found", 404)
    return json_ok({"log": _row_to_log(row)})


async def handle_update_log(request, env, log_id):
    user = await get_current_user(request, env)
    if user is None:
        return json_err("Not authenticated", 401)

    existing = _dict(await env.DB.prepare(
        "SELECT * FROM work_logs WHERE id = ? AND user_id = ?"
    ).bind(log_id, user["id"]).first())
    if existing is None:
        return json_err("Log not found", 404)

    body = await _read_json_body(request)
    try:
        data = _normalize_log_payload(body, partial=True)
    except ValueError as exc:
        return json_err(str(exc), 400)
    if not data:
        return json_err("No fields to update", 400)

    data["updated_at"] = _now_ms()
    assignments = [f"{key} = ?" for key in data]
    await env.DB.prepare(
        "UPDATE work_logs SET " + ", ".join(assignments) + " WHERE id = ? AND user_id = ?"
    ).bind(*data.values(), log_id, user["id"]).run()
    row = _dict(await env.DB.prepare(
        "SELECT * FROM work_logs WHERE id = ? AND user_id = ?"
    ).bind(log_id, user["id"]).first())
    return json_ok({"log": _row_to_log(row)})


async def handle_delete_log(request, env, log_id):
    user = await get_current_user(request, env)
    if user is None:
        return json_err("Not authenticated", 401)

    existing = _dict(await env.DB.prepare(
        "SELECT id FROM work_logs WHERE id = ? AND user_id = ?"
    ).bind(log_id, user["id"]).first())
    if existing is None:
        return json_err("Log not found", 404)
    await env.DB.prepare(
        "DELETE FROM work_logs WHERE id = ? AND user_id = ?"
    ).bind(log_id, user["id"]).run()
    return json_ok({"ok": True})


def _range_start_ms(range_name):
    now_seconds = int(time.time())
    if range_name == "today":
        return (now_seconds - (now_seconds % 86400)) * 1000
    if range_name == "week":
        return (now_seconds - 7 * 86400) * 1000
    if range_name == "month":
        return (now_seconds - 30 * 86400) * 1000
    return 0


async def handle_stats(request, env, query_string):
    user = await get_current_user(request, env)
    if user is None:
        return json_err("Not authenticated", 401)
    params = parse_qs(query_string or "")
    range_name = params.get("range", ["today"])[0]
    start = _range_start_ms(range_name)
    row = _dict(await env.DB.prepare(
        "SELECT COUNT(*) AS sessions, COALESCE(SUM(duration_seconds), 0) AS total_seconds"
        " FROM work_logs WHERE user_id = ? AND start_time >= ?"
    ).bind(user["id"], start).first())
    sessions = row.get("sessions", 0) if row else 0
    total = row.get("total_seconds", 0) if row else 0
    return json_ok({
        "range": range_name,
        "sessions": sessions,
        "totalSeconds": total,
        "averageSeconds": int(total / sessions) if sessions else 0,
    })


async def _all_user_logs(env, user_id):
    result = await env.DB.prepare(
        "SELECT * FROM work_logs WHERE user_id = ? ORDER BY start_time DESC"
    ).bind(user_id).all()
    return [_row_to_log(row) for row in _rows(result)]


async def handle_export_json(request, env):
    user = await get_current_user(request, env)
    if user is None:
        return json_err("Not authenticated", 401)
    return json_ok({"logs": await _all_user_logs(env, user["id"])})


async def handle_export_csv(request, env):
    user = await get_current_user(request, env)
    if user is None:
        return json_err("Not authenticated", 401)
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "title", "notes", "project", "referenceUrl", "source", "startTime", "endTime", "durationSeconds"],
    )
    writer.writeheader()
    for log in await _all_user_logs(env, user["id"]):
        writer.writerow({key: log.get(key) for key in writer.fieldnames})
    return Response(
        output.getvalue(),
        status=200,
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": "attachment; filename=blt-timer-logs.csv",
            **_CORS_HEADERS,
        },
    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

_ROUTES = [
    ("GET",  r"^/$",                                          "root"),
    ("GET",  r"^/health$",                                    "health"),
    ("POST", r"^/api/auth/register$",                         "register"),
    ("POST", r"^/api/auth/login$",                            "login"),
    ("POST", r"^/api/auth/logout$",                           "logout"),
    ("GET",  r"^/api/me$",                                    "me"),
    ("PATCH", r"^/api/me$",                                   "update_me"),
    ("GET",  r"^/api/logs$",                                  "list_logs"),
    ("POST", r"^/api/logs$",                                  "create_log"),
    ("GET",  r"^/api/logs/(?P<sid>[^/]+)$",                   "get_log"),
    ("PATCH", r"^/api/logs/(?P<sid>[^/]+)$",                  "update_log"),
    ("DELETE", r"^/api/logs/(?P<sid>[^/]+)$",                 "delete_log"),
    ("GET",  r"^/api/stats$",                                 "stats"),
    ("GET",  r"^/api/export\.csv$",                           "export_csv"),
    ("GET",  r"^/api/export\.json$",                          "export_json"),
]


async def on_fetch(request, env):
    """Cloudflare Worker entry point."""
    if request.method == "OPTIONS":
        return Response(
            "",
            status=204,
            headers={
                **_CORS_HEADERS,
                "Access-Control-Max-Age": "86400",
            },
        )

    parsed = urlparse(request.url)
    path = parsed.path
    qs = parsed.query

    for method, pattern, name in _ROUTES:
        if request.method != method:
            continue
        m = re.match(pattern, path)
        if not m:
            continue
        sid = m.groupdict().get("sid")
        try:
            if name == "root":
                return handle_root()
            elif name == "health":
                return handle_health()
            elif name == "register":
                return await handle_register(request, env)
            elif name == "login":
                return await handle_login(request, env)
            elif name == "logout":
                return await handle_logout(request, env)
            elif name == "me":
                return await handle_me(request, env)
            elif name == "update_me":
                return await handle_update_me(request, env)
            elif name == "list_logs":
                return await handle_list_logs(request, env, qs)
            elif name == "create_log":
                return await handle_create_log(request, env)
            elif name == "get_log":
                return await handle_get_log(request, env, sid)
            elif name == "update_log":
                return await handle_update_log(request, env, sid)
            elif name == "delete_log":
                return await handle_delete_log(request, env, sid)
            elif name == "stats":
                return await handle_stats(request, env, qs)
            elif name == "export_csv":
                return await handle_export_csv(request, env)
            elif name == "export_json":
                return await handle_export_json(request, env)
        except Exception as exc:
            print(f"[ERROR] route={name} sid={sid}: {exc}")
            return json_err("Internal server error", 500)

    return json_err("Not found", 404)
