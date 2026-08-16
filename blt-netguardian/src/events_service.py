"""Verified events: emit on convert/resolve, HMAC webhook, list API."""

from __future__ import annotations

import asyncio
import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from auth import AuthError, require_org_auth
from canonicalize import hmac_sha256_hex
from d1_compat import row_get
from events_store import (
    ALLOWED_EVENT_TYPES,
    EVENT_CONVERTED,
    EVENT_RESOLVED,
    STATUS_DELIVERED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_SKIPPED,
    EventsQuery,
    EventsStore,
    build_event_payload,
)

DEFAULT_LIMIT = 50
MAX_LIMIT = 100
MAX_WEBHOOK_ATTEMPTS = 5
SIGNATURE_HEADER = "X-NetGuardian-Signature"
EVENT_ID_HEADER = "X-NetGuardian-Event-Id"
EVENT_TYPE_HEADER = "X-NetGuardian-Event-Type"


@dataclass
class EventsApiResult:
    status: int
    body: dict
    headers: dict | None = None


def webhook_url(env: Any) -> Optional[str]:
    raw = getattr(env, "NG_EVENTS_WEBHOOK_URL", None)
    if not raw:
        return None
    value = str(raw).strip()
    return value or None


def webhook_secret(env: Any) -> Optional[bytes]:
    raw = getattr(env, "NG_EVENTS_WEBHOOK_SECRET", None)
    if not raw:
        return None
    value = str(raw).strip()
    if not value:
        return None
    # Accept hex (64 chars) or utf-8 secret string.
    if len(value) == 64:
        try:
            return bytes.fromhex(value)
        except ValueError:
            pass
    return value.encode("utf-8")


def sign_webhook_body(secret: bytes, raw_body: bytes) -> str:
    return f"sha256={hmac_sha256_hex(secret, raw_body)}"


def build_webhook_envelope(event_row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": event_row["id"],
        "org_id": event_row["org_id"],
        "event_type": event_row["event_type"],
        "dedupe_key": event_row["dedupe_key"],
        "created_at": event_row["created_at"],
        "payload": event_row["payload"],
    }


def _urllib_fetch(url: str, method: str, headers: Mapping[str, str], body: bytes) -> tuple[int, str]:
    req = urllib.request.Request(url, data=body, method=method, headers=dict(headers))
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 - operator-configured webhook URL
            return int(getattr(resp, "status", 200) or 200), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read().decode("utf-8", errors="replace")


async def _js_fetch(url: str, method: str, headers: Mapping[str, str], body: bytes) -> tuple[int, str]:
    from js import fetch  # type: ignore[import-not-found]

    resp = await fetch(
        url,
        {
            "method": method,
            "headers": dict(headers),
            "body": body.decode("utf-8"),
        },
    )
    text = await resp.text()
    return int(resp.status), str(text)


async def _default_fetch(url: str, method: str, headers: Mapping[str, str], body: bytes) -> tuple[int, str]:
    """Prefer Workers JS fetch; fall back to urllib for local/dev Python."""
    try:
        from js import fetch  # noqa: F401
        return await _js_fetch(url, method, headers, body)
    except ImportError:
        return await asyncio.to_thread(_urllib_fetch, url, method, headers, body)


