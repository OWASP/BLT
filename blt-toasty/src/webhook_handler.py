"""
Cloudflare Workers Python Webhook Handler for GitLab Events

This module implements the webhook ingress gateway for the Toasty platform,
handling secure GitLab webhook validation, replay attack prevention, and
triage event storage in D1.
"""

from js import Response, Headers, Uint8Array, TextEncoder
import js
from pyodide.ffi import to_js
import base64
import hashlib
import hmac
import json
import secrets


async def verify_hmac_signature(secret: str, webhook_id: str, timestamp: str, body: str, signature_header: str) -> bool:
    """
    Verify GitLab webhook signature using Web Crypto API.
    
    Args:
        secret: The webhook secret (e.g., whsec_...)
        webhook_id: The webhook-id header value
        timestamp: The webhook-timestamp header value
        body: The raw request body text
        signature_header: The webhook-signature header value

    Returns:
        bool: True if signature is valid
    """
    if not secret or not signature_header or not signature_header.startswith("v1,"):
        return False
        
    try:
        raw_key_str = secret.replace("whsec_", "")
        raw_key_bytes = base64.b64decode(raw_key_str)
        
        key_array = Uint8Array.new(len(raw_key_bytes))
        for i, b in enumerate(raw_key_bytes):
            key_array[i] = b
            
        crypto_key = await js.crypto.subtle.importKey(
            "raw",
            key_array,
            to_js({"name": "HMAC", "hash": "SHA-256"}, dict_converter=js.Object.fromEntries),
            False,
            to_js(["sign"])
        )
        
        message = f"{webhook_id}.{timestamp}.{body}"
        encoder = TextEncoder.new()
        message_buffer = encoder.encode(message)
        
        signature_buffer = await js.crypto.subtle.sign("HMAC", crypto_key, message_buffer)
        
        sig_array = Uint8Array.new(signature_buffer)
        sig_bytes = bytes(sig_array)
        computed_signature = base64.b64encode(sig_bytes).decode('utf-8')
        expected_signature = f"v1,{computed_signature}"
        
        return hmac.compare_digest(signature_header, expected_signature)
    except Exception:
        return False


async def check_and_store_delivery_id(kv, delivery_id: str) -> bool:
    """
    Check if delivery_id exists in KV store (replay prevention).

    Looks up delivery_id (GitLab UUID) in KV. If unique, stores with 86400s TTL.

    Args:
        kv: Cloudflare KV namespace binding
        delivery_id: GitLab Event UUID (X-Gitlab-Event-UUID header)

    Returns:
        bool: True if delivery_id is unique and successfully stored, False if duplicate
    """
    try:
        # Check if delivery_id already exists
        existing = await kv.get(delivery_id)
        if existing is not None:
            return False

        # Store delivery_id with 24-hour TTL (86400 seconds)
        await kv.put(delivery_id, json.dumps({"received_at": "timestamp"}), {"expirationTtl": 86400})
        return True
    except Exception:
        return False


def normalize_payload(event_type: str, body: dict) -> dict:
    """
    Extract and normalize GitLab webhook payload.

    Handles 'Issue Hook' and 'Note Hook' events, extracting relevant fields.

    Args:
        event_type: GitLab event type (e.g., 'Issue Hook', 'Note Hook')
        body: Parsed webhook payload dictionary

    Returns:
        dict: Normalized event with keys: event_type, action, project_id, issue_iid
        Raises KeyError if required fields are missing
    """
    normalized = {"event_type": event_type}

    if event_type == "Issue Hook":
        # Extract from Issue Hook payload
        action = body["object_attributes"]["action"]
        project_id = body["project"]["id"]
        issue_iid = body["object_attributes"]["iid"]

        normalized["action"] = action
        normalized["project_id"] = project_id
        normalized["issue_iid"] = issue_iid

    elif event_type == "Note Hook":
        # Extract from Note Hook payload
        action = body["object_attributes"]["action"]
        project_id = body["project"]["id"]
        issue_iid = body["issue"]["iid"]

        normalized["action"] = action
        normalized["project_id"] = project_id
        normalized["issue_iid"] = issue_iid

    else:
        raise ValueError(f"Unsupported event type: {event_type}")

    return normalized


async def store_triage_event(db, event_id: str, delivery_id: str, normalized: dict, body_hash: str) -> None:
    """
    Store normalized triage event in D1 database.

    Inserts into triage_events table with status='pending'.

    Args:
        db: Cloudflare D1 database binding
        event_id: Generated event identifier
        delivery_id: GitLab Event UUID
        normalized: Normalized event dictionary
        body_hash: SHA-256 hash of webhook body
    """
    try:
        query = """
            INSERT INTO triage_events (
                event_id, delivery_id, event_type, action,
                project_id, issue_iid, body_hash, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', datetime('now'))
        """

        params = [
            event_id,
            delivery_id,
            normalized.get("event_type"),
            normalized.get("action"),
            normalized.get("project_id"),
            normalized.get("issue_iid"),
            body_hash,
        ]

        stmt = db.prepare(query)
        stmt.bind(*params)
        stmt.run()
    except Exception as e:
        raise RuntimeError(f"Failed to store triage event: {str(e)}")


