"""BLT-API polling adapter (VF02).

Background task that polls ``/bugs`` paginates to fetch every unseen
record, normalizes them, and enqueues the results.
Failures are logged and skipped without affecting the GitLab pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import settings
from ..core.logging import get_logger
from ..core.retry import RetryConfig, RetryableHTTPError, retry_async
from ..state.queue import EventQueue
from ..storage import CursorQueries, Database


logger = get_logger(__name__)


class BLTPoller:
    """Periodically poll the BLT-API for new bugs and hunts."""

    SOURCES = ("blt_bugs", "blt_hunts")

    def __init__(
        self,
        *,
        db: Database,
        queue: EventQueue,
    ) -> None:
        self.db = db
        self.queue = queue
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
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="blt-poller")
        logger.info(
            "blt poller started",
            extra={
                "interval_s": settings.blt_poll_interval_seconds,
                "per_page": settings.blt_per_page,
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
        logger.info("blt poller stopped")

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
            base_url=settings.blt_api_base_url,
            headers={"X-BLT-API-Key": settings.blt_api_key} if settings.blt_api_key else {},
            timeout=httpx.Timeout(15.0, connect=5.0),
        )
        while not self._stop_event.is_set():
            try:
                t0 = time.monotonic()
                enqueued = await self._poll()
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                logger.info(
                    "blt poller cycle complete",
                    extra={"enqueued": enqueued, "elapsed_ms": elapsed_ms},
                )
                self._last_success = datetime.now(tz=timezone.utc)
            except Exception:  # noqa: BLE001
                logger.exception("blt poll iteration failed")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=settings.blt_poll_interval_seconds
                )
            except asyncio.TimeoutError:
                continue

    async def _poll(self) -> int:
        """Single poll cycle. Returns total enqueued count."""
        enqueued = 0

        bugs, max_bug_id = await self._fetch_paginated(
            "blt_bugs", "/bugs", "bugs"
        )
        for record in bugs:
            from ..normalization.blt import normalize_blt_bug
            event = normalize_blt_bug(record)
            await self.queue.put(event)
            enqueued += 1
        if max_bug_id > 0:
            await self._cursors.upsert("blt_bugs", max_bug_id)

        hunts, max_hunt_id = await self._fetch_paginated(
            "blt_hunts", "/hunts", "hunts"
        )
        for record in hunts:
            from ..normalization.blt import normalize_blt_hunt
            event = normalize_blt_hunt(record)
            await self.queue.put(event)
            enqueued += 1
        if max_hunt_id > 0:
            await self._cursors.upsert("blt_hunts", max_hunt_id)

        self._total_enqueued += enqueued
        return enqueued

    # ------------------------------------------------------------------
    # Paginated fetches
    # ------------------------------------------------------------------

    async def _fetch_paginated(
        self, cursor_name: str, path: str, label: str,
    ) -> tuple[list[dict[str, Any]], int]:
        """Fetch all unseen records from a BLT endpoint. Returns (records, max_id)."""
        if self._client is None:
            return [], 0

        cursor = await self._cursors.get(cursor_name)
        last_seen = cursor[0] if cursor else 0
        all_records: list[dict[str, Any]] = []
        new_high = last_seen
        page = 1
        per_page = settings.blt_per_page

        logger.info(
            "blt poller fetching", extra={
                "source": label, "last_seen_id": last_seen, "page_size": per_page,
            }
        )

        while True:
            async def _do() -> list[dict[str, Any]]:
                assert self._client is not None
                resp = await self._client.get(
                    path,
                    params={"page": page, "per_page": per_page},
                )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict):
                    data = data.get("data") or data.get("results") or []
                return [r for r in data if isinstance(r, dict)]

            try:
                page_records = await retry_async(
                    _do,
                    description=f"blt.{label}[page={page}]",
                    config=RetryConfig(
                        max_attempts=settings.blt_max_retries,
                        base_delay=settings.blt_retry_base_delay,
                        max_delay=settings.blt_retry_max_delay,
                    ),
                    on_failure=self._on_failure,
                )
            except RetryableHTTPError as exc:
                logger.warning("blt fetch exhausted", extra={
                    "source": label, "error": str(exc),
                })
                self._last_error = f"blt.{label}: {exc}"
                return all_records, new_high

            logger.info(
                "blt poller fetched page", extra={
                    "source": label, "page": page, "count": len(page_records),
                }
            )

            if not page_records:
                break

            for record in page_records:
                rec_id = int(record.get("id", 0))
                if rec_id <= last_seen:
                    return all_records, new_high
                all_records.append(record)
                new_high = max(new_high, rec_id)

            if len(page_records) < per_page:
                break
            page += 1

        return all_records, new_high

    async def _on_failure(self, exc: Exception) -> None:
        from ..broadcast.hub import get_hub
        get_hub().record_error()
