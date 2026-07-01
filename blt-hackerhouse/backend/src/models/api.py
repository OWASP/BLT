"""
REST API response and request models.

Wrappers for paginated responses, activity feed items, leaderboard
entries, status payloads, and health check responses.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated API response wrapper."""

    success: bool = True
    data: list[T] = Field(default_factory=list)
    pagination: PaginationMeta


class PaginationMeta(BaseModel):
    """Pagination metadata included in every paginated response."""

    page: int = Field(ge=1)
    per_page: int = Field(ge=1, le=100)
    count: int = Field(ge=0, description="Number of items in this page.")
    total: int = Field(ge=0, description="Total items across all pages.")
    total_pages: int = Field(ge=0)


class ActivityFeedItem(BaseModel):
    """A single entry in the activity feed."""

    id: UUID
    source: str
    event_type: str
    actor_name: str
    repository: str = ""
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class LeaderboardEntry(BaseModel):
    """A single row on the leaderboard."""

    contributor_id: UUID
    display_name: str
    score: int = Field(ge=0)
    rank: int = Field(ge=1)


class StatusResponse(BaseModel):
    """Aggregated ecosystem status for the maintainer visibility panel."""

    success: bool = True

    data: StatusData


class StatusData(BaseModel):
    """Payload for the /status endpoint."""

    room_occupancy: dict[str, int] = Field(default_factory=dict)
    identity_stats: IdentityStats
    pipeline_health: PipelineHealth


class IdentityStats(BaseModel):
    """Identity resolution statistics."""

    total_contributors: int = Field(ge=0)
    linked_contributors: int = Field(ge=0)
    unlinked_contributors: int = Field(ge=0)
    linkage_rate: float = Field(ge=0.0, le=1.0)


class PipelineHealth(BaseModel):
    """Event pipeline health metrics."""

    events_ingested_last_minute: int = Field(ge=0)
    gitlab_webhooks_received: int = Field(ge=0)
    blt_polls_completed: int = Field(ge=0)
    errors_last_hour: int = Field(ge=0)
    queue_depth: int = Field(ge=0)


class HealthResponse(BaseModel):
    """Response for the /health endpoint."""

    status: str = Field(description="One of: healthy, degraded, unhealthy.")
    components: dict[str, ComponentHealth] = Field(default_factory=dict)
    uptime_seconds: float = Field(ge=0)


class ComponentHealth(BaseModel):
    """Health status of a single pipeline component."""

    status: str = Field(description="healthy, degraded, or unhealthy.")
    last_event_at: str | None = None
    last_poll_at: str | None = None
    last_seen_bug_id: int | None = None
    event_count: int | None = None
    connected_clients: int | None = None
    resolution_cache_size: int | None = None
    total_enqueued: int | None = None
    last_error: str | None = None
    tracked_projects: int | None = None


class StateResponse(BaseModel):
    """HTTP polling fallback response — same shape as WebSocket snapshot."""

    success: bool = True
    data: StateResponseData


class StateResponseData(BaseModel):
    """Snapshot-compatible payload for GET /state."""

    contributors: list[SnapshotStateContributor] = Field(default_factory=list)
    room_occupancy: dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc).replace(microsecond=0),
    )


class SnapshotStateContributor(BaseModel):
    """Contributor entry in the polling fallback state response."""

    id: UUID
    display_name: str
    floor: int | None = None
    room: str | None = None
    identity_linked: bool = False
    last_event: str | None = None
    score: int = 0
