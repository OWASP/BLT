"""Regression tests for the web-served compact agent context."""

from pathlib import Path

import pytest

import main
from handlers.homepage import handle_llm_txt


ROOT = Path(__file__).resolve().parents[1]
ROOT_LLM_TXT = ROOT / "llm.txt"


class MockRequest:
    def __init__(self, url="https://api.example.com/llm.txt"):
        self.url = url
        self.method = "GET"


class MockEnv:
    pass


async def _llm_response():
    response = await handle_llm_txt(
        MockRequest(),
        MockEnv(),
        path_params={},
        query_params={},
        path="/llm.txt",
    )
    assert response.status == 200
    assert "text/plain" in response.headers["Content-Type"]
    return response


def test_llm_txt_is_served_from_web_route_not_repo_root_file():
    assert not ROOT_LLM_TXT.exists()


def test_llm_txt_route_is_registered():
    route_paths = {(route.method, route.pattern) for route in main.router.routes}
    assert ("GET", "/llm.txt") in route_paths


@pytest.mark.asyncio
async def test_llm_txt_route_returns_required_agent_context():
    response = await _llm_response()
    text = response.body
    lower_text = text.lower()

    for required in [
        "blt-api",
        "owasp blt",
        "cloudflare workers",
        "d1",
        "wrangler",
        "x-blt-api-key",
        "jwt",
        "bearer",
        "/v2",
        "src/main.py",
        "src/handlers/",
        "migrations/",
        "tests/",
        "readme.md",
        "contributing.md",
        "docs/database.md",
    ]:
        assert required in lower_text


@pytest.mark.asyncio
async def test_llm_txt_keeps_api_key_and_jwt_roles_separate():
    response = await _llm_response()
    text = response.body

    assert "X-BLT-API-Key" in text
    assert "API access gate" in text or "API gate" in text
    assert "JWT" in text
    assert "user identity" in text or "user session" in text


@pytest.mark.asyncio
async def test_llm_txt_is_compact_and_secret_free():
    response = await _llm_response()
    text = response.body
    non_empty_lines = [line for line in text.splitlines() if line.strip()]

    assert len(non_empty_lines) <= 120
    assert "f5537412b459790f9fa1cc47b862b9c7016471957178dc9b161d59355b6fd051" not in text
    assert "your-very-secure-random-string-here" not in text
