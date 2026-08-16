"""Evidence attachments: metadata in D1, bytes in R2 or D1 fallback."""

from __future__ import annotations

import base64
import hashlib
from typing import Any, Mapping, Optional

from d1_compat import d1_row, d1_rows, row_get

MAX_EVIDENCE_BYTES = 262_144  # 256 KiB


class EvidenceStore:
    def __init__(self, db: Any, env: Any = None):
        self.db = db
        self.env = env

    def _r2(self) -> Any:
        if self.env is None:
            return None
        return getattr(self.env, "EVIDENCE", None) or getattr(self.env, "R2", None)

    async def list_for_finding(self, org_id: str, finding_id: str) -> list[dict[str, Any]]:
        if self.db is None:
            return []
        rows = d1_rows(
            await self.db.prepare(
                """
                SELECT id, org_id, finding_id, r2_key, digest, size_bytes,
                       media_type, created_at
                FROM evidence_meta
                WHERE org_id = ? AND finding_id = ?
                ORDER BY created_at DESC
                """
            ).bind(org_id, finding_id).all()
        )
        return [self._row_to_item(row) for row in rows]

    async def get_meta(self, org_id: str, evidence_id: str) -> Optional[dict[str, Any]]:
        if self.db is None:
            return None
        row = d1_row(
            await self.db.prepare(
                """
                SELECT id, org_id, finding_id, r2_key, digest, size_bytes,
                       media_type, created_at
                FROM evidence_meta
                WHERE id = ? AND org_id = ?
                """
            ).bind(evidence_id, org_id).first()
        )
        return self._row_to_item(row) if row else None

    async def put(
        self,
        *,
        evidence_id: str,
        org_id: str,
        finding_id: str,
        data: bytes,
        media_type: str,
        created_at_unix: int,
    ) -> dict[str, Any]:
        if self.db is None:
            raise RuntimeError("D1 not configured")
        if len(data) > MAX_EVIDENCE_BYTES:
            raise ValueError(f"evidence exceeds {MAX_EVIDENCE_BYTES} bytes")
        digest = hashlib.sha256(data).hexdigest()
        r2 = self._r2()
        if r2 is not None:
            key = f"{org_id}/{finding_id}/{evidence_id}"
            put = getattr(r2, "put", None)
            if put is None:
                raise RuntimeError("R2 binding missing put()")
            result = put(key, data)
            if hasattr(result, "__await__"):
                await result
            r2_key = f"r2:{key}"
        else:
            encoded = base64.b64encode(data).decode("ascii")
            await self.db.prepare(
                "INSERT INTO evidence_blobs (id, data_b64) VALUES (?, ?)"
            ).bind(evidence_id, encoded).run()
            r2_key = f"d1:{evidence_id}"

        await self.db.prepare(
            """
            INSERT INTO evidence_meta (
              id, org_id, finding_id, r2_key, digest, size_bytes, media_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
        ).bind(
            evidence_id,
            org_id,
            finding_id,
            r2_key,
            digest,
            len(data),
            media_type,
            created_at_unix,
        ).run()
        meta = await self.get_meta(org_id, evidence_id)
        if meta is None:
            raise RuntimeError("failed to persist evidence metadata")
        return meta

    async def get_bytes(self, meta: Mapping[str, Any]) -> Optional[bytes]:
        key = str(meta.get("r2_key") or "")
        if key.startswith("r2:"):
            r2 = self._r2()
            if r2 is None:
                return None
            obj = r2.get(key[3:])
            if hasattr(obj, "__await__"):
                obj = await obj
            if obj is None:
                return None
            data = getattr(obj, "body", None) or getattr(obj, "arrayBuffer", None)
            if callable(data):
                data = data()
            if hasattr(data, "__await__"):
                data = await data
            if isinstance(data, bytes):
                return data
            if data is not None:
                return bytes(data)
            return None
        if key.startswith("d1:"):
            if self.db is None:
                return None
            row = d1_row(
                await self.db.prepare(
                    "SELECT data_b64 FROM evidence_blobs WHERE id = ?"
                ).bind(key[3:]).first()
            )
            if row is None:
                return None
            raw = row_get(row, "data_b64")
            if not raw:
                return None
            return base64.b64decode(str(raw))
        return None

    @staticmethod
    def _row_to_item(row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": row_get(row, "id"),
            "org_id": row_get(row, "org_id"),
            "finding_id": row_get(row, "finding_id"),
            "r2_key": row_get(row, "r2_key"),
            "digest": row_get(row, "digest"),
            "size_bytes": int(row_get(row, "size_bytes") or 0),
            "media_type": row_get(row, "media_type"),
            "created_at": row_get(row, "created_at"),
            "backend": "r2" if str(row_get(row, "r2_key") or "").startswith("r2:") else "d1",
        }
