"""GitLab Events API gap detector (VF19).

Polls ``GET /api/v4/projects/{id}/events`` for tracked projects and
feeds missed events back through the normalizer pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import time
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


class GitLabGapDetector:
    """Periodically fetch GitLab project events and enqueue anything new."""

    def __init__(
        self,
        *,
        db: Database,
        queue: EventQueue,
        project_ids: list[int],
    ) -> None:
        self.db = db
        self.queue = queue
        self.project_ids = [int(pid) for pid in project_ids]
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._cursors = CursorQueries(db)
        self._client: httpx.AsyncClient | None = None
        self._last_success: datetime | None = None
        self._last_error: str | None = None
        self._total_enqueued: int = 0

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
            extra={
                "interval_s": settings.gitlab_poll_interval_seconds,
                "lookback_m": settings.gitlab_lookback_minutes,
                "projects": len(self.project_ids),
                "project_ids": self.project_ids,
            },
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
    # Readiness helpers
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def last_success_at(self) -> datetime | None:
        return self._last_success

    @property
    def last_error_text(self) -> str | None:
        return self._last_error

    @property
    def total_enqueued(self) -> int:
        return self._total_enqueued

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
                t0 = time.monotonic()
                enqueued = await self._detect()
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                logger.info(
                    "gap detector poll complete",
                    extra={"enqueued": enqueued, "elapsed_ms": elapsed_ms},
                )
                self._last_success = datetime.now(tz=timezone.utc)
            except Exception:  # noqa: BLE001
                logger.exception("gap detector iteration failed")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=settings.gitlab_poll_interval_seconds
                )
            except asyncio.TimeoutError:
                continue

    async def _detect(self) -> int:
        """Run a single detection pass. Returns number of events enqueued."""
        if self._client is None:
            return 0

        enqueued = 0
        after = (
            datetime.now(tz=timezone.utc) - timedelta(minutes=settings.gitlab_lookback_minutes)
        ).strftime("%Y-%m-%d")

        for project_id in self.project_ids:
            source_key = f"gitlab_events_{project_id}"
            cursor = await self._cursors.get(source_key)
            last_seen = cursor[0] if cursor else 0

            logger.info(
                "gap detector polling project", extra={
                    "project_id": project_id, "last_seen_event_id": last_seen,
                }
            )

            try:
                events, new_high = await self._fetch_all_pages(project_id, after, last_seen)
            except RetryableHTTPError as exc:
                msg = f"project {project_id}: {exc}"
                logger.warning("gap detector fetch exhausted", extra={
                    "project_id": project_id, "error": str(exc),
                })
                self._last_error = msg
                continue

            for raw in events:
                event_id = int(raw.get("id", 0))
                try:
                    event = normalize_gitlab_payload(raw)
                except Exception:  # noqa: BLE001
                    logger.exception("gap normalize failed", extra={"event_id": event_id})
                    continue
                await self.queue.put(event)
                enqueued += 1

            if new_high > last_seen:
                await self._cursors.upsert(source_key, new_high)
                logger.info(
                    "gap detector cursor advanced",
                    extra={"project_id": project_id, "old": last_seen, "new": new_high},
                )

        self._total_enqueued += enqueued
        return enqueued

    async def _fetch_all_pages(
        self, project_id: int, after: str, last_seen: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """Fetch all pages of events for a project. Returns (events, max_id)."""
        assert self._client is not None
        all_events: list[dict[str, Any]] = []
        new_high = last_seen
        page = 1
        per_page = settings.gitlab_per_page

        while True:
            async def _do() -> list[dict[str, Any]]:
                assert self._client is not None
                resp = await self._client.get(
                    f"/projects/{project_id}/events",
                    params={"after": after, "per_page": per_page, "page": page},
                )
                resp.raise_for_status()
                data = resp.json()
                return data if isinstance(data, list) else []

            try:
                page_events = await retry_async(
                    _do,
                    description=f"gitlab.events[proj={project_id}, page={page}]",
                    config=RetryConfig(
                        max_attempts=settings.gitlab_max_retries,
                        base_delay=settings.gitlab_retry_base_delay,
                        max_delay=settings.gitlab_retry_max_delay,
                    ),
                    on_failure=self._on_failure,
                )
            except RetryableHTTPError:
                raise

            if not page_events:
                break

            logger.info(
                "gap detector fetched page",
                extra={"project_id": project_id, "page": page, "count": len(page_events)},
            )

            for raw in page_events:
                event_id = int(raw.get("id", 0))
                if event_id <= last_seen:
                    # Cursor reached — stop across all remaining pages
                    return all_events, new_high
                all_events.append(raw)
                new_high = max(new_high, event_id)

            if len(page_events) < per_page:
                break
            page += 1

        return all_events, new_high

    async def _on_failure(self, exc: Exception) -> None:
        from ..broadcast.hub import get_hub
        get_hub().record_error()
