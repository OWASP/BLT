"""D1 store for the shared domain scan queue."""

from __future__ import annotations

import json
from typing import Any, Optional

from d1_compat import d1_row, d1_rows, row_get

STATUSES = frozenset(
    {"pending", "in_progress", "scanned", "failed", "retry_required"}
)
CLAIMABLE = frozenset({"pending", "retry_required"})
MAX_RETRIES = 5


def row_to_job(row: Any) -> dict[str, Any]:
    result_raw = row_get(row, "result_json")
    result = None
    if result_raw:
        try:
            result = json.loads(str(result_raw))
        except json.JSONDecodeError:
            result = None
    return {
        "id": row_get(row, "id"),
        "org_id": row_get(row, "org_id"),
        "host_key": row_get(row, "host_key"),
        "seed_url": row_get(row, "seed_url"),
        "status": row_get(row, "status"),
        "discovered_at": row_get(row, "discovered_at"),
        "last_scan_at": row_get(row, "last_scan_at"),
        "claimed_by": row_get(row, "claimed_by"),
        "claim_until": row_get(row, "claim_until"),
        "retry_count": int(row_get(row, "retry_count") or 0),
        "last_error": row_get(row, "last_error"),
        "result": result,
        "source_url": row_get(row, "source_url"),
    }


