"""Idempotency-based deduplication (VF03).

Looks up the ``idempotency_key`` on the ``events`` table to drop
duplicate deliveries before they reach normalization.
"""

from __future__ import annotations

from uuid import UUID

from ..models.event import Event
from ..storage import Database, EventQueries


async def is_duplicate(db: Database, event: Event) -> bool:
    """Return True if this event's idempotency key already exists."""
    queries = EventQueries(db)
    existing = await queries.get_by_idempotency_key(event.idempotency_key)
    return existing is not None


async def record_if_absent(db: Database, event: Event) -> bool:
    """Insert the event idempotently; return True if it was newly recorded."""
    queries = EventQueries(db)
    return await queries.insert(event)


async def already_seen(db: Database, event_id: UUID) -> bool:
    """Return True if an event with the given UUID already exists."""
    async with db.conn.execute(
        "SELECT 1 FROM events WHERE id = ?", (str(event_id),)
    ) as cursor:
        row = await cursor.fetchone()
    return row is not None