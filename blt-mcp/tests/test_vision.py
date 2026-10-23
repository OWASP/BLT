"""
Unit Tests for the `draft_vision_issue` prompt, response parsing and tool wiring.

Test Scenarios:
- Prompt contract: plain-text, two-field, no-Markdown and no-issue fallback instructions.
- Valid output: parsed into the canonical `TITLE:`/`DESCRIPTION:` text, whitespace and punctuation preserved.
- Malformed output: every case is rejected with `ValueError` rather than repaired into a fake bug.
- Tool wiring: the Cloudflare response is mocked (no network) and failures surface as a controlled `RuntimeError`.
- TUI contract: the canonical output is consumed by a line parser equivalent to the one in `blt-cli`.
"""

import pytest

from blt_mcp import server
from blt_mcp.vision import (
    NO_ISSUE_DESCRIPTION,
    NO_ISSUE_TITLE,
    build_vision_prompt,
    parse_vision_response,
)


def test_prompt_contract():
    prompt = build_vision_prompt()
    assert "plain text only, not Markdown" in prompt
    for banned in ("headings", "backticks", "code fences", "HTML tags"):
        assert banned in prompt
    assert prompt.index("TITLE: <") < prompt.index("DESCRIPTION: <")
    assert "exactly once" in prompt
    assert "any other fields" in prompt
    assert "Never invent" in prompt
    assert f"TITLE: {NO_ISSUE_TITLE}\nDESCRIPTION: {NO_ISSUE_DESCRIPTION}" in prompt


def test_prompt_appends_context_only_when_given():
    assert "Additional user context" not in build_vision_prompt("   ")
    assert (
        "Additional user context about this image:\nlogin page"
        in build_vision_prompt("login page")
    )


def test_parse_valid_response():
    raw = "\n  TITLE:  Button text overflows its container  \nDESCRIPTION: The 'Submit' label (bottom right) is clipped, e.g. at 200% zoom.  \n"
    assert parse_vision_response(raw) == (
        "TITLE: Button text overflows its container\n"
        "DESCRIPTION: The 'Submit' label (bottom right) is clipped, e.g. at 200% zoom."
    )


def test_parse_multiline_description_preserved():
    raw = "TITLE: Broken layout\nDESCRIPTION: Header overlaps the menu.\nThe footer is also cut off."
    assert parse_vision_response(raw) == (
        "TITLE: Broken layout\n"
        "DESCRIPTION: Header overlaps the menu.\nThe footer is also cut off."
    )


def test_parse_tolerates_fence_and_bold_markers():
    raw = (
        "```\n**TITLE:** Broken layout\n**DESCRIPTION:** Header overlaps the menu.\n```"
    )
    assert parse_vision_response(raw) == (
        "TITLE: Broken layout\nDESCRIPTION: Header overlaps the menu."
    )


def test_parse_no_issue_fallback():
    raw = f"TITLE: {NO_ISSUE_TITLE}\nDESCRIPTION: {NO_ISSUE_DESCRIPTION}"
    assert parse_vision_response(raw) == raw


@pytest.mark.parametrize(
    "raw",
    [
        "DESCRIPTION: Only a description.",
        "TITLE: Only a title",
        "TITLE:\nDESCRIPTION: Something is wrong.",
        "TITLE: A title\nDESCRIPTION:   ",
        "DESCRIPTION: Something is wrong.\nTITLE: A title",
        "TITLE: One\nDESCRIPTION: Two\nTITLE: Three",
        "TITLE: One\nDESCRIPTION: Two\nDESCRIPTION: Three",
        "Here is the analysis:\nTITLE: One\nDESCRIPTION: Two",
        "The page shows a TITLE: and DESCRIPTION: somewhere inline.",
        "TITLE: One\nextra line\nDESCRIPTION: Two",
        "",
        "   \n\t ",
        None,
        {"unexpected": "structure"},
    ],
)
def test_parse_rejects_malformed(raw):
    with pytest.raises(ValueError):
        parse_vision_response(raw)


def _tui_parse(text: str) -> tuple[str, str]:
    """Mirror of the VisionDraftComplete line parser in blt-cli/src/tui/mod.rs."""
    title, description, in_desc = "", "", False
    for line in text.splitlines():
        upper = line.upper()
        if upper.startswith("TITLE:"):
            title = line[len("TITLE:") :].strip()
        elif upper.startswith("DESCRIPTION:"):
            in_desc = True
            description = line[len("DESCRIPTION:") :].strip()
        elif in_desc:
            description += "\n" + line
    return title, description.strip()


def test_tui_contract_prefills_form_without_markdown():
    out = parse_vision_response(
        "```text\n**TITLE:** Overlapping modal\n**DESCRIPTION:** The modal covers the nav bar.\n```"
    )
    assert _tui_parse(out) == ("Overlapping modal", "The modal covers the nav bar.")


def test_tui_contract_no_issue_is_explicit_non_bug():
    out = parse_vision_response(
        f"TITLE: {NO_ISSUE_TITLE}\nDESCRIPTION: {NO_ISSUE_DESCRIPTION}"
    )
    assert _tui_parse(out) == (NO_ISSUE_TITLE, NO_ISSUE_DESCRIPTION)


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = "provider-secret-detail"

    def json(self):
        return self._payload


def _patch_client(monkeypatch, response):
    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers=None, json=None, timeout=None):
            _FakeClient.sent = json
            return response

    monkeypatch.setattr(server.httpx, "AsyncClient", _FakeClient)
    return _FakeClient


@pytest.fixture
def image_env(tmp_path, monkeypatch):
    image = tmp_path / "shot.png"
    image.write_bytes(b"\x89PNG")
    monkeypatch.setenv("BLT_APPROVED_ROOT", str(tmp_path))
    monkeypatch.setenv("CF_ACCOUNT_ID", "acct")
    monkeypatch.setenv("CF_API_TOKEN", "token")
    return str(image)


async def test_tool_returns_canonical_output(image_env, monkeypatch):
    client = _patch_client(
        monkeypatch,
        _FakeResponse(
            {
                "success": True,
                "result": {
                    "response": "TITLE: Clipped label\nDESCRIPTION: Text is cut off."
                },
            }
        ),
    )
    out = await server.draft_vision_issue(image_env, context="checkout page")
    assert out == "TITLE: Clipped label\nDESCRIPTION: Text is cut off."
    assert (
        "TITLE:" in client.sent["prompt"] and "checkout page" in client.sent["prompt"]
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"success": True, "result": {"response": "Looks like a bug to me."}},
        {"success": True, "result": {"response": ""}},
        {"success": True, "result": {}},
        {"success": True, "result": "not a dict"},
        {"success": True, "result": None},
    ],
)
async def test_tool_rejects_unusable_provider_output(image_env, monkeypatch, payload):
    _patch_client(monkeypatch, _FakeResponse(payload))
    with pytest.raises(RuntimeError, match="could not be parsed"):
        await server.draft_vision_issue(image_env)


async def test_tool_provider_error_does_not_leak_details(image_env, monkeypatch):
    _patch_client(monkeypatch, _FakeResponse({}, status_code=500))
    with pytest.raises(RuntimeError) as exc:
        await server.draft_vision_issue(image_env)
    assert "provider-secret-detail" not in str(exc.value)
