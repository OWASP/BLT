"""Integration tests for GET /activity (VF14)."""

from __future__ import annotations

from datetime import datetime, timezone

from httpx import AsyncClient

from tests.integration.conftest import insert_event


class TestActivityEndpoint:
    """Activity feed — paginated, reverse-chronological events."""

    async def test_empty_activity(self, client: AsyncClient):
        """Returns empty list when no events exist."""
        response = await client.get("/activity")
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["pagination"]["total"] == 0
        assert body["pagination"]["total_pages"] == 0
        assert body["success"] is True

    async def test_paginated_activity_order(self, client: AsyncClient, db):
        """Events are returned in reverse chronological order."""
        e1 = await insert_event(
            db, event_type="mr_opened",
            timestamp=datetime(2026, 6, 24, 10, 0, 0, tzinfo=timezone.utc),
        )
        e2 = await insert_event(
            db, event_type="mr_merged",
            timestamp=datetime(2026, 6, 24, 11, 0, 0, tzinfo=timezone.utc),
        )

        response = await client.get("/activity?per_page=10")
        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]) == 2
        assert body["data"][0]["event_type"] == "mr_merged"
        assert body["data"][1]["event_type"] == "mr_opened"
        assert body["pagination"]["total"] == 2
        assert body["pagination"]["total_pages"] == 1

    async def test_activity_pagination(self, client: AsyncClient, db):
        """Pagination controls work correctly."""
        for i in range(5):
            await insert_event(db, actor_id=str(i), actor_name=str(i), event_type=["mr_opened", "mr_merged", "issue_opened", "note_added", "pipeline_run"][i])

        r1 = await client.get("/activity?page=1&per_page=2")
        assert r1.status_code == 200
        assert len(r1.json()["data"]) == 2
        assert r1.json()["pagination"]["page"] == 1
        assert r1.json()["pagination"]["total_pages"] == 3

        r2 = await client.get("/activity?page=3&per_page=2")
        assert r2.status_code == 200
        assert len(r2.json()["data"]) == 1
        assert r2.json()["pagination"]["page"] == 3

    async def test_activity_per_page_capped(self, client: AsyncClient):
        """per_page > 100 is rejected."""
        response = await client.get("/activity?per_page=200")
        assert response.status_code == 422

    async def test_activity_negative_page_rejected(self, client: AsyncClient):
        """Negative page is rejected."""
        response = await client.get("/activity?page=-1")
        assert response.status_code == 422

    async def test_activity_fields(self, client: AsyncClient, db):
        """Activity items contain expected fields."""
        await insert_event(db, event_type="issue_opened", repository="owasp/blt-ui")

        response = await client.get("/activity")
        assert response.status_code == 200
        item = response.json()["data"][0]
        assert "id" in item
        assert "source" in item
        assert "event_type" in item
        assert "actor_name" in item
        assert "repository" in item
        assert "timestamp" in item
