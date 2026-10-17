"""
Unit tests for BLT-Byte – non-AI helper functions that don't require the
Cloudflare Workers runtime.
"""
import json
import sys
import os

import pytest

# Make src importable without installing as a package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import only the pure-Python helpers (no runtime deps needed)
from main import (
    FAQ_CONTEXT,
    MCP_MANIFEST,
    SCAN_SYSTEM_PROMPT,
    _get_onboarding_guide,
    cors_headers,
)


# ---------------------------------------------------------------------------
# cors_headers
# ---------------------------------------------------------------------------
class TestCorsHeaders:
    def test_returns_dict(self):
        headers = cors_headers()
        assert isinstance(headers, dict)

    def test_allow_origin_wildcard(self):
        assert cors_headers()["Access-Control-Allow-Origin"] == "*"

    def test_contains_methods_and_headers(self):
        h = cors_headers()
        assert "GET" in h["Access-Control-Allow-Methods"]
        assert "POST" in h["Access-Control-Allow-Methods"]
        assert "Content-Type" in h["Access-Control-Allow-Headers"]


# ---------------------------------------------------------------------------
# _get_onboarding_guide
# ---------------------------------------------------------------------------
class TestGetOnboardingGuide:
    def test_contributor_guide(self):
        guide = _get_onboarding_guide("contributor")
        assert guide["role"] == "contributor"
        assert isinstance(guide["steps"], list)
        assert len(guide["steps"]) > 0
        assert "resources" in guide

    def test_bug_hunter_guide(self):
        guide = _get_onboarding_guide("bug_hunter")
        assert guide["role"] == "bug_hunter"
        assert isinstance(guide["steps"], list)
        # Must mention the platform URL
        all_text = " ".join(guide["steps"])
        assert "blt.owasp.org" in all_text.lower()

    def test_organisation_guide(self):
        guide = _get_onboarding_guide("organisation")
        assert guide["role"] == "organisation"
        assert isinstance(guide["steps"], list)

    def test_unknown_role_returns_error(self):
        guide = _get_onboarding_guide("unknown_role")
        assert "error" in guide
        assert "unknown_role" in guide["error"]

    def test_all_valid_roles_return_steps(self):
        for role in ("contributor", "bug_hunter", "organisation"):
            guide = _get_onboarding_guide(role)
            assert "steps" in guide, f"Missing 'steps' for role={role}"
            assert len(guide["steps"]) >= 4, f"Too few steps for role={role}"


# ---------------------------------------------------------------------------
# MCP_MANIFEST structure
# ---------------------------------------------------------------------------
class TestMcpManifest:
    def test_has_required_fields(self):
        assert "name" in MCP_MANIFEST
        assert "tools" in MCP_MANIFEST
        assert "schema_version" in MCP_MANIFEST

    def test_tools_is_list(self):
        assert isinstance(MCP_MANIFEST["tools"], list)

    def test_tool_names(self):
        names = {t["name"] for t in MCP_MANIFEST["tools"]}
        assert "chat" in names
        assert "scan_url" in names
        assert "get_onboarding_guide" in names

    def test_each_tool_has_parameters(self):
        for tool in MCP_MANIFEST["tools"]:
            assert "parameters" in tool, f"Tool '{tool['name']}' missing 'parameters'"
            assert "properties" in tool["parameters"], (
                f"Tool '{tool['name']}' parameters missing 'properties'"
            )

    def test_manifest_is_json_serialisable(self):
        # Must not raise
        serialised = json.dumps(MCP_MANIFEST)
        parsed = json.loads(serialised)
        assert parsed["name"] == MCP_MANIFEST["name"]


# ---------------------------------------------------------------------------
# FAQ_CONTEXT and SCAN_SYSTEM_PROMPT content sanity
# ---------------------------------------------------------------------------
class TestPromptContent:
    def test_faq_context_mentions_blt(self):
        assert "BLT" in FAQ_CONTEXT or "blt" in FAQ_CONTEXT.lower()

    def test_faq_context_mentions_onboarding(self):
        lower = FAQ_CONTEXT.lower()
        assert "onboarding" in lower or "contributing" in lower or "fork" in lower

    def test_faq_context_mentions_gsoc(self):
        lower = FAQ_CONTEXT.lower()
        assert "gsoc" in lower or "google summer of code" in lower

    def test_faq_context_mentions_owasp_blt_url(self):
        assert "blt.owasp.org" in FAQ_CONTEXT

    def test_faq_context_no_bugheist(self):
        assert "bugheist" not in FAQ_CONTEXT.lower()

    def test_scan_prompt_mentions_owasp(self):
        assert "OWASP" in SCAN_SYSTEM_PROMPT or "security" in SCAN_SYSTEM_PROMPT.lower()

    def test_scan_prompt_requests_json(self):
        assert "JSON" in SCAN_SYSTEM_PROMPT or "json" in SCAN_SYSTEM_PROMPT.lower()
