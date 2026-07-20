"""Typed query helpers for every table.

Each ``*Queries`` class wraps raw SQL and returns/accepts Pydantic
models using Cloudflare D1's native prepared-statement API.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from models.contributor import Contributor
from models.event import Event
from models.identity import IdentityMapping
from models.room import AvatarState
from .d1_utils import d1_row, d1_rows, dumps_json, loads_json, parse_utc, utc_now_iso


logger = logging.getLogger(__name__)


class EventQueries:
    """Queries for the ``events`` table."""

    def __init__(self, d1):
        self._db = d1

    async def insert(self, event: Event) -> bool:
        stmt = self._db.prepare("""
            INSERT OR IGNORE INTO events (
                id, source, event_type, actor_id, actor_name,
                contributor_id, repository, timestamp, metadata,
                idempotency_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """).bind(
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
        result = await stmt.run()
        return result.success

    async def assign_sequence(self, event_id: UUID, sequence: int) -> None:
        await self._db.prepare(
            "UPDATE events SET sequence_number = ? WHERE id = ?"
        ).bind(sequence, str(event_id)).run()

    async def get_by_idempotency_key(self, key: str) -> Event | None:
        result = await self._db.prepare(
            "SELECT * FROM events WHERE idempotency_key = ?"
        ).bind(key).first()
        row = d1_row(result)
        return _row_to_event(row) if row else None

    async def list_activity(self, page: int, per_page: int) -> tuple[list[Event], int]:
        offset = (page - 1) * per_page

        total_result = await self._db.prepare(
            "SELECT COUNT(*) AS total FROM events"
        ).first()
        total = d1_row(total_result).get("total", 0)

        result = await self._db.prepare("""
            SELECT * FROM events
            ORDER BY timestamp DESC, sequence_number DESC
            LIMIT ? OFFSET ?
        """).bind(per_page, offset).all()
        rows = d1_rows(result)
        events = [_row_to_event(r) for r in rows]
        return events, total

    async def count(self) -> int:
        result = await self._db.prepare(
            "SELECT COUNT(*) AS c FROM events"
        ).first()
        row = d1_row(result)
        return int(row.get("c", 0))

    async def count_since(self, since: datetime) -> int:
        utc_since = since.astimezone(timezone.utc) if since.tzinfo else since.replace(tzinfo=timezone.utc)
        result = await self._db.prepare(
            "SELECT COUNT(*) AS c FROM events WHERE datetime(created_at) >= datetime(?)"
        ).bind(utc_since.isoformat()).first()
        row = d1_row(result)
        return int(row.get("c", 0))

    async def max_sequence_number(self) -> int:
        """Return the highest sequence_number in the events table, or 0 if empty."""
        result = await self._db.prepare(
            "SELECT COALESCE(MAX(sequence_number), 0) AS m FROM events"
        ).first()
        row = d1_row(result)
        return int(row.get("m", 0))


class ContributorQueries:
    """Queries for the ``contributors`` table."""

    def __init__(self, d1):
        self._db = d1

    async def upsert(self, contributor: Contributor) -> Contributor:
        await self._db.prepare("""
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
        """).bind(
            str(contributor.id),
            contributor.display_name,
            dumps_json(contributor.usernames),
            dumps_json(contributor.aliases),
            dumps_json(contributor.platform_ids),
            1 if contributor.is_linked else 0,
            contributor.score,
            contributor.created_at.isoformat() if isinstance(contributor.created_at, datetime) else str(contributor.created_at),
            contributor.updated_at.isoformat() if isinstance(contributor.updated_at, datetime) else str(contributor.updated_at),
        ).run()
        return contributor

    async def get(self, contributor_id: UUID) -> Contributor | None:
        result = await self._db.prepare(
            "SELECT * FROM contributors WHERE id = ?"
        ).bind(str(contributor_id)).first()
        row = d1_row(result)
        return _row_to_contributor(row) if row else None

    async def list_all(self) -> list[Contributor]:
        result = await self._db.prepare(
            "SELECT * FROM contributors ORDER BY score DESC, display_name ASC"
        ).all()
        rows = d1_rows(result)
        return [_row_to_contributor(r) for r in rows]

    async def list_top(self, limit: int, offset: int) -> tuple[list[Contributor], int]:
        count_result = await self._db.prepare(
            "SELECT COUNT(*) AS c FROM contributors"
        ).first()
        total = d1_row(count_result).get("c", 0)

        result = await self._db.prepare(
            "SELECT * FROM contributors ORDER BY score DESC, display_name ASC LIMIT ? OFFSET ?"
        ).bind(limit, offset).all()
        rows = d1_rows(result)
        return [_row_to_contributor(r) for r in rows], total

    async def stats(self) -> dict[str, int]:
        result = await self._db.prepare("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN is_linked = 1 THEN 1 ELSE 0 END) AS linked
            FROM contributors
        """).first()
        row = d1_row(result)
        total = int(row.get("total", 0))
        linked = int(row.get("linked", 0))
        unlinked = max(0, total - linked)
        return {"total": total, "linked": linked, "unlinked": unlinked}


