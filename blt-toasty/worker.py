"""
Cloudflare Worker for Toasty - AI Code Reviewer Backend

This worker handles API requests for the Toasty AI code review service.
It provides endpoints for code analysis, health checks, webhook ingestion,
and status monitoring.
"""

import json
import urllib.parse
from js import Response, Headers, console
from src.rationale_builder import audit_completeness_check
from src.webhook_handler import handle_webhook

# Maximum request body size in bytes (1MB)
MAX_BODY_SIZE = 1024 * 1024


def parse_path(url):
    """
    Extract clean path from URL, handling query params and fragments.

    Args:
        url: The full URL string

    Returns:
        str: The path component of the URL
    """
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    if not path or path == "":
        path = "/"
    elif not path.startswith("/"):
        path = "/" + path
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


async def on_fetch(request, env):
    """
    Main entry point for Cloudflare Worker requests.

    Args:
        request: The incoming HTTP request
        env: Environment variables and bindings

    Returns:
        Response: HTTP response object
    """
    url = request.url
    method = request.method

    # Parse the URL to get the path
    try:
        path = parse_path(url)
    except Exception as e:
        return create_error_response(f"Error parsing URL: {str(e)}", 500)

    # Handle CORS preflight requests
    if method == "OPTIONS":
        return handle_options(request)

    # Route requests based on path and method
    if path == "/" or path == "":
        if method in ("GET", "HEAD"):
            return handle_root(request)
        else:
            return create_method_not_allowed_response(path, ["GET", "HEAD"])
    elif path == "/health":
        if method in ("GET", "HEAD"):
            return handle_health(request)
        else:
            return create_method_not_allowed_response(path, ["GET", "HEAD"])
    elif path == "/api/review":
        if method == "POST":
            return await handle_review(request, env)
        else:
            return create_method_not_allowed_response(path, ["POST"])
    elif path == "/webhook/gitlab":
        if method == "POST":
            return await handle_gitlab_webhook(request, env)
        else:
            return create_method_not_allowed_response(path, ["POST"])
    elif path == "/api/status":
        if method in ("GET", "HEAD"):
            return handle_status(request)
        else:
            return create_method_not_allowed_response(path, ["GET", "HEAD"])
    elif path.startswith("/triage/") and path.endswith("/rationale"):
        if method == "GET":
            # Extract and decode event_id from /triage/{event_id}/rationale
            raw_event_id = path[len("/triage/") : -len("/rationale")]
            event_id = urllib.parse.unquote(raw_event_id)
            if not event_id:
                return create_error_response("Missing event_id in path", 400)
            if "/" in event_id:
                return create_error_response("Invalid event_id: must not contain path separators", 400)
            return await handle_rationale(request, env, event_id)
        else:
            return create_method_not_allowed_response(path, ["GET"])
    elif path.startswith("/conversations/"):
        return await _route_conversation(path, method, request, env)
    else:
        return create_error_response(f"Not Found: {path}", 404)


def handle_options(request):
    """
    Handle CORS preflight OPTIONS requests.

    Args:
        request: The incoming HTTP request

    Returns:
        Response: 204 No Content with CORS headers
    """
    headers = Headers.new()
    headers.set("Access-Control-Allow-Origin", "*")
    headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD, DELETE")
    headers.set("Access-Control-Allow-Headers", "Content-Type")
    headers.set("Access-Control-Max-Age", "86400")

    return Response.new("", status=204, headers=headers)


def handle_root(request):
    """
    Handle root endpoint requests.

    Args:
        request: The incoming HTTP request

    Returns:
        Response: Welcome message
    """
    response_data = {
        "service": "Toasty AI Code Reviewer",
        "version": "1.0.0",
        "description": "Backend API for OWASP BLT's AI-powered code review service",
        "endpoints": {
            "/": "Service information",
            "/health": "Health check endpoint",
            "/api/review": "POST - Submit code for review",
            "/webhook/gitlab": "POST - GitLab webhook receiver",
            "/api/status": "GET - Check service status",
            "/triage/{event_id}/rationale": "GET - Retrieve structured rationale for a triage event",
            "/conversations/{triage_id}/reply": "POST - Append a turn to a triage conversation",
            "/conversations/{triage_id}/history": "GET - Retrieve conversation history",
            "/conversations/{triage_id}": "DELETE - Close and archive a conversation",
        },
    }

    return create_json_response(response_data, 200)


def handle_health(request):
    """
    Handle health check endpoint.

    Args:
        request: The incoming HTTP request

    Returns:
        Response: Health status
    """
    health_data = {
        "status": "healthy",
        "service": "toasty-backend",
        "timestamp": None,  # Would use datetime in production
    }

    return create_json_response(health_data, 200)