async def handle_webhook(request, env) -> Response:
    """
    Main webhook request handler.

    Validates GitLab webhook token, prevents replays, normalizes payload,
    and stores triage event.

    Process:
    1. Extract and validate X-Gitlab-Token header (401 if invalid)
    2. Extract X-Gitlab-Event-UUID header (422 if missing)
    3. Check KV for duplicate delivery_id (409 if duplicate)
    4. Normalize payload (422 if normalization fails)
    5. Hash webhook body
    6. Store triage event in D1
    7. Return 202 Accepted with event_id and status

    Args:
        request: The incoming HTTP request
        env: Environment bindings (DB, TOASTY_KV, GITLAB_WEBHOOK_SECRET)

    Returns:
        Response: HTTP response with appropriate status code
    """
    try:
        # Get webhook secret from environment
        webhook_secret = getattr(env, "GITLAB_WEBHOOK_SECRET", None)
        if not webhook_secret:
            headers = Headers.new()
            headers.set("Content-Type", "application/json")
            error_data = {"error": "Webhook secret not configured", "status": 500}
            return Response.new(json.dumps(error_data), status=500, headers=headers)

        # 1. Extract Webhook UUID (used for replay protection)
        delivery_id = request.headers.get("X-Gitlab-Event-UUID")
        if not delivery_id:
            headers = Headers.new()
            headers.set("Content-Type", "application/json")
            error_data = {"error": "Missing X-Gitlab-Event-UUID header", "status": 422}
            return Response.new(json.dumps(error_data), status=422, headers=headers)

        # 2. Extract Web Crypto Validation Headers
        webhook_id = request.headers.get("webhook-id")
        webhook_timestamp = request.headers.get("webhook-timestamp")
        webhook_signature = request.headers.get("webhook-signature")
        
        if not webhook_id or not webhook_timestamp or not webhook_signature:
            headers = Headers.new()
            headers.set("Content-Type", "application/json")
            error_data = {"error": "Missing webhook signature headers", "status": 401}
            return Response.new(json.dumps(error_data), status=401, headers=headers)

        # 3. Parse request body text
        body_text = await request.text()
        if not body_text:
            headers = Headers.new()
            headers.set("Content-Type", "application/json")
            error_data = {"error": "Request body is required", "status": 422}
            return Response.new(json.dumps(error_data), status=422, headers=headers)

        # 4. Verify HMAC-SHA256 signature
        is_valid = await verify_hmac_signature(webhook_secret, webhook_id, webhook_timestamp, body_text, webhook_signature)
        if not is_valid:
            headers = Headers.new()
            headers.set("Content-Type", "application/json")
            error_data = {"error": "Unauthorized: Invalid webhook signature", "status": 401}
            return Response.new(json.dumps(error_data), status=401, headers=headers)

        try:
            body = json.loads(body_text)
        except json.JSONDecodeError:
            headers = Headers.new()
            headers.set("Content-Type", "application/json")
            error_data = {"error": "Invalid JSON in request body", "status": 422}
            return Response.new(json.dumps(error_data), status=422, headers=headers)

        # 4. Replay attack check
        kv = getattr(env, "TOASTY_KV", None)
        if kv:
            is_unique = await check_and_store_delivery_id(kv, delivery_id)
            if not is_unique:
                headers = Headers.new()
                headers.set("Content-Type", "application/json")
                error_data = {"error": "Duplicate delivery_id (replay detected)", "status": 409}
                return Response.new(json.dumps(error_data), status=409, headers=headers)

        # 5. Get event type and normalize payload
        event_type = request.headers.get("X-Gitlab-Event")
        if not event_type:
            headers = Headers.new()
            headers.set("Content-Type", "application/json")
            error_data = {"error": "Missing X-Gitlab-Event header", "status": 422}
            return Response.new(json.dumps(error_data), status=422, headers=headers)

        try:
            normalized = normalize_payload(event_type, body)
        except (KeyError, ValueError) as e:
            headers = Headers.new()
            headers.set("Content-Type", "application/json")
            error_data = {"error": f"Failed to normalize payload: {str(e)}", "status": 422}
            return Response.new(json.dumps(error_data), status=422, headers=headers)

        # 6. Calculate SHA-256 hash of body
        body_hash = hashlib.sha256(body_text.encode()).hexdigest()

        # 7. Generate event_id
        event_id = secrets.token_hex(16)

        # 8. Store triage event in D1
        db = getattr(env, "DB", None)
        if db:
            try:
                await store_triage_event(db, event_id, delivery_id, normalized, body_hash)
            except Exception as e:
                headers = Headers.new()
                headers.set("Content-Type", "application/json")
                error_data = {"error": f"Failed to store event: {str(e)}", "status": 500}
                return Response.new(json.dumps(error_data), status=500, headers=headers)

        # 9. Return 202 Accepted with event_id
        response_data = {"event_id": event_id, "status": "pending"}
        headers = Headers.new()
        headers.set("Content-Type", "application/json")
        return Response.new(json.dumps(response_data), status=202, headers=headers)

    except Exception as e:
        headers = Headers.new()
        headers.set("Content-Type", "application/json")
        error_data = {"error": f"Unexpected error: {str(e)}", "status": 500}
        return Response.new(json.dumps(error_data), status=500, headers=headers)
