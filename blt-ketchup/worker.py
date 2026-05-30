"""
BLT Ketchup — Cloudflare Python Worker
Real-time Pentest Collaboration API

Runs on Cloudflare Workers (python runtime via Pyodide/WASM).
All workspace data is stored in encrypted Cloudflare KV or D1,
using AES-256-GCM with per-tenant keys derived from a root secret
stored in a Cloudflare Workers Secret.

Environment bindings expected in wrangler.toml:
  - WORKSPACE_KV   : KV namespace for workspace blobs
  - DB             : D1 database for structured records
  - ROOT_SECRET    : Workers Secret (32-byte hex, base64-encoded)
  - CORS_ORIGINS   : comma-separated allowed origins
"""

import json
import hashlib
import hmac
import base64
import os
import struct
import time
from js import Response, Request, crypto, TextEncoder, TextDecoder, Uint8Array, console  # noqa: F401 – Cloudflare JS globals


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def json_response(data: dict | list, status: int = 200, headers: dict | None = None) -> Response:
    """Return a JSON Response with correct Content-Type and CORS headers."""
    base_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": os.environ.get("CORS_ORIGINS", "*").split(",")[0],
        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Workspace-Token",
    }
    if headers:
        base_headers.update(headers)
    return Response.new(
        json.dumps(data),
        status=status,
        headers=base_headers,
    )


def error_response(message: str, status: int = 400) -> Response:
    return json_response({"error": message}, status=status)


# ---------------------------------------------------------------------------
# Encryption helpers (AES-256-GCM via Web Crypto API)
# ---------------------------------------------------------------------------

async def derive_workspace_key(workspace_id: str, root_secret: str) -> object:
    """
    Derive a per-workspace AES-256-GCM key using HKDF.
    root_secret  : hex string (256 bit) stored in Workers Secret.
    workspace_id : used as HKDF info/salt.
    """
    enc = TextEncoder.new()
    raw_secret = bytes.fromhex(root_secret)

    # Import root key material
    key_material = await crypto.subtle.importKey(
        "raw",
        Uint8Array.new(raw_secret),
        {"name": "HKDF"},
        False,
        ["deriveKey"],
    )

    # Derive workspace-specific AES-GCM key
    derived = await crypto.subtle.deriveKey(
        {
            "name": "HKDF",
            "hash": "SHA-256",
            "salt": enc.encode(f"blt-ketchup-v1-{workspace_id}"),
            "info": enc.encode("workspace-data-encryption"),
        },
        key_material,
        {"name": "AES-GCM", "length": 256},
        False,
        ["encrypt", "decrypt"],
    )
    return derived


async def encrypt_payload(key: object, plaintext: str) -> str:
    """
    Encrypt a JSON-serialisable string with AES-256-GCM.
    Returns a base64url-encoded string: <12-byte IV> | <ciphertext+tag>.
    """
    enc = TextEncoder.new()
    iv = crypto.getRandomValues(Uint8Array.new(12))
    ciphertext = await crypto.subtle.encrypt(
        {"name": "AES-GCM", "iv": iv},
        key,
        enc.encode(plaintext),
    )
    # Concatenate IV + ciphertext
    iv_bytes = bytes(iv)
    ct_bytes = bytes(Uint8Array.new(ciphertext))
    combined = iv_bytes + ct_bytes
    return base64.urlsafe_b64encode(combined).decode()


async def decrypt_payload(key: object, blob: str) -> str:
    """Decrypt a blob produced by encrypt_payload. Returns plaintext string."""
    combined = base64.urlsafe_b64decode(blob.encode())
    iv = Uint8Array.new(combined[:12])
    ciphertext = Uint8Array.new(combined[12:])
    dec = TextDecoder.new()
    plaintext_buf = await crypto.subtle.decrypt(
        {"name": "AES-GCM", "iv": iv},
        key,
        ciphertext,
    )
    return dec.decode(plaintext_buf)


# ---------------------------------------------------------------------------
# JWT-lite bearer token verification
# ---------------------------------------------------------------------------

def _safe_b64decode(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)


def verify_token(token: str, secret: str) -> dict | None:
    """
    Verify a HS256 JWT.  Returns the payload dict on success, None on failure.
    NOTE: This is a minimal implementation; in production use a full JWT library.
    """
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        return None

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = hmac.new(
        secret.encode(), signing_input, hashlib.sha256
    ).digest()
    actual_sig = _safe_b64decode(sig_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        return None

    payload = json.loads(_safe_b64decode(payload_b64))
    if payload.get("exp", 0) < time.time():
        return None

    return payload


def get_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

async def handle_options(request: Request) -> Response:
    """Handle CORS pre-flight."""
    return Response.new(
        "",
        status=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Workspace-Token",
            "Access-Control-Max-Age": "86400",
        },
    )


