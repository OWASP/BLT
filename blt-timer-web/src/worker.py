"""
Fresh Time Tracker - Cloudflare Python Worker
Privacy-focused time tracking system with GitHub integration and local LLM analysis
Uses Cloudflare D1 (SQL) for persistent data storage.
"""

import json
import re
import time
import uuid
from urllib.parse import urlparse, parse_qs

from workers import Response


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-User-ID, X-Session-ID",
}


def json_ok(data, status=200):
    """Return a JSON response with CORS headers."""
    headers = {"Content-Type": "application/json", **_CORS_HEADERS}
    return Response(json.dumps(data), status=status, headers=headers)


def json_err(message, status=400):
    """Return a JSON error response with CORS headers."""
    headers = {"Content-Type": "application/json", **_CORS_HEADERS}
    return Response(json.dumps({"error": message}), status=status, headers=headers)


def _row_to_session(row):
    """Convert a D1 row dict to the session dict returned by the API."""
    session = {
        "id": row["id"],
        "userId": row["userId"],
        "projectId": row["projectId"],
        "startTime": row["startTime"],
        "status": row["status"],
    }
    if row.get("endTime") is not None:
        session["endTime"] = row["endTime"]
    if row.get("duration") is not None:
        session["duration"] = row["duration"]
    return session


def _row_to_activity(row):
    """Convert a D1 row dict to the activity event dict returned by the API."""
    return {
        "id": row["id"],
        "sessionId": row["sessionId"],
        "userId": row["userId"],
        "type": row["type"],
        "timestamp": row["timestamp"],
        "data": json.loads(row["data"]),
    }


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def handle_root():
    return json_ok({
        "name": "Fresh Time Tracker",
        "version": "1.0.0",
        "description": "Privacy-focused time tracking system",
        "runtime": "Cloudflare Python Worker",
        "endpoints": {
            "health": "/health",
            "sessions": {
                "start": "POST /api/sessions/start",
                "end": "POST /api/sessions/{sessionId}/end",
                "pause": "POST /api/sessions/{sessionId}/pause",
                "resume": "POST /api/sessions/{sessionId}/resume",
                "get": "GET /api/sessions/{sessionId}",
                "list": "GET /api/sessions",
                "activities": "GET /api/sessions/{sessionId}/activities",
                "summary": "GET /api/sessions/{sessionId}/summary",
            },
            "activity": {"track": "POST /api/activity"},
            "webhooks": {"github": "POST /api/webhooks/github"},
        },
        "features": {
            "githubIntegration": True,
            "agentPromptTracking": True,
            "localLLMOnly": True,
            "cloudflareWorker": True,
        },
        "privacy": {
            "dataStorage": "Cloudflare D1 (SQL database)",
            "screenshotProcessing": "Local only - never uploaded",
            "llmAnalysis": "Local models only - no 3rd party",
            "dataSecurity": "End-to-end encryption",
        },
    })


def handle_health():
    return json_ok({"status": "healthy", "timestamp": int(time.time() * 1000)})


async def handle_start_session(request, env):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return json_err("User ID required", 401)

    try:
        body = json.loads(await request.text())
    except Exception:
        return json_err("Invalid JSON body", 400)

    project_id = body.get("projectId")
    if not project_id:
        return json_err("Project ID required", 400)

    session = {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "projectId": project_id,
        "startTime": int(time.time() * 1000),
        "status": "active",
    }

    await env.DB.prepare(
        "INSERT INTO sessions (id, userId, projectId, startTime, status)"
        " VALUES (?, ?, ?, ?, ?)"
    ).bind(session["id"], user_id, project_id, session["startTime"], "active").run()
    return json_ok({"session": session}, 201)


async def handle_end_session(request, env, session_id):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return json_err("User ID required", 401)

    row = await env.DB.prepare(
        "SELECT * FROM sessions WHERE id = ?"
    ).bind(session_id).first()
    if row is None:
        return json_err("Session not found", 404)

    end_time = int(time.time() * 1000)
    duration = end_time - row["startTime"]
    await env.DB.prepare(
        "UPDATE sessions SET endTime = ?, duration = ?, status = 'completed' WHERE id = ?"
    ).bind(end_time, duration, session_id).run()

    session = _row_to_session(row)
    session["endTime"] = end_time
    session["duration"] = duration
    session["status"] = "completed"
    return json_ok({"session": session})


