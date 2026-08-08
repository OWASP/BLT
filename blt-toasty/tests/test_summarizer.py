"""
Tests for the Token-Optimized Triage Summarizer.

Covers:
    1. Schema compliance — LLM returns valid JSON → TriageSummary correct
    2. Token budget enforcement — 2000-word report truncated to ≤ 1200 tokens
    3. CWE validation — hallucinated CWE-99999 replaced with CWE-UNKNOWN
    4. CWE validation — valid CWE-89 kept as-is
    5. Repro step re-redaction — IP address in repro step redacted
    6. LLM fallback — both providers fail → first 150 words used
    7. State transition — D1 status = "summarized" after success
    8. Guard blocks non-redacted events → StateTransitionError
    9. Sentence-boundary truncation — truncated text ends cleanly
    10. Repro step extraction — curl commands extracted
    11. Repro step limit — max 5 steps enforced
    12. Executive summary word limit — over-long summary trimmed
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.errors import LLMUnavailableError, StateTransitionError
from src.summarizer import (
    MAX_EXECUTIVE_WORDS,
    MAX_INPUT_TOKENS,
    MAX_REPRO_STEPS,
    TriageSummary,
    build_triage_messages,
    estimate_tokens,
    extract_repro_steps,
    sanitize_cwe_hints,
    summarize,
    truncate_to_token_budget,
    validate_triage_output,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_LLM_RESPONSE = json.dumps(
    {
        "executive_summary": "SQL injection vulnerability found in the login endpoint.",
        "reviewer_pack": "The application fails to sanitize user input in the login form.",
        "cwe_hints": ["CWE-89"],
        "repro_steps": ["Navigate to /login", "Enter ' OR 1=1 -- in username field"],
        "confidence": 0.85,
    }
)


def _make_mock_db(*, status="redaction_passed"):
    """Create a mock D1 database handle (D1 prepare/bind API).

    Returns a status row for SELECT queries and records all prepare() calls.
    """
    from tests.utils import make_d1_mock

    first_return = {"status": status} if status else None
    return make_d1_mock(first_return=first_return)


def _make_mock_env():
    """Create a mock Cloudflare Worker env."""
    env = MagicMock()
    return env


def _make_mock_do_stub():
    """Create a mock Durable Object stub (from test_llm_router.py pattern)."""

    class MockDOStorage:
        def __init__(self):
            self._store: dict[str, str] = {}

        async def get(self, key: str):
            return self._store.get(key)

        async def put(self, key: str, value: str):
            self._store[key] = value

    class MockDOStub:
        def __init__(self):
            self.storage = MockDOStorage()

    return MockDOStub()


# ---------------------------------------------------------------------------
# Tests: Token estimation and truncation
# ---------------------------------------------------------------------------


class TestEstimateTokens:
    """Tests for the estimate_tokens function."""

    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_whitespace_only(self):
        assert estimate_tokens("   ") == 0

    def test_single_word(self):
        result = estimate_tokens("hello")
        assert result >= 1

    def test_proportional_to_word_count(self):
        short = estimate_tokens("hello world")
        long = estimate_tokens("hello world this is a longer sentence")
        assert long > short


class TestTruncateToTokenBudget:
    """Tests for the truncate_to_token_budget function."""

    def test_short_text_unchanged(self):
        text = "This is short."
        result = truncate_to_token_budget(text, 100)
        assert result == text

    def test_long_text_truncated(self):
        words = ["word"] * 2000
        text = " ".join(words)
        result = truncate_to_token_budget(text, 50)
        assert estimate_tokens(result) <= 50 + 5  # small tolerance

    def test_empty_text(self):
        assert truncate_to_token_budget("", 100) == ""

    def test_sentence_boundary_preserved(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
        result = truncate_to_token_budget(text, 5)
        # Should break at a sentence boundary when possible.
        assert result.endswith(".") or len(result.split()) <= 5


# ---------------------------------------------------------------------------
# Tests: Prompt assembly
# ---------------------------------------------------------------------------


class TestBuildTriageMessages:
    """Tests for the build_triage_messages function."""

    def test_returns_system_and_user_messages(self):
        messages = build_triage_messages("Some report text")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_report_text_in_user_message(self):
        messages = build_triage_messages("SQL injection in login")
        assert "SQL injection in login" in messages[1]["content"]

    def test_duplicate_snippets_included(self):
        messages = build_triage_messages("Main report", ["Dup 1", "Dup 2"])
        assert "DUPLICATE_CONTEXT" in messages[1]["content"]
        assert "Dup 1" in messages[1]["content"]

    def test_token_budget_enforced_on_large_report(self):
        # Generate a report with ~2000 words → should be truncated to 550 tokens max.
        large_report = " ".join(["vulnerability"] * 2000)
        messages = build_triage_messages(large_report)

        user_content = messages[1]["content"]
        total_tokens = estimate_tokens(messages[0]["content"]) + estimate_tokens(user_content)
        assert total_tokens <= MAX_INPUT_TOKENS + 50  # tolerance for rounding


# ---------------------------------------------------------------------------
# Tests: Output validation
# ---------------------------------------------------------------------------


class TestValidateTriageOutput:
    """Tests for the validate_triage_output function."""

    def test_valid_output_passes(self):
        data = {
            "executive_summary": "SQL injection found.",
            "reviewer_pack": "Details here.",
            "cwe_hints": ["CWE-89"],
            "repro_steps": ["step 1"],
            "confidence": 0.85,
        }
        is_valid, errors = validate_triage_output(data)
        assert is_valid is True
        assert errors == []

    def test_missing_executive_summary_fails(self):
        data = {"cwe_hints": ["CWE-89"], "confidence": 0.5}
        is_valid, errors = validate_triage_output(data)
        assert is_valid is False
        assert any("executive_summary" in e for e in errors)

    def test_confidence_out_of_range_fails(self):
        data = {
            "executive_summary": "Summary.",
            "cwe_hints": ["CWE-89"],
            "confidence": 1.5,
        }
        is_valid, errors = validate_triage_output(data)
        assert is_valid is False
        assert any("confidence" in e for e in errors)

    def test_invalid_cwe_format_fails(self):
        data = {
            "executive_summary": "Summary.",
            "cwe_hints": ["not-a-cwe"],
            "confidence": 0.5,
        }
        is_valid, errors = validate_triage_output(data)
        assert is_valid is False
        assert any("cwe_hints" in e for e in errors)


# ---------------------------------------------------------------------------
# Tests: CWE sanitization
# ---------------------------------------------------------------------------


class TestSanitizeCweHints:
    """Tests for the sanitize_cwe_hints function."""

    def test_valid_cwe_kept(self):
        result = sanitize_cwe_hints(["CWE-89", "CWE-79"])
        assert result == ["CWE-89", "CWE-79"]

    def test_hallucinated_cwe_replaced(self):
        result = sanitize_cwe_hints(["CWE-99999"])
        assert result == ["CWE-UNKNOWN"]

    def test_mixed_valid_and_invalid(self):
        result = sanitize_cwe_hints(["CWE-89", "CWE-12345", "CWE-79"])
        assert result == ["CWE-89", "CWE-UNKNOWN", "CWE-79"]

    def test_cwe_unknown_passthrough(self):
        result = sanitize_cwe_hints(["CWE-UNKNOWN"])
        assert result == ["CWE-UNKNOWN"]

    def test_case_insensitive(self):
        result = sanitize_cwe_hints(["cwe-89"])
        assert result == ["CWE-89"]

    def test_empty_list(self):
        result = sanitize_cwe_hints([])
        assert result == []


# ---------------------------------------------------------------------------
# Tests: Repro step extraction
# ---------------------------------------------------------------------------


class TestExtractReproSteps:
    """Tests for the extract_repro_steps function."""

    def test_numbered_list(self):
        text = "1. Open the page\n2. Click submit\n3. Observe the error"
        steps = extract_repro_steps(text)
        assert len(steps) == 3
        assert "Open the page" in steps[0]

    def test_curl_command(self):
        text = "To reproduce:\ncurl -X POST https://example.com/api/login -d 'user=admin'"
        steps = extract_repro_steps(text)
        assert any("curl" in s.lower() for s in steps)

    def test_http_method(self):
        text = "Send a GET /api/users request to the server."
        steps = extract_repro_steps(text)
        assert any("GET" in s for s in steps)

    def test_max_five_steps(self):
        lines = "\n".join([f"{i}. Step {i}" for i in range(1, 11)])
        steps = extract_repro_steps(lines)
        assert len(steps) <= MAX_REPRO_STEPS

    def test_empty_text(self):
        assert extract_repro_steps("") == []

    def test_step_truncated_to_200_chars(self):
        text = "1. " + "A" * 300
        steps = extract_repro_steps(text)
        assert all(len(s) <= 200 for s in steps)


# ---------------------------------------------------------------------------
# Tests: Repro step re-redaction
# ---------------------------------------------------------------------------


class TestReproStepReRedaction:
    """Tests for PII re-redaction in reproduction steps."""

    def test_ip_address_redacted(self):
        from src.summarizer import _re_redact_repro_steps

        steps = ["Connect to 192.168.1.100 on port 8080"]
        redacted = _re_redact_repro_steps(steps)
        assert "192.168.1.100" not in redacted[0]
        assert "[IP_ADDRESS]" in redacted[0]

    def test_email_redacted(self):
        from src.summarizer import _re_redact_repro_steps

        steps = ["Send payload to admin@example.com"]
        redacted = _re_redact_repro_steps(steps)
        assert "admin@example.com" not in redacted[0]
        assert "[EMAIL_ADDRESS]" in redacted[0]


# ---------------------------------------------------------------------------
# Tests: Full summarize() pipeline
# ---------------------------------------------------------------------------


class TestSummarize:
    """Integration tests for the summarize function."""

    @pytest.mark.asyncio
    async def test_schema_compliance(self):
        """Mock LLM returns valid JSON → TriageSummary has all correct fields."""
        db = _make_mock_db(status="redaction_passed")
        env = _make_mock_env()
        do_stub = _make_mock_do_stub()

        with patch("src.summarizer.call_llm", new_callable=AsyncMock, return_value=VALID_LLM_RESPONSE):
            result = await summarize("Redacted report text", env, db, do_stub, "evt-001")

        assert isinstance(result, TriageSummary)
        assert result.event_id == "evt-001"
        assert result.executive_summary == "SQL injection vulnerability found in the login endpoint."
        assert result.cwe_hints == ["CWE-89"]
        assert result.confidence == 0.85
        assert "prompt_tokens" in result.token_usage

    @pytest.mark.asyncio
    async def test_state_transition_to_summarized(self):
        """After successful summarize(), D1 status transitions to 'summarized'."""
        db = _make_mock_db(status="redaction_passed")
        env = _make_mock_env()
        do_stub = _make_mock_do_stub()

        with patch("src.summarizer.call_llm", new_callable=AsyncMock, return_value=VALID_LLM_RESPONSE):
            await summarize("Report text", env, db, do_stub, "evt-002")

        # The state UPDATE is done via prepare(sql).bind("summarized", event_id).run()
        stmt = db.prepare.return_value
        bind_args = [str(call) for call in stmt.bind.call_args_list]
        assert any("summarized" in a for a in bind_args)

    @pytest.mark.asyncio
    async def test_guard_blocks_non_redacted_event(self):
        """summarize() must raise StateTransitionError if event is not redaction_passed."""
        db = _make_mock_db(status="pending")
        env = _make_mock_env()
        do_stub = _make_mock_do_stub()

        with pytest.raises(StateTransitionError):
            await summarize("Report text", env, db, do_stub, "evt-003")

    @pytest.mark.asyncio
    async def test_llm_fallback_summary(self):
        """When both LLM providers fail, a truncation-based fallback is returned."""
        db = _make_mock_db(status="redaction_passed")
        env = _make_mock_env()
        do_stub = _make_mock_do_stub()

        with patch(
            "src.summarizer.call_llm",
            new_callable=AsyncMock,
            side_effect=LLMUnavailableError("all down", providers_tried=["cf_ai", "openai"]),
        ):
            result = await summarize("This is the redacted report text.", env, db, do_stub, "evt-004")

        assert result.model_used == "fallback:truncation"
        assert result.confidence == 0.0
        assert result.cwe_hints == []
        assert "This is the redacted report text." in result.executive_summary

    @pytest.mark.asyncio
    async def test_cwe_sanitization_in_pipeline(self):
        """Hallucinated CWEs are replaced with CWE-UNKNOWN in the full pipeline."""
        response = json.dumps(
            {
                "executive_summary": "XSS vulnerability.",
                "reviewer_pack": "Details.",
                "cwe_hints": ["CWE-79", "CWE-99999"],
                "repro_steps": [],
                "confidence": 0.7,
            }
        )

        db = _make_mock_db(status="redaction_passed")
        env = _make_mock_env()
        do_stub = _make_mock_do_stub()

        with patch("src.summarizer.call_llm", new_callable=AsyncMock, return_value=response):
            result = await summarize("XSS report", env, db, do_stub, "evt-005")

        assert result.cwe_hints == ["CWE-79", "CWE-UNKNOWN"]

    @pytest.mark.asyncio
    async def test_repro_steps_re_redacted_in_pipeline(self):
        """Repro steps containing PII are re-redacted before storage."""
        response = json.dumps(
            {
                "executive_summary": "SSRF found.",
                "reviewer_pack": "Details.",
                "cwe_hints": ["CWE-918"],
                "repro_steps": ["Connect to 10.0.0.50 on port 8080"],
                "confidence": 0.9,
            }
        )

        db = _make_mock_db(status="redaction_passed")
        env = _make_mock_env()
        do_stub = _make_mock_do_stub()

        with patch("src.summarizer.call_llm", new_callable=AsyncMock, return_value=response):
            result = await summarize("SSRF report", env, db, do_stub, "evt-006")

        assert "10.0.0.50" not in result.repro_steps[0]
        assert "[IP_ADDRESS]" in result.repro_steps[0]

    @pytest.mark.asyncio
    async def test_non_json_response_triggers_fallback(self):
        """If the LLM returns non-JSON, fallback summary should be used."""
        db = _make_mock_db(status="redaction_passed")
        env = _make_mock_env()
        do_stub = _make_mock_do_stub()

        with patch(
            "src.summarizer.call_llm",
            new_callable=AsyncMock,
            return_value="This is not JSON at all.",
        ):
            result = await summarize("Report text here", env, db, do_stub, "evt-007")

        assert result.model_used == "fallback:truncation"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_executive_summary_word_limit_enforced(self):
        """Over-long executive summary from LLM is trimmed to MAX_EXECUTIVE_WORDS."""
        long_summary = " ".join(["word"] * 300)
        response = json.dumps(
            {
                "executive_summary": long_summary,
                "reviewer_pack": "Short.",
                "cwe_hints": ["CWE-79"],
                "repro_steps": [],
                "confidence": 0.8,
            }
        )

        db = _make_mock_db(status="redaction_passed")
        env = _make_mock_env()
        do_stub = _make_mock_do_stub()

        with patch("src.summarizer.call_llm", new_callable=AsyncMock, return_value=response):
            result = await summarize("Report", env, db, do_stub, "evt-008")

        assert len(result.executive_summary.split()) <= MAX_EXECUTIVE_WORDS

    @pytest.mark.asyncio
    async def test_d1_insert_called(self):
        """Verify the INSERT into triage_summaries is actually executed."""
        db = _make_mock_db(status="redaction_passed")
        env = _make_mock_env()
        do_stub = _make_mock_do_stub()

        with patch("src.summarizer.call_llm", new_callable=AsyncMock, return_value=VALID_LLM_RESPONSE):
            await summarize("Report", env, db, do_stub, "evt-009")

        insert_calls = [str(c) for c in db.prepare.call_args_list if "INSERT INTO triage_summaries" in str(c)]
        assert len(insert_calls) >= 1
