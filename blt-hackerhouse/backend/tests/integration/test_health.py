"""Integration tests for GET /health (VF17)."""

from __future__ import annotations

from httpx import AsyncClient

from tests.integration.conftest import insert_event


class TestHealthEndpoint:
    """Health check — component-level status."""

    async def test_health_returns_healthy(self, client: AsyncClient):
        """Base health returns healthy status with all components."""
        response = await client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert "components" in body
        assert "database" in body["components"]
        assert "websocket" in body["components"]
        assert "identity_resolver" in body["components"]
        assert body["uptime_seconds"] >= 0

    async def test_health_reflects_event_count(self, client: AsyncClient, db):
        """Event count in health reflects inserted events."""
        await insert_event(db)
        await insert_event(db, event_type="mr_merged")

        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["components"]["database"]["event_count"] == 2

    async def test_health_websocket_clients(self, client: AsyncClient):
        """Connected clients reported correctly at startup."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["components"]["websocket"]["connected_clients"] == 0
