"""D1 queries for org-scoped findings triage."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from d1_compat import d1_row, d1_rows, row_get


ALLOWED_SORT_FIELDS = frozenset({"updated_at", "created_at", "severity", "rule_id"})
ALLOWED_STATUSES = frozenset({"open", "triaging", "converted", "snoozed", "wontfix"})

# Rank severities by risk so sorting reflects urgency, not alphabetical order.
SEVERITY_RANK_SQL = (
    "CASE severity "
    "WHEN 'critical' THEN 5 "
    "WHEN 'high' THEN 4 "
    "WHEN 'medium' THEN 3 "
    "WHEN 'low' THEN 2 "
    "WHEN 'info' THEN 1 "
    "ELSE 0 END"
)
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
    created_from: Optional[int] = None
    created_to: Optional[int] = None
    triage_queue: bool = False
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
        if query.created_from is not None:
            where.append("created_at >= ?")
            params.append(query.created_from)
        if query.created_to is not None:
            where.append("created_at <= ?")
            params.append(query.created_to)
        if query.triage_queue:
            where.append("status = 'open'")
            where.append("(blt_issue_id IS NULL OR blt_issue_id = '')")
            where.append("severity IN ('critical', 'high')")
        return " AND ".join(where), params

    async def list_findings(self, query: FindingsQuery) -> tuple[list[dict], int]:
        if self.db is None:
            raise RuntimeError("D1 not configured")

        where_sql, params = self._where_clause(query)
        count_row = d1_row(await self.db.prepare(
            f"SELECT COUNT(*) AS total FROM findings WHERE {where_sql}"
        ).bind(*params).first())
        total = int(row_get(count_row, "total", 0) or 0)

        sort_field = query.sort if query.sort in ALLOWED_SORT_FIELDS else "updated_at"
        sort_dir = "DESC" if query.order.lower() == "desc" else "ASC"

        # Severity is a category, not a lexical value: rank it by risk so
        # "Severity (high first)" in the UI actually surfaces critical/high,
        # rather than alphabetical (critical < high < info < low < medium).
        if sort_field == "severity":
            order_sql = f"{SEVERITY_RANK_SQL} {sort_dir}, updated_at DESC"
        else:
            order_sql = f"{sort_field} {sort_dir}"

        rows = d1_rows(await self.db.prepare(
            f"""
            SELECT id, org_id, envelope_id, rule_id, severity, title, target,
                   status, fingerprint, cve_id, cve_score, blt_issue_id,
                   created_at, updated_at
            FROM findings
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
            """
        ).bind(*params, query.limit, query.offset).all())

        items = [self._row_to_item(row) for row in rows]
        return items, total

    async def export_findings(self, query: FindingsQuery) -> list[dict]:
        export_query = FindingsQuery(
            org_id=query.org_id,
            status=query.status,
            severity=query.severity,
            cve_id=query.cve_id,
            created_from=query.created_from,
            created_to=query.created_to,
            triage_queue=query.triage_queue,
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
        row = d1_row(await self.db.prepare(
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
        ).bind(finding_id, org_id).first())
        return row

    async def find_by_fingerprint(self, org_id: str, fingerprint: str) -> Optional[dict]:
        if self.db is None or not fingerprint:
            return None
        row = d1_row(await self.db.prepare(
            """
            SELECT id, org_id, fingerprint, blt_issue_id
            FROM findings
            WHERE org_id = ? AND fingerprint = ?
            """
        ).bind(org_id, fingerprint).first())
        return row

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
        # Omit detail_json when absent: a Python None binding becomes JS
        # ``undefined`` on the Workers D1 bridge, which is rejected.
        if detail_json is None:
            await self.db.prepare(
                """
                INSERT INTO access_logs (
                  id, org_id, finding_id, actor, action, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """
            ).bind(log_id, org_id, finding_id, actor, action, created_at_unix).run()
        else:
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
        logs = []
        for row in d1_rows(await self.db.prepare(
            """
            SELECT id, actor, action, detail_json, created_at
            FROM access_logs
            WHERE org_id = ? AND finding_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """
        ).bind(org_id, finding_id, limit).all()):
            entry = {
                "id": row["id"],
                "actor": row["actor"],
                "action": row["action"],
                "created_at": row["created_at"],
            }
            if row_get(row, "detail_json"):
                try:
                    entry["detail"] = json.loads(row_get(row, "detail_json"))
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
            SET blt_issue_id = ?, status = 'converted', updated_at = ?
            WHERE id = ? AND org_id = ?
            """
        ).bind(blt_issue_id, updated_at_unix, finding_id, org_id).run()
        row = d1_row(await self.db.prepare(
            "SELECT blt_issue_id FROM findings WHERE id = ? AND org_id = ?"
        ).bind(finding_id, org_id).first())
        return row is not None and row_get(row, "blt_issue_id") == blt_issue_id

    async def update_finding_status(
        self,
        org_id: str,
        finding_id: str,
        status: str,
        updated_at_unix: int,
    ) -> bool:
        if self.db is None:
            raise RuntimeError("D1 not configured")
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"invalid status: {status}")
        await self.db.prepare(
            """
            UPDATE findings
            SET status = ?, updated_at = ?
            WHERE id = ? AND org_id = ?
            """
        ).bind(status, updated_at_unix, finding_id, org_id).run()
        row = d1_row(await self.db.prepare(
            "SELECT status FROM findings WHERE id = ? AND org_id = ?"
        ).bind(finding_id, org_id).first())
        return row is not None and row_get(row, "status") == status

    @staticmethod
    def _row_to_item(row: dict) -> dict:
        return finding_row_to_item(row)


def finding_row_to_item(row: Mapping[str, Any]) -> dict:
    """Project a findings row into the public finding shape (single source of truth)."""
    return {
        "id": row_get(row, "id"),
        "org_id": row_get(row, "org_id"),
        "envelope_id": row_get(row, "envelope_id"),
        "rule_id": row_get(row, "rule_id"),
        "severity": row_get(row, "severity"),
        "title": row_get(row, "title"),
        "target": row_get(row, "target"),
        "status": row_get(row, "status"),
        "fingerprint": row_get(row, "fingerprint"),
        "cve_id": row_get(row, "cve_id"),
        "cve_score": row_get(row, "cve_score"),
        "blt_issue_id": row_get(row, "blt_issue_id"),
        "created_at": row_get(row, "created_at"),
        "updated_at": row_get(row, "updated_at"),
    }