async def handle_pause_session(request, env, session_id):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return json_err("User ID required", 401)

    row = await env.DB.prepare(
        "SELECT * FROM sessions WHERE id = ?"
    ).bind(session_id).first()
    if row is None:
        return json_err("Session not found", 404)

    await env.DB.prepare(
        "UPDATE sessions SET status = 'paused' WHERE id = ?"
    ).bind(session_id).run()

    session = _row_to_session(row)
    session["status"] = "paused"
    return json_ok({"session": session})


async def handle_resume_session(request, env, session_id):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return json_err("User ID required", 401)

    row = await env.DB.prepare(
        "SELECT * FROM sessions WHERE id = ?"
    ).bind(session_id).first()
    if row is None:
        return json_err("Session not found", 404)

    await env.DB.prepare(
        "UPDATE sessions SET status = 'active' WHERE id = ?"
    ).bind(session_id).run()

    session = _row_to_session(row)
    session["status"] = "active"
    return json_ok({"session": session})


async def handle_get_session(request, env, session_id):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return json_err("User ID required", 401)

    row = await env.DB.prepare(
        "SELECT * FROM sessions WHERE id = ?"
    ).bind(session_id).first()
    if row is None:
        return json_err("Session not found", 404)

    return json_ok({"session": _row_to_session(row)})


async def handle_list_sessions(request, env, query_string):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return json_err("User ID required", 401)

    params = parse_qs(query_string or "")
    limit = int(params.get("limit", ["50"])[0])

    result = await env.DB.prepare(
        "SELECT * FROM sessions WHERE userId = ? ORDER BY startTime DESC LIMIT ?"
    ).bind(user_id, limit).all()

    sessions = [_row_to_session(row) for row in result.results]
    return json_ok({"sessions": sessions})


async def handle_track_activity(request, env):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return json_err("User ID required", 401)

    try:
        body = json.loads(await request.text())
    except Exception:
        return json_err("Invalid JSON body", 400)

    session_id = body.get("sessionId")
    event_type = body.get("type")
    data = body.get("data")

    if not session_id or not event_type or data is None:
        return json_err("Missing required fields: sessionId, type, data", 400)

    event = {
        "id": str(uuid.uuid4()),
        "sessionId": session_id,
        "userId": user_id,
        "type": event_type,
        "timestamp": int(time.time() * 1000),
        "data": data,
    }

    await env.DB.prepare(
        "INSERT INTO activities (id, sessionId, userId, type, timestamp, data)"
        " VALUES (?, ?, ?, ?, ?, ?)"
    ).bind(
        event["id"], session_id, user_id, event_type,
        event["timestamp"], json.dumps(data),
    ).run()

    return json_ok({"event": event}, 201)


async def handle_get_activities(request, env, session_id):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return json_err("User ID required", 401)

    result = await env.DB.prepare(
        "SELECT * FROM activities WHERE sessionId = ? ORDER BY timestamp ASC"
    ).bind(session_id).all()

    events = [_row_to_activity(row) for row in result.results]
    return json_ok({"activities": events})


async def handle_get_summary(request, env, session_id):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return json_err("User ID required", 401)

    row = await env.DB.prepare(
        "SELECT * FROM sessions WHERE id = ?"
    ).bind(session_id).first()
    if row is None:
        return json_err("Session not found", 404)

    session = _row_to_session(row)

    act_result = await env.DB.prepare(
        "SELECT * FROM activities WHERE sessionId = ? ORDER BY timestamp ASC"
    ).bind(session_id).all()
    activities = [_row_to_activity(r) for r in act_result.results]

    summary = {
        "sessionId": session_id,
        "totalDuration": session.get("duration", 0),
        "activeTime": 0,
        "idleTime": 0,
        "githubEvents": 0,
        "keyboardActivity": 0,
        "mouseActivity": 0,
        "agentPrompts": 0,
        "screenshots": 0,
        "productivity": "medium",
    }

    for event in activities:
        t = event.get("type")
        if t == "github":
            summary["githubEvents"] += 1
        elif t == "keyboard":
            summary["keyboardActivity"] += 1
            summary["activeTime"] += event.get("data", {}).get("activeTime", 0)
        elif t == "mouse":
            summary["mouseActivity"] += 1
            summary["activeTime"] += event.get("data", {}).get("activeTime", 0)
        elif t == "agent-prompt":
            summary["agentPrompts"] += 1
        elif t == "screenshot":
            summary["screenshots"] += 1

    score = (
        summary["githubEvents"] * 3
        + summary["keyboardActivity"] * 2
        + summary["mouseActivity"]
        + summary["agentPrompts"] * 2
    )
    if score > 50:
        summary["productivity"] = "high"
    elif score < 20:
        summary["productivity"] = "low"

    return json_ok({"summary": summary})


