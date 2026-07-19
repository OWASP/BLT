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
    poll_ms = _settings().pipeline_poll_interval_ms / 1000.0
    runner = PipelineRunner(db=db, queue=queue, hub=hub, poll_interval=poll_ms)
    await runner.start()

    # Startup validation
    _validate_startup()

    blt_poller = BLTPoller(db=db, queue=queue)
    await blt_poller.start()

    project_ids = _parse_project_ids()
    gap_detector = GitLabGapDetector(
        db=db,
        queue=queue,
        project_ids=project_ids,
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


def _validate_startup() -> None:
    """Validate required configuration. Logs warnings for non-critical items."""
    from .config import settings

    if not settings.gitlab_webhook_secret:
        logger.warning("GITLAB_WEBHOOK_SECRET not set — webhooks will accept no requests")

    if settings.gitlab_api_token:
        project_ids = _parse_project_ids()
        if project_ids:
            logger.info(
                "gap detector configured",
                extra={"project_ids": project_ids, "count": len(project_ids)},
            )
        else:
            logger.warning(
                "GITLAB_TRACKED_PROJECT_IDS is empty — gap detector will not poll any projects"
            )
    else:
        logger.warning("GITLAB_API_TOKEN missing — gap detector disabled")

    if not settings.websocket_auth_token:
        logger.warning("WEBSOCKET_AUTH_TOKEN not set — WebSocket connections will be rejected")

    logger.info(
        "configuration summary",
        extra={
            "webhook_enabled": bool(settings.gitlab_webhook_secret),
            "gap_detector_enabled": bool(settings.gitlab_api_token and _parse_project_ids()),
            "blt_poller_enabled": bool(settings.blt_api_key),
            "blt_poll_interval_s": settings.blt_poll_interval_seconds,
            "gitlab_poll_interval_s": settings.gitlab_poll_interval_seconds,
            "gitlab_lookback_m": settings.gitlab_lookback_minutes,
            "log_level": settings.log_level,
        },
    )


def _parse_project_ids() -> list[int]:
    from .config import settings

    raw = settings.gitlab_tracked_project_ids
    if not raw:
        return []
    out: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if token.isdigit():
            out.append(int(token))
        else:
            logger.warning("ignoring non-integer project ID", extra={"value": token})
    return out


def _settings():
    from .config import settings
    return settings


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(
        title="BLT-Hackerhouse",
        version="0.1.0",
        description="Real-time contributor visualization for OWASP BLT",
        lifespan=lifespan,
    )
    app.include_router(router)

    # WebSocket route must be registered before the static mount
    # to prevent StaticFiles from intercepting WS upgrade requests.
    @app.websocket("/ws")
    async def _ws(websocket: WebSocket, token: str | None = None) -> None:
        await websocket_endpoint(websocket, app.state.hub, app.state.runner, token=token)

    # Serve UI HTML files for local testing (keep at end of routes)
    from pathlib import Path

    # Mount avatars BEFORE root so /avatars isn't swallowed by the root catch-all
    avatars_dir = Path(__file__).resolve().parents[2] / "UI" / "avatars"
    if avatars_dir.is_dir():
        from fastapi.staticfiles import StaticFiles
        app.mount("/avatars", StaticFiles(directory=str(avatars_dir)), name="avatars")

    ui_dir = Path(__file__).resolve().parents[2] / "UI" / "html"
    if ui_dir.is_dir():
        from fastapi.staticfiles import StaticFiles
        app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")

    return app


app = create_app()
