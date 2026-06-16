"""GET /api/findings business logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from auth import AuthError, require_org_auth
from findings_store import ALLOWED_SORT_FIELDS, FindingsQuery, FindingsStore

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


@dataclass
class FindingsListResult:
    status: int
    body: dict


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


def parse_findings_query(params: Mapping[str, str]) -> tuple[Optional[FindingsQuery], Optional[str]]:
    """Parse query string into FindingsQuery (org_id filled by caller)."""
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

    status = params.get("status") or None
    severity = params.get("severity") or None
    cve_id = params.get("cve_id") or None

    return FindingsQuery(
        status=status,
        severity=severity,
        cve_id=cve_id,
        limit=limit,
        offset=offset,
        sort=sort,
        order=order,
        org_id="",
    ), None


async def list_findings_for_request(
    *,
    env: Any,
    db: Any,
    headers: Mapping[str, str],
    query_params: Mapping[str, str],
    store: Optional[FindingsStore] = None,
) -> FindingsListResult:
    auth = require_org_auth(env, headers)

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


def findings_error_response(exc: AuthError) -> FindingsListResult:
    return FindingsListResult(status=exc.status, body=exc.to_response_body())
