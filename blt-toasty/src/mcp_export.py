"""
MCP Export API for OWASP BLT-Toasty.

Exposes the canonical triage schema via a GET /mcp/triage/{triage_id} endpoint.
Secured using RS256 JWT verification (OWASP service principal).
Enforces per-agent rate limiting via Durable Objects.
"""

import json
import logging
from typing import Any
from js import Date

from src.auth import verify_agent_jwt
from src.errors import AuditIncompleteError, JWTExpiredError, JWTInvalidError
from src.rationale_builder import audit_completeness_check
from js import Response, Headers

logger = logging.getLogger("toasty.mcp_export")


def create_json_response(data: dict, status_code: int = 200, extra_headers: dict | None = None) -> Response:
    headers = Headers.new()
    headers.set("Content-Type", "application/json")
    headers.set("Access-Control-Allow-Origin", "*")
    if extra_headers:
        for k, v in extra_headers.items():
            headers.set(k, v)
    return Response.new(json.dumps(data), status=status_code, headers=headers)


def create_error_response(message: str, status_code: int = 500) -> Response:
    return create_json_response({"error": message, "status": status_code}, status_code)


async def get_triage_record(event_id: str, db: Any) -> dict:
    """
    Fetch and assemble the complete triage record from D1.

    Args:
        event_id: The triage event ID.
        db: The Cloudflare D1 database handle (prepare/bind API).

    Returns:
        The canonical JSON export contract dict.

    Raises:
        KeyError: If the event is not found.
        AuditIncompleteError: If the event hasn't completed the pipeline.
    """
    # 1. Event base details
    event_row = (
        await db.prepare("SELECT status, project_id, issue_iid, created_at FROM triage_events WHERE id = ?")
        .bind(event_id)
        .first()
    )

    if not event_row:
        raise KeyError(f"Event {event_id} not found")

    def get_val(r, k, idx):
        return r[k] if hasattr(r, "__getitem__") and k in r else r[idx]

    status = get_val(event_row, "status", 0)
    if status != "complete":
        raise AuditIncompleteError(f"Triage event {event_id} is not complete (status: {status})", event_id, ["status"])

    # Verify audit completeness
    is_complete, missing = await audit_completeness_check(event_id, db)
    if not is_complete:
        raise AuditIncompleteError(f"Audit incomplete for {event_id}", event_id, missing)

    issue_iid = get_val(event_row, "issue_iid", 2)

    # 2. Triage summaries
    summary_row = (
        await db.prepare(
            "SELECT executive_summary, cwe_hints, model_used, confidence "
            "FROM triage_summaries WHERE triage_event_id = ?"
        )
        .bind(event_id)
        .first()
    )

    # 3. Triage rationale
    rationale_row = (
        await db.prepare(
            "SELECT cwe_rationale, duplicate_rationale, confidence_trace "
            "FROM triage_rationale WHERE triage_event_id = ?"
        )
        .bind(event_id)
        .first()
    )

    # 4. Duplicate candidates
    dup_res = (
        await db.prepare(
            "SELECT candidate_event_id, similarity_score, llm_rationale "
            "FROM duplicate_candidates WHERE triage_event_id = ? "
            "ORDER BY similarity_score DESC LIMIT 3"
        )
        .bind(event_id)
        .all()
    )
    dup_candidates_raw = getattr(dup_res, "results", []) or []

    # 5. Redaction audit (count only)
    audit_row = (
        await db.prepare("SELECT COUNT(*) AS cnt FROM redaction_audit WHERE triage_event_id = ?").bind(event_id).first()
    )

    # Construct the JSON export contract (Version 1.0)
    issue_iid_str = str(issue_iid) if issue_iid else "unknown"
    source_ref = f"https://gitlab.com/OWASP-BLT/BLT/-/issues/{issue_iid_str}"

    cwe_hints = []
    if rationale_row:
        cwe_rationale_str = get_val(rationale_row, "cwe_rationale", 0)
        cwe_hints = json.loads(cwe_rationale_str) if cwe_rationale_str else []

    reasoning = {
        "confidence_trace": {},
        "model_used": "unknown",
        "model_version": "1.0",
    }

    if summary_row:
        reasoning["model_used"] = get_val(summary_row, "model_used", 2)
    if rationale_row:
        trace_str = get_val(rationale_row, "confidence_trace", 2)
        if trace_str:
            reasoning["confidence_trace"] = json.loads(trace_str)

    duplicate_candidates = []
    for cand in dup_candidates_raw:
        duplicate_candidates.append(
            {
                "event_id": get_val(cand, "candidate_event_id", 0),
                "score": float(get_val(cand, "similarity_score", 1)),
                "rationale": get_val(cand, "llm_rationale", 2),
            }
        )

    audit_cnt = get_val(audit_row, "cnt", 0) if audit_row else 0
    audit = {"redaction_entity_count": audit_cnt, "redaction_method": "native", "used_fallback": False}

    now_utc = Date.now()
    now_iso = Date.new(now_utc).toISOString()

    return {
        "schema_version": "1.0",
        "triage_id": event_id,
        "source_ref": source_ref,
        "summary_150": get_val(summary_row, "executive_summary", 0) if summary_row else "",
        "duplicate_candidates": duplicate_candidates,
        "cwe_hints": cwe_hints,
        "reasoning": reasoning,
        "audit": audit,
        "exported_at": now_iso,
    }


