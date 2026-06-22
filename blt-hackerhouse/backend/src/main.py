"""FastAPI application entry point.

Wires storage, queue, pipeline runner, broadcast hub, polling
adapters, and routes together inside a single ASGI lifespan.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket

from .api.routes import router, set_dependencies
from .api.websocket import websocket_endpoint
from .broadcast.hub import WebSocketHub, get_hub
from .core.logging import configure_logging
from .ingestion.blt_poller import BLTPoller
from .ingestion.gap_detector import GitLabGapDetector
from .state.pipeline import PipelineRunner
from .state.queue import EventQueue
from .storage import Database, get_database


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("startup begin")

    db: Database = get_database()
    await db.connect()
    applied = await db.run_migrations()
    logger.info("migrations applied", extra={"count": applied})

    queue = EventQueue()
    hub: WebSocketHub = get_hub()
    runner = PipelineRunner(db=db, queue=queue, hub=hub)
    await runner.start()

    blt_poller = BLTPoller(db=db, queue=queue)
    await blt_poller.start()

    gap_project_ids = _parse_project_ids()
    gap_detector = GitLabGapDetector(
        db=db,
        queue=queue,
        project_ids=gap_project_ids,
    )
    await gap_detector.start()

    app.state.event_queue = queue
    app.state.hub = hub
    app.state.runner = runner
    app.state.blt_poller = blt_poller
    app.state.gap_detector = gap_detector

    set_dependencies(db, runner, hub, started_at=time.time())

    logger.info("startup complete")
    try:
        yield
    finally:
        logger.info("shutdown begin")
        await gap_detector.stop()
        await blt_poller.stop()
        await runner.stop()
        await db.close()
        logger.info("shutdown complete")


def _parse_project_ids() -> list[int]:
    raw = os.environ.get("GITLAB_TRACKED_PROJECT_IDS", "")
    if not raw:
        return []
    out: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if token.isdigit():
            out.append(int(token))
    return out


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(
        title="BLT-Hackerhouse",
        version="0.1.0",
        description="Real-time contributor visualization for OWASP BLT",
        lifespan=lifespan,
    )
    app.include_router(router)

    @app.websocket("/ws")
    async def _ws(websocket: WebSocket, token: str | None = None) -> None:
        await websocket_endpoint(websocket, app.state.hub, app.state.runner, token=token)

    return app


app = create_app()