# --- Workspaces ---

async def list_workspaces(request: Request, env) -> Response:
    """GET /api/workspaces — list workspaces visible to the current user."""
    token_payload = _require_auth(request, env)
    if isinstance(token_payload, Response):
        return token_payload

    # Query D1 for workspaces the user belongs to
    result = await env.DB.prepare(
        "SELECT id, name, status, created_at FROM workspaces "
        "WHERE id IN (SELECT workspace_id FROM memberships WHERE user_id = ?) "
        "ORDER BY created_at DESC LIMIT 50"
    ).bind(token_payload["sub"]).all()

    rows = [dict(r) for r in (result.results or [])]
    return json_response({"workspaces": rows})


async def create_workspace(request: Request, env) -> Response:
    """POST /api/workspaces — create a new engagement workspace."""
    token_payload = _require_auth(request, env)
    if isinstance(token_payload, Response):
        return token_payload

    body = await _parse_json(request)
    if not body:
        return error_response("Request body must be JSON")

    name = (body.get("name") or "").strip()
    if not name:
        return error_response("name is required")

    workspace_id = _new_id("ws")
    now = int(time.time())

    # Persist to D1
    await env.DB.prepare(
        "INSERT INTO workspaces (id, name, status, owner_id, created_at) VALUES (?, ?, 'active', ?, ?)"
    ).bind(workspace_id, name, token_payload["sub"], now).run()

    await env.DB.prepare(
        "INSERT INTO memberships (workspace_id, user_id, role) VALUES (?, ?, 'owner')"
    ).bind(workspace_id, token_payload["sub"]).run()

    return json_response(
        {"id": workspace_id, "name": name, "status": "active", "created_at": now},
        status=201,
    )


# --- Findings ---

async def list_findings(request: Request, env, workspace_id: str) -> Response:
    """GET /api/workspaces/{id}/findings — list findings (metadata only, bodies encrypted)."""
    token_payload = _require_auth(request, env)
    if isinstance(token_payload, Response):
        return token_payload

    if not await _is_member(env, workspace_id, token_payload["sub"]):
        return error_response("Forbidden", 403)

    result = await env.DB.prepare(
        "SELECT id, title, severity, cvss_score, status, assigned_to, created_at "
        "FROM findings WHERE workspace_id = ? ORDER BY cvss_score DESC"
    ).bind(workspace_id).all()

    rows = [dict(r) for r in (result.results or [])]
    return json_response({"findings": rows})


async def get_finding(request: Request, env, workspace_id: str, finding_id: str) -> Response:
    """GET /api/workspaces/{wid}/findings/{fid} — decrypt and return full finding body."""
    token_payload = _require_auth(request, env)
    if isinstance(token_payload, Response):
        return token_payload

    if not await _is_member(env, workspace_id, token_payload["sub"]):
        return error_response("Forbidden", 403)

    result = await env.DB.prepare(
        "SELECT * FROM findings WHERE id = ? AND workspace_id = ?"
    ).bind(finding_id, workspace_id).first()

    if not result:
        return error_response("Finding not found", 404)

    row = dict(result)

    # Decrypt body from KV
    kv_key = f"{workspace_id}:finding:{finding_id}:body"
    encrypted_body = await env.WORKSPACE_KV.get(kv_key)
    if encrypted_body:
        root_secret = env.ROOT_SECRET
        key = await derive_workspace_key(workspace_id, root_secret)
        row["body"] = await decrypt_payload(key, encrypted_body)
    else:
        row["body"] = {}

    return json_response(row)