async def handle_review(request, env):
    """
    Handle code review requests.

    Args:
        request: The incoming HTTP request
        env: Environment variables and bindings

    Returns:
        Response: Code review results
    """
    try:
        # Check Content-Length header if present
        content_length_header = request.headers.get("Content-Length")
        if content_length_header:
            try:
                content_length = int(content_length_header)
                if content_length > MAX_BODY_SIZE:
                    return create_error_response(f"Request body too large. Maximum size is {MAX_BODY_SIZE} bytes", 413)
            except ValueError:
                pass  # Invalid Content-Length, will be caught during reading

        # Parse request body with size limit
        body = await request.text()

        if len(body) > MAX_BODY_SIZE:
            return create_error_response(f"Request body too large. Maximum size is {MAX_BODY_SIZE} bytes", 413)

        if not body:
            return create_error_response("Request body is required", 400)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return create_error_response("Invalid JSON in request body", 400)

        if not isinstance(data, dict):
            return create_error_response("Request body must be a JSON object", 400)

        # Validate required fields
        if "code" not in data:
            return create_error_response("Missing required field: 'code'", 400)

        code = data.get("code")

        # Validate that code is a non-empty string
        if not isinstance(code, str):
            return create_error_response("Field 'code' must be a string", 400)

        if not code or not code.strip():
            return create_error_response("Field 'code' cannot be empty", 400)

        language = data.get("language", "unknown")
        _context = data.get("context", "")

        # Placeholder for actual AI review logic
        # In production, this would call AI services, perform static analysis, etc.
        review_result = {
            "status": "success",
            "analysis": {
                "language": language,
                "lines_of_code": len(code.split("\n")),
                "issues": [],
                "suggestions": [
                    {
                        "type": "info",
                        "message": "Code review placeholder - integration with AI services pending",
                        "line": 0,
                    }
                ],
                "summary": "Review completed successfully",
            },
            "metadata": {"processed_at": None, "worker_version": "1.0.0"},  # Would use datetime in production
        }

        return create_json_response(review_result, 200)

    except Exception as e:
        return create_error_response(f"Error processing review request: {str(e)}", 500)


async def handle_gitlab_webhook(request, env):
    """
    Handle GitLab webhook requests.

    Delegates to the webhook ingress handler in src.webhook_handler.

    Args:
        request: The incoming HTTP request
        env: Environment variables and bindings

    Returns:
        Response: Webhook processing result
    """
    return await handle_webhook(request, env)


async def handle_rationale(request, env, event_id):
    """
    Handle GET /triage/{event_id}/rationale requests.

    Returns the full structured rationale for a triage decision,
    including CWE evidence snippets, duplicate detection reasoning,
    and the per-component confidence trace.

    If any required audit record is absent from D1 the endpoint returns
    HTTP 424 Failed Dependency (blocking MCP export) with a ``missing_fields``
    list so operators can identify which pipeline stage did not complete.

    Args:
        request: The incoming HTTP request.
        env: The Cloudflare Worker environment bindings.
        event_id: The triage event ID parsed from the URL path.

    Returns:
        Response: 200 with rationale JSON, 404 if not found, or 424 if
            audit data is missing.
    """
    try:
        db = env.DB

        # ── Audit completeness gate ───────────────────────────────────────────
        is_complete, missing_fields = await audit_completeness_check(event_id, db)
        if not is_complete:
            return create_json_response(
                {
                    "error": "Audit data incomplete — MCP export blocked",
                    "missing_fields": missing_fields,
                    "event_id": event_id,
                },
                424,
            )

        # ── Fetch stored rationale from D1 ────────────────────────────────────
        cursor = await db.execute(
            "SELECT cwe_rationale, duplicate_rationale, confidence_trace "
            "FROM triage_rationale WHERE triage_event_id = ? LIMIT 1",
            [event_id],
        )
        row = cursor.fetchone()
        if row is None:
            return create_error_response(f"Rationale not found for event {event_id}", 404)

        cwe_rationale_raw = json.loads(row[0])
        dup_rationale_raw = json.loads(row[1]) if row[1] else None
        confidence_trace_raw = json.loads(row[2])

        return create_json_response(
            {
                "event_id": event_id,
                "status": "complete",
                "cwe_rationale": cwe_rationale_raw,
                "duplicate_rationale": dup_rationale_raw,
                "confidence_trace": confidence_trace_raw,
            },
            200,
        )

    except Exception as exc:
        console.error(f"handle_rationale error for {event_id}: {exc}")
        return create_error_response("Internal server error", 500)


def handle_status(request):
    """
    Handle status check endpoint.

    Args:
        request: The incoming HTTP request

    Returns:
        Response: Service status information
    """
    status_data = {
        "service": "toasty-backend",
        "status": "operational",
        "version": "1.0.0",
        "features": {"code_review": "available", "health_check": "available", "status_monitoring": "available"},
        "uptime": "available",
    }

    return create_json_response(status_data, 200)


