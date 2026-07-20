"""Idempotency-based deduplication (VF03).

Looks up the ``idempotency_key`` on the ``events`` table to drop
duplicate deliveries before they reach normalization.
"""

from __future__ import annotations

from uuid import UUID

from models.event import Event
from storage import EventQueries


async def is_duplicate(d1, event: Event) -> bool:
    """Return True if this event's idempotency key already exists."""
    queries = EventQueries(d1)
    existing = await queries.get_by_idempotency_key(event.idempotency_key)
    return existing is not None


async def record_if_absent(d1, event: Event) -> bool:
    """Insert the event idempotently; return True if it was newly recorded."""
    queries = EventQueries(d1)
    return await queries.insert(event)


async def already_seen(d1, event_id: UUID) -> bool:
    """Return True if an event with the given UUID already exists."""
    result = await d1.prepare(
        "SELECT 1 FROM events WHERE id = ?"
    ).bind(str(event_id)).first()
    return result is not None
