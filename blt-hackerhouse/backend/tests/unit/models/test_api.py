"""Unit tests for API response/request models."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from models.api import (
    PaginatedResponse,
    PaginationMeta,
    ActivityFeedItem,
    LeaderboardEntry,
    StatusResponse,
    StatusData,
    IdentityStats,
    PipelineHealth,
    HealthResponse,
    ComponentHealth,
    StateResponse,
    StateResponseData,
    SnapshotStateContributor,
)


class TestPaginationMeta:
    def test_valid_meta(self):
        meta = PaginationMeta(page=1, per_page=20, count=20, total=312, total_pages=16)
        assert meta.total_pages == 16

    def test_negative_page_rejected(self):
        with pytest.raises(ValidationError):
            PaginationMeta(page=0, per_page=20, count=0, total=0, total_pages=0)

    def test_per_page_limit(self):
        with pytest.raises(ValidationError):
            PaginationMeta(page=1, per_page=200, count=0, total=0, total_pages=0)


class TestPaginatedResponse:
    def test_paginated_response(self):
        meta = PaginationMeta(page=1, per_page=20, count=2, total=2, total_pages=1)
        resp = PaginatedResponse[str](data=["a", "b"], pagination=meta)
        assert resp.success is True
        assert len(resp.data) == 2
        assert resp.pagination.count == 2


class TestActivityFeedItem:
    def test_valid_item(self):
        item = ActivityFeedItem(
            id=uuid4(),
            source="gitlab",
            event_type="mr_opened",
            actor_name="rudra-rps",
            repository="OWASP-BLT/BLT",
            timestamp="2026-07-15T10:22:00",
            metadata={"title": "Add webhook ingestion"},
        )
        assert item.source == "gitlab"
        assert item.metadata["title"] == "Add webhook ingestion"


class TestLeaderboardEntry:
    def test_valid_entry(self):
        entry = LeaderboardEntry(
            contributor_id=uuid4(),
            display_name="Test User",
            score=142,
            rank=1,
        )
        assert entry.rank == 1

    def test_negative_score_rejected(self):
        with pytest.raises(ValidationError):
            LeaderboardEntry(contributor_id=uuid4(), display_name="x", score=-1, rank=1)

    def test_zero_rank_rejected(self):
        with pytest.raises(ValidationError):
            LeaderboardEntry(contributor_id=uuid4(), display_name="x", score=0, rank=0)


class TestStatusResponse:
    def test_status_response(self):
        data = StatusData(
            room_occupancy={"issue_triage_desk": 5},
            identity_stats=IdentityStats(
                total_contributors=87,
                linked_contributors=64,
                unlinked_contributors=23,
                linkage_rate=0.736,
            ),
            pipeline_health=PipelineHealth(
                events_ingested_last_minute=12,
                gitlab_webhooks_received=145,
                blt_polls_completed=8,
                errors_last_hour=2,
                queue_depth=0,
            ),
        )
        resp = StatusResponse(data=data)
        assert resp.success is True
        assert resp.data.identity_stats.linkage_rate == 0.736

    def test_linkage_rate_bounds(self):
        # 0.0 valid
        IdentityStats(
            total_contributors=1, linked_contributors=0, unlinked_contributors=1, linkage_rate=0.0,
        )
        # 1.0 valid
        IdentityStats(
            total_contributors=1, linked_contributors=1, unlinked_contributors=0, linkage_rate=1.0,
        )
        # above 1.0
        with pytest.raises(ValidationError):
            IdentityStats(total_contributors=1, linked_contributors=1, unlinked_contributors=0, linkage_rate=1.5)


class TestHealthResponse:
    def test_health_response(self):
        resp = HealthResponse(
            status="healthy",
            components={
                "gitlab_webhook": ComponentHealth(status="healthy", last_event_at="2026-07-15T10:22:00Z"),
                "database": ComponentHealth(status="healthy", event_count=5432),
                "websocket": ComponentHealth(status="healthy", connected_clients=5),
            },
            uptime_seconds=3600.0,
        )
        assert resp.status == "healthy"
        assert resp.components["database"].event_count == 5432


class TestStateResponse:
    def test_state_response(self):
        cid = uuid4()
        data = StateResponseData(
            contributors=[
                SnapshotStateContributor(
                    id=cid,
                    display_name="Test",
                    floor=2,
                    room="merge_request_room",
                    identity_linked=True,
                    last_event="mr_opened",
                    score=42,
                )
            ],
            room_occupancy={"merge_request_room": 1},
        )
        resp = StateResponse(data=data)
        assert resp.success is True
        assert resp.data.contributors[0].display_name == "Test"

    def test_state_response_empty(self):
        resp = StateResponse(data=StateResponseData())
        assert resp.data.contributors == []
        assert resp.data.room_occupancy == {}