class DomainQueueStore:
    def __init__(self, db):
        self.db = db

    async def get_by_host(self, org_id: str, host_key: str) -> Optional[dict]:
        row = d1_row(
            await self.db.prepare(
                "SELECT * FROM domain_jobs WHERE org_id = ? AND host_key = ?"
            )
            .bind(org_id, host_key)
            .first()
        )
        return row_to_job(row) if row else None

    async def get_by_id(self, org_id: str, job_id: str) -> Optional[dict]:
        row = d1_row(
            await self.db.prepare(
                "SELECT * FROM domain_jobs WHERE org_id = ? AND id = ?"
            )
            .bind(org_id, job_id)
            .first()
        )
        return row_to_job(row) if row else None

    async def insert_pending(
        self,
        *,
        job_id: str,
        org_id: str,
        host_key: str,
        seed_url: str,
        discovered_at: int,
        source_url: Optional[str],
    ) -> bool:
        """Insert if new. Returns True if inserted, False if duplicate."""
        existing = await self.get_by_host(org_id, host_key)
        if existing:
            return False
        try:
            await self.db.prepare(
                """
                INSERT INTO domain_jobs (
                  id, org_id, host_key, seed_url, status, discovered_at, source_url
                ) VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """
            ).bind(job_id, org_id, host_key, seed_url, discovered_at, source_url).run()
        except Exception:  # noqa: BLE001 — unique (org_id, host_key)
            return False
        return True

    async def pick_claimable(self, org_id: str, now: int) -> Optional[dict]:
        row = d1_row(
            await self.db.prepare(
                """
                SELECT * FROM domain_jobs
                WHERE org_id = ?
                  AND (
                    status IN ('pending', 'retry_required')
                    OR (status = 'in_progress' AND (claim_until IS NULL OR claim_until < ?))
                  )
                ORDER BY discovered_at ASC
                LIMIT 1
                """
            )
            .bind(org_id, now)
            .first()
        )
        return row_to_job(row) if row else None

    async def claim(
        self, *, org_id: str, job_id: str, sender_id: str, now: int, claim_until: int
    ) -> Optional[dict]:
        await self.db.prepare(
            """
            UPDATE domain_jobs
            SET status = 'in_progress',
                claimed_by = ?,
                claim_until = ?
            WHERE org_id = ? AND id = ?
              AND (
                status IN ('pending', 'retry_required')
                OR (status = 'in_progress' AND (claim_until IS NULL OR claim_until < ?))
              )
            """
        ).bind(sender_id, claim_until, org_id, job_id, now).run()
        row = await self.get_by_id(org_id, job_id)
        if row and row.get("claimed_by") == sender_id and row.get("status") == "in_progress":
            return row
        return None

    async def heartbeat(
        self, *, org_id: str, job_id: str, sender_id: str, claim_until: int
    ) -> Optional[dict]:
        await self.db.prepare(
            """
            UPDATE domain_jobs
            SET claim_until = ?
            WHERE org_id = ? AND id = ? AND claimed_by = ? AND status = 'in_progress'
            """
        ).bind(claim_until, org_id, job_id, sender_id).run()
        return await self.get_by_id(org_id, job_id)

    async def complete(
        self,
        *,
        org_id: str,
        job_id: str,
        sender_id: str,
        now: int,
        result_json: str,
    ) -> Optional[dict]:
        await self.db.prepare(
            """
            UPDATE domain_jobs
            SET status = 'scanned',
                last_scan_at = ?,
                last_error = NULL,
                result_json = ?,
                claim_until = NULL
            WHERE org_id = ? AND id = ? AND claimed_by = ? AND status = 'in_progress'
            """
        ).bind(now, result_json, org_id, job_id, sender_id).run()
        return await self.get_by_id(org_id, job_id)

    async def fail(
        self,
        *,
        org_id: str,
        job_id: str,
        sender_id: str,
        now: int,
        error: str,
        max_retries: int = MAX_RETRIES,
    ) -> Optional[dict]:
        job = await self.get_by_id(org_id, job_id)
        if not job:
            return None
        retries = int(job.get("retry_count") or 0) + 1
        status = "failed" if retries >= max_retries else "retry_required"
        await self.db.prepare(
            """
            UPDATE domain_jobs
            SET status = ?,
                last_scan_at = ?,
                last_error = ?,
                retry_count = ?,
                claimed_by = NULL,
                claim_until = NULL
            WHERE org_id = ? AND id = ? AND claimed_by = ?
            """
        ).bind(status, now, error[:500], retries, org_id, job_id, sender_id).run()
        return await self.get_by_id(org_id, job_id)

    async def list_jobs(
        self,
        org_id: str,
        *,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        if status:
            rows = d1_rows(
                await self.db.prepare(
                    """
                    SELECT * FROM domain_jobs
                    WHERE org_id = ? AND status = ?
                    ORDER BY discovered_at DESC
                    LIMIT ?
                    """
                )
                .bind(org_id, status, limit)
                .all()
            )
        else:
            rows = d1_rows(
                await self.db.prepare(
                    """
                    SELECT * FROM domain_jobs
                    WHERE org_id = ?
                    ORDER BY discovered_at DESC
                    LIMIT ?
                    """
                )
                .bind(org_id, limit)
                .all()
            )
        return [row_to_job(r) for r in rows]

    async def counts(self, org_id: str) -> dict[str, int]:
        rows = d1_rows(
            await self.db.prepare(
                """
                SELECT status, COUNT(*) AS n
                FROM domain_jobs
                WHERE org_id = ?
                GROUP BY status
                """
            )
            .bind(org_id)
            .all()
        )
        out = {s: 0 for s in STATUSES}
        for row in rows:
            key = str(row_get(row, "status") or "")
            if key in out:
                out[key] = int(row_get(row, "n") or 0)
        return out

    async def expire_stale(self, now: int) -> int:
        """Return expired in_progress jobs to retry_required."""
        rows = d1_rows(
            await self.db.prepare(
                """
                SELECT id FROM domain_jobs
                WHERE status = 'in_progress'
                  AND claim_until IS NOT NULL
                  AND claim_until < ?
                """
            )
            .bind(now)
            .all()
        )
        for row in rows:
            job_id = row_get(row, "id")
            await self.db.prepare(
                """
                UPDATE domain_jobs
                SET status = 'retry_required',
                    claimed_by = NULL,
                    claim_until = NULL,
                    last_error = 'lease_expired'
                WHERE id = ? AND status = 'in_progress'
                """
            ).bind(job_id).run()
        return len(rows)