def get_env_value(env, key, default=None):
    """
    Read a value from the worker environment.

    Args:
        env: Environment object or mapping
        key: Environment variable name
        default: Fallback value if the key is missing

    Returns:
        Any: The resolved environment value
    """
    if hasattr(env, "get"):
        return env.get(key, default)

    return getattr(env, key, default)


def constant_time_equals(left, right):
    """
    Compare two strings without early exit.

    Args:
        left: First string
        right: Second string

    Returns:
        bool: True when both values match exactly
    """
    if not isinstance(left, str) or not isinstance(right, str):
        return False

    if len(left) != len(right):
        return False

    result = 0
    for index in range(len(left)):
        result |= ord(left[index]) ^ ord(right[index])

    return result == 0


def extract_gitlab_action(payload):
    """
    Extract the GitLab action from a webhook payload.

    Args:
        payload: Parsed JSON body from GitLab

    Returns:
        str: The best-effort action value
    """
    object_attributes = payload.get("object_attributes", {}) if isinstance(payload, dict) else {}

    if isinstance(object_attributes, dict):
        action = object_attributes.get("action")
        if action:
            return str(action)

    if isinstance(payload, dict):
        action = payload.get("action")
        if action:
            return str(action)

    return "unknown"


def extract_gitlab_object_type(payload):
    """
    Extract the GitLab object type from a webhook payload.

    Args:
        payload: Parsed JSON body from GitLab

    Returns:
        str: The best-effort object type value
    """
    if not isinstance(payload, dict):
        return "unknown"

    object_kind = payload.get("object_kind")
    if object_kind:
        return str(object_kind)

    object_attributes = payload.get("object_attributes", {})
    if isinstance(object_attributes, dict):
        target_type = object_attributes.get("target_type")
        if target_type:
            return str(target_type)

    return "unknown"


def create_json_response(data, status_code=200):
    """
    Create a JSON response with proper headers.

    Args:
        data: Dictionary to serialize as JSON
        status_code: HTTP status code

    Returns:
        Response: JSON response object
    """
    headers = Headers.new()
    headers.set("Content-Type", "application/json")
    headers.set("Access-Control-Allow-Origin", "*")
    headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD, DELETE")
    headers.set("Access-Control-Allow-Headers", "Content-Type")

    return Response.new(json.dumps(data), status=status_code, headers=headers)


def create_text_response(message, status_code=200):
    """
    Create a plain-text response.

    Args:
        message: Text body to return
        status_code: HTTP status code

    Returns:
        Response: Text response object
    """
    headers = Headers.new()
    headers.set("Content-Type", "text/plain; charset=utf-8")
    headers.set("Access-Control-Allow-Origin", "*")

    return Response.new(message, status=status_code, headers=headers)


def create_error_response(message, status_code=500):
    """
    Create an error response.

    Args:
        message: Error message
        status_code: HTTP status code

    Returns:
        Response: Error response object
    """
    error_data = {"error": message, "status": status_code}

    return create_json_response(error_data, status_code)


def create_method_not_allowed_response(path, allowed_methods):
    """
    Create a 405 Method Not Allowed response.

    Args:
        path: The request path
        allowed_methods: List of allowed HTTP methods

    Returns:
        Response: HTTP 405 response with Allow header
    """
    message = f"Method Not Allowed for {path}. Allowed methods: {', '.join(allowed_methods)}"

    headers = Headers.new()
    headers.set("Content-Type", "application/json")
    headers.set("Access-Control-Allow-Origin", "*")
    headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD, DELETE")
    headers.set("Access-Control-Allow-Headers", "Content-Type")
    headers.set("Allow", ", ".join(allowed_methods))

    error_data = {"error": "Method Not Allowed", "message": message, "status": 405}

    return Response.new(json.dumps(error_data), status=405, headers=headers)


# ---------------------------------------------------------------------------
# Conversation routes
# ---------------------------------------------------------------------------


def _extract_triage_id(path: str, prefix: str, suffix: str = "") -> str | None:
    """Extract and validate triage_id from a conversation URL path.

    Args:
        path: The full URL path.
        prefix: The path prefix before the triage_id.
        suffix: The path suffix after the triage_id (optional).

    Returns:
        The decoded triage_id, or ``None`` if invalid.
    """
    raw = path[len(prefix) :]
    if suffix:
        raw = raw[: -len(suffix)]
    decoded = urllib.parse.unquote(raw)
    if not decoded or "/" in decoded:
        return None
    return decoded


