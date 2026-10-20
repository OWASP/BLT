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
    REPRO_EXTRACTED,
    REPRO_INSUFFICIENT,
    REPRO_MISSING,
    REPRO_UNKNOWN,
    TriageSummary,
    build_triage_messages,
    estimate_tokens,
    extract_repro_steps,
    resolve_repro_result,
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
            report = "SSRF report: connect to the internal host on port 8080 via the fetch endpoint."
            result = await summarize(report, env, db, do_stub, "evt-006")

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


# ---------------------------------------------------------------------------
# Tests: Repro-step extractor (explicit states, no fabrication)
# ---------------------------------------------------------------------------

NUMBERED_REPORT = (
    "Stored XSS in comments.\n"
    "1. Log in as any user\n"
    "2. Open the comments page\n"
    "3. Submit a comment containing a script tag\n"
    "Expected: the tag is escaped."
)
BULLETED_REPORT = (
    "Stored XSS in comments.\n"
    "- Log in as any user\n"
    "- Open the comments page\n"
    "- Submit a comment containing a script tag\n"
)
NO_STEPS_REPORT = "The login form seems to be vulnerable to SQL injection."
VAGUE_REPORT = "Login is broken for some inputs. Just try the login page with weird characters."


def _llm_json(**overrides):
    base = {
        "executive_summary": "Summary.",
        "reviewer_pack": "Details.",
        "cwe_hints": ["CWE-79"],
        "repro_steps": [],
        "repro_status": "missing",
        "confidence": 0.8,
    }
    base.update(overrides)
    return json.dumps(base)


async def _run_summarize(report: str, llm_response: str, event_id: str = "evt-r"):
    db = _make_mock_db(status="redaction_passed")
    with patch("src.summarizer.call_llm", new_callable=AsyncMock, return_value=llm_response):
        result = await summarize(report, _make_mock_env(), db, _make_mock_do_stub(), event_id)
    return result, db


class TestReproStepExtractor:
    """Repro steps are extracted faithfully; absence is explicit and never invented."""

    def test_prompt_forbids_fabrication_and_declares_status(self):
        system = build_triage_messages("report")[0]["content"]
        assert "repro_status" in system
        assert "NEVER invent" in system

    @pytest.mark.asyncio
    async def test_explicit_numbered_steps_extracted(self):
        steps = ["Log in as any user", "Open the comments page", "Submit a comment containing a script tag"]
        result, _ = await _run_summarize(NUMBERED_REPORT, _llm_json(repro_steps=steps, repro_status="extracted"))
        assert result.repro_status == REPRO_EXTRACTED
        assert result.repro_steps == steps  # order preserved

    @pytest.mark.asyncio
    async def test_bulleted_steps_extracted(self):
        steps = ["Log in as any user", "Open the comments page", "Submit a comment containing a script tag"]
        result, _ = await _run_summarize(BULLETED_REPORT, _llm_json(repro_steps=steps, repro_status="extracted"))
        assert result.repro_status == REPRO_EXTRACTED
        assert result.repro_steps == steps

    @pytest.mark.asyncio
    async def test_no_steps_reported_as_missing(self):
        result, _ = await _run_summarize(NO_STEPS_REPORT, _llm_json())
        assert result.repro_status == REPRO_MISSING
        assert result.repro_steps == []

    @pytest.mark.asyncio
    async def test_vague_steps_reported_as_insufficient(self):
        result, _ = await _run_summarize(
            VAGUE_REPORT,
            _llm_json(repro_steps=["Try the login page with weird characters"], repro_status="insufficient"),
        )
        assert result.repro_status == REPRO_INSUFFICIENT
        assert result.repro_steps == ["Try the login page with weird characters"]

    @pytest.mark.asyncio
    async def test_bug_without_how_to_reproduce_is_not_extracted(self):
        report = "The export feature crashes the server and leaks a stack trace."
        result, _ = await _run_summarize(report, _llm_json(repro_status="missing"))
        assert result.repro_status == REPRO_MISSING
        assert result.repro_steps == []

    @pytest.mark.asyncio
    async def test_fabricated_steps_are_dropped(self):
        """Steps with no basis in the report must not survive, even if the model claims 'extracted'."""
        invented = ["Run sqlmap -u http://target --dump", "Download the database dump"]
        result, _ = await _run_summarize(NO_STEPS_REPORT, _llm_json(repro_steps=invented, repro_status="extracted"))
        assert result.repro_steps == []
        assert result.repro_status == REPRO_MISSING

    @pytest.mark.asyncio
    async def test_extracted_claim_without_steps_is_not_trusted(self):
        result, _ = await _run_summarize(NUMBERED_REPORT, _llm_json(repro_steps=[], repro_status="extracted"))
        assert result.repro_status == REPRO_MISSING

    @pytest.mark.asyncio
    async def test_legacy_response_without_status_is_derived(self):
        """Responses lacking repro_status (old schema) still work and get a derived status."""
        data = json.loads(_llm_json(repro_steps=["Open the comments page"]))
        del data["repro_status"]
        result, _ = await _run_summarize(NUMBERED_REPORT, json.dumps(data))
        assert result.repro_status == REPRO_EXTRACTED

    @pytest.mark.asyncio
    async def test_step_limit_applies(self):
        report = "\n".join(f"{i}. perform action number {i}" for i in range(1, 9))
        steps = [f"perform action number {i}" for i in range(1, 9)]
        result, _ = await _run_summarize(report, _llm_json(repro_steps=steps, repro_status="extracted"))
        assert len(result.repro_steps) == MAX_REPRO_STEPS

    @pytest.mark.asyncio
    async def test_status_persisted_to_d1(self):
        _, db = await _run_summarize(NO_STEPS_REPORT, _llm_json())
        stmt = db.prepare.return_value
        insert_bind = next(c.args for c in stmt.bind.call_args_list if len(c.args) == 11 and c.args[1] == "evt-r")
        assert REPRO_MISSING in insert_bind
        sqls = [c.args[0] for c in db.prepare.call_args_list]
        assert any("INSERT INTO triage_summaries" in q and "repro_status" in q for q in sqls)


