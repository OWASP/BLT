"""Integration test fixtures: isolated DB, test app, and HTTPX client per test."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from typing import AsyncIterator
from uuid import UUID, uuid4

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routes import router, set_dependencies
from src.api.websocket import websocket_endpoint
from src.broadcast.hub import WebSocketHub, get_hub, reset_hub
from src.core.logging import configure_logging
from src.models.contributor import Contributor
from src.models.event import Event
from src.models.room import AvatarState
from src.state.pipeline import PipelineRunner
from src.state.queue import EventQueue
from src.storage import (
    AvatarStateQueries,
    ContributorQueries,
    Database,
    EventQueries,
    get_database,
    reset_database,
)


# ---------------------------------------------------------------------------
# Singleton cleanup
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def _reset_singletons():
    """Reset database and hub singletons before every test."""
    reset_database()
    reset_hub()
    yield


# ---------------------------------------------------------------------------
# Database fixture (same pattern as unit tests)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db() -> AsyncIterator[Database]:
    """Fresh on-disk SQLite with migrations applied, per test."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.db"
        os.environ["DATABASE_PATH"] = str(path)
        from src import config as config_module
        config_module.settings.__init__()

        database = Database(path=path)
        await database.connect()
        await database.run_migrations()
        try:
            yield database
        finally:
            await database.close()


# ---------------------------------------------------------------------------
# Test app (no external pollers — manual lifecycle)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_app(db: Database) -> AsyncIterator[FastAPI]:
    """Build a FastAPI app with real router + PipelineRunner, no external pollers."""
    configure_logging()

    hub: WebSocketHub = get_hub()
    queue = EventQueue()
    runner = PipelineRunner(db=db, queue=queue, hub=hub)
    await runner.start()

    set_dependencies(db, runner, hub, started_at=time.time())

    app = FastAPI(title="BLT-Hackerhouse-Integration-Test")
    app.include_router(router)
    app.state.event_queue = queue
    app.state.hub = hub
    app.state.runner = runner

    @app.websocket("/ws")
    async def _ws(websocket, token: str | None = None):
        await websocket_endpoint(websocket, hub, runner, token=token)

    yield app

    await runner.stop()


@pytest_asyncio.fixture
async def client(test_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """HTTPX async client wired to the test app via ASGI transport."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

async def insert_event(db: Database, **overrides) -> Event:
    """Insert a test event directly (bypasses webhook)."""
    defaults = dict(
        source="gitlab",
        event_type="mr_opened",
        actor_id="42",
        actor_name="test-user",
        repository="owasp/blt",
    )
    event = Event(**{**defaults, **overrides})
    await EventQueries(db).insert(event)
    return event


async def insert_contributor(db: Database, **overrides) -> Contributor:
    """Insert a test contributor directly."""
    defaults = dict(
        id=uuid4(),
        display_name="Test Contributor",
        usernames=["test-user"],
        platform_ids={"gitlab_id": "42"},
    )
    contrib = Contributor(**{**defaults, **overrides})
    await ContributorQueries(db).upsert(contrib)
    return contrib


async def set_avatar_state(db: Database, contributor_id: UUID, **overrides) -> AvatarState:
    """Insert or update an avatar state."""
    defaults = dict(
        contributor_id=contributor_id,
        floor=2,
        room="merge_request_room",
        last_event="mr_opened",
    )
    state = AvatarState(**{**defaults, **overrides})
    await AvatarStateQueries(db).upsert(state)
    return state
