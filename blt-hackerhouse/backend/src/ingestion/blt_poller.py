"""BLT-API polling adapter (VF02).

Background task that polls ``/bugs`` and ``/hunts`` every
``POLL_INTERVAL_SECONDS``, filters to records newer than the stored
cursor, and enqueues each record on the EventQueue for normalization.
Failures are logged and skipped without affecting the GitLab pipeline.
"""

from __future__ import annotations

import asyncio
import logging
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
        poll_interval: int | None = None,
        page_size: int = 50,
    ) -> None:
        self.db = db
        self.queue = queue
        self.poll_interval = poll_interval or settings.poll_interval_seconds
        self.page_size = page_size
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
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="blt-poller")
        logger.info("blt poller started", extra={"interval": self.poll_interval})

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
                await self.poll_once()
            except Exception as exc:  # noqa: BLE001
                logger.exception("blt poll iteration failed")
                self._record_error()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval)
            except asyncio.TimeoutError:
                continue

    async def poll_once(self) -> dict[str, int]:
        """Perform a single poll of both bugs and hunts. Returns counts enqueued."""
        enqueued = {"bugs": 0, "hunts": 0}
        bugs = await self._fetch_bugs()
        for record in bugs:
            from ..normalization.blt import normalize_blt_bug
            event = normalize_blt_bug(record)
            await self.queue.put(event)
            enqueued["bugs"] += 1
        if bugs:
            await self._cursors.upsert("blt_bugs", max(int(b.get("id", 0)) for b in bugs))

        hunts = await self._fetch_hunts()
        for record in hunts:
            from ..normalization.blt import normalize_blt_hunt
            event = normalize_blt_hunt(record)
            await self.queue.put(event)
            enqueued["hunts"] += 1
        if hunts:
            await self._cursors.upsert("blt_hunts", max(int(h.get("id", 0)) for h in hunts))

        return enqueued

    # ------------------------------------------------------------------
    # HTTP fetch
    # ------------------------------------------------------------------

    async def _fetch_bugs(self) -> list[dict[str, Any]]:
        if self._client is None:
            return []
        cursor = await self._cursors.get("blt_bugs")
        last_seen = cursor[0] if cursor else 0

        async def _do() -> list[dict[str, Any]]:
            assert self._client is not None
            resp = await self._client.get(
                "/bugs",
                params={"page": 1, "per_page": self.page_size},
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                data = data.get("data") or data.get("results") or []
            return [r for r in data if isinstance(r, dict)]

        try:
            records = await retry_async(
                _do,
                description="blt.fetch_bugs",
                on_failure=self._on_failure,
            )
        except RetryableHTTPError as exc:
            logger.warning("blt fetch_bugs exhausted", extra={"error": str(exc)})
            return []

        return [r for r in records if int(r.get("id", 0)) > last_seen]

    async def _fetch_hunts(self) -> list[dict[str, Any]]:
        if self._client is None:
            return []
        cursor = await self._cursors.get("blt_hunts")
        last_seen = cursor[0] if cursor else 0

        async def _do() -> list[dict[str, Any]]:
            assert self._client is not None
            resp = await self._client.get("/hunts")
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                data = data.get("data") or data.get("results") or []
            return [r for r in data if isinstance(r, dict)]

        try:
            records = await retry_async(
                _do,
                description="blt.fetch_hunts",
                on_failure=self._on_failure,
            )
        except RetryableHTTPError as exc:
            logger.warning("blt fetch_hunts exhausted", extra={"error": str(exc)})
            return []

        return [r for r in records if int(r.get("id", 0)) > last_seen]

    async def _on_failure(self, exc: Exception) -> None:
        self._record_error()

    def _record_error(self) -> None:
        # Imported lazily to avoid a circular import with broadcast.hub.
        from ..broadcast.hub import get_hub
        get_hub().record_error()