class AvatarStateQueries:
    """Queries for the ``avatar_state`` table."""

    def __init__(self, d1):
        self._db = d1

    async def upsert(self, state: AvatarState) -> None:
        await self._db.prepare("""
            INSERT INTO avatar_state (contributor_id, floor, room, last_event, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(contributor_id) DO UPDATE SET
                floor = excluded.floor,
                room = excluded.room,
                last_event = excluded.last_event,
                updated_at = excluded.updated_at
        """).bind(
            str(state.contributor_id),
            state.floor,
            state.room,
            state.last_event,
            state.updated_at.isoformat() if isinstance(state.updated_at, datetime) else str(state.updated_at),
        ).run()

    async def get(self, contributor_id: UUID) -> AvatarState | None:
        result = await self._db.prepare(
            "SELECT * FROM avatar_state WHERE contributor_id = ?"
        ).bind(str(contributor_id)).first()
        row = d1_row(result)
        return _row_to_avatar(row) if row else None

    async def list_all(self) -> list[dict]:
        result = await self._db.prepare(
            "SELECT * FROM avatar_state ORDER BY updated_at DESC"
        ).all()
        return d1_rows(result)

    async def occupancy(self) -> dict[str, int]:
        rows = d1_rows(await self._db.prepare(
            "SELECT room, COUNT(*) AS c FROM avatar_state GROUP BY room"
        ).all())
        return {r["room"]: int(r["c"]) for r in rows}


class IdentityQueries:
    """Queries for the ``identity_mappings`` table."""

    def __init__(self, d1):
        self._db = d1

    async def insert(self, mapping: IdentityMapping) -> IdentityMapping:
        await self._db.prepare("""
            INSERT INTO identity_mappings (
                platform, platform_user_id, contributor_id, confidence, confirmed_by
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(platform, platform_user_id) DO UPDATE SET
                contributor_id = excluded.contributor_id,
                confidence     = excluded.confidence,
                confirmed_by   = excluded.confirmed_by
        """).bind(
            mapping.platform,
            mapping.platform_user_id,
            str(mapping.contributor_id),
            mapping.confidence,
            mapping.confirmed_by,
        ).run()
        return mapping

    async def lookup(self, platform: str, platform_user_id: str) -> IdentityMapping | None:
        result = await self._db.prepare("""
            SELECT * FROM identity_mappings
            WHERE platform = ? AND platform_user_id = ?
        """).bind(platform, platform_user_id).first()
        row = d1_row(result)
        return _row_to_identity(row) if row else None

    async def confirm(self, mapping_id: int, confirmed_by: str) -> None:
        await self._db.prepare(
            "UPDATE identity_mappings SET confirmed_by = ? WHERE id = ?"
        ).bind(confirmed_by, mapping_id).run()

    async def list_for_contributor(self, contributor_id: UUID) -> list[IdentityMapping]:
        result = await self._db.prepare(
            "SELECT * FROM identity_mappings WHERE contributor_id = ?"
        ).bind(str(contributor_id)).all()
        rows = d1_rows(result)
        return [_row_to_identity(r) for r in rows]


class CursorQueries:
    """Queries for the ``poll_cursors`` table."""

    def __init__(self, d1):
        self._db = d1

    async def get(self, source: str) -> tuple[int, str | None] | None:
        result = await self._db.prepare(
            "SELECT last_seen_id, last_polled_at FROM poll_cursors WHERE source = ?"
        ).bind(source).first()
        if result is None:
            return None
        row = d1_row(result)
        return int(row["last_seen_id"]), row.get("last_polled_at")

    async def upsert(self, source: str, last_seen_id: int) -> None:
        await self._db.prepare("""
            INSERT INTO poll_cursors (source, last_seen_id, last_polled_at)
            VALUES (?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                last_seen_id   = excluded.last_seen_id,
                last_polled_at = excluded.last_polled_at
        """).bind(source, last_seen_id, utc_now_iso()).run()


class DeadLetterQueries:
    """Queries for the ``dead_letter_queue`` table (capped at 500)."""

    CAP = 500

    def __init__(self, d1):
        self._db = d1

    async def add(
        self,
        *,
        event_id: str | None,
        source: str | None,
        error: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self._evict_if_full()
        await self._db.prepare("""
            INSERT INTO dead_letter_queue (event_id, source, error, payload, attempts, last_attempt_at)
            VALUES (?, ?, ?, ?, 1, ?)
        """).bind(event_id, source, error, dumps_json(payload or {}), utc_now_iso()).run()

    async def _evict_if_full(self) -> None:
        count_result = await self._db.prepare(
            "SELECT COUNT(*) AS c FROM dead_letter_queue"
        ).first()
        count = d1_row(count_result).get("c", 0)
        if count < self.CAP:
            return
        evict = count - self.CAP + 1
        logger.critical(
            "Dead letter queue at capacity (%d). Evicting %d oldest entries.",
            count,
            evict,
        )
        await self._db.prepare("""
            DELETE FROM dead_letter_queue
            WHERE id IN (
                SELECT id FROM dead_letter_queue
                ORDER BY created_at ASC
                LIMIT ?
            )
        """).bind(evict).run()

    async def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        result = await self._db.prepare(
            "SELECT * FROM dead_letter_queue ORDER BY created_at DESC LIMIT ?"
        ).bind(limit).all()
        return d1_rows(result)


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