async def deliver_event_webhook(
    *,
    env: Any,
    store: EventsStore,
    event_row: Mapping[str, Any],
    now: Optional[datetime] = None,
    fetch_impl: Any = None,
) -> dict[str, Any]:
    """Attempt one webhook delivery; updates outbox status/attempts."""
    now = now or datetime.now(timezone.utc)
    updated = int(now.timestamp())
    org_id = str(event_row["org_id"])
    event_id = str(event_row["id"])
    attempts = int(event_row.get("attempts") or 0) + 1

    url = webhook_url(env)
    if not url:
        await store.mark_delivery(
            org_id=org_id,
            event_id=event_id,
            status=STATUS_SKIPPED,
            attempts=attempts,
            last_error=None,
            updated_at_unix=updated,
        )
        refreshed = await store.get_event(org_id, event_id)
        return refreshed or {**event_row, "status": STATUS_SKIPPED, "attempts": attempts}

    secret = webhook_secret(env)
    if secret is None:
        await store.mark_delivery(
            org_id=org_id,
            event_id=event_id,
            status=STATUS_FAILED,
            attempts=attempts,
            last_error="webhook secret not configured",
            updated_at_unix=updated,
        )
        refreshed = await store.get_event(org_id, event_id)
        return refreshed or {**event_row, "status": STATUS_FAILED, "attempts": attempts}

    envelope = build_webhook_envelope(event_row)
    raw_body = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False, sort_keys=True).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        SIGNATURE_HEADER: sign_webhook_body(secret, raw_body),
        EVENT_ID_HEADER: event_id,
        EVENT_TYPE_HEADER: str(event_row["event_type"]),
    }

    fetch = fetch_impl or _default_fetch
    try:
        status_code, _body = await fetch(url, "POST", headers, raw_body)
        if 200 <= int(status_code) < 300:
            await store.mark_delivery(
                org_id=org_id,
                event_id=event_id,
                status=STATUS_DELIVERED,
                attempts=attempts,
                last_error=None,
                updated_at_unix=updated,
            )
        else:
            terminal = attempts >= MAX_WEBHOOK_ATTEMPTS
            await store.mark_delivery(
                org_id=org_id,
                event_id=event_id,
                status=STATUS_FAILED if terminal else STATUS_PENDING,
                attempts=attempts,
                last_error=f"webhook HTTP {status_code}",
                updated_at_unix=updated,
            )
    except Exception as exc:  # noqa: BLE001 - delivery must never crash convert path
        terminal = attempts >= MAX_WEBHOOK_ATTEMPTS
        await store.mark_delivery(
            org_id=org_id,
            event_id=event_id,
            status=STATUS_FAILED if terminal else STATUS_PENDING,
            attempts=attempts,
            last_error=str(exc)[:500],
            updated_at_unix=updated,
        )

    refreshed = await store.get_event(org_id, event_id)
    return refreshed or dict(event_row)


async def emit_verified_event(
    *,
    env: Any,
    db: Any,
    finding_row: Mapping[str, Any],
    event_type: str,
    issue_id: Optional[str] = None,
    store: Optional[EventsStore] = None,
    new_id: Any = None,
    now: Optional[datetime] = None,
    fetch_impl: Any = None,
    deliver: bool = True,
) -> dict[str, Any]:
    """Persist a verified event (idempotent) and optionally deliver webhook."""
    if event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(f"unsupported event_type: {event_type}")
    if db is None:
        raise RuntimeError("D1 not configured")

    store = store or EventsStore(db)
    now = now or datetime.now(timezone.utc)
    created_at = int(now.timestamp())
    finding_id = str(row_get(finding_row, "id"))
    org_id = str(row_get(finding_row, "org_id"))
    payload = build_event_payload(
        event_type=event_type,
        finding_row=finding_row,
        issue_id=issue_id,
        created_at_unix=created_at,
    )
    id_fn = new_id or (
        lambda prefix: hashlib.sha256(
            f"{prefix}-{org_id}-{payload['dedupe_key']}-{created_at}".encode()
        ).hexdigest()[:16]
    )
    event_id = id_fn("evt")

    row, created = await store.insert_idempotent(
        event_id=event_id,
        org_id=org_id,
        event_type=event_type,
        dedupe_key=payload["dedupe_key"],
        payload=payload,
        created_at_unix=created_at,
        status=STATUS_PENDING,
    )

    if deliver and (created or row.get("status") == STATUS_PENDING):
        row = await deliver_event_webhook(
            env=env,
            store=store,
            event_row=row,
            now=now,
            fetch_impl=fetch_impl,
        )

    return {"event": row, "created": created}


