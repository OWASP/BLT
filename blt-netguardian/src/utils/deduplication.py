"""Task deduplication utilities."""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


class TaskDeduplicator:
    """Handles task deduplication to prevent redundant scanning."""

    DEDUP_WINDOW = timedelta(hours=24)
    UPSERT_TASK_HASH_SQL = """
        INSERT INTO task_hashes (task_hash, created_at)
        VALUES (?, ?)
        ON CONFLICT(task_hash) DO UPDATE
            SET created_at = excluded.created_at
            WHERE datetime(task_hashes.created_at) <= datetime('now', '-24 hours')
    """

    def __init__(self):
        # task_hash -> first seen timestamp for the active 24-hour dedup window
        self.seen_hashes: Dict[str, datetime] = {}

    def generate_task_hash(self, task) -> str:
        """Generate a unique hash for a task based on its key attributes."""
        # Create hash from target_id, task_type combination
        hash_input = f"{task.target_id}:{task.task_type}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def _evict_expired_hashes(self, now: datetime) -> None:
        """Evict in-memory hashes that are outside the deduplication window."""
        expired_hashes = [
            task_hash
            for task_hash, seen_at in self.seen_hashes.items()
            if (now - seen_at) >= self.DEDUP_WINDOW
        ]
        for task_hash in expired_hashes:
            self.seen_hashes.pop(task_hash, None)

    def _extract_rows_affected(self, result: Any) -> Optional[int]:
        """Extract affected-row metadata from D1 response shapes."""
        if result is None:
            return None

        def _get(source: Any, key: str) -> Any:
            if isinstance(source, dict):
                return source.get(key)
            return getattr(source, key, None)

        for key in ("rows_affected", "rows_written", "changes"):
            value = _get(result, key)
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str) and value.isdigit():
                return int(value)

        meta = _get(result, "meta")
        if meta is None:
            return None

        for key in ("rows_affected", "rows_written", "changes"):
            value = _get(meta, key)
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str) and value.isdigit():
                return int(value)

        return None

    async def is_duplicate(self, task, task_queue) -> bool:
        """Check if a task is a duplicate of an existing task."""
        task_hash = self.generate_task_hash(task)
        now = datetime.now(timezone.utc)

        # Keep in-memory dedup cache aligned with the 24-hour D1 window.
        self._evict_expired_hashes(now)

        seen_at = self.seen_hashes.get(task_hash)
        if seen_at is not None and (now - seen_at) < self.DEDUP_WINDOW:
            return True
        self.seen_hashes.pop(task_hash, None)

        db = getattr(task_queue, "db", None)
        if db is None:
            self.seen_hashes[task_hash] = now
            return False

        created_at = now.strftime("%Y-%m-%d %H:%M:%S")
        result = await db.prepare(self.UPSERT_TASK_HASH_SQL).bind(task_hash, created_at).run()
        rows_affected = self._extract_rows_affected(result)

        if rows_affected == 0:
            return True

        if rows_affected == 1:
            self.seen_hashes[task_hash] = now
            return False

        # If runtime metadata is unavailable, keep behavior permissive.
        self.seen_hashes[task_hash] = now
        return False

    def clear_cache(self):
        """Clear the in-memory deduplication cache."""
        self.seen_hashes.clear()