class TestReproMalformedModelOutput:
    """Malformed model responses never yield fabricated steps."""

    @pytest.mark.parametrize(
        "response",
        [
            "not json at all",
            "",
            "[]",
            json.dumps({"executive_summary": "x"}),
            json.dumps({"executive_summary": "x", "cwe_hints": [], "confidence": 0.5, "repro_steps": "1. do a thing"}),
            json.dumps({"executive_summary": "x", "cwe_hints": [], "confidence": 0.5, "repro_steps": [1, {"a": "b"}]}),
            json.dumps({"executive_summary": "x", "cwe_hints": [], "confidence": 0.5, "repro_status": "definitely"}),
        ],
    )
    @pytest.mark.asyncio
    async def test_malformed_response_falls_back_with_unknown_status(self, response):
        result, _ = await _run_summarize(NUMBERED_REPORT, response)
        assert result.model_used == "fallback:truncation"
        assert result.repro_steps == []
        assert result.repro_status == REPRO_UNKNOWN

    @pytest.mark.asyncio
    async def test_llm_unavailable_status_is_unknown_not_missing(self):
        db = _make_mock_db(status="redaction_passed")
        with patch(
            "src.summarizer.call_llm",
            new_callable=AsyncMock,
            side_effect=LLMUnavailableError("down", providers_tried=["cf_ai"]),
        ):
            result = await summarize(NUMBERED_REPORT, _make_mock_env(), db, _make_mock_do_stub(), "evt-u")
        assert result.repro_status == REPRO_UNKNOWN
        assert result.repro_steps == []

    def test_validate_rejects_unknown_status(self):
        ok, errs = validate_triage_output(
            {"executive_summary": "s", "cwe_hints": [], "confidence": 0.5, "repro_status": "bogus"}
        )
        assert ok is False
        assert any("repro_status" in e for e in errs)

    def test_validate_accepts_absent_status(self):
        ok, _ = validate_triage_output({"executive_summary": "s", "cwe_hints": [], "confidence": 0.5})
        assert ok is True

    def test_resolve_skips_blank_and_non_string_steps(self):
        steps, status = resolve_repro_result(["", "   ", None, 5], "extracted", "anything here")
        assert steps == []
        assert status == REPRO_MISSING


class TestExistingSummarizationCompatible:
    @pytest.mark.asyncio
    async def test_existing_fields_unchanged_and_default_status(self):
        report = "Login endpoint: navigate to /login and enter a quote in the username field."
        result, _ = await _run_summarize(report, VALID_LLM_RESPONSE)
        assert result.executive_summary == "SQL injection vulnerability found in the login endpoint."
        assert result.cwe_hints == ["CWE-89"]
        assert result.confidence == 0.85
        assert result.repro_status == REPRO_EXTRACTED

    def test_summary_constructible_without_status(self):
        summary = TriageSummary("e", "s", "r", [], [], 0.5, "m", {})
        assert summary.repro_status == REPRO_UNKNOWN
