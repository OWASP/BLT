"""Utility helpers for database serialization.

Originally part of storage/connection.py — extracted so D1 query
classes don't depend on aiosqlite.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


logger = logging.getLogger(__name__)


def d1_row(result: Any) -> dict[str, Any]:
    """Convert a D1 query result to a plain Python dict.

    Uses ``result.copy()`` — the approach validated in Spike 3 for
    this Workers runtime where ``to_py()`` is not available.
    """
    if result is None:
        return {}
    return result.copy()


def d1_rows(result: Any) -> list[dict[str, Any]]:
    """Convert a D1 ``.all()`` result to a list of plain Python dicts."""
    if result is None:
        return []
    return [r.copy() for r in (result.results or [])]


def utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string with second precision."""
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()


def parse_utc(value: str | datetime) -> datetime:
    """Parse an ISO 8601 string (or pass-through a datetime) into a naive UTC datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    text = value.replace("Z", "+00:00") if isinstance(value, str) else str(value)
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def dumps_json(value: object) -> str:
    """Serialize Python object to compact JSON for storage."""
    return json.dumps(value, separators=(",", ":"), default=str)


def loads_json(text: str | None) -> object:
    """Deserialize JSON column, defaulting to {} or [] on empty."""
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in column, returning empty: %r", text[:80])
        return {}
