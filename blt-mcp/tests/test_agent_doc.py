"""
Keeps the tool reference in AGENT.md in step with the tools registered on the MCP server.

- `test_agent_doc_matches_registered_tools`: fails with one line per mismatch when AGENT.md and the
  registered tool schemas disagree (see `tests/agent_doc.py` for what is checked).
- The remaining tests feed the checker deliberately wrong documents and schemas to prove it reports drift.
"""

import copy
from pathlib import Path

import pytest

import blt_mcp.server  # noqa: F401  (registers the tools)
from blt_mcp.server_base import mcp
from tests import agent_doc

AGENT_MD = (Path(__file__).resolve().parent.parent / "AGENT.md").read_text()


@pytest.fixture
async def tools():
    return [
        {"name": t.name, "inputSchema": t.inputSchema} for t in await mcp.list_tools()
    ]


async def test_agent_doc_matches_registered_tools(tools):
    assert agent_doc.check(AGENT_MD, tools) == []


async def test_detects_undocumented_and_removed_tools(tools):
    fake = tools + [{"name": "brand_new_tool", "inputSchema": {"properties": {}}}]
    trimmed = AGENT_MD.replace(
        "### `summarize_issue_context`", "### `summarise_issue_context`"
    )
    problems = agent_doc.check(trimmed, fake)
    assert "brand_new_tool: registered tool is not documented in AGENT.md" in problems
    assert (
        "summarize_issue_context: registered tool is not documented in AGENT.md"
        in problems
    )
    assert "summarise_issue_context: documented tool is not registered" in problems


async def test_detects_renamed_argument(tools):
    stale = AGENT_MD.replace(
        "`steps_to_reproduce` (string, optional)", "`steps` (string, optional)"
    )
    problems = agent_doc.check(stale, tools)
    assert "submit_issue.steps: documented argument does not exist" in problems
    assert "submit_issue.steps_to_reproduce: argument is not documented" in problems


async def test_detects_required_type_and_default_mismatch(tools):
    stale = AGENT_MD.replace(
        "`title` (string, required): Title of the bug.",
        "`title` (string, optional): Title of the bug.",
    )
    stale = stale.replace(
        "`issue_id` (string, required): ID of the issue to summarize.",
        "`issue_id` (boolean, required): ID of the issue to summarize.",
    )
    stale = stale.replace(
        "(boolean, optional, default `false`)", "(boolean, optional, default `true`)", 1
    )
    problems = agent_doc.check(stale, tools)
    assert (
        "submit_issue.title: documented as optional but schema says required"
        in problems
    )
    assert (
        "summarize_issue_context.issue_id: documented type 'boolean' but schema type is 'string'"
        in problems
    )
    assert any(
        p.startswith("submit_issue.confirmed: documented default") for p in problems
    )


async def test_detects_v2_list_drift(tools):
    stale = AGENT_MD.replace(
        "`create_bug(url, title, description, repo_id?, labels?, assignee?)`",
        "`create_bug(url, title, description, repo_id, labels?, severity?)`",
    )
    stale = stale.replace(
        "`auth_signin(email, password)` does not take `confirmed`.",
        "`auth_signin(email, password)`.",
    )
    problems = agent_doc.check(stale, tools)
    assert (
        "create_bug.repo_id: documented as required but schema says optional"
        in problems
    )
    assert "create_bug.severity: documented argument does not exist" in problems
    assert "create_bug.assignee: argument is not documented" in problems
    assert any(
        p.startswith("auth_signin: documented with `confirmed`") for p in problems
    )


async def test_detects_schema_change(tools):
    changed = copy.deepcopy(tools)
    schema = next(t for t in changed if t["name"] == "draft_vision_issue")[
        "inputSchema"
    ]
    schema["properties"]["style"] = {"type": "string"}
    assert "draft_vision_issue.style: argument is not documented" in agent_doc.check(
        AGENT_MD, changed
    )


async def test_detects_create_bug_url_drift(tools):
    dropped = AGENT_MD.replace("`create_bug(url, title,", "`create_bug(title,")
    assert "create_bug.url: argument is not documented" in agent_doc.check(
        dropped, tools
    )
    optional = AGENT_MD.replace("`create_bug(url, title,", "`create_bug(url?, title,")
    assert (
        "create_bug.url: documented as optional but schema says required"
        in agent_doc.check(optional, tools)
    )
