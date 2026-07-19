"""WebSocket endpoint (VF11 + VF12)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..broadcast.hub import WebSocketHub
from ..config import settings
from ..core.security import verify_token
from ..state.pipeline import PipelineRunner


logger = logging.getLogger(__name__)

ws_router = APIRouter()


async def websocket_endpoint(
    websocket: WebSocket,
    hub: WebSocketHub,
    runner: PipelineRunner,
) -> None:
    # Extract token from Sec-WebSocket-Protocol header to avoid exposing
    # the secret in the URL query string.
    protocols = websocket.headers.get("sec-websocket-protocol", "")
    token = protocols.split(",")[0].strip() if protocols else None

    if not verify_token(token, settings.websocket_auth_token):
        await websocket.close(code=1008, reason="Unauthorized")
        return

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