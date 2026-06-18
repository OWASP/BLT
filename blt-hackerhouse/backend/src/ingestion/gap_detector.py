"""GitLab Events API gap detector (VF19).

Polls ``GET /api/v4/projects/{id}/events`` for tracked projects and
feeds missed events back through the normalizer pipeline.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from ..config import settings
from ..core.logging import get_logger
from ..core.retry import RetryConfig, RetryableHTTPError, retry_async
from ..normalization.gitlab import normalize_gitlab_payload
from ..state.queue import EventQueue
from ..storage import CursorQueries, Database


logger = get_logger(__name__)

POLL_INTERVAL_SECONDS = 90
LOOKBACK_MINUTES = 30


class GitLabGapDetector:
    """Periodically fetch GitLab project events and enqueue anything new."""

    def __init__(
        self,
        *,
        db: Database,
        queue: EventQueue,
        project_ids: list[int],
        poll_interval: int = POLL_INTERVAL_SECONDS,
    ) -> None:
        self.db = db
        self.queue = queue
        self.project_ids = [int(pid) for pid in project_ids]
        self.poll_interval = poll_interval
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._cursors = CursorQueries(db)
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        if not settings.gitlab_api_token or not self.project_ids:
            logger.info("gap detector disabled (no token or projects)")
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="gitlab-gap-detector")
        logger.info(
            "gap detector started",
            extra={"interval": self.poll_interval, "projects": len(self.project_ids)},
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        try:
            await asyncio.wait_for(self._task, timeout=5.0)
        except asyncio.TimeoutError:
            self._task.cancel()
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._task = None
        logger.info("gap detector stopped")

    # ------------------------------------------------------------------
    # Run loop
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        self._client = httpx.AsyncClient(
            base_url="https://gitlab.com/api/v4",
            headers={"PRIVATE-TOKEN": settings.gitlab_api_token},
            timeout=httpx.Timeout(15.0, connect=5.0),
        )
        while not self._stop_event.is_set():
            try:
                await self.detect_once()
            except Exception:  # noqa: BLE001
                logger.exception("gap detector iteration failed")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval)
            except asyncio.TimeoutError:
                continue

    async def detect_once(self) -> int:
        """Run a single detection pass. Returns number of events enqueued."""
        if self._client is None:
            return 0
        enqueued = 0
        after = (datetime.now(tz=timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)).strftime("%Y-%m-%d")
        for project_id in self.project_ids:
            source_key = f"gitlab_events_{project_id}"
            cursor = await self._cursors.get(source_key)
            last_seen = cursor[0] if cursor else 0

            try:
                events = await self._fetch_project_events(project_id, after)
            except RetryableHTTPError as exc:
                logger.warning(
                    "gap fetch failed",
                    extra={"project_id": project_id, "error": str(exc)},
                )
                continue

            new_high = last_seen
            for raw in events:
                event_id = int(raw.get("id", 0))
                if event_id <= last_seen:
                    continue
                try:
                    event = normalize_gitlab_payload(raw)
                except Exception:  # noqa: BLE001
                    logger.exception("gap normalize failed", extra={"event_id": event_id})
                    continue
                await self.queue.put(event)
                enqueued += 1
                new_high = max(new_high, event_id)

            if new_high > last_seen:
                await self._cursors.upsert(source_key, new_high)

        return enqueued

    async def _fetch_project_events(self, project_id: int, after: str) -> list[dict[str, Any]]:
        assert self._client is not None

        async def _do() -> list[dict[str, Any]]:
            assert self._client is not None
            resp = await self._client.get(
                f"/projects/{project_id}/events",
                params={"after": after, "per_page": 100, "page": 1},
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []

        return await retry_async(
            _do,
            description=f"gitlab.events[{project_id}]",
            on_failure=self._on_failure,
        )

    async def _on_failure(self, exc: Exception) -> None:
        from ..broadcast.hub import get_hub
        get_hub().record_error()