async def emit_converted_event(
    *,
    env: Any,
    db: Any,
    finding_row: Mapping[str, Any],
    issue_id: str,
    store: Optional[EventsStore] = None,
    new_id: Any = None,
    now: Optional[datetime] = None,
    fetch_impl: Any = None,
) -> dict[str, Any]:
    return await emit_verified_event(
        env=env,
        db=db,
        finding_row=finding_row,
        event_type=EVENT_CONVERTED,
        issue_id=issue_id,
        store=store,
        new_id=new_id,
        now=now,
        fetch_impl=fetch_impl,
    )


async def emit_resolved_event(
    *,
    env: Any,
    db: Any,
    finding_row: Mapping[str, Any],
    store: Optional[EventsStore] = None,
    new_id: Any = None,
    now: Optional[datetime] = None,
    fetch_impl: Any = None,
) -> dict[str, Any]:
    return await emit_verified_event(
        env=env,
        db=db,
        finding_row=finding_row,
        event_type=EVENT_RESOLVED,
        issue_id=row_get(finding_row, "blt_issue_id"),
        store=store,
        new_id=new_id,
        now=now,
        fetch_impl=fetch_impl,
    )


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


def parse_events_query(params: Mapping[str, str], org_id: str) -> tuple[Optional[EventsQuery], Optional[str]]:
    limit = _parse_int_param(params.get("limit"), default=DEFAULT_LIMIT, minimum=1, maximum=MAX_LIMIT)
    if limit is None:
        return None, "invalid limit parameter"
    offset = _parse_int_param(params.get("offset"), default=0, minimum=0, maximum=1_000_000)
    if offset is None:
        return None, "invalid offset parameter"

    event_type = params.get("event_type") or None
    if event_type is not None and event_type not in ALLOWED_EVENT_TYPES:
        return None, f"invalid event_type; allowed: {', '.join(sorted(ALLOWED_EVENT_TYPES))}"

    status = params.get("status") or None
    if status is not None and status not in {
        STATUS_PENDING,
        STATUS_DELIVERED,
        STATUS_SKIPPED,
        STATUS_FAILED,
    }:
        return None, "invalid status parameter"

    return EventsQuery(
        org_id=org_id,
        event_type=event_type,
        finding_id=params.get("finding_id") or None,
        status=status,
        limit=limit,
        offset=offset,
    ), None


async def list_events_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    query_params: Mapping[str, str],
    store: Optional[EventsStore] = None,
) -> EventsApiResult:
    try:
        # Always require a real org token — never fall back to NG_DEFAULT_ORG.
        auth = require_org_auth(env, headers)
    except AuthError as exc:
        return EventsApiResult(status=exc.status, body=exc.to_response_body())

    if db is None:
        return EventsApiResult(
            status=503,
            body={"error": "service_unavailable", "message": "events storage not configured"},
        )

    query, err = parse_events_query(query_params, auth.org_id)
    if err or query is None:
        return EventsApiResult(status=400, body={"error": "invalid_query", "message": err or "invalid query"})

    store = store or EventsStore(db)
    total = await store.count_events(query)
    items = await store.list_events(query)
    return EventsApiResult(
        status=200,
        body={
            "events": items,
            "total": total,
            "limit": query.limit,
            "offset": query.offset,
        },
    )


async def get_event_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    event_id: str,
    store: Optional[EventsStore] = None,
) -> EventsApiResult:
    try:
        # Always require a real org token — never fall back to NG_DEFAULT_ORG.
        auth = require_org_auth(env, headers)
    except AuthError as exc:
        return EventsApiResult(status=exc.status, body=exc.to_response_body())

    if db is None:
        return EventsApiResult(
            status=503,
            body={"error": "service_unavailable", "message": "events storage not configured"},
        )

    store = store or EventsStore(db)
    row = await store.get_event(auth.org_id, event_id)
    if row is None:
        return EventsApiResult(status=404, body={"error": "not_found", "message": "event not found"})
    return EventsApiResult(status=200, body={"event": row})


# Keep mutation auth available for future retry endpoints.
require_events_mutation_auth = require_org_auth
