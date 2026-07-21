"""Queries for the ``health_state`` table (created by migration 002)."""

from __future__ import annotations

from .d1_utils import d1_row, utc_now_iso


class HealthStateQueries:

    def __init__(self, d1):
        self._db = d1

    async def upsert(self, component: str, field: str, value: str) -> None:
        await self._db.prepare("""
            INSERT INTO health_state (component, field, value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(component, field) DO UPDATE SET
                value     = excluded.value,
                updated_at = excluded.updated_at
        """).bind(component, field, value, utc_now_iso()).run()

    async def get(self, component: str, field: str) -> str | None:
        result = await self._db.prepare(
            "SELECT value FROM health_state WHERE component = ? AND field = ?"
        ).bind(component, field).first()
        row = d1_row(result)
        return row.get("value") if row else None

    async def get_component(self, component: str) -> dict[str, str]:
        result = await self._db.prepare(
            "SELECT field, value FROM health_state WHERE component = ?"
        ).bind(component).all()
        if result is None:
            return {}
        return {r.copy()["field"]: r.copy()["value"] for r in (result.results or [])}
