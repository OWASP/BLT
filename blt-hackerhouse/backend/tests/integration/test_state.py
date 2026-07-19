"""Integration tests for GET /state (VF13 — HTTP polling fallback)."""

from __future__ import annotations

from uuid import uuid4

from httpx import AsyncClient

from tests.integration.conftest import insert_contributor, set_avatar_state


class TestStateEndpoint:
    """HTTP fallback for WebSocket snapshot."""

    async def test_empty_state(self, client: AsyncClient):
        """Returns empty snapshot when no data exists."""
        response = await client.get("/state")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["contributors"] == []
        assert body["data"]["room_occupancy"] == {}
        assert "generated_at" in body["data"]

    async def test_state_with_contributor(self, client: AsyncClient, db):
        """Contributors with avatar state appear in snapshot."""
        c = await insert_contributor(db, score=42)
        await set_avatar_state(db, c.id, floor=2, room="merge_request_room", last_event="mr_opened")

        response = await client.get("/state")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["contributors"]) == 1
        assert data["contributors"][0]["display_name"] == "Test Contributor"
        assert data["contributors"][0]["score"] == 42
        assert data["contributors"][0]["floor"] == 2
        assert data["room_occupancy"]["merge_request_room"] == 1

    async def test_state_with_multiple_contributors(self, client: AsyncClient, db):
        """Multiple contributors appear in state."""
        c1 = await insert_contributor(db, id=uuid4(), display_name="Alice", score=30)
        c2 = await insert_contributor(db, id=uuid4(), display_name="Bob", score=50)
        await set_avatar_state(db, c1.id, floor=1, room="issue_room", last_event="issue_opened")
        await set_avatar_state(db, c2.id, floor=3, room="deployment_room", last_event="pipeline_run")

        response = await client.get("/state")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["contributors"]) == 2
        assert data["room_occupancy"]["issue_room"] == 1
        assert data["room_occupancy"]["deployment_room"] == 1

    async def test_state_contributor_without_avatar(self, client: AsyncClient, db):
        """Contributor without avatar state gets defaults (floor=1, activity_monitor)."""
        c = await insert_contributor(db, score=10)

        response = await client.get("/state")
        data = response.json()["data"]
        contrib = next(x for x in data["contributors"] if x["id"] == str(c.id))
        assert contrib["floor"] == 1
        assert contrib["room"] == "activity_monitor"
        assert contrib["score"] == 10