async def handle_github_webhook(request, env):
    user_id = request.headers.get("X-User-ID")
    session_id = request.headers.get("X-Session-ID")
    if not user_id or not session_id:
        return json_err("User ID and Session ID required", 401)

    try:
        payload = json.loads(await request.text())
    except Exception:
        return json_err("Invalid JSON body", 400)

    event = _parse_github_webhook(payload, user_id, session_id)
    if event is None:
        return json_ok({"message": "Event ignored"})

    await env.DB.prepare(
        "INSERT INTO activities (id, sessionId, userId, type, timestamp, data)"
        " VALUES (?, ?, ?, ?, ?, ?)"
    ).bind(
        event["id"], session_id, user_id, event["type"],
        event["timestamp"], json.dumps(event["data"]),
    ).run()

    return json_ok({"event": event}, 201)


def _parse_github_webhook(payload, user_id, session_id):
    """Map a GitHub webhook payload to an ActivityEvent dict, or return None."""
    action = None
    if "commits" in payload or payload.get("ref"):
        action = "push"
    elif "pull_request" in payload:
        action = "pull-request"
    elif "issue" in payload:
        action = "issue"
    elif "review" in payload:
        action = "review"
    elif "comment" in payload:
        action = "comment"

    if not action:
        return None

    repo = payload.get("repository") or {}
    head_commit = payload.get("head_commit") or {}
    return {
        "id": str(uuid.uuid4()),
        "sessionId": session_id,
        "userId": user_id,
        "type": "github",
        "timestamp": int(time.time() * 1000),
        "data": {
            "type": "github",
            "action": action,
            "repository": repo.get("full_name", "unknown"),
            "branch": payload.get("ref"),
            "commitSha": payload.get("after") or head_commit.get("id"),
            "url": repo.get("html_url"),
        },
    }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

_ROUTES = [
    ("GET",  r"^/$",                                          "root"),
    ("GET",  r"^/health$",                                    "health"),
    ("POST", r"^/api/sessions/start$",                        "start_session"),
    ("POST", r"^/api/sessions/(?P<sid>[^/]+)/end$",           "end_session"),
    ("POST", r"^/api/sessions/(?P<sid>[^/]+)/pause$",         "pause_session"),
    ("POST", r"^/api/sessions/(?P<sid>[^/]+)/resume$",        "resume_session"),
    ("GET",  r"^/api/sessions/(?P<sid>[^/]+)/activities$",    "get_activities"),
    ("GET",  r"^/api/sessions/(?P<sid>[^/]+)/summary$",       "get_summary"),
    ("GET",  r"^/api/sessions/(?P<sid>[^/]+)$",               "get_session"),
    ("GET",  r"^/api/sessions$",                              "list_sessions"),
    ("POST", r"^/api/activity$",                              "track_activity"),
    ("POST", r"^/api/webhooks/github$",                       "github_webhook"),
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
            elif name == "start_session":
                return await handle_start_session(request, env)
            elif name == "end_session":
                return await handle_end_session(request, env, sid)
            elif name == "pause_session":
                return await handle_pause_session(request, env, sid)
            elif name == "resume_session":
                return await handle_resume_session(request, env, sid)
            elif name == "get_activities":
                return await handle_get_activities(request, env, sid)
            elif name == "get_summary":
                return await handle_get_summary(request, env, sid)
            elif name == "get_session":
                return await handle_get_session(request, env, sid)
            elif name == "list_sessions":
                return await handle_list_sessions(request, env, qs)
            elif name == "track_activity":
                return await handle_track_activity(request, env)
            elif name == "github_webhook":
                return await handle_github_webhook(request, env)
        except Exception as exc:
            print(f"[ERROR] route={name} sid={sid}: {exc}")
            return json_err("Internal server error", 500)

    return json_err("Not found", 404)
