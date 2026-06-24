"""Integration tests for GET /leaderboard (VF16)."""

from __future__ import annotations

from httpx import AsyncClient

from tests.integration.conftest import insert_contributor


class TestLeaderboardEndpoint:
    """Leaderboard — ranked contributors by score descending."""

    async def test_empty_leaderboard(self, client: AsyncClient):
        """Empty leaderboard returns empty list."""
        response = await client.get("/leaderboard")
        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["pagination"]["total"] == 0
        assert body["success"] is True

    async def test_leaderboard_ordering(self, client: AsyncClient, db):
        """Contributors returned in score-descending order with correct ranks."""
        from uuid import uuid4

        low = await insert_contributor(db, id=uuid4(), display_name="Low", score=10)
        high = await insert_contributor(db, id=uuid4(), display_name="High", score=99)

        response = await client.get("/leaderboard")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data[0]["display_name"] == "High"
        assert data[0]["score"] == 99
        assert data[0]["rank"] == 1
        assert data[1]["display_name"] == "Low"
        assert data[1]["score"] == 10
        assert data[1]["rank"] == 2

    async def test_leaderboard_pagination(self, client: AsyncClient, db):
        """Pagination works for leaderboard."""
        from uuid import uuid4

        for i in range(5):
            await insert_contributor(db, id=uuid4(), display_name=f"User{i}", score=i * 10)

        r1 = await client.get("/leaderboard?page=1&per_page=2")
        assert r1.status_code == 200
        assert len(r1.json()["data"]) == 2
        assert r1.json()["pagination"]["total_pages"] == 3

    async def test_leaderboard_per_page_capped(self, client: AsyncClient):
        """per_page > 100 is rejected."""
        response = await client.get("/leaderboard?per_page=200")
        assert response.status_code == 422

    async def test_leaderboard_fields(self, client: AsyncClient, db):
        """Leaderboard entries contain expected fields."""
        from uuid import uuid4

        await insert_contributor(db, id=uuid4(), display_name="Alice", score=50)

        response = await client.get("/leaderboard")
        item = response.json()["data"][0]
        assert "contributor_id" in item
        assert "display_name" in item
        assert "score" in item
        assert "rank" in item
