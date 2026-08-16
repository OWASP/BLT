"""HTTP handlers for finding evidence attachments."""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from auth import AuthError, require_org_auth_async, resolve_org_auth_async
from evidence_store import MAX_EVIDENCE_BYTES, EvidenceStore
from findings_service import FindingsListResult
from findings_store import FindingsStore

ALLOWED_MEDIA = frozenset({
    "text/plain",
    "application/json",
    "application/octet-stream",
    "image/png",
    "image/jpeg",
    "text/html",
})


async def list_evidence_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    finding_id: str,
    store: Optional[EvidenceStore] = None,
) -> FindingsListResult:
    try:
        auth = await resolve_org_auth_async(env, headers, db)
    except AuthError as exc:
        return FindingsListResult(status=exc.status, body=exc.to_response_body())
    if db is None:
        return FindingsListResult(
            status=503,
            body={"error": "service_unavailable", "message": "storage not configured"},
        )
    finding = await FindingsStore(db).get_finding_detail(auth.org_id, finding_id)
    if finding is None:
        return FindingsListResult(status=404, body={"error": "not_found", "message": "finding not found"})
    store = store or EvidenceStore(db, env)
    items = await store.list_for_finding(auth.org_id, finding_id)
    return FindingsListResult(
        status=200,
        body={"finding_id": finding_id, "attachments": items},
    )


async def get_evidence_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    finding_id: str,
    evidence_id: str,
    store: Optional[EvidenceStore] = None,
) -> FindingsListResult:
    try:
        auth = await resolve_org_auth_async(env, headers, db)
    except AuthError as exc:
        return FindingsListResult(status=exc.status, body=exc.to_response_body())
    if db is None:
        return FindingsListResult(
            status=503,
            body={"error": "service_unavailable", "message": "storage not configured"},
        )
    store = store or EvidenceStore(db, env)
    meta = await store.get_meta(auth.org_id, evidence_id)
    if meta is None or meta.get("finding_id") != finding_id:
        return FindingsListResult(status=404, body={"error": "not_found", "message": "evidence not found"})
    data = await store.get_bytes(meta)
    if data is None:
        return FindingsListResult(status=404, body={"error": "not_found", "message": "evidence blob missing"})
    return FindingsListResult(
        status=200,
        body={
            "attachment": meta,
            "data_b64": base64.b64encode(data).decode("ascii"),
        },
    )


async def put_evidence_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    finding_id: str,
    body: Mapping[str, Any],
    store: Optional[EvidenceStore] = None,
    new_id: Any = None,
    now: Optional[datetime] = None,
) -> FindingsListResult:
    try:
        auth = await require_org_auth_async(env, headers, db)
    except AuthError as exc:
        return FindingsListResult(status=exc.status, body=exc.to_response_body())
    if db is None:
        return FindingsListResult(
            status=503,
            body={"error": "service_unavailable", "message": "storage not configured"},
        )
    finding = await FindingsStore(db).get_finding_detail(auth.org_id, finding_id)
    if finding is None:
        return FindingsListResult(status=404, body={"error": "not_found", "message": "finding not found"})

    raw_b64 = body.get("data_b64")
    if not isinstance(raw_b64, str) or not raw_b64.strip():
        return FindingsListResult(status=400, body={"error": "invalid_body", "message": "data_b64 required"})
    try:
        data = base64.b64decode(raw_b64, validate=True)
    except (ValueError, TypeError):
        return FindingsListResult(status=400, body={"error": "invalid_body", "message": "data_b64 is not valid base64"})
    if not data:
        return FindingsListResult(status=400, body={"error": "invalid_body", "message": "empty evidence"})
    if len(data) > MAX_EVIDENCE_BYTES:
        return FindingsListResult(
            status=413,
            body={"error": "too_large", "message": f"evidence exceeds {MAX_EVIDENCE_BYTES} bytes"},
        )
    media_type = str(body.get("media_type") or "application/octet-stream").strip()
    if media_type not in ALLOWED_MEDIA:
        return FindingsListResult(
            status=400,
            body={"error": "invalid_body", "message": f"unsupported media_type: {media_type}"},
        )

    now = now or datetime.now(timezone.utc)
    created = int(now.timestamp())
    id_fn = new_id or (
        lambda prefix: hashlib.sha256(
            f"{prefix}-{finding_id}-{created}-{len(data)}".encode()
        ).hexdigest()[:16]
    )
    store = store or EvidenceStore(db, env)
    try:
        meta = await store.put(
            evidence_id=id_fn("evd"),
            org_id=auth.org_id,
            finding_id=finding_id,
            data=data,
            media_type=media_type,
            created_at_unix=created,
        )
    except ValueError as exc:
        return FindingsListResult(status=413, body={"error": "too_large", "message": str(exc)})
    return FindingsListResult(status=201, body={"attachment": meta})