async def _route_conversation(path, method, request, env):
    """Route /conversations/* requests to the appropriate handler.

    Args:
        path: The cleaned URL path.
        method: The HTTP method.
        request: The incoming HTTP request.
        env: The Cloudflare Worker environment.

    Returns:
        Response: The handler's HTTP response.
    """
    if path.endswith("/reply"):
        if method != "POST":
            return create_method_not_allowed_response(path, ["POST"])
        triage_id = _extract_triage_id(path, "/conversations/", "/reply")
        if not triage_id:
            return create_error_response("Invalid or missing triage_id", 400)
        return await handle_conversation_reply(request, env, triage_id)
    elif path.endswith("/history"):
        if method != "GET":
            return create_method_not_allowed_response(path, ["GET"])
        triage_id = _extract_triage_id(path, "/conversations/", "/history")
        if not triage_id:
            return create_error_response("Invalid or missing triage_id", 400)
        return await handle_conversation_history(request, env, triage_id)
    else:
        # DELETE /conversations/{triage_id}
        if method != "DELETE":
            return create_method_not_allowed_response(path, ["DELETE"])
        triage_id = _extract_triage_id(path, "/conversations/")
        if not triage_id:
            return create_error_response("Invalid or missing triage_id", 400)
        return await handle_conversation_close(request, env, triage_id)


async def _get_do_stub(env, triage_id):
    """Get the Durable Object stub for a conversation.

    Args:
        env: The Cloudflare Worker environment with CONVERSATION_DO binding.
        triage_id: The triage event ID to use as the DO name.

    Returns:
        The Durable Object stub.

    Raises:
        AttributeError: If CONVERSATION_DO binding is not configured.
    """
    do_namespace = env.CONVERSATION_DO
    do_id = do_namespace.idFromName(triage_id)
    return do_namespace.get(do_id)


async def handle_conversation_reply(request, env, triage_id):
    """Handle POST /conversations/{triage_id}/reply.

    Forwards the request body (with triage_id injected) to the
    ConversationDO for turn appending.

    Args:
        request: The incoming HTTP request.
        env: The Cloudflare Worker environment.
        triage_id: The triage event ID.

    Returns:
        Response: The DO's response (turn_count, conversation_id).
    """
    try:
        body_text = await request.text()
        if not body_text:
            return create_error_response("Request body is required", 400)

        try:
            body = json.loads(body_text)
        except json.JSONDecodeError:
            return create_error_response("Invalid JSON in request body", 400)

        if not isinstance(body, dict):
            return create_error_response("Request body must be a JSON object", 400)

        # Inject triage_id into the body for the DO
        body["triage_id"] = triage_id

        stub = await _get_do_stub(env, triage_id)
        # Forward as a new Request to the DO
        from js import Request as JSRequest

        do_request = JSRequest.new(
            "https://do-internal/reply",
            {"method": "POST", "body": json.dumps(body), "headers": {"Content-Type": "application/json"}},
        )
        do_response = await stub.fetch(do_request)
        return create_json_response(json.loads(await do_response.text()), do_response.status)

    except Exception as exc:
        console.error(f"handle_conversation_reply error for {triage_id}: {exc}")
        return create_error_response("Internal server error", 500)


async def handle_conversation_history(request, env, triage_id):
    """Handle GET /conversations/{triage_id}/history.

    Forwards the request to the ConversationDO to retrieve turn history.

    Args:
        request: The incoming HTTP request.
        env: The Cloudflare Worker environment.
        triage_id: The triage event ID.

    Returns:
        Response: The DO's response (turns, turn_count, status).
    """
    try:
        stub = await _get_do_stub(env, triage_id)
        # Forward the original request URL so the DO can read ?full=true
        from js import Request as JSRequest

        do_url = "https://do-internal/history"
        # Preserve query params from the original request
        parsed_url = urllib.parse.urlparse(request.url)
        if parsed_url.query:
            do_url += f"?{parsed_url.query}"

        do_request = JSRequest.new(do_url, {"method": "GET"})
        do_response = await stub.fetch(do_request)
        return create_json_response(json.loads(await do_response.text()), do_response.status)

    except Exception as exc:
        console.error(f"handle_conversation_history error for {triage_id}: {exc}")
        return create_error_response("Internal server error", 500)


async def handle_conversation_close(request, env, triage_id):
    """Handle DELETE /conversations/{triage_id}.

    Forwards the request to the ConversationDO to close and archive
    the conversation.

    Args:
        request: The incoming HTTP request.
        env: The Cloudflare Worker environment.
        triage_id: The triage event ID.

    Returns:
        Response: The DO's response (archived, turns_archived).
    """
    try:
        stub = await _get_do_stub(env, triage_id)
        from js import Request as JSRequest

        do_request = JSRequest.new("https://do-internal/archive", {"method": "DELETE"})
        do_response = await stub.fetch(do_request)
        return create_json_response(json.loads(await do_response.text()), do_response.status)

    except Exception as exc:
        console.error(f"handle_conversation_close error for {triage_id}: {exc}")
        return create_error_response("Internal server error", 500)
