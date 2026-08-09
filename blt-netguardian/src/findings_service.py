"""Findings triage API business logic."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from auth import AuthError, require_org_auth_async, resolve_org_auth_async
from blt_api_client import BltApiError, create_bug_from_finding, is_blt_api_configured
from d1_compat import row_get
from disclosure import disclosure_for_finding_row
from findings_store import (
    ALLOWED_SORT_FIELDS,
    ALLOWED_STATUSES,
    CSV_COLUMNS,
    FindingsQuery,
    FindingsStore,
    finding_row_to_item,
)
from payload_crypto import PayloadCryptoError, decrypt_payload, get_org_key, is_wrapped_ciphertext
from payload_redact import redact_payload
from pdf_report import build_findings_pdf
from remediation import lookup_remediation

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


@dataclass
class FindingsListResult:
    status: int
    body: dict
    headers: dict | None = None
    content_type: str = "application/json"


def _parse_int_param(raw: Optional[str], *, default: int, minimum: int, maximum: int) -> Optional[int]:
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value < minimum:
        return None
    return min(value, maximum)


def _parse_unix_param(raw: Optional[str]) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _parse_bool_param(raw: Optional[str]) -> bool:
    return str(raw or "").lower() in {"1", "true", "yes"}


def parse_findings_query(params: Mapping[str, str]) -> tuple[Optional[FindingsQuery], Optional[str]]:
    limit = _parse_int_param(params.get("limit"), default=DEFAULT_LIMIT, minimum=1, maximum=MAX_LIMIT)
    if limit is None:
        return None, "invalid limit parameter"

    offset = _parse_int_param(params.get("offset"), default=0, minimum=0, maximum=1_000_000)
    if offset is None:
        return None, "invalid offset parameter"

    sort = params.get("sort", "updated_at") or "updated_at"
    if sort not in ALLOWED_SORT_FIELDS:
        return None, f"invalid sort field; allowed: {', '.join(sorted(ALLOWED_SORT_FIELDS))}"

    order = (params.get("order", "desc") or "desc").lower()
    if order not in {"asc", "desc"}:
        return None, "invalid order parameter; use asc or desc"

    created_from = _parse_unix_param(params.get("created_from"))
    created_to = _parse_unix_param(params.get("created_to"))
    if params.get("created_from") and created_from is None:
        return None, "invalid created_from parameter"
    if params.get("created_to") and created_to is None:
        return None, "invalid created_to parameter"

    status = params.get("status") or None
    if status is not None and status not in ALLOWED_STATUSES:
        return None, f"invalid status; allowed: {', '.join(sorted(ALLOWED_STATUSES))}"

    return FindingsQuery(
        status=status,
        severity=params.get("severity") or None,
        cve_id=params.get("cve_id") or None,
        created_from=created_from,
        created_to=created_to,
        triage_queue=_parse_bool_param(params.get("triage_queue")),
        limit=limit,
        offset=offset,
        sort=sort,
        order=order,
        org_id="",
    ), None


async def _auth_or_error(env: Any, headers: Mapping[str, str], db: Any = None):
    """Read-path auth: Bearer, GitHub session, or demo default-org fallback."""
    return await resolve_org_auth_async(env, headers, db)


async def _mutation_auth_or_error(env: Any, headers: Mapping[str, str], db: Any = None):
    """Write-path auth: Bearer or GitHub session (no demo fallback)."""
    return await require_org_auth_async(env, headers, db)


async def list_findings_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    query_params: Mapping[str, str],
    store: Optional[FindingsStore] = None,
) -> FindingsListResult:
    auth = await _auth_or_error(env, headers, db)

    parsed, error = parse_findings_query(query_params)
    if error:
        return FindingsListResult(status=400, body={"error": "invalid_query", "message": error})

    assert parsed is not None
    parsed.org_id = auth.org_id

    if db is None:
        return FindingsListResult(
            status=503,
            body={"error": "service_unavailable", "message": "findings storage not configured"},
        )

    store = store or FindingsStore(db)
    items, total = await store.list_findings(parsed)

    return FindingsListResult(
        status=200,
        body={
            "org_id": auth.org_id,
            "total": total,
            "limit": parsed.limit,
            "offset": parsed.offset,
            "sort": parsed.sort,
            "order": parsed.order,
            "findings": items,
        },
    )


async def get_finding_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    finding_id: str,
    store: Optional[FindingsStore] = None,
    new_id: Any = None,
    now: Optional[datetime] = None,
) -> FindingsListResult:
    auth = await _auth_or_error(env, headers, db)
    if db is None:
        return FindingsListResult(
            status=503,
            body={"error": "service_unavailable", "message": "findings storage not configured"},
        )

    store = store or FindingsStore(db)
    row = await store.get_finding_detail(auth.org_id, finding_id)
    if row is None:
        return FindingsListResult(status=404, body={"error": "not_found", "message": "finding not found"})

    now = now or datetime.now(timezone.utc)
    id_fn = new_id or (lambda prefix: __import__("hashlib").sha256(
        f"{prefix}-{finding_id}-{now.timestamp()}".encode()
    ).hexdigest()[:16])

    try:
        stored = json.loads(row_get(row, "payload_json") or "{}")
    except json.JSONDecodeError:
        stored = {}

    payload_raw: dict = {}
    encrypted_at_rest = False
    decrypted = False
    if is_wrapped_ciphertext(stored):
        encrypted_at_rest = True
        action = "decrypt_view"
        key = get_org_key(env, auth.org_id)
        if key is not None:
            try:
                payload_raw = decrypt_payload(
                    key, stored["ciphertext"], aad=auth.org_id.encode()
                )
                decrypted = True
            except PayloadCryptoError:
                payload_raw = {}
    else:
        action = "view_detail"
        payload_raw = stored if isinstance(stored, dict) else {}

    await store.record_access(
        log_id=id_fn("access-view"),
        org_id=auth.org_id,
        finding_id=finding_id,
        actor=auth.org_id,
        action=action,
        detail={
            "route": "GET /api/findings/{id}",
            "encrypted_at_rest": encrypted_at_rest,
            "decrypted": decrypted,
        },
        created_at_unix=int(now.timestamp()),
    )
    access_logs = await store.list_access_logs(auth.org_id, finding_id, limit=5)

    finding = finding_row_to_item(row)
    remediation = lookup_remediation(
        row_get(row, "rule_id"),
        cve_id=row_get(row, "cve_id"),
    )

    return FindingsListResult(
        status=200,
        body={
            "finding": finding,
            "payload_snippet": redact_payload(payload_raw),
            "remediation": remediation,
            "evidence": {
                "encrypted_at_rest": encrypted_at_rest,
                "decrypted": decrypted,
            },
            "envelope": {
                "sender_id": row_get(row, "sender_id"),
                "kid": row_get(row, "kid"),
                "received_at": row_get(row, "envelope_received_at"),
            },
            "access": {
                "view_logged": True,
                "recent": access_logs,
            },
        },
    )


async def disclosure_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    finding_id: str,
    store: Optional[FindingsStore] = None,
    fetch_impl: Any = None,
) -> FindingsListResult:
    """GET /api/findings/{id}/disclosure — security.txt discovery for the finding target."""
    auth = _auth_or_error(env, headers)
    if db is None:
        return FindingsListResult(
            status=503,
            body={"error": "service_unavailable", "message": "findings storage not configured"},
        )
    store = store or FindingsStore(db)
    row = await store.get_finding_detail(auth.org_id, finding_id)
    if row is None:
        return FindingsListResult(status=404, body={"error": "not_found", "message": "finding not found"})

    disclosure = await disclosure_for_finding_row(row, fetch_impl=fetch_impl)
    return FindingsListResult(
        status=200,
        body={"finding_id": finding_id, "disclosure": disclosure},
    )


async def export_csv_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    query_params: Mapping[str, str],
    store: Optional[FindingsStore] = None,
) -> FindingsListResult:
    auth = await _auth_or_error(env, headers, db)

    parsed, error = parse_findings_query(query_params)
    if error:
        return FindingsListResult(status=400, body={"error": "invalid_query", "message": error})

    assert parsed is not None
    parsed.org_id = auth.org_id

    if db is None:
        return FindingsListResult(
            status=503,
            body={"error": "service_unavailable", "message": "findings storage not configured"},
        )

    store = store or FindingsStore(db)
    rows = await store.export_findings(parsed)

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({col: row.get(col, "") for col in CSV_COLUMNS})

    return FindingsListResult(
        status=200,
        body={"csv": buffer.getvalue()},
        content_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="findings.csv"'},
    )


def _payload_for_pdf(env: Any, org_id: str, stored: Any) -> dict[str, Any]:
    """Decrypt when possible; never return ciphertext wrappers or unretracted secrets."""
    if not isinstance(stored, dict):
        return {}
    if is_wrapped_ciphertext(stored):
        key = get_org_key(env, org_id)
        if key is None:
            return {"encrypted_at_rest": True, "decrypted": False}
        try:
            plain = decrypt_payload(key, stored["ciphertext"], aad=org_id.encode())
            return redact_payload(plain if isinstance(plain, dict) else {"value": plain})
        except PayloadCryptoError:
            return {"encrypted_at_rest": True, "decrypted": False, "error": "decrypt_failed"}
    return redact_payload(stored)


async def export_pdf_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    query_params: Mapping[str, str],
    store: Optional[FindingsStore] = None,
) -> FindingsListResult:
    """GET /api/findings/export.pdf — org-scoped multi-finding PDF (metadata only)."""
    auth = await _auth_or_error(env, headers, db)

    parsed, error = parse_findings_query(query_params)
    if error:
        return FindingsListResult(status=400, body={"error": "invalid_query", "message": error})

    assert parsed is not None
    parsed.org_id = auth.org_id

    if db is None:
        return FindingsListResult(
            status=503,
            body={"error": "service_unavailable", "message": "findings storage not configured"},
        )

    store = store or FindingsStore(db)
    rows = await store.export_findings(parsed)
    findings = [finding_row_to_item(row) for row in rows]
    pdf_bytes = build_findings_pdf(findings, org_id=auth.org_id)

    return FindingsListResult(
        status=200,
        body={"pdf": pdf_bytes},
        content_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="findings.pdf"'},
    )


async def export_finding_pdf_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    finding_id: str,
    store: Optional[FindingsStore] = None,
    new_id: Any = None,
    now: Optional[datetime] = None,
) -> FindingsListResult:
    """GET /api/findings/{id}/export.pdf — single finding PDF with redacted evidence."""
    auth = _auth_or_error(env, headers)
    if db is None:
        return FindingsListResult(
            status=503,
            body={"error": "service_unavailable", "message": "findings storage not configured"},
        )

    store = store or FindingsStore(db)
    row = await store.get_finding_detail(auth.org_id, finding_id)
    if row is None:
        return FindingsListResult(status=404, body={"error": "not_found", "message": "finding not found"})

    now = now or datetime.now(timezone.utc)
    id_fn = new_id or (lambda prefix: __import__("hashlib").sha256(
        f"{prefix}-{finding_id}-{now.timestamp()}".encode()
    ).hexdigest()[:16])

    try:
        stored = json.loads(row_get(row, "payload_json") or "{}")
    except json.JSONDecodeError:
        stored = {}

    snippet = _payload_for_pdf(env, auth.org_id, stored)
    await store.record_access(
        log_id=id_fn("access-pdf"),
        org_id=auth.org_id,
        finding_id=finding_id,
        actor=auth.org_id,
        action="export_pdf",
        detail={"route": "GET /api/findings/{id}/export.pdf"},
        created_at_unix=int(now.timestamp()),
    )

    finding = finding_row_to_item(row)
    pdf_bytes = build_findings_pdf(
        [finding],
        org_id=auth.org_id,
        title="NetGuardian Finding Report",
        snippet_by_id={finding_id: snippet},
    )
    return FindingsListResult(
        status=200,
        body={"pdf": pdf_bytes},
        content_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="finding-{finding_id}.pdf"'},
    )


async def convert_to_issue_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    finding_id: str,
    store: Optional[FindingsStore] = None,
    new_id: Any = None,
    now: Optional[datetime] = None,
    fetch_impl: Any = None,
) -> FindingsListResult:
    auth = await _mutation_auth_or_error(env, headers, db)
    if db is None:
        return FindingsListResult(
            status=503,
            body={"error": "service_unavailable", "message": "findings storage not configured"},
        )

    store = store or FindingsStore(db)
    row = await store.get_finding_detail(auth.org_id, finding_id)
    if row is None:
        return FindingsListResult(status=404, body={"error": "not_found", "message": "finding not found"})

    existing = row_get(row, "blt_issue_id")
    if existing:
        return FindingsListResult(
            status=200,
            body={
                "status": "existing",
                "finding_id": finding_id,
                "blt_issue_id": existing,
            },
        )

    now = now or datetime.now(timezone.utc)
    id_fn = new_id or (lambda prefix: __import__("hashlib").sha256(
        f"{prefix}-{finding_id}-{now.timestamp()}".encode()
    ).hexdigest()[:16])

    use_stub = not is_blt_api_configured(env)
    audit_detail: dict[str, Any] = {"finding_id": finding_id}

    try:
        if use_stub:
            blt_issue_id = id_fn("blt")
            audit_detail["blt_issue_id"] = blt_issue_id
            audit_detail["stub"] = True
        else:
            blt_issue_id = await create_bug_from_finding(
                env, row, fetch_impl=fetch_impl,
            )
            audit_detail["blt_issue_id"] = blt_issue_id
            audit_detail["blt_api"] = True
    except BltApiError as exc:
        return FindingsListResult(
            status=502,
            body={
                "error": "blt_api_error",
                "message": str(exc),
                "blt_status": exc.status,
            },
        )

    updated = int(now.timestamp())
    await store.set_blt_issue_id(auth.org_id, finding_id, blt_issue_id, updated)
    await store.record_access(
        log_id=id_fn("access-convert"),
        org_id=auth.org_id,
        finding_id=finding_id,
        actor=auth.org_id,
        action="convert_to_issue",
        detail=audit_detail,
        created_at_unix=updated,
    )

    body: dict[str, Any] = {
        "status": "created",
        "finding_id": finding_id,
        "blt_issue_id": blt_issue_id,
    }
    if use_stub:
        body["stub"] = True

    return FindingsListResult(status=201, body=body)


async def update_finding_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    finding_id: str,
    body: Mapping[str, Any],
    store: Optional[FindingsStore] = None,
    new_id: Any = None,
    now: Optional[datetime] = None,
) -> FindingsListResult:
    auth = await _mutation_auth_or_error(env, headers, db)
    if db is None:
        return FindingsListResult(
            status=503,
            body={"error": "service_unavailable", "message": "findings storage not configured"},
        )

    status = body.get("status")
    if not status or status not in ALLOWED_STATUSES:
        return FindingsListResult(
            status=400,
            body={
                "error": "invalid_body",
                "message": f"status required; allowed: {', '.join(sorted(ALLOWED_STATUSES))}",
            },
        )

    store = store or FindingsStore(db)
    row = await store.get_finding_detail(auth.org_id, finding_id)
    if row is None:
        return FindingsListResult(status=404, body={"error": "not_found", "message": "finding not found"})

    now = now or datetime.now(timezone.utc)
    updated = int(now.timestamp())
    id_fn = new_id or (lambda prefix: __import__("hashlib").sha256(
        f"{prefix}-{finding_id}-{now.timestamp()}".encode()
    ).hexdigest()[:16])

    try:
        ok = await store.update_finding_status(auth.org_id, finding_id, status, updated)
    except ValueError as exc:
        return FindingsListResult(status=400, body={"error": "invalid_body", "message": str(exc)})

    if not ok:
        return FindingsListResult(status=404, body={"error": "not_found", "message": "finding not found"})

    await store.record_access(
        log_id=id_fn("access-status"),
        org_id=auth.org_id,
        finding_id=finding_id,
        actor=auth.org_id,
        action="status_change",
        detail={"from": row_get(row, "status"), "to": status},
        created_at_unix=updated,
    )

    updated_row = await store.get_finding_detail(auth.org_id, finding_id)
    finding = finding_row_to_item(updated_row)

    return FindingsListResult(
        status=200,
        body={"finding": finding, "status": "updated"},
    )


def findings_error_response(exc: AuthError) -> FindingsListResult:
    return FindingsListResult(status=exc.status, body=exc.to_response_body())
