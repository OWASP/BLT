"""BLT-API payload normalizer (VF06).

Maps BLT bug and hunt records into unified ``Event`` objects per
``MVP_V1_SPEC.md`` §VF06.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from models.event import Event


def normalize_blt_bug(
    record: dict[str, Any],
    *,
    received_at: datetime | None = None,
) -> Event:
    """Convert a single BLT bug record into an ``Event``.

    New bugs produce ``bug_bounty_submitted``. Status deltas produce
    ``bug_status_change``. Anything else falls through to ``unknown``.
    """
    bug_id = record.get("id")
    user_id = record.get("user") or record.get("user_id") or bug_id
    username = (
        record.get("username")
        or record.get("user_name")
        or record.get("reported_by")
        or "unknown"
    )
    raw_hunt = record.get("hunt")
    hunt: dict[str, Any] = raw_hunt if isinstance(raw_hunt, dict) else {}
    repo = (
        record.get("repo")
        or hunt.get("repo")
        or hunt.get("domain")
        or ""
    )
    timestamp = _parse_ts(record.get("created") or record.get("modified")) or received_at \
        or datetime.now(tz=timezone.utc).replace(microsecond=0)

    status = (record.get("status") or "").lower()
    is_new = status in ("new", "open", "") or record.get("modified") == record.get("created")
    event_type = "bug_bounty_submitted" if is_new else "bug_status_change"

    return Event(
        source="blt",
        event_type=event_type,
        actor_id=str(user_id) if user_id is not None else "unknown",
        actor_name=str(username),
        repository=str(repo),
        timestamp=timestamp,
        metadata={
            "bug_id": bug_id,
            "url": record.get("url"),
            "description": record.get("description") or record.get("description_raw"),
            "status": record.get("status"),
            "hunt_id": record.get("hunt") if isinstance(record.get("hunt"), int) else hunt.get("id"),
            "domain_name": record.get("domain_name") or hunt.get("domain"),
        },
    )


def normalize_blt_hunt(
    record: dict[str, Any],
    *,
    received_at: datetime | None = None,
) -> Event:
    """Convert a single BLT hunt record into a ``hunt_activity`` event."""
    hunt_id = record.get("id")
    user_id = record.get("user") or record.get("user_id") or hunt_id
    username = record.get("username") or record.get("user_name") or "unknown"
    timestamp = _parse_ts(record.get("created") or record.get("modified")) or received_at \
        or datetime.now(tz=timezone.utc).replace(microsecond=0)

    return Event(
        source="blt",
        event_type="hunt_activity",
        actor_id=str(user_id) if user_id is not None else "unknown",
        actor_name=str(username),
        repository=str(record.get("repo") or record.get("domain") or ""),
        timestamp=timestamp,
        metadata={
            "hunt_id": hunt_id,
            "name": record.get("name"),
            "url": record.get("url"),
            "domain": record.get("domain"),
            "status": record.get("status"),
        },
    )


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc)
        else:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (TypeError, ValueError):
        return None