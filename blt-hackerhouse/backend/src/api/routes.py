"""REST API routes (VF14, VF15, VF17, VF13 fallback)."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request

from ..broadcast.hub import WebSocketHub
from ..models.api import (
    ActivityFeedItem,
    HealthResponse,
    LeaderboardEntry,
    PaginatedResponse,
    PaginationMeta,
    PipelineHealth,
    IdentityStats,
    SnapshotStateContributor,
    StateResponse,
    StateResponseData,
    StatusData,
    StatusResponse,
)
from ..state.pipeline import PipelineRunner
from ..storage import (
    AvatarStateQueries,
    ContributorQueries,
    CursorQueries,
    DeadLetterQueries,
    EventQueries,
)


logger = logging.getLogger(__name__)

router = APIRouter()


# Dependents are injected at app startup via set_dependencies()
_db_dep: Any = None
_runner_dep: Any = None
_hub_dep: Any = None
_started_at: float = 0.0


def set_dependencies(db, runner: PipelineRunner, hub: WebSocketHub, started_at: float) -> None:
    """Wire the request-scoped dependencies (called from FastAPI lifespan)."""
    global _db_dep, _runner_dep, _hub_dep, _started_at
    _db_dep = db
    _runner_dep = runner
    _hub_dep = hub
    _started_at = started_at


def _require_deps():
    if _db_dep is None or _runner_dep is None or _hub_dep is None:
        raise RuntimeError("API dependencies not initialized. Did the app start?")
    return _db_dep, _runner_dep, _hub_dep


# ---------------------------------------------------------------------------
# /webhook/gitlab (VF01)
# ---------------------------------------------------------------------------

@router.post("/webhook/gitlab")
async def gitlab_webhook(
    request: Request,
    x_gitlab_token: str | None = Header(default=None),
    x_gitlab_event: str | None = Header(default=None),
) -> dict[str, str]:
    from ..config import settings
    from ..ingestion.gitlab_webhook import verify_gitlab_signature
    from ..normalization.gitlab import normalize_gitlab_payload
    from ..state.queue import EventQueue

    if not verify_gitlab_signature(x_gitlab_token, settings.gitlab_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid token")

    db, runner, hub = _require_deps()

    payload = await request.json()
    try:
        event = normalize_gitlab_payload(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("webhook normalize failed", extra={"error": repr(exc)})
        hub.record_error()
        raise HTTPException(status_code=400, detail="Could not normalize payload")

    queue: EventQueue = request.app.state.event_queue
    try:
        await asyncio.wait_for(queue.put(event), timeout=5.0)
    except asyncio.TimeoutError:
        logger.warning("webhook queue full, rejecting event")
        raise HTTPException(status_code=503, detail="Queue full, please retry")
    hub.record_event()
    return {"status": "accepted"}


# ---------------------------------------------------------------------------
# /activity (VF14)
# ---------------------------------------------------------------------------

@router.get("/activity", response_model=PaginatedResponse[ActivityFeedItem])
async def list_activity(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse[ActivityFeedItem]:
    db, _, _ = _require_deps()
    events, total = await EventQueries(db).list_activity(page=page, per_page=per_page)
    items = [
        ActivityFeedItem(
            id=e.id,
            source=e.source,
            event_type=e.event_type,
            actor_name=e.actor_name,
            repository=e.repository,
            timestamp=e.timestamp,
            metadata=e.metadata,
        )
        for e in events
    ]
    return PaginatedResponse[ActivityFeedItem](
        data=items,
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            count=len(items),
            total=total,
            total_pages=(total + per_page - 1) // per_page if total else 0,
        ),
    )


# ---------------------------------------------------------------------------
# /leaderboard (VF16)
# ---------------------------------------------------------------------------

@router.get("/leaderboard", response_model=PaginatedResponse[LeaderboardEntry])
async def leaderboard(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[LeaderboardEntry]:
    db, _, _ = _require_deps()
    offset = (page - 1) * per_page
    contributors, total = await ContributorQueries(db).list_top(per_page, offset)
    entries: list[LeaderboardEntry] = []
    for rank, c in enumerate(contributors, start=offset + 1):
        entries.append(
            LeaderboardEntry(
                contributor_id=c.id,
                display_name=c.display_name,
                score=c.score,
                rank=rank,
            )
        )
    return PaginatedResponse[LeaderboardEntry](
        data=entries,
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            count=len(entries),
            total=total,
            total_pages=(total + per_page - 1) // per_page if total else 0,
        ),
    )


# ---------------------------------------------------------------------------
# /status (VF15)
# ---------------------------------------------------------------------------

@router.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    db, runner, hub = _require_deps()
    occupancy = await runner.room_occupancy()
    stats = await ContributorQueries(db).stats()
    events_min = await runner.events_last_minute()

    return StatusResponse(
        data=StatusData(
            room_occupancy=occupancy,
            identity_stats=IdentityStats(
                total_contributors=stats["total"],
                linked_contributors=stats["linked"],
                unlinked_contributors=stats["unlinked"],
                linkage_rate=(stats["linked"] / stats["total"]) if stats["total"] else 0.0,
            ),
            pipeline_health=PipelineHealth(
                events_ingested_last_minute=events_min,
                gitlab_webhooks_received=events_min,  # MVP doesn't split; good enough for status
                blt_polls_completed=0,
                errors_last_hour=hub.errors_last_hour(),
                queue_depth=runner.queue.qsize(),
            ),
        )
    )


# ---------------------------------------------------------------------------
# /health (VF17)
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    db, runner, hub = _require_deps()
    event_count = await EventQueries(db).count()
    stats = await ContributorQueries(db).stats()
    blt_bugs_cursor = await CursorQueries(db).get("blt_bugs")
    return HealthResponse(
        status="healthy",
        components={
            "gitlab_webhook": {
                "status": "healthy",
                "last_event_at": None,
            },
            "blt_polling": {
                "status": "healthy",
                "last_poll_at": blt_bugs_cursor[1] if blt_bugs_cursor else None,
                "last_seen_bug_id": blt_bugs_cursor[0] if blt_bugs_cursor else 0,
            },
            "database": {
                "status": "healthy",
                "event_count": event_count,
            },
            "websocket": {
                "status": "healthy",
                "connected_clients": hub.client_count,
            },
            "identity_resolver": {
                "status": "healthy",
                "resolution_cache_size": stats["total"],
            },
        },
        uptime_seconds=(time.time() - _started_at) if _started_at else 0.0,
    )


# ---------------------------------------------------------------------------
# /state — HTTP polling fallback for WS clients (VF13)
# ---------------------------------------------------------------------------

@router.get("/state", response_model=StateResponse)
async def state_snapshot() -> StateResponse:
    db, runner, _ = _require_deps()
    snapshot = await runner.build_snapshot()
    return StateResponse(
        data=StateResponseData(
            contributors=[
                SnapshotStateContributor(
                    id=c.id,
                    display_name=c.display_name,
                    floor=c.floor,
                    room=c.room,
                    identity_linked=c.identity_linked,
                    last_event=c.last_event,
                    score=c.score,
                )
                for c in snapshot.data.contributors
            ],
            room_occupancy=snapshot.data.room_occupancy,
            generated_at=snapshot.data.generated_at,
        )
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

async def _fetch_cursors(db) -> dict[str, int]:
    out: dict[str, int] = {}
    cursor_q = CursorQueries(db)
    results = await asyncio.gather(
        cursor_q.get("blt_bugs"),
        cursor_q.get("blt_hunts"),
    )
    for src, c in zip(("blt_bugs", "blt_hunts"), results):
        if c is not None:
            out[src] = c[0]
    return out