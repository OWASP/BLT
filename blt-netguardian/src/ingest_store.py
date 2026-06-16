"""D1 persistence for ztr-finding-1 ingest."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping, Optional


class IngestStore:
    def __init__(self, db):
        self.db = db

    async def sender_key_active(self, org_id: str, sender_id: str, kid: str) -> bool:
        if self.db is None:
            return True
        row = await self.db.prepare(
            """
            SELECT active FROM sender_keys
            WHERE org_id = ? AND sender_id = ? AND kid = ?
            """
        ).bind(org_id, sender_id, kid).first()
        if row is None:
            return True
        return int(row["active"]) == 1

    async def find_duplicate(self, org_id: str, sender_id: str, nonce: str) -> Optional[dict]:
        if self.db is None:
            return None
        row = await self.db.prepare(
            """
            SELECT id, finding_id FROM envelopes
            WHERE org_id = ? AND sender_id = ? AND nonce = ?
            """
        ).bind(org_id, sender_id, nonce).first()
        if row is None:
            return None
        return {"envelope_id": row["id"], "finding_id": row["finding_id"]}

    async def check_rate_limit(self, org_id: str, *, limit_per_minute: int, now: datetime) -> bool:
        """Return True if under limit, False if rate limited."""
        if self.db is None or limit_per_minute <= 0:
            return True
        bucket = now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        row = await self.db.prepare(
            "SELECT ingest_accepted FROM ng_metrics WHERE org_id = ? AND day = ?"
        ).bind(org_id, bucket).first()
        current = int(row["ingest_accepted"]) if row else 0
        return current < limit_per_minute

    async def record_rate_accept(self, org_id: str, now: datetime) -> None:
        if self.db is None:
            return
        bucket = now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        await self.db.prepare(
            """
            INSERT INTO ng_metrics (org_id, day, ingest_accepted, ingest_duplicate,
                                    ingest_rejected, findings_open)
            VALUES (?, ?, 1, 0, 0, 0)
            ON CONFLICT(org_id, day) DO UPDATE SET
              ingest_accepted = ingest_accepted + 1
            """
        ).bind(org_id, bucket).run()

    async def insert_accepted(
        self,
        *,
        envelope_id: str,
        finding_id: str,
        org_id: str,
        sender_id: str,
        kid: str,
        nonce: str,
        body_digest: str,
        payload_digest: str,
        issued_at_unix: int,
        received_at_unix: int,
        payload_json: str,
        payload: Mapping[str, Any],
    ) -> None:
        if self.db is None:
            raise RuntimeError("D1 not configured")
        rule_id = str(payload.get("rule_id", "unknown"))
        severity = str(payload.get("severity", "info"))
        title = str(payload.get("title", "Untitled finding"))
        target = payload.get("target")
        fingerprint = payload.get("fingerprint")
        cve_id = payload.get("cve_id")

        await self.db.batch([
            self.db.prepare(
                """
                INSERT INTO envelopes (
                  id, org_id, sender_id, kid, nonce, digest, payload_digest,
                  issued_at, received_at, validated_at, status, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'accepted', ?)
                """
            ).bind(
                envelope_id,
                org_id,
                sender_id,
                kid,
                nonce,
                body_digest,
                payload_digest,
                issued_at_unix,
                received_at_unix,
                received_at_unix,
                payload_json,
            ),
            self.db.prepare(
                """
                INSERT INTO findings (
                  id, org_id, envelope_id, rule_id, severity, title, target,
                  status, fingerprint, cve_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)
                """
            ).bind(
                finding_id,
                org_id,
                envelope_id,
                rule_id,
                severity,
                title,
                target,
                fingerprint,
                cve_id,
                received_at_unix,
                received_at_unix,
            ),
            self.db.prepare(
                "UPDATE envelopes SET finding_id = ? WHERE id = ?"
            ).bind(finding_id, envelope_id),
        ])
