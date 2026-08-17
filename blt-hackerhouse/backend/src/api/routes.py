"""REST API routes (VF14, VF15, VF17, VF13 fallback).

All routes receive the D1 binding via ``request.scope["env"]``
which is injected by the ASGI adapter (``asgi.fetch(app, request, env)``).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Query, Request

from broadcast.messages import avatar_url
from config import settings
from core.security import verify_token
from ingestion.gitlab_webhook import verify_gitlab_signature
from normalization.gitlab import normalize_gitlab_payload
from storage import (
    AvatarStateQueries,
    ContributorQueries,
    CursorQueries,
    EventQueries,
)
from models.api import (
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


logger = logging.getLogger(__name__)

router = APIRouter()


def _get_env(request: Request):
    """Return the Workers env object injected by the ASGI adapter."""
    return request.scope["env"]


# ---------------------------------------------------------------------------
# /webhook/gitlab (VF01)
# ---------------------------------------------------------------------------

@router.post("/webhook/gitlab")
async def gitlab_webhook(
    request: Request,
    x_gitlab_token: str | None = Header(default=None),
) -> dict[str, str]:
    if not verify_gitlab_signature(x_gitlab_token, settings.gitlab_webhook_secret):
        logger.warning("webhook rejected — invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")

    payload = await request.json()
    object_kind = payload.get("object_kind", "unknown")
    try:
        event = normalize_gitlab_payload(payload)
    except Exception as exc:
        logger.warning("webhook normalize failed", extra={"error": repr(exc)})
        raise HTTPException(status_code=400, detail="Could not normalize payload")

    env = _get_env(request)
    await env.PIPELINE_QUEUE.send(event.model_dump(mode="json"))
    return {"status": "accepted"}


# ---------------------------------------------------------------------------
# /activity (VF14)
# ---------------------------------------------------------------------------

@router.get("/activity", response_model=PaginatedResponse[ActivityFeedItem])
async def list_activity(
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse[ActivityFeedItem]:
    env = _get_env(request)
    db = env.HH_DB
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
    request: Request,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[LeaderboardEntry]:
    env = _get_env(request)
    db = env.HH_DB
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
async def status(request: Request) -> StatusResponse:
    env = _get_env(request)
    db = env.HH_DB
    avatars = AvatarStateQueries(db)
    contributors = ContributorQueries(db)
    events = EventQueries(db)

    occupancy = await avatars.occupancy()
    stats = await contributors.stats()
    event_count = await events.count()

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
                events_ingested_last_minute=0,
                gitlab_webhooks_received=0,
                blt_polls_completed=0,
                errors_last_hour=0,
                queue_depth=None,
            ),
        )
    )


# ---------------------------------------------------------------------------
# /health (VF17)
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    env = _get_env(request)
    db = env.HH_DB
    events = EventQueries(db)
    contributors = ContributorQueries(db)
    cursors = CursorQueries(db)

    event_count = await events.count()
    stats = await contributors.stats()
    blt_bugs_cursor = await cursors.get("blt_bugs")

    webhook_healthy = bool(settings.gitlab_webhook_secret)
    gap_enabled = bool(settings.gitlab_api_token and settings.gitlab_tracked_project_ids)
    blt_enabled = bool(settings.blt_api_key)

    return HealthResponse(
        status="healthy",
        components={
            "gitlab_webhook": {
                "status": "healthy" if webhook_healthy else "disabled",
                "last_event_at": None,
            },
            "gitlab_gap_detector": {
                "status": "healthy" if gap_enabled else "disabled",
                "last_poll_at": None,
                "total_enqueued": 0,
                "last_error": None,
                "tracked_projects": len(settings.gitlab_tracked_project_ids.split(",")) if settings.gitlab_tracked_project_ids else 0,
            },
            "blt_polling": {
                "status": "healthy" if blt_enabled else "disabled",
                "last_poll_at": None,
                "last_seen_bug_id": blt_bugs_cursor[0] if blt_bugs_cursor else 0,
                "total_enqueued": 0,
                "last_error": None,
            },
            "database": {
                "status": "healthy",
                "event_count": event_count,
            },
            "websocket": {
                "status": "healthy",
                "connected_clients": 0,
            },
            "identity_resolver": {
                "status": "healthy",
                "resolution_cache_size": stats["total"],
            },
        },
        uptime_seconds=0.0,
    )


# ---------------------------------------------------------------------------
# /state — HTTP polling fallback for WS clients (VF13)
# ---------------------------------------------------------------------------

@router.get("/state", response_model=StateResponse)
async def state_snapshot(request: Request) -> StateResponse:
    env = _get_env(request)
    db = env.HH_DB
    contributors = ContributorQueries(db)
    avatars = AvatarStateQueries(db)

    contributors_list = await contributors.list_all()
    avatars_list = await avatars.list_all()
    avatar_map = {a["contributor_id"]: a for a in avatars_list}
    occupancy = await avatars.occupancy()

    # Build contributor snapshots from raw D1 data
    snapshot_contributors = []
    for c in contributors_list:
        avatar = avatar_map.get(str(c.id))
        snapshot_contributors.append(
            SnapshotStateContributor(
                id=c.id,
                display_name=c.display_name,
                avatar_url=avatar_url(c.id) if c.id else "",
                floor=avatar["floor"] if avatar else 1,
                room=avatar["room"] if avatar else "activity_monitor",
                identity_linked=c.is_linked,
                last_event=avatar["last_event"] if avatar else None,
                score=c.score,
            )
        )

    from datetime import datetime, timezone
    return StateResponse(
        data=StateResponseData(
            contributors=snapshot_contributors,
            room_occupancy=occupancy,
            generated_at=datetime.now(tz=timezone.utc).replace(microsecond=0),
        )
    )


# ---------------------------------------------------------------------------
# Test endpoints
# ---------------------------------------------------------------------------

@router.get("/d1-read")
async def d1_read(request: Request) -> dict:
    env = _get_env(request)
    db = env.HH_DB
    result = await db.prepare("SELECT 1 AS one").first()
    if result is not None:
        return dict(result.copy())
    return {"one": None}


@router.get("/d1-write")
async def d1_write(request: Request) -> dict:
    env = _get_env(request)
    db = env.HH_DB
    await db.prepare(
        "INSERT OR IGNORE INTO contributors (id, display_name) VALUES (?, ?)"
    ).bind("test-001", "Test User").run()
    return {"inserted": True}


@router.get("/queue-produce")
async def queue_produce(request: Request) -> dict:
    env = _get_env(request)
    await env.PIPELINE_QUEUE.send({"hello": "world"})
    return {"queued": True}
