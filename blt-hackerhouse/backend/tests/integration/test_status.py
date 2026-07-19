"""Integration tests for GET /status (VF15)."""

from __future__ import annotations

from uuid import uuid4

from httpx import AsyncClient

from tests.integration.conftest import insert_contributor


class TestStatusEndpoint:
    """Ecosystem status — occupancy, identity stats, pipeline health."""

    async def test_status_structure(self, client: AsyncClient):
        """Returns expected top-level keys."""
        response = await client.get("/status")
        assert response.status_code == 200

        data = response.json()["data"]
        assert "room_occupancy" in data
        assert "identity_stats" in data
        assert "pipeline_health" in data

    async def test_status_identity_stats(self, client: AsyncClient, db):
        """Identity stats reflect seeded contributors."""
        await insert_contributor(db, is_linked=True)
        await insert_contributor(
            db, id=uuid4(), display_name="Unlinked",
            usernames=["unlinked"], platform_ids={}, is_linked=False,
        )

        response = await client.get("/status")
        assert response.status_code == 200
        stats = response.json()["data"]["identity_stats"]
        assert stats["total_contributors"] >= 2
        assert stats["linked_contributors"] >= 1
        assert stats["unlinked_contributors"] >= 1
        assert 0 < stats["linkage_rate"] <= 1.0

    async def test_status_pipeline_health_defaults(self, client: AsyncClient):
        """Pipeline health starts with zeroed metrics."""
        response = await client.get("/status")
        assert response.status_code == 200

        ph = response.json()["data"]["pipeline_health"]
        assert ph["events_ingested_last_minute"] == 0
        assert ph["gitlab_webhooks_received"] == 0
        assert ph["blt_polls_completed"] == 0
        assert ph["errors_last_hour"] == 0
        assert ph["queue_depth"] == 0

    async def test_status_empty_occupancy(self, client: AsyncClient):
        """Room occupancy is empty when no data exists."""
        response = await client.get("/status")
        assert response.status_code == 200
        assert response.json()["data"]["room_occupancy"] == {}
