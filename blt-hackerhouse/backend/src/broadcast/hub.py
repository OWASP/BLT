"""WebSocket broadcast hub (VF11/VF12/VF13).

Manages the in-memory set of connected clients, fans out messages,
sends full snapshots to new clients, and tracks per-component health
counters used by ``GET /health``.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque

from fastapi import WebSocket

from ..models.websocket import (
    AvatarMoveMessage,
    IdentityFlagMessage,
    LeaderboardUpdateMessage,
    SnapshotMessage,
)


logger = logging.getLogger(__name__)


class WebSocketHub:
    """In-process WebSocket broadcast hub."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._error_log: Deque[datetime] = deque(maxlen=1024)
        self._last_event_at: datetime | None = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
        logger.info("ws connect", extra={"clients": len(self._clients)})

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)
        logger.info("ws disconnect", extra={"clients": len(self._clients)})

    @property
    def client_count(self) -> int:
        return len(self._clients)

    def record_event(self) -> None:
        self._last_event_at = datetime.now(tz=timezone.utc).replace(microsecond=0)

    def record_error(self) -> None:
        self._error_log.append(datetime.now(tz=timezone.utc).replace(microsecond=0))

    def errors_last_hour(self) -> int:
        now = datetime.now(tz=timezone.utc).replace(microsecond=0)
        cutoff = now.timestamp() - 3600
        return sum(1 for ts in self._error_log if ts.timestamp() >= cutoff)

    async def broadcast(self, message: AvatarMoveMessage | IdentityFlagMessage | LeaderboardUpdateMessage) -> None:
        """Fan out a message to every connected client."""
        text = message.model_dump_json()
        async with self._lock:
            targets = list(self._clients)
        if not targets:
            return
        results = await asyncio.gather(
            *(self._safe_send(ws, text) for ws in targets), return_exceptions=True
        )
        for result in results:
            if isinstance(result, Exception):
                self.record_error()
                logger.warning("ws broadcast error", extra={"error": repr(result)})

    async def send_snapshot(self, websocket: WebSocket, snapshot: SnapshotMessage) -> None:
        text = snapshot.model_dump_json()
        try:
            await websocket.send_text(text)
        except Exception as exc:  # noqa: BLE001
            self.record_error()
            logger.warning("ws snapshot error", extra={"error": repr(exc)})

    async def _safe_send(self, websocket: WebSocket, text: str) -> None:
        try:
            await websocket.send_text(text)
        except Exception as exc:  # noqa: BLE001
            await self.disconnect(websocket)
            raise


_hub: WebSocketHub | None = None


def get_hub() -> WebSocketHub:
    """Return the process-wide hub singleton."""
    global _hub
    if _hub is None:
        _hub = WebSocketHub()
    return _hub


def reset_hub() -> None:
    """Test helper."""
    global _hub
    _hub = None