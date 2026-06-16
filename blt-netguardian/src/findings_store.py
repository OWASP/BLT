"""D1 queries for org-scoped findings list."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


ALLOWED_SORT_FIELDS = frozenset({"updated_at", "created_at", "severity", "rule_id"})


@dataclass
class FindingsQuery:
    org_id: str
    status: Optional[str] = None
    severity: Optional[str] = None
    cve_id: Optional[str] = None
    limit: int = 50
    offset: int = 0
    sort: str = "updated_at"
    order: str = "desc"


class FindingsStore:
    def __init__(self, db):
        self.db = db

    async def list_findings(self, query: FindingsQuery) -> tuple[list[dict], int]:
        if self.db is None:
            raise RuntimeError("D1 not configured")

        where = ["org_id = ?"]
        params: list[Any] = [query.org_id]

        if query.status is not None:
            where.append("status = ?")
            params.append(query.status)
        if query.severity is not None:
            where.append("severity = ?")
            params.append(query.severity)
        if query.cve_id is not None:
            where.append("cve_id = ?")
            params.append(query.cve_id)

        where_sql = " AND ".join(where)
        count_row = await self.db.prepare(
            f"SELECT COUNT(*) AS total FROM findings WHERE {where_sql}"
        ).bind(*params).first()
        total = int(count_row["total"]) if count_row else 0

        sort_field = query.sort if query.sort in ALLOWED_SORT_FIELDS else "updated_at"
        sort_dir = "DESC" if query.order.lower() == "desc" else "ASC"

        rows = await self.db.prepare(
            f"""
            SELECT id, org_id, envelope_id, rule_id, severity, title, target,
                   status, fingerprint, cve_id, cve_score, created_at, updated_at
            FROM findings
            WHERE {where_sql}
            ORDER BY {sort_field} {sort_dir}
            LIMIT ? OFFSET ?
            """
        ).bind(*params, query.limit, query.offset).all()

        items = [self._row_to_item(row) for row in rows.results]
        return items, total

    @staticmethod
    def _row_to_item(row: dict) -> dict:
        return {
            "id": row["id"],
            "org_id": row["org_id"],
            "envelope_id": row["envelope_id"],
            "rule_id": row["rule_id"],
            "severity": row["severity"],
            "title": row["title"],
            "target": row.get("target"),
            "status": row["status"],
            "fingerprint": row.get("fingerprint"),
            "cve_id": row.get("cve_id"),
            "cve_score": row.get("cve_score"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
