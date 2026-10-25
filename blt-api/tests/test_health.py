"""
Tests for health check handler.
"""

import json
import pytest
from handlers.health import handle_health


class MockRequest:
    def __init__(self, url="https://api.owaspblt.org/health"):
        self.url = url
        self.method = "GET"


class MockEnv:
    pass


@pytest.mark.asyncio
async def test_health_check_returns_all_expected_endpoints():
    request = MockRequest()
    env = MockEnv()
    response = await handle_health(request, env, {}, {}, "/health")

    assert response.status == 200
    data = json.loads(response.body)
    assert data["status"] == "healthy"
    assert data["api"] == "BLT API"

    endpoints = data["endpoints"]
    expected_keys = [
        "bugs",
        "users",
        "domains",
        "organizations",
        "projects",
        "hunts",
        "stats",
        "leaderboard",
        "contributors",
        "repos",
        "jobs",
        "hackathons",
        "routes",
        "auth",
    ]
    for key in expected_keys:
        assert key in endpoints, f"Missing endpoint key: {key}"