async def handle_mcp_export(request: Any, env: Any, triage_id: str) -> Any:
    """
    Handle the GET /mcp/triage/{triage_id} request.

    Enforces JWT authentication, Rate Limiting, and gathers the triage record.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return create_error_response("Missing or malformed Authorization header", 401)

    token = auth_header[len("Bearer ") :].strip()

    try:
        claims = await verify_agent_jwt(token, env)
    except JWTExpiredError as e:
        return create_error_response(f"Token expired: {e}", 401)
    except JWTInvalidError as e:
        return create_error_response(f"Unauthorized: {e}", 401)

    agent_id = claims["sub"]

    # Rate Limiting via Durable Object
    rl_id = env.RATE_LIMITER_DO.idFromName(agent_id)
    rl_obj = env.RATE_LIMITER_DO.get(rl_id)

    from js import Request, Object, Reflect

    opts = Object.new()
    Reflect.set(opts, "method", "POST")

    h = Object.new()
    Reflect.set(h, "Content-Type", "application/json")
    Reflect.set(opts, "headers", h)
    Reflect.set(opts, "body", json.dumps({"agent_id": agent_id}))

    js_req = Request.new("http://internal/check", opts)

    rl_resp = await rl_obj.fetch(js_req)
    if rl_resp.status == 429:
        resp_body = json.loads(await rl_resp.text())
        retry_after = resp_body.get("retry_after", 60)

        headers = {"Retry-After": str(retry_after)}
        return create_json_response({"error": "rate_limit_exceeded"}, 429, headers)
    elif rl_resp.status != 200:
        logger.error(f"Rate Limiter DO returned {rl_resp.status}")
        return create_error_response("Internal server error", 500)

    try:
        db = env.DB
        record = await get_triage_record(triage_id, db)

        headers = {"Cache-Control": "no-store", "X-Triage-Schema-Version": "1.0"}
        return create_json_response(record, 200, headers)

    except KeyError:
        return create_error_response(f"Triage event {triage_id} not found", 404)
    except AuditIncompleteError as e:
        headers = {"Retry-After": "30"}
        return create_json_response(
            {"error": "triage_incomplete", "missing_fields": e.missing_fields, "retry_after": 30}, 503, headers
        )
    except Exception as e:
        logger.error(f"Error in mcp export: {e}")
        return create_error_response("Internal server error", 500)
