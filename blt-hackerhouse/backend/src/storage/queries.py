"""Typed query helpers for every table.

Each ``*Queries`` class wraps raw SQL and returns/accepts Pydantic
models. This isolates SQL from the rest of the codebase so swapping
storage backends only touches this module.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from ..models.contributor import Contributor
from ..models.event import Event
from ..models.identity import IdentityMapping
from ..models.room import AvatarState
from .connection import Database, dumps_json, loads_json, parse_utc, utc_now_iso


logger = logging.getLogger(__name__)


class EventQueries:
    """Queries for the ``events`` table."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def insert(self, event: Event) -> bool:
        """Insert an event. Returns True if inserted, False if duplicate."""
        sql = """
            INSERT INTO events (
                id, source, event_type, actor_id, actor_name,
                contributor_id, repository, timestamp, metadata,
                idempotency_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(idempotency_key) DO NOTHING
        """
        params = (
            str(event.id),
            event.source,
            event.event_type,
            event.actor_id,
            event.actor_name,
            str(event.contributor_id) if event.contributor_id else None,
            event.repository,
            event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp),
            dumps_json(event.metadata),
            event.idempotency_key,
        )
        async with self.db.conn.execute(sql, params) as cursor:
            await self.db.conn.commit()
            return cursor.rowcount > 0

    async def assign_sequence(self, event_id: UUID, sequence: int) -> None:
        """Stamp a monotonic sequence number onto a freshly inserted event."""
        await self.db.conn.execute(
            "UPDATE events SET sequence_number = ? WHERE id = ?",
            (sequence, str(event_id)),
        )
        await self.db.conn.commit()

    async def get_by_idempotency_key(self, key: str) -> Event | None:
        async with self.db.conn.execute(
            "SELECT * FROM events WHERE idempotency_key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
        return _row_to_event(row) if row else None

    async def list_activity(self, page: int, per_page: int) -> tuple[list[Event], int]:
        offset = (page - 1) * per_page
        async with self.db.conn.execute(
            "SELECT COUNT(*) AS total FROM events"
        ) as cursor:
            total_row = await cursor.fetchone()
            total = int(total_row["total"]) if total_row else 0

        async with self.db.conn.execute(
            """
            SELECT * FROM events
            ORDER BY timestamp DESC, sequence_number DESC
            LIMIT ? OFFSET ?
            """,
            (per_page, offset),
        ) as cursor:
            rows = await cursor.fetchall()
        events = [_row_to_event(r) for r in rows if r is not None]
        return events, total

    async def count(self) -> int:
        async with self.db.conn.execute("SELECT COUNT(*) AS c FROM events") as cursor:
            row = await cursor.fetchone()
        return int(row["c"]) if row else 0

    async def count_since(self, since: datetime) -> int:
        """Count events ingested since ``since`` (UTC)."""
        async with self.db.conn.execute(
            "SELECT COUNT(*) AS c FROM events WHERE created_at >= ?",
            (since.replace(tzinfo=None).isoformat(),),
        ) as cursor:
            row = await cursor.fetchone()
        return int(row["c"]) if row else 0

    async def max_sequence_number(self) -> int:
        """Return the highest sequence_number in the events table, or 0 if empty."""
        async with self.db.conn.execute(
            "SELECT COALESCE(MAX(sequence_number), 0) AS m FROM events"
        ) as cursor:
            row = await cursor.fetchone()
        return int(row["m"]) if row else 0


class ContributorQueries:
    """Queries for the ``contributors`` table."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def upsert(self, contributor: Contributor) -> Contributor:
        """Insert or update a contributor record. Returns the persisted model."""
        sql = """
            INSERT INTO contributors (
                id, display_name, usernames, aliases, platform_ids,
                is_linked, score, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                display_name = excluded.display_name,
                usernames    = excluded.usernames,
                aliases      = excluded.aliases,
                platform_ids = excluded.platform_ids,
                is_linked    = excluded.is_linked,
                score        = excluded.score,
                updated_at   = excluded.updated_at
        """
        params = (
            str(contributor.id),
            contributor.display_name,
            dumps_json(contributor.usernames),
            dumps_json(contributor.aliases),
            dumps_json(contributor.platform_ids),
            1 if contributor.is_linked else 0,
            contributor.score,
            contributor.created_at.isoformat() if isinstance(contributor.created_at, datetime) else str(contributor.created_at),
            contributor.updated_at.isoformat() if isinstance(contributor.updated_at, datetime) else str(contributor.updated_at),
        )
        await self.db.conn.execute(sql, params)
        await self.db.conn.commit()
        return contributor

    async def get(self, contributor_id: UUID) -> Contributor | None:
        async with self.db.conn.execute(
            "SELECT * FROM contributors WHERE id = ?", (str(contributor_id),)
        ) as cursor:
            row = await cursor.fetchone()
        return _row_to_contributor(row) if row else None

    async def list_all(self) -> list[Contributor]:
        async with self.db.conn.execute(
            "SELECT * FROM contributors ORDER BY score DESC, display_name ASC"
        ) as cursor:
            rows = await cursor.fetchall()
        return [_row_to_contributor(r) for r in rows if r is not None]

    async def list_top(self, limit: int, offset: int) -> tuple[list[Contributor], int]:
        async with self.db.conn.execute("SELECT COUNT(*) AS c FROM contributors") as cursor:
            row = await cursor.fetchone()
            total = int(row["c"]) if row else 0
        async with self.db.conn.execute(
            "SELECT * FROM contributors ORDER BY score DESC, display_name ASC LIMIT ? OFFSET ?",
            (limit, offset),
        ) as cursor:
            rows = await cursor.fetchall()
        return [_row_to_contributor(r) for r in rows if r is not None], total

    async def stats(self) -> dict[str, int]:
        """Return identity resolution statistics."""
        async with self.db.conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN is_linked = 1 THEN 1 ELSE 0 END) AS linked
            FROM contributors
            """
        ) as cursor:
            row = await cursor.fetchone()
        total = int(row["total"]) if row and row["total"] is not None else 0
        linked = int(row["linked"]) if row and row["linked"] is not None else 0
        unlinked = max(0, total - linked)
        return {"total": total, "linked": linked, "unlinked": unlinked}


class AvatarStateQueries:
    """Queries for the ``avatar_state`` table."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def upsert(self, state: AvatarState) -> None:
        sql = """
            INSERT INTO avatar_state (contributor_id, floor, room, last_event, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(contributor_id) DO UPDATE SET
                floor = excluded.floor,
                room = excluded.room,
                last_event = excluded.last_event,
                updated_at = excluded.updated_at
        """
        params = (
            str(state.contributor_id),
            state.floor,
            state.room,
            state.last_event,
            state.updated_at.isoformat() if isinstance(state.updated_at, datetime) else str(state.updated_at),
        )
        await self.db.conn.execute(sql, params)
        await self.db.conn.commit()

    async def get(self, contributor_id: UUID) -> AvatarState | None:
        async with self.db.conn.execute(
            "SELECT * FROM avatar_state WHERE contributor_id = ?", (str(contributor_id),)
        ) as cursor:
            row = await cursor.fetchone()
        return _row_to_avatar(row) if row else None

    async def list_all(self) -> list[AvatarState]:
        async with self.db.conn.execute(
            "SELECT * FROM avatar_state ORDER BY updated_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
        return [_row_to_avatar(r) for r in rows if r is not None]

    async def occupancy(self) -> dict[str, int]:
        async with self.db.conn.execute(
            "SELECT room, COUNT(*) AS c FROM avatar_state GROUP BY room"
        ) as cursor:
            rows = await cursor.fetchall()
        return {r["room"]: int(r["c"]) for r in rows}


class IdentityQueries:
    """Queries for the ``identity_mappings`` table."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def insert(self, mapping: IdentityMapping) -> IdentityMapping:
        sql = """
            INSERT INTO identity_mappings (
                platform, platform_user_id, contributor_id, confidence, confirmed_by
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(platform, platform_user_id) DO UPDATE SET
                contributor_id = excluded.contributor_id,
                confidence     = excluded.confidence,
                confirmed_by   = excluded.confirmed_by
        """
        params = (
            mapping.platform,
            mapping.platform_user_id,
            str(mapping.contributor_id),
            mapping.confidence,
            mapping.confirmed_by,
        )
        async with self.db.conn.execute(sql, params) as cursor:
            await self.db.conn.commit()
            if mapping.id is None:
                mapping.id = cursor.lastrowid
        return mapping

    async def lookup(self, platform: str, platform_user_id: str) -> IdentityMapping | None:
        async with self.db.conn.execute(
            """
            SELECT * FROM identity_mappings
            WHERE platform = ? AND platform_user_id = ?
            """,
            (platform, platform_user_id),
        ) as cursor:
            row = await cursor.fetchone()
        return _row_to_identity(row) if row else None

    async def confirm(self, mapping_id: int, confirmed_by: str) -> None:
        await self.db.conn.execute(
            "UPDATE identity_mappings SET confirmed_by = ? WHERE id = ?",
            (confirmed_by, mapping_id),
        )
        await self.db.conn.commit()

    async def list_for_contributor(self, contributor_id: UUID) -> list[IdentityMapping]:
        async with self.db.conn.execute(
            "SELECT * FROM identity_mappings WHERE contributor_id = ?",
            (str(contributor_id),),
        ) as cursor:
            rows = await cursor.fetchall()
        return [_row_to_identity(r) for r in rows if r is not None]


class CursorQueries:
    """Queries for the ``poll_cursors`` table."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def get(self, source: str) -> tuple[int, str | None] | None:
        async with self.db.conn.execute(
            "SELECT last_seen_id, last_polled_at FROM poll_cursors WHERE source = ?",
            (source,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return int(row["last_seen_id"]), row["last_polled_at"]

    async def upsert(self, source: str, last_seen_id: int) -> None:
        await self.db.conn.execute(
            """
            INSERT INTO poll_cursors (source, last_seen_id, last_polled_at)
            VALUES (?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                last_seen_id   = excluded.last_seen_id,
                last_polled_at = excluded.last_polled_at
            """,
            (source, last_seen_id, utc_now_iso()),
        )
        await self.db.conn.commit()


class DeadLetterQueries:
    """Queries for the ``dead_letter_queue`` table (capped at 500)."""

    CAP = 500

    def __init__(self, db: Database) -> None:
        self.db = db

    async def add(
        self,
        *,
        event_id: str | None,
        source: str | None,
        error: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self._evict_if_full()
        sql = """
            INSERT INTO dead_letter_queue (event_id, source, error, payload, attempts, last_attempt_at)
            VALUES (?, ?, ?, ?, 1, ?)
        """
        await self.db.conn.execute(
            sql,
            (
                event_id,
                source,
                error,
                dumps_json(payload or {}),
                utc_now_iso(),
            ),
        )
        await self.db.conn.commit()

    async def _evict_if_full(self) -> None:
        async with self.db.conn.execute("SELECT COUNT(*) AS c FROM dead_letter_queue") as cursor:
            row = await cursor.fetchone()
        count = int(row["c"]) if row else 0
        if count < self.CAP:
            return
        evict = count - self.CAP + 1
        logger.critical(
            "Dead letter queue at capacity (%d). Evicting %d oldest entries.",
            count,
            evict,
        )
        await self.db.conn.execute(
            """
            DELETE FROM dead_letter_queue
            WHERE id IN (
                SELECT id FROM dead_letter_queue
                ORDER BY created_at ASC
                LIMIT ?
            )
            """,
            (evict,),
        )
        await self.db.conn.commit()

    async def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        async with self.db.conn.execute(
            "SELECT * FROM dead_letter_queue ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Row → model adapters
# ---------------------------------------------------------------------------

def _row_to_event(row: Any) -> Event:
    payload = dict(row)
    contributor_id = payload.get("contributor_id")
    return Event(
        id=UUID(payload["id"]),
        source=payload["source"],
        event_type=payload["event_type"],
        actor_id=payload["actor_id"],
        actor_name=payload["actor_name"],
        repository=payload.get("repository", "") or "",
        timestamp=parse_utc(payload["timestamp"]),
        metadata=loads_json(payload.get("metadata")) or {},
        contributor_id=UUID(contributor_id) if contributor_id else None,
        sequence_number=payload.get("sequence_number"),
    )


def _row_to_contributor(row: Any) -> Contributor:
    payload = dict(row)
    return Contributor(
        id=UUID(payload["id"]),
        display_name=payload["display_name"],
        usernames=list(loads_json(payload.get("usernames")) or []),
        aliases=list(loads_json(payload.get("aliases")) or []),
        platform_ids=dict(loads_json(payload.get("platform_ids")) or {}),
        is_linked=bool(payload.get("is_linked", 0)),
        score=int(payload.get("score", 0)),
        created_at=parse_utc(payload["created_at"]),
        updated_at=parse_utc(payload["updated_at"]),
    )


def _row_to_avatar(row: Any) -> AvatarState:
    payload = dict(row)
    return AvatarState(
        contributor_id=UUID(payload["contributor_id"]),
        floor=int(payload["floor"]),
        room=payload["room"],
        last_event=payload["last_event"],
        updated_at=parse_utc(payload["updated_at"]),
    )


def _row_to_identity(row: Any) -> IdentityMapping:
    payload = dict(row)
    return IdentityMapping(
        id=int(payload["id"]) if payload.get("id") is not None else None,
        platform=payload["platform"],
        platform_user_id=payload["platform_user_id"],
        contributor_id=UUID(payload["contributor_id"]),
        confidence=float(payload["confidence"]),
        confirmed_by=payload.get("confirmed_by"),
        created_at=parse_utc(payload["created_at"]),
    )