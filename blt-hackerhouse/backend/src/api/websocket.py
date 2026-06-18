"""WebSocket endpoint (VF11 + VF12)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..broadcast.hub import WebSocketHub
from ..state.pipeline import PipelineRunner


logger = logging.getLogger(__name__)

ws_router = APIRouter()


async def websocket_endpoint(
    websocket: WebSocket,
    hub: WebSocketHub,
    runner: PipelineRunner,
) -> None:
    await hub.connect(websocket)
    try:
        snapshot = await runner.build_snapshot()
        await hub.send_snapshot(websocket, snapshot)
        # Keep the connection open; messages are pushed by the broadcast hub.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.warning("ws session error", extra={"error": repr(exc)})
    finally:
        await hub.disconnect(websocket)