"""
Confirmation tests for every write tool, run through the registered tool dispatch (`mcp.call_tool`).

For each tool whose schema has a `confirmed` argument:
- `confirmed` omitted and `confirmed=False`: the call is rejected with the confirmation error and no HTTP
  request is made.
- `confirmed=True`: exactly one HTTP request is made.
- A malformed `confirmed` value is rejected by schema validation and no HTTP request is made.

`test_write_tool_set_is_explicit` fails when a tool gains or loses `confirmed`, so a new tool has to be
classified here on purpose.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

import blt_mcp.server  # noqa: F401  (registers the tools)
from blt_mcp import server_base
from blt_mcp.server_base import mcp

WRITE_TOOLS = {
    "submit_issue",
    "auth_signup",
    "create_bug",
    "update_bug",
    "create_user",
    "create_job",
    "update_job",
    "record_job_view",
    "create_hackathon",
    "update_hackathon",
    "register_hackathon_participant",
}
NO_CONFIRMATION_TOOLS = {
    "auth_signin",
    "summarize_issue_context",
    "triage_vulnerability",
    "draft_vision_issue",
}
CONFIRMATION_ERROR = "Write operation requires confirmation"


def _minimal_args(schema: dict) -> dict:
    return {name: "1" for name in schema.get("required", [])}


@pytest.fixture
def http(monkeypatch):
    """Replace the HTTP client used by the v1 and v2 tools and record every request."""
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value={"id": 1})
    response.text = "{}"
    client = MagicMock()
    for method in ("get", "post", "patch", "put", "delete", "request"):
        setattr(client, method, AsyncMock(return_value=response))
    monkeypatch.setattr(server_base, "http_client", client)
    return client


def _requests_made(client) -> int:
    return sum(
        getattr(client, m).await_count
        for m in ("get", "post", "patch", "put", "delete", "request")
    )


async def _schemas():
    return {t.name: t.inputSchema for t in await mcp.list_tools()}


async def test_write_tool_set_is_explicit():
    schemas = await _schemas()
    with_confirmed = {
        name
        for name, schema in schemas.items()
        if "confirmed" in schema.get("properties", {})
    }
    assert with_confirmed == WRITE_TOOLS
    assert set(schemas) == WRITE_TOOLS | NO_CONFIRMATION_TOOLS
    for name in WRITE_TOOLS:
        assert schemas[name]["properties"]["confirmed"]["default"] is False
        assert "confirmed" not in schemas[name].get("required", [])


@pytest.mark.parametrize("tool", sorted(WRITE_TOOLS))
async def test_confirmation_omitted_is_rejected(tool, http):
    args = _minimal_args((await _schemas())[tool])
    with pytest.raises(Exception, match=CONFIRMATION_ERROR):
        await mcp.call_tool(tool, args)
    assert _requests_made(http) == 0


@pytest.mark.parametrize("tool", sorted(WRITE_TOOLS))
async def test_confirmation_false_is_rejected(tool, http):
    args = {**_minimal_args((await _schemas())[tool]), "confirmed": False}
    with pytest.raises(Exception, match=CONFIRMATION_ERROR):
        await mcp.call_tool(tool, args)
    assert _requests_made(http) == 0


@pytest.mark.parametrize("tool", sorted(WRITE_TOOLS))
async def test_confirmation_true_performs_the_write(tool, http):
    args = {**_minimal_args((await _schemas())[tool]), "confirmed": True}
    await mcp.call_tool(tool, args)
    assert _requests_made(http) == 1
    method = next(
        m for m in ("post", "patch", "put", "delete") if getattr(http, m).await_count
    )
    assert method in {"post", "patch"}


@pytest.mark.parametrize("tool", sorted(WRITE_TOOLS))
async def test_malformed_confirmation_is_rejected(tool, http):
    args = {**_minimal_args((await _schemas())[tool]), "confirmed": "maybe"}
    with pytest.raises(Exception, match="confirmed"):
        await mcp.call_tool(tool, args)
    assert _requests_made(http) == 0


V2_WRITE_TOOLS = sorted(WRITE_TOOLS - {"submit_issue"})


@pytest.mark.parametrize("tool", V2_WRITE_TOOLS)
async def test_v2_tools_use_the_client_created_at_startup(tool, monkeypatch):
    """Regression: v2 tools once kept the import-time client (None) instead of the one the lifespan creates."""
    monkeypatch.setattr(server_base, "http_client", None)
    args = {**_minimal_args((await _schemas())[tool]), "confirmed": True}
    with pytest.raises(Exception, match="HTTP client is not initialized"):
        await mcp.call_tool(tool, args)


async def test_v2_write_works_after_the_server_lifespan_starts():
    async with server_base.server_lifespan(mcp):
        assert server_base.http_client is not None
        result = await mcp.call_tool(
            "create_bug",
            {
                "url": "https://example.com",
                "title": "t",
                "description": "d",
                "confirmed": True,
            },
        )
    assert "Successfully created bug: t" in str(result)
    assert server_base.http_client is not None and server_base.http_client.is_closed


# tool -> (HTTP method, path, body fields it must send); every required argument is "1" in these calls.
V2_REQUESTS = {
    "auth_signup": (
        "post",
        "/v2/auth/signup",
        {"email": "1", "password": "1", "username": "1"},
    ),
    "create_bug": ("post", "/v2/bugs", {"url": "1", "title": "1", "description": "1"}),
    "update_bug": ("patch", "/v2/bugs/1", {}),
    "create_user": (
        "post",
        "/v2/users",
        {"username": "1", "email": "1", "password": "1"},
    ),
    "create_job": (
        "post",
        "/v2/jobs",
        {"title": "1", "description": "1", "company": "1"},
    ),
    "update_job": ("patch", "/v2/jobs/1", {}),
    "record_job_view": ("post", "/v2/jobs/1/view", {}),
    "create_hackathon": ("post", "/v2/hackathons", {"name": "1", "description": "1"}),
    "update_hackathon": ("patch", "/v2/hackathons/1", {}),
    "register_hackathon_participant": (
        "post",
        "/v2/hackathons/1/register",
        {"user_id": "1"},
    ),
}


def test_v2_request_table_covers_every_v2_write_tool():
    assert set(V2_REQUESTS) == set(V2_WRITE_TOOLS)


@pytest.mark.parametrize("tool", V2_WRITE_TOOLS)
async def test_v2_confirmed_request_method_path_and_payload(tool, http):
    method, path, fields = V2_REQUESTS[tool]
    args = {**_minimal_args((await _schemas())[tool]), "confirmed": True}
    await mcp.call_tool(tool, args)
    call = getattr(http, method).await_args
    assert call.args[0] == path
    body = call.kwargs["json"]
    assert fields.items() <= body.items()
    assert "confirmed" not in body
    assert body["metadata"]["ai_generated"] is True
    assert call.kwargs["headers"]["X-AI-Generated"] == "true"


@pytest.mark.parametrize("tool", V2_WRITE_TOOLS)
async def test_v2_http_error_is_reported_not_swallowed(tool, http):
    http.post.return_value.raise_for_status.side_effect = RuntimeError("500 from API")
    http.patch.return_value.raise_for_status.side_effect = RuntimeError("500 from API")
    args = {**_minimal_args((await _schemas())[tool]), "confirmed": True}
    with pytest.raises(Exception, match="500 from API"):
        await mcp.call_tool(tool, args)
