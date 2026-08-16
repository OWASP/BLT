"""D1 outbox store for verified NetGuardian events."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from d1_compat import d1_row, d1_rows, row_get

EVENT_VERSION = "ng-event-1"
EVENT_CONVERTED = "finding.converted"
EVENT_RESOLVED = "finding.resolved"
ALLOWED_EVENT_TYPES = frozenset({EVENT_CONVERTED, EVENT_RESOLVED})

STATUS_PENDING = "pending"
STATUS_DELIVERED = "delivered"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"


@dataclass
class EventsQuery:
    org_id: str
    event_type: Optional[str] = None
    finding_id: Optional[str] = None
    status: Optional[str] = None
    limit: int = 50
    offset: int = 0


def build_dedupe_key(event_type: str, finding_id: str) -> str:
    return f"{event_type}:{finding_id}"


def build_event_payload(
    *,
    event_type: str,
    finding_row: Mapping[str, Any],
    issue_id: Optional[str] = None,
    created_at_unix: int,
) -> dict[str, Any]:
    finding_id = str(row_get(finding_row, "id"))
    org_id = str(row_get(finding_row, "org_id"))
    return {
        "version": EVENT_VERSION,
        "event_type": event_type,
        "cve_id": row_get(finding_row, "cve_id"),
        "cve_score": row_get(finding_row, "cve_score"),
        "rule_id": row_get(finding_row, "rule_id"),
        "severity": row_get(finding_row, "severity"),
        "org_id": org_id,
        "target": row_get(finding_row, "target"),
        "finding_id": finding_id,
        "issue_id": issue_id or row_get(finding_row, "blt_issue_id"),
        "created_at": created_at_unix,
        "dedupe_key": build_dedupe_key(event_type, finding_id),
    }


class EventsStore:
    def __init__(self, db: Any):
        self.db = db

    async def insert_idempotent(
        self,
        *,
        event_id: str,
        org_id: str,
        event_type: str,
        dedupe_key: str,
        payload: Mapping[str, Any],
        created_at_unix: int,
        status: str = STATUS_PENDING,
    ) -> tuple[dict[str, Any], bool]:
        """Insert outbox row. Returns (row, created). Duplicate dedupe_key → existing."""
        if self.db is None:
            raise RuntimeError("D1 not configured")

        existing = d1_row(
            await self.db.prepare(
                """
                SELECT id, org_id, event_type, dedupe_key, payload_json, status,
                       attempts, last_error, created_at, updated_at
                FROM events_outbox
                WHERE org_id = ? AND dedupe_key = ?
                """
            ).bind(org_id, dedupe_key).first()
        )
        if existing is not None:
            return self._row_to_item(existing), False

        payload_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        try:
            await self.db.prepare(
                """
                INSERT INTO events_outbox (
                  id, org_id, event_type, dedupe_key, payload_json,
                  status, attempts, last_error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)
                """
            ).bind(
                event_id,
                org_id,
                event_type,
                dedupe_key,
                payload_json,
                status,
                created_at_unix,
                created_at_unix,
            ).run()
        except Exception:  # noqa: BLE001 - unique-index race on concurrent emit
            raced = d1_row(
                await self.db.prepare(
                    """
                    SELECT id, org_id, event_type, dedupe_key, payload_json, status,
                           attempts, last_error, created_at, updated_at
                    FROM events_outbox
                    WHERE org_id = ? AND dedupe_key = ?
                    """
                ).bind(org_id, dedupe_key).first()
            )
            if raced is not None:
                return self._row_to_item(raced), False
            raise

        row = d1_row(
            await self.db.prepare(
                """
                SELECT id, org_id, event_type, dedupe_key, payload_json, status,
                       attempts, last_error, created_at, updated_at
                FROM events_outbox
                WHERE org_id = ? AND dedupe_key = ?
                """
            ).bind(org_id, dedupe_key).first()
        )
        if row is None:
            raise RuntimeError("failed to persist outbox event")
        created = row_get(row, "id") == event_id
        return self._row_to_item(row), created

    async def mark_delivery(
        self,
        *,
        org_id: str,
        event_id: str,
        status: str,
        attempts: int,
        last_error: Optional[str],
        updated_at_unix: int,
    ) -> None:
        if self.db is None:
            raise RuntimeError("D1 not configured")
        await self.db.prepare(
            """
            UPDATE events_outbox
            SET status = ?, attempts = ?, last_error = ?, updated_at = ?
            WHERE id = ? AND org_id = ?
            """
        ).bind(status, attempts, last_error, updated_at_unix, event_id, org_id).run()

    async def get_event(self, org_id: str, event_id: str) -> Optional[dict[str, Any]]:
        if self.db is None:
            return None
        row = d1_row(
            await self.db.prepare(
                """
                SELECT id, org_id, event_type, dedupe_key, payload_json, status,
                       attempts, last_error, created_at, updated_at
                FROM events_outbox
                WHERE id = ? AND org_id = ?
                """
            ).bind(event_id, org_id).first()
        )
        return self._row_to_item(row) if row else None

    async def count_events(self, query: EventsQuery) -> int:
        if self.db is None:
            return 0
        sql, params = self._filter_sql(query, count=True)
        row = d1_row(await self.db.prepare(sql).bind(*params).first())
        if row is None:
            return 0
        return int(row_get(row, "total") or 0)

    async def list_events(self, query: EventsQuery) -> list[dict[str, Any]]:
        if self.db is None:
            return []
        sql, params = self._filter_sql(query, count=False)
        rows = d1_rows(await self.db.prepare(sql).bind(*params).all())
        return [self._row_to_item(row) for row in rows]

    def _filter_sql(self, query: EventsQuery, *, count: bool) -> tuple[str, list[Any]]:
        clauses = ["org_id = ?"]
        params: list[Any] = [query.org_id]

        if query.event_type:
            clauses.append("event_type = ?")
            params.append(query.event_type)
        if query.status:
            clauses.append("status = ?")
            params.append(query.status)
        if query.finding_id:
            clauses.append("json_extract(payload_json, '$.finding_id') = ?")
            params.append(query.finding_id)

        where = " AND ".join(clauses)
        if count:
            return f"SELECT COUNT(*) AS total FROM events_outbox WHERE {where}", params

        params.extend([query.limit, query.offset])
        return (
            f"""
            SELECT id, org_id, event_type, dedupe_key, payload_json, status,
                   attempts, last_error, created_at, updated_at
            FROM events_outbox
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            params,
        )

    @staticmethod
    def _row_to_item(row: Mapping[str, Any]) -> dict[str, Any]:
        payload_raw = row_get(row, "payload_json")
        try:
            payload = json.loads(payload_raw) if payload_raw else {}
        except json.JSONDecodeError:
            payload = {}
        return {
            "id": row_get(row, "id"),
            "org_id": row_get(row, "org_id"),
            "event_type": row_get(row, "event_type"),
            "dedupe_key": row_get(row, "dedupe_key"),
            "payload": payload,
            "status": row_get(row, "status"),
            "attempts": int(row_get(row, "attempts") or 0),
            "last_error": row_get(row, "last_error"),
            "created_at": row_get(row, "created_at"),
            "updated_at": row_get(row, "updated_at"),
        }
