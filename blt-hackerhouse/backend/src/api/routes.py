"""REST API routes (VF14, VF15, VF17, VF13 fallback)."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request

from ..broadcast.hub import WebSocketHub
from ..broadcast.messages import avatar_url
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
_settings = None


def set_dependencies(db, runner: PipelineRunner, hub: WebSocketHub, started_at: float) -> None:
    """Wire the request-scoped dependencies (called from FastAPI lifespan)."""
    global _db_dep, _runner_dep, _hub_dep, _started_at, _settings
    from ..config import settings
    _db_dep = db
    _runner_dep = runner
    _hub_dep = hub
    _started_at = started_at
    _settings = settings


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

    logger.info(
        "webhook received",
        extra={"event_header": x_gitlab_event, "token_present": bool(x_gitlab_token)},
    )

    if not verify_gitlab_signature(x_gitlab_token, settings.gitlab_webhook_secret):
        logger.warning("webhook rejected — invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")

    logger.info("webhook token verified")

    db, runner, hub = _require_deps()

    payload = await request.json()
    object_kind = payload.get("object_kind", "unknown")
    try:
        event = normalize_gitlab_payload(payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("webhook normalize failed", extra={
            "error": repr(exc), "object_kind": object_kind,
        })
        hub.record_error()
        raise HTTPException(status_code=400, detail="Could not normalize payload")

    queue: EventQueue = request.app.state.event_queue
    await queue.put(event)
    hub.record_event()
    logger.info(
        "webhook enqueued",
        extra={
            "event_type": event.event_type,
            "object_kind": object_kind,
            "actor": event.actor_name,
            "queue_depth": queue.qsize(),
        },
    )
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
            contributor_id=str(e.contributor_id) if e.contributor_id else "",
            avatar_url=avatar_url(e.contributor_id) if e.contributor_id else "",
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
                avatar_url=avatar_url(c.id),
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
async def health(request: Request) -> HealthResponse:
    db, runner, hub = _require_deps()
    event_count = await EventQueries(db).count()
    stats = await ContributorQueries(db).stats()
    blt_bugs_cursor = await CursorQueries(db).get("blt_bugs")
    gitlab_cursor = await CursorQueries(db).get("gitlab_events_0")

    blt_poller = getattr(request.app.state, "blt_poller", None)
    gap_detector = getattr(request.app.state, "gap_detector", None)

    webhook_healthy = bool(_settings.gitlab_webhook_secret)

    blt_last_poll = blt_poller.last_success_at.isoformat() if (
        blt_poller and blt_poller.last_success_at
    ) else None
    blt_last_error = blt_poller.last_error_text if blt_poller else None

    gap_last_poll = gap_detector.last_success_at.isoformat() if (
        gap_detector and gap_detector.last_success_at
    ) else None
    gap_last_error = gap_detector.last_error_text if gap_detector else None

    return HealthResponse(
        status="healthy",
        components={
            "gitlab_webhook": {
                "status": "healthy" if webhook_healthy else "disabled",
                "last_event_at": hub.last_event_at.isoformat() if hub.last_event_at else None,
            },
            "gitlab_gap_detector": {
                "status": "healthy" if (gap_detector and gap_detector.enabled) else "disabled",
                "last_poll_at": gap_last_poll,
                "total_enqueued": gap_detector.total_enqueued if gap_detector else 0,
                "last_error": gap_last_error,
                "tracked_projects": len(gap_detector.project_ids) if gap_detector else 0,
            },
            "blt_polling": {
                "status": "healthy" if (blt_poller and blt_poller.enabled) else "disabled",
                "last_poll_at": blt_last_poll,
                "last_seen_bug_id": blt_bugs_cursor[0] if blt_bugs_cursor else 0,
                "total_enqueued": blt_poller.total_enqueued if blt_poller else 0,
                "last_error": blt_last_error,
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
                    avatar_url=avatar_url(c.id),
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