"""Shared domain queue API: submit, claim, complete, fail, list, expire."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from auth import AuthError, resolve_org_auth_async
from domain_normalize import normalize_domain
from domain_queue_store import CLAIMABLE, DomainQueueStore, MAX_RETRIES, STATUSES

LEASE_SECONDS = 180
DEFAULT_LIMIT = 100
MAX_LIMIT = 200
MAX_SUBMIT = 50


class DomainQueueError(Exception):
    def __init__(self, message: str, *, status: int = 400, code: str = "bad_request"):
        self.message = message
        self.status = status
        self.code = code
        super().__init__(message)


def _now() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _job_id(org_id: str, host_key: str) -> str:
    return hashlib.sha256(f"{org_id}:{host_key}".encode()).hexdigest()[:16]


def _sender_id(body: Mapping[str, Any], headers: Mapping[str, str]) -> str:
    raw = (
        body.get("sender_id")
        or headers.get("X-NG-Sender")
        or headers.get("x-ng-sender")
        or "scanner-1"
    )
    text = str(raw).strip()
    return text[:80] if text else "scanner-1"


async def _auth(env, headers, db):
    return await resolve_org_auth_async(env, headers, db=db)


def error_body(exc: DomainQueueError | AuthError) -> tuple[int, dict]:
    if isinstance(exc, AuthError):
        return exc.status, exc.to_response_body()
    return exc.status, {"error": exc.code, "message": exc.message}


async def submit_domains_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    body: Mapping[str, Any],
) -> tuple[int, dict]:
    ctx = await _auth(env, headers, db)
    if db is None:
        raise DomainQueueError("database unavailable", status=503, code="no_db")
    store = DomainQueueStore(db)
    sender = _sender_id(body, headers)
    raw_domains = body.get("domains") or body.get("urls") or []
    if isinstance(raw_domains, str):
        raw_domains = [raw_domains]
    if not isinstance(raw_domains, list) or not raw_domains:
        raise DomainQueueError("domains must be a non-empty list")
    source_url = str(body.get("source_url") or "")[:500] or None
    created: list[dict] = []
    duplicates: list[str] = []
    rejected: list[str] = []
    now = _now()
    for raw in raw_domains[:MAX_SUBMIT]:
        parsed = normalize_domain(str(raw))
        if parsed is None:
            rejected.append(str(raw)[:200])
            continue
        host_key, seed_url = parsed
        job_id = _job_id(ctx.org_id, host_key)
        inserted = await store.insert_pending(
            job_id=job_id,
            org_id=ctx.org_id,
            host_key=host_key,
            seed_url=seed_url,
            discovered_at=now,
            source_url=source_url,
        )
        if inserted:
            job = await store.get_by_id(ctx.org_id, job_id)
            if job:
                created.append(job)
        else:
            duplicates.append(host_key)
    return 200, {
        "org_id": ctx.org_id,
        "sender_id": sender,
        "created": created,
        "duplicate_hosts": duplicates,
        "rejected": rejected,
    }


async def claim_domain_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    body: Mapping[str, Any],
) -> tuple[int, dict]:
    ctx = await _auth(env, headers, db)
    if db is None:
        raise DomainQueueError("database unavailable", status=503, code="no_db")
    store = DomainQueueStore(db)
    sender = _sender_id(body, headers)
    now = _now()
    await store.expire_stale(now)
    for _ in range(5):
        candidate = await store.pick_claimable(ctx.org_id, now)
        if candidate is None:
            return 200, {"job": None, "org_id": ctx.org_id, "sender_id": sender}
        claimed = await store.claim(
            org_id=ctx.org_id,
            job_id=candidate["id"],
            sender_id=sender,
            now=now,
            claim_until=now + LEASE_SECONDS,
        )
        if claimed:
            return 200, {"job": claimed, "org_id": ctx.org_id, "sender_id": sender}
    return 200, {"job": None, "org_id": ctx.org_id, "sender_id": sender}


async def heartbeat_domain_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    body: Mapping[str, Any],
    job_id: str,
) -> tuple[int, dict]:
    ctx = await _auth(env, headers, db)
    if db is None:
        raise DomainQueueError("database unavailable", status=503, code="no_db")
    store = DomainQueueStore(db)
    sender = _sender_id(body, headers)
    job = await store.heartbeat(
        org_id=ctx.org_id,
        job_id=job_id,
        sender_id=sender,
        claim_until=_now() + LEASE_SECONDS,
    )
    if not job or job.get("claimed_by") != sender:
        raise DomainQueueError("job not claimed by this sender", status=409, code="not_owner")
    return 200, {"job": job}


async def complete_domain_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    body: Mapping[str, Any],
    job_id: str,
) -> tuple[int, dict]:
    ctx = await _auth(env, headers, db)
    if db is None:
        raise DomainQueueError("database unavailable", status=503, code="no_db")
    store = DomainQueueStore(db)
    sender = _sender_id(body, headers)
    result = body.get("result") if isinstance(body.get("result"), dict) else {}
    job = await store.complete(
        org_id=ctx.org_id,
        job_id=job_id,
        sender_id=sender,
        now=_now(),
        result_json=json.dumps(result, separators=(",", ":")),
    )
    if not job or job.get("status") != "scanned":
        raise DomainQueueError("job not claimed by this sender", status=409, code="not_owner")
    return 200, {"job": job}


async def fail_domain_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    body: Mapping[str, Any],
    job_id: str,
) -> tuple[int, dict]:
    ctx = await _auth(env, headers, db)
    if db is None:
        raise DomainQueueError("database unavailable", status=503, code="no_db")
    store = DomainQueueStore(db)
    sender = _sender_id(body, headers)
    error = str(body.get("error") or "scan_failed")[:500]
    job = await store.fail(
        org_id=ctx.org_id,
        job_id=job_id,
        sender_id=sender,
        now=_now(),
        error=error,
        max_retries=MAX_RETRIES,
    )
    if not job:
        raise DomainQueueError("job not found", status=404, code="not_found")
    return 200, {"job": job}


async def list_domains_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    query_params: Mapping[str, str],
) -> tuple[int, dict]:
    ctx = await _auth(env, headers, db)
    if db is None:
        raise DomainQueueError("database unavailable", status=503, code="no_db")
    store = DomainQueueStore(db)
    status = (query_params.get("status") or "").strip() or None
    if status and status not in STATUSES:
        raise DomainQueueError(f"invalid status; want {sorted(STATUSES)}")
    try:
        limit = int(query_params.get("limit") or DEFAULT_LIMIT)
    except ValueError:
        limit = DEFAULT_LIMIT
    limit = max(1, min(limit, MAX_LIMIT))
    jobs = await store.list_jobs(ctx.org_id, status=status, limit=limit)
    counts = await store.counts(ctx.org_id)
    return 200, {
        "org_id": ctx.org_id,
        "jobs": jobs,
        "counts": counts,
        "claimable": sorted(CLAIMABLE),
    }


async def expire_domain_leases(*, db: Any) -> int:
    if db is None:
        return 0
    return await DomainQueueStore(db).expire_stale(_now())