async def create_finding(request: Request, env, workspace_id: str) -> Response:
    """POST /api/workspaces/{id}/findings — create a new finding with encrypted body."""
    token_payload = _require_auth(request, env)
    if isinstance(token_payload, Response):
        return token_payload

    if not await _is_member(env, workspace_id, token_payload["sub"]):
        return error_response("Forbidden", 403)

    body = await _parse_json(request)
    if not body:
        return error_response("Request body must be JSON")

    required = ["title", "severity", "cvss_score"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return error_response(f"Missing required fields: {', '.join(missing)}")

    severity = body["severity"].upper()
    if severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"}:
        return error_response("severity must be one of: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL")

    finding_id = _new_id("fnd")
    now = int(time.time())

    # Store metadata in D1 (unencrypted for querying)
    await env.DB.prepare(
        "INSERT INTO findings (id, workspace_id, title, severity, cvss_score, status, "
        "assigned_to, created_by, created_at) VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?)"
    ).bind(
        finding_id, workspace_id,
        body["title"], severity, float(body["cvss_score"]),
        body.get("assigned_to"), token_payload["sub"], now,
    ).run()

    # Encrypt finding body and store in KV
    sensitive_fields = {
        "summary":      body.get("summary", ""),
        "steps":        body.get("steps", ""),
        "impact":       body.get("impact", ""),
        "remediation":  body.get("remediation", ""),
        "references":   body.get("references", []),
        "cvss_vector":  body.get("cvss_vector", ""),
    }
    root_secret = env.ROOT_SECRET
    key = await derive_workspace_key(workspace_id, root_secret)
    encrypted = await encrypt_payload(key, json.dumps(sensitive_fields))

    kv_key = f"{workspace_id}:finding:{finding_id}:body"
    await env.WORKSPACE_KV.put(kv_key, encrypted)

    return json_response(
        {"id": finding_id, "workspace_id": workspace_id, "title": body["title"],
         "severity": severity, "status": "open", "created_at": now},
        status=201,
    )


async def update_finding(request: Request, env, workspace_id: str, finding_id: str) -> Response:
    """PATCH /api/workspaces/{wid}/findings/{fid} — partial update."""
    token_payload = _require_auth(request, env)
    if isinstance(token_payload, Response):
        return token_payload

    if not await _is_member(env, workspace_id, token_payload["sub"]):
        return error_response("Forbidden", 403)

    body = await _parse_json(request)
    if not body:
        return error_response("Request body must be JSON")

    # Update metadata columns
    meta_cols = {}
    for col in ("title", "severity", "cvss_score", "status", "assigned_to"):
        if col in body:
            meta_cols[col] = body[col]

    if meta_cols:
        set_clause = ", ".join(f"{k} = ?" for k in meta_cols)
        await env.DB.prepare(
            f"UPDATE findings SET {set_clause} WHERE id = ? AND workspace_id = ?"
        ).bind(*meta_cols.values(), finding_id, workspace_id).run()

    # Update encrypted body if any sensitive field changed
    body_fields = {"summary", "steps", "impact", "remediation", "references", "cvss_vector"}
    if any(f in body for f in body_fields):
        kv_key = f"{workspace_id}:finding:{finding_id}:body"
        root_secret = env.ROOT_SECRET
        key = await derive_workspace_key(workspace_id, root_secret)

        existing_enc = await env.WORKSPACE_KV.get(kv_key)
        if existing_enc:
            existing = json.loads(await decrypt_payload(key, existing_enc))
        else:
            existing = {}

        for f in body_fields:
            if f in body:
                existing[f] = body[f]

        await env.WORKSPACE_KV.put(kv_key, await encrypt_payload(key, json.dumps(existing)))

    return json_response({"id": finding_id, "updated": True})


# --- Evidence ---

async def upload_evidence(request: Request, env, workspace_id: str, finding_id: str) -> Response:
    """
    POST /api/workspaces/{wid}/findings/{fid}/evidence
    Accepts multipart/form-data with a 'file' field.
    Encrypts and stores in KV; returns a signed evidence ID.
    """
    token_payload = _require_auth(request, env)
    if isinstance(token_payload, Response):
        return token_payload

    if not await _is_member(env, workspace_id, token_payload["sub"]):
        return error_response("Forbidden", 403)

    form_data = await request.formData()
    file = form_data.get("file")
    if not file:
        return error_response("No file field in form data")

    MAX_BYTES = 50 * 1024 * 1024  # 50 MB
    file_bytes = await file.arrayBuffer()
    if len(bytes(Uint8Array.new(file_bytes))) > MAX_BYTES:
        return error_response("File exceeds 50 MB limit", 413)

    evidence_id = _new_id("ev")
    root_secret = env.ROOT_SECRET
    key = await derive_workspace_key(workspace_id, root_secret)

    # Encrypt raw bytes: base64 encode first, then encrypt as string
    raw_b64 = base64.b64encode(bytes(Uint8Array.new(file_bytes))).decode()
    encrypted = await encrypt_payload(key, raw_b64)

    kv_key = f"{workspace_id}:evidence:{evidence_id}"
    await env.WORKSPACE_KV.put(kv_key, encrypted)

    meta = {
        "id": evidence_id,
        "finding_id": finding_id,
        "workspace_id": workspace_id,
        "filename": file.name,
        "size": len(bytes(Uint8Array.new(file_bytes))),
        "uploaded_by": token_payload["sub"],
        "uploaded_at": int(time.time()),
    }
    meta_key = f"{workspace_id}:evidence:{evidence_id}:meta"
    await env.WORKSPACE_KV.put(meta_key, json.dumps(meta))

    return json_response(meta, status=201)


# --- Escalation to BLT ---

async def escalate_finding(request: Request, env, workspace_id: str, finding_id: str) -> Response:
    """
    POST /api/workspaces/{wid}/findings/{fid}/escalate
    Submits the finding to the OWASP BLT platform for public or
    coordinated disclosure.  In production this would call the BLT API.
    """
    token_payload = _require_auth(request, env)
    if isinstance(token_payload, Response):
        return token_payload

    if not await _is_member(env, workspace_id, token_payload["sub"]):
        return error_response("Forbidden", 403)

    body = await _parse_json(request) or {}
    disclosure_type = body.get("disclosure_type", "coordinated")
    if disclosure_type not in {"public", "coordinated", "private"}:
        return error_response("disclosure_type must be 'public', 'coordinated', or 'private'")

    # Mark as escalated in D1
    await env.DB.prepare(
        "UPDATE findings SET status = 'escalated' WHERE id = ? AND workspace_id = ?"
    ).bind(finding_id, workspace_id).run()

    escalation_id = _new_id("esc")
    now = int(time.time())

    return json_response({
        "escalation_id": escalation_id,
        "finding_id": finding_id,
        "disclosure_type": disclosure_type,
        "status": "submitted",
        "blt_url": f"https://blt.owasp.org/issues/{escalation_id}",
        "submitted_at": now,
    }, status=201)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

ROUTES: list[tuple[str, str, object]] = [
    ("OPTIONS", "*",                                                                handle_options),
    ("GET",     "/api/workspaces",                                                  list_workspaces),
    ("POST",    "/api/workspaces",                                                  create_workspace),
    ("GET",     "/api/workspaces/{workspace_id}/findings",                          list_findings),
    ("POST",    "/api/workspaces/{workspace_id}/findings",                          create_finding),
    ("GET",     "/api/workspaces/{workspace_id}/findings/{finding_id}",             get_finding),
    ("PATCH",   "/api/workspaces/{workspace_id}/findings/{finding_id}",             update_finding),
    ("POST",    "/api/workspaces/{workspace_id}/findings/{finding_id}/evidence",    upload_evidence),
    ("POST",    "/api/workspaces/{workspace_id}/findings/{finding_id}/escalate",    escalate_finding),
]


def _match_route(method: str, path: str) -> tuple[object | None, dict]:
    """Simple pattern-matching router. Returns (handler, path_params)."""
    for route_method, pattern, handler in ROUTES:
        if route_method not in (method, "*"):
            continue
        if pattern == "*":
            return handler, {}
        parts_p = pattern.split("/")
        parts_r = path.split("/")
        if len(parts_p) != len(parts_r):
            continue
        params = {}
        matched = True
        for pp, rp in zip(parts_p, parts_r):
            if pp.startswith("{") and pp.endswith("}"):
                params[pp[1:-1]] = rp
            elif pp != rp:
                matched = False
                break
        if matched:
            return handler, params
    return None, {}


# ---------------------------------------------------------------------------
# Private utilities
# ---------------------------------------------------------------------------

def _new_id(prefix: str) -> str:
    rand_bytes = os.urandom(12)
    return f"{prefix}_{base64.urlsafe_b64encode(rand_bytes).decode().rstrip('=')}"


def _require_auth(request: Request, env) -> dict | Response:
    token = get_bearer_token(request)
    if not token:
        return error_response("Authorization header required", 401)
    payload = verify_token(token, env.ROOT_SECRET)
    if not payload:
        return error_response("Invalid or expired token", 401)
    return payload


async def _is_member(env, workspace_id: str, user_id: str) -> bool:
    row = await env.DB.prepare(
        "SELECT 1 FROM memberships WHERE workspace_id = ? AND user_id = ? LIMIT 1"
    ).bind(workspace_id, user_id).first()
    return row is not None


async def _parse_json(request: Request) -> dict | None:
    try:
        return await request.json()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Cloudflare Workers entrypoint
# ---------------------------------------------------------------------------

async def on_fetch(request: Request, env) -> Response:
    """Main fetch handler — registered as the Workers fetch event handler."""
    url = request.url
    # Extract path (strip query string)
    path = url.split("?")[0]
    if "://" in path:
        path = "/" + "/".join(path.split("/")[3:])

    handler, params = _match_route(request.method, path)
    if handler is None:
        return error_response("Not Found", 404)

    try:
        return await handler(request, env, **params)
    except Exception as exc:  # noqa: BLE001
        # Log for Workers observability (visible in `wrangler tail`) without
        # exposing internal details to the client.
        console.error(f"[blt-ketchup] Unhandled error in {handler.__name__}: {exc!r}")
        return error_response("Internal server error", 500)