"""D1 queries for org-scoped findings triage."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional


ALLOWED_SORT_FIELDS = frozenset({"updated_at", "created_at", "severity", "rule_id"})
CSV_COLUMNS = (
    "id",
    "rule_id",
    "severity",
    "title",
    "target",
    "status",
    "cve_id",
    "cve_score",
    "fingerprint",
    "blt_issue_id",
    "created_at",
    "updated_at",
)


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

    def _where_clause(self, query: FindingsQuery) -> tuple[str, list[Any]]:
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
        return " AND ".join(where), params

    async def list_findings(self, query: FindingsQuery) -> tuple[list[dict], int]:
        if self.db is None:
            raise RuntimeError("D1 not configured")

        where_sql, params = self._where_clause(query)
        count_row = await self.db.prepare(
            f"SELECT COUNT(*) AS total FROM findings WHERE {where_sql}"
        ).bind(*params).first()
        total = int(count_row["total"]) if count_row else 0

        sort_field = query.sort if query.sort in ALLOWED_SORT_FIELDS else "updated_at"
        sort_dir = "DESC" if query.order.lower() == "desc" else "ASC"

        rows = await self.db.prepare(
            f"""
            SELECT id, org_id, envelope_id, rule_id, severity, title, target,
                   status, fingerprint, cve_id, cve_score, blt_issue_id,
                   created_at, updated_at
            FROM findings
            WHERE {where_sql}
            ORDER BY {sort_field} {sort_dir}
            LIMIT ? OFFSET ?
            """
        ).bind(*params, query.limit, query.offset).all()

        items = [self._row_to_item(row) for row in rows.results]
        return items, total

    async def export_findings(self, query: FindingsQuery) -> list[dict]:
        export_query = FindingsQuery(
            org_id=query.org_id,
            status=query.status,
            severity=query.severity,
            cve_id=query.cve_id,
            limit=10_000,
            offset=0,
            sort=query.sort,
            order=query.order,
        )
        items, _ = await self.list_findings(export_query)
        return items

    async def get_finding_detail(self, org_id: str, finding_id: str) -> Optional[dict]:
        if self.db is None:
            raise RuntimeError("D1 not configured")
        row = await self.db.prepare(
            """
            SELECT f.id, f.org_id, f.envelope_id, f.rule_id, f.severity, f.title,
                   f.target, f.status, f.fingerprint, f.cve_id, f.cve_score,
                   f.blt_issue_id, f.created_at, f.updated_at,
                   e.sender_id, e.kid, e.received_at AS envelope_received_at,
                   e.payload_json
            FROM findings f
            JOIN envelopes e ON e.id = f.envelope_id
            WHERE f.id = ? AND f.org_id = ?
            """
        ).bind(finding_id, org_id).first()
        if row is None:
            return None
        return dict(row)

    async def find_by_fingerprint(self, org_id: str, fingerprint: str) -> Optional[dict]:
        if self.db is None or not fingerprint:
            return None
        row = await self.db.prepare(
            """
            SELECT id, org_id, fingerprint, blt_issue_id
            FROM findings
            WHERE org_id = ? AND fingerprint = ?
            """
        ).bind(org_id, fingerprint).first()
        if row is None:
            return None
        return dict(row)

    async def record_access(
        self,
        *,
        log_id: str,
        org_id: str,
        finding_id: str,
        actor: str,
        action: str,
        detail: Optional[dict] = None,
        created_at_unix: int,
    ) -> None:
        if self.db is None:
            raise RuntimeError("D1 not configured")
        detail_json = json.dumps(detail, separators=(",", ":")) if detail else None
        await self.db.prepare(
            """
            INSERT INTO access_logs (
              id, org_id, finding_id, actor, action, detail_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
        ).bind(log_id, org_id, finding_id, actor, action, detail_json, created_at_unix).run()

    async def list_access_logs(self, org_id: str, finding_id: str, *, limit: int = 10) -> list[dict]:
        if self.db is None:
            return []
        rows = await self.db.prepare(
            """
            SELECT id, actor, action, detail_json, created_at
            FROM access_logs
            WHERE org_id = ? AND finding_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """
        ).bind(org_id, finding_id, limit).all()
        logs = []
        for row in rows.results:
            entry = {
                "id": row["id"],
                "actor": row["actor"],
                "action": row["action"],
                "created_at": row["created_at"],
            }
            if row.get("detail_json"):
                try:
                    entry["detail"] = json.loads(row["detail_json"])
                except json.JSONDecodeError:
                    entry["detail"] = None
            logs.append(entry)
        return logs

    async def set_blt_issue_id(
        self,
        org_id: str,
        finding_id: str,
        blt_issue_id: str,
        updated_at_unix: int,
    ) -> bool:
        if self.db is None:
            raise RuntimeError("D1 not configured")
        await self.db.prepare(
            """
            UPDATE findings
            SET blt_issue_id = ?, updated_at = ?
            WHERE id = ? AND org_id = ?
            """
        ).bind(blt_issue_id, updated_at_unix, finding_id, org_id).run()
        row = await self.db.prepare(
            "SELECT blt_issue_id FROM findings WHERE id = ? AND org_id = ?"
        ).bind(finding_id, org_id).first()
        return row is not None and row.get("blt_issue_id") == blt_issue_id

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
            "blt_issue_id": row.get("blt_issue_id"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
