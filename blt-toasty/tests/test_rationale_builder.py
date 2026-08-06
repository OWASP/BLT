"""Tests for src/rationale_builder.py (Issue #10 — Label Rationale API).

Coverage targets
----------------
* ``build_cwe_rationale`` — keyword extraction, PII safety gate, empty text guard
* ``build_duplicate_rationale`` — maps DuplicateDetectionResult fields; None cases
* ``build_confidence_trace`` — geometric mean; zero score clamping; None components
* ``audit_completeness_check`` — all pass / individual misses / zero-count redaction
* ``store_rationale`` — correct SQL; idempotent REPLACE; NULL dup_rationale
* Route handler ``handle_rationale`` (via tests/test_worker.py pattern) — 200, 424, 404, 405
"""

from __future__ import annotations

import dataclasses
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.errors import AuditIncompleteError
from src.rationale_builder import (
    MAX_EVIDENCE_SNIPPETS,
    MAX_SNIPPET_CHARS,
    CWERationale,
    _extract_snippets_for_cwe,
    _is_pii_free,
    audit_completeness_check,
    build_confidence_trace,
    build_cwe_rationale,
    build_duplicate_rationale,
    store_rationale,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_db(
    *,
    has_summary: bool = True,
    has_rationale: bool = True,
    audit_count: int = 1,
    rationale_row: dict | None = None,
) -> MagicMock:
    """Build a mock D1 database handle for testing (D1 prepare/bind API)."""

    def make_stmt(first_val):
        mock_run = MagicMock()
        mock_run.meta = MagicMock()
        mock_run.meta.changes = 1
        stmt = MagicMock()
        stmt.bind = MagicMock(return_value=stmt)
        stmt.first = AsyncMock(return_value=first_val)
        stmt.run = AsyncMock(return_value=mock_run)
        stmt.all = AsyncMock(return_value=MagicMock(results=[]))
        return stmt

    def prepare_side_effect(sql: str):
        sql_lower = sql.strip().lower()
        if "triage_summaries" in sql_lower and "select id" in sql_lower:
            first_val = {"id": "sum-001"} if has_summary else None
        elif "triage_rationale" in sql_lower and "select id" in sql_lower:
            first_val = {"id": "rat-001"} if has_rationale else None
        elif "count(*) as cnt" in sql_lower and "redaction_audit" in sql_lower:
            first_val = {"cnt": audit_count}
        elif "triage_rationale" in sql_lower:
            first_val = rationale_row
        else:
            first_val = None
        return make_stmt(first_val)

    db = MagicMock()
    db.prepare = MagicMock(side_effect=prepare_side_effect)
    return db


def _make_dup_result(
    *,
    event_id: str = "evt-old-001",
    similarity_score: float = 0.87,
    llm_confirmed: bool = False,
    llm_confidence: float | None = None,
    llm_rationale: str | None = None,
    detection_method: str = "retrieval_only",
) -> MagicMock:
    """Build a mock DuplicateDetectionResult."""
    candidate = MagicMock()
    candidate.event_id = event_id
    candidate.similarity_score = similarity_score
    candidate.llm_confirmed = llm_confirmed
    candidate.llm_confidence = llm_confidence
    candidate.llm_rationale = llm_rationale

    result = MagicMock()
    result.event_id = "evt-new-001"
    result.top_candidate = candidate
    result.detection_method = detection_method
    return result


# ---------------------------------------------------------------------------
# _is_pii_free
# ---------------------------------------------------------------------------


class TestIsPiiFree:
    def test_clean_text_passes(self):
        """Text with no PII returns True."""
        assert _is_pii_free("SELECT * FROM users WHERE active = 1") is True

    def test_email_detected(self):
        """Text containing an email address returns False."""
        assert _is_pii_free("Send results to user@example.com for review") is False

    def test_ip_address_detected(self):
        """Text containing an IP address returns False."""
        assert _is_pii_free("Request from 192.168.1.100 was blocked") is False

    def test_redacted_placeholder_passes(self):
        """A typed placeholder left by the redaction engine is safe."""
        assert _is_pii_free("Request from [IP_ADDRESS] was blocked") is True

    def test_empty_string_passes(self):
        """Empty string has no PII."""
        assert _is_pii_free("") is True


# ---------------------------------------------------------------------------
# _extract_snippets_for_cwe
# ---------------------------------------------------------------------------


class TestExtractSnippetsForCwe:
    def test_extracts_sql_keywords(self):
        """SQL keywords trigger snippet extraction for CWE-89."""
        text = "The attacker can inject: SELECT * FROM users WHERE id = 1 OR 1=1"
        snippets = _extract_snippets_for_cwe("CWE-89", text)
        assert len(snippets) >= 1
        assert all(isinstance(s, str) for s in snippets)

    def test_snippet_max_chars(self):
        """No snippet exceeds MAX_SNIPPET_CHARS characters."""
        long_text = "SELECT " + "x" * 500 + " FROM users"
        snippets = _extract_snippets_for_cwe("CWE-89", long_text)
        for snippet in snippets:
            assert len(snippet) <= MAX_SNIPPET_CHARS

    def test_max_evidence_snippets_cap(self):
        """At most MAX_EVIDENCE_SNIPPETS are returned."""
        # Repeat many SQL keywords to force multiple matches.
        text = " SELECT WHERE INSERT DELETE UPDATE SELECT WHERE INSERT DELETE UPDATE " * 10
        snippets = _extract_snippets_for_cwe("CWE-89", text)
        assert len(snippets) <= MAX_EVIDENCE_SNIPPETS

    def test_pii_tainted_snippet_dropped(self):
        """Snippets that contain PII are dropped."""
        # Inject a real IP next to the keyword so the PII gate fires.
        text = "SELECT * FROM users WHERE ip = 10.0.0.1"
        snippets = _extract_snippets_for_cwe("CWE-89", text)
        # All returned snippets must be PII-free.
        for snippet in snippets:
            assert _is_pii_free(snippet), f"PII found in snippet: {snippet!r}"

    def test_unknown_cwe_returns_empty(self):
        """CWE with no keyword list returns an empty snippet list."""
        snippets = _extract_snippets_for_cwe("CWE-UNKNOWN", "arbitrary text with no keywords")
        assert snippets == []

    def test_xss_keywords(self):
        """XSS keywords trigger snippet extraction for CWE-79."""
        text = "The page renders <script>alert(document.cookie)</script> without escaping"
        snippets = _extract_snippets_for_cwe("CWE-79", text)
        assert len(snippets) >= 1

    def test_no_duplicate_snippets(self):
        """Snippets from overlapping matches are deduplicated by window start."""
        text = "SELECT SELECT SELECT"
        snippets = _extract_snippets_for_cwe("CWE-89", text)
        # All snippets must be unique strings.
        assert len(snippets) == len(set(snippets))


# ---------------------------------------------------------------------------
# build_cwe_rationale
# ---------------------------------------------------------------------------


class TestBuildCweRationale:
    def test_basic_cwe89(self):
        """Returns one CWERationale with correct cwe_id and label."""
        text = "The endpoint accepts raw SQL: SELECT * FROM orders WHERE id=user_input"
        result = build_cwe_rationale(["CWE-89"], text, summary_confidence=0.9)
        assert len(result) == 1
        r = result[0]
        assert r.cwe_id == "CWE-89"
        assert r.label == "SQL Injection"
        assert isinstance(r.confidence, float)
        assert 0.0 <= r.confidence <= 1.0
        assert isinstance(r.reasoning, str)
        assert len(r.reasoning) > 0

    def test_multiple_cwes_returns_all(self):
        """Returns one record per CWE hint."""
        text = "XSS via <script> and also SELECT query injection"
        result = build_cwe_rationale(["CWE-79", "CWE-89"], text, summary_confidence=0.8)
        assert len(result) == 2
        ids = [r.cwe_id for r in result]
        assert "CWE-79" in ids
        assert "CWE-89" in ids

    def test_empty_redacted_text_raises(self):
        """Empty redacted_text raises ValueError."""
        with pytest.raises(ValueError, match="non-empty"):
            build_cwe_rationale(["CWE-89"], "", summary_confidence=0.8)

    def test_whitespace_only_raises(self):
        """Whitespace-only redacted_text raises ValueError."""
        with pytest.raises(ValueError, match="non-empty"):
            build_cwe_rationale(["CWE-89"], "   \n\t  ", summary_confidence=0.8)

    def test_empty_hints_returns_empty_list(self):
        """Empty cwe_hints returns an empty list without error."""
        result = build_cwe_rationale([], "some report text", summary_confidence=0.7)
        assert result == []

    def test_confidence_clamped(self):
        """Confidence is clamped to [0.0, 1.0]."""
        r1 = build_cwe_rationale(["CWE-20"], "input validation missing", summary_confidence=1.5)
        assert r1[0].confidence <= 1.0
        r2 = build_cwe_rationale(["CWE-20"], "input validation missing", summary_confidence=-0.5)
        assert r2[0].confidence >= 0.0

    def test_snippets_all_pii_free(self):
        """No returned snippet contains detectable PII."""
        text = (
            "SQL injection in login form. "
            "SELECT user FROM accounts WHERE name=[REDACTED_USERNAME] "
            "Reported by [EMAIL_ADDRESS]."
        )
        result = build_cwe_rationale(["CWE-89"], text, summary_confidence=0.85)
        for r in result:
            for snippet in r.evidence_snippets:
                assert _is_pii_free(snippet), f"PII in snippet: {snippet!r}"

    def test_unknown_cwe_label(self):
        """CWE-UNKNOWN gets the correct human-readable label."""
        result = build_cwe_rationale(["CWE-UNKNOWN"], "unclassified issue", summary_confidence=0.5)
        assert result[0].label == "Unknown / Unclassified"

    def test_reasoning_max_chars(self):
        """Reasoning string never exceeds MAX_REASONING_CHARS."""
        result = build_cwe_rationale(["CWE-89"], "SELECT * FROM x", summary_confidence=0.9)
        for r in result:
            assert len(r.reasoning) <= 300  # MAX_REASONING_CHARS


# ---------------------------------------------------------------------------
# build_duplicate_rationale
# ---------------------------------------------------------------------------


class TestBuildDuplicateRationale:
    def test_returns_none_when_dup_result_is_none(self):
        """None input returns None."""
        assert build_duplicate_rationale(None) is None

    def test_returns_none_for_no_duplicates(self):
        """no_duplicates method returns None."""
        dup = _make_dup_result(detection_method="no_duplicates")
        dup.top_candidate = None
        assert build_duplicate_rationale(dup) is None

    def test_maps_retrieval_only_candidate(self):
        """Retrieval-only candidate is mapped correctly."""
        dup = _make_dup_result(
            event_id="evt-prev",
            similarity_score=0.88,
            llm_confirmed=False,
            detection_method="retrieval_only",
        )
        result = build_duplicate_rationale(dup)
        assert result is not None
        assert result.top_candidate_event_id == "evt-prev"
        assert result.similarity_score == pytest.approx(0.88, abs=1e-4)
        assert result.llm_confirmed is False
        assert result.llm_confidence is None
        assert result.detection_method == "retrieval_only"

    def test_maps_llm_adjudicated_candidate(self):
        """LLM-adjudicated candidate includes llm_confidence and rationale."""
        dup = _make_dup_result(
            event_id="evt-prev-2",
            similarity_score=0.82,
            llm_confirmed=True,
            llm_confidence=0.91,
            llm_rationale="Both describe SQL injection in the login form.",
            detection_method="retrieval_plus_llm",
        )
        result = build_duplicate_rationale(dup)
        assert result is not None
        assert result.llm_confirmed is True
        assert result.llm_confidence == pytest.approx(0.91, abs=1e-4)
        assert result.llm_rationale == "Both describe SQL injection in the login form."

    def test_similarity_score_rounded(self):
        """Similarity score is rounded to 4 decimal places."""
        dup = _make_dup_result(similarity_score=0.876543210)
        result = build_duplicate_rationale(dup)
        assert result is not None
        assert result.similarity_score == pytest.approx(0.8765, abs=1e-4)


# ---------------------------------------------------------------------------
# build_confidence_trace
# ---------------------------------------------------------------------------


class TestBuildConfidenceTrace:
    def test_basic_geometric_mean(self):
        """Geometric mean of two equal scores is that score."""
        trace = build_confidence_trace(
            redaction_entity_count=3,
            redaction_confidence_min=0.9,
            summary_confidence=0.9,
        )
        assert trace.overall_triage_confidence == pytest.approx(0.9, abs=1e-4)
        assert trace.redaction_entity_count == 3

    def test_geometric_mean_with_dup(self):
        """Geometric mean includes dup similarity when present and confirmed."""
        dup = _make_dup_result(similarity_score=0.81, llm_confirmed=True)
        trace = build_confidence_trace(
            redaction_entity_count=2,
            redaction_confidence_min=1.0,
            summary_confidence=1.0,
            dup_result=dup,
        )
        # With scores [1.0, 1.0, 0.81], geometric mean = (0.81)^(1/3) ≈ 0.9325
        assert 0.92 < trace.overall_triage_confidence < 0.94

    def test_zero_score_clamps_overall_to_zero(self):
        """A zero component collapses overall_triage_confidence to 0."""
        trace = build_confidence_trace(
            redaction_entity_count=0,
            redaction_confidence_min=0.0,
            summary_confidence=0.9,
        )
        assert trace.overall_triage_confidence == 0.0

    def test_scores_clamped_to_unit_interval(self):
        """All scores are clamped to [0.0, 1.0]."""
        trace = build_confidence_trace(
            redaction_entity_count=1,
            redaction_confidence_min=1.5,  # over 1
            summary_confidence=-0.2,  # negative
        )
        assert trace.redaction_confidence_min <= 1.0
        assert trace.summary_confidence >= 0.0
        assert 0.0 <= trace.overall_triage_confidence <= 1.0

    def test_no_dup_result_leaves_dup_fields_none(self):
        """Without a dup_result, duplicate_similarity_score is None."""
        trace = build_confidence_trace(
            redaction_entity_count=5,
            redaction_confidence_min=0.97,
            summary_confidence=0.82,
        )
        assert trace.duplicate_similarity_score is None
        assert trace.llm_adjudication_confidence is None

    def test_dataclass_is_frozen(self):
        """ConfidenceTrace is immutable."""
        trace = build_confidence_trace(
            redaction_entity_count=1,
            redaction_confidence_min=0.99,
            summary_confidence=0.85,
        )
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            trace.summary_confidence = 0.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# audit_completeness_check
# ---------------------------------------------------------------------------


class TestAuditCompletenessCheck:
    @pytest.mark.asyncio
    async def test_returns_true_when_all_present(self):
        """Returns (True, []) when all three audit records exist."""
        db = _make_db(has_summary=True, has_rationale=True, audit_count=3)
        ok, missing = await audit_completeness_check("evt-001", db)
        assert ok is True
        assert missing == []

    @pytest.mark.asyncio
    async def test_missing_summary(self):
        """Returns (False, ['triage_summary']) when summary row absent."""
        db = _make_db(has_summary=False, has_rationale=True, audit_count=1)
        ok, missing = await audit_completeness_check("evt-001", db)
        assert ok is False
        assert "triage_summary" in missing

    @pytest.mark.asyncio
    async def test_missing_rationale(self):
        """Returns (False, ['triage_rationale']) when rationale row absent."""
        db = _make_db(has_summary=True, has_rationale=False, audit_count=1)
        ok, missing = await audit_completeness_check("evt-001", db)
        assert ok is False
        assert "triage_rationale" in missing

    @pytest.mark.asyncio
    async def test_zero_redaction_audit_rows(self):
        """Returns (False, ['redaction_audit']) when no audit entries exist."""
        db = _make_db(has_summary=True, has_rationale=True, audit_count=0)
        ok, missing = await audit_completeness_check("evt-001", db)
        assert ok is False
        assert "redaction_audit" in missing

    @pytest.mark.asyncio
    async def test_all_three_missing(self):
        """Returns all three field names when nothing is in D1."""
        db = _make_db(has_summary=False, has_rationale=False, audit_count=0)
        ok, missing = await audit_completeness_check("evt-001", db)
        assert ok is False
        assert set(missing) == {"triage_summary", "triage_rationale", "redaction_audit"}

    @pytest.mark.asyncio
    async def test_only_redaction_missing(self):
        """Returns exactly one field when only redaction_audit is absent."""
        db = _make_db(has_summary=True, has_rationale=True, audit_count=0)
        ok, missing = await audit_completeness_check("evt-001", db)
        assert ok is False
        assert missing == ["redaction_audit"]


# ---------------------------------------------------------------------------
# store_rationale
# ---------------------------------------------------------------------------


class TestStoreRationale:
    @pytest.mark.asyncio
    async def test_insert_called_with_correct_arity(self):
        """INSERT OR REPLACE is called with 5 positional params via bind."""
        from tests.utils import make_d1_mock

        db = make_d1_mock()
        cwe_r = [
            CWERationale(
                cwe_id="CWE-89",
                label="SQL Injection",
                evidence_snippets=["SELECT * FROM users"],
                confidence=0.9,
                reasoning="Report mentions raw SQL query.",
            )
        ]
        trace = build_confidence_trace(
            redaction_entity_count=2,
            redaction_confidence_min=0.99,
            summary_confidence=0.9,
        )
        await store_rationale(db, "evt-001", cwe_r, None, trace)

        # prepare() called with INSERT OR REPLACE sql; bind() receives 5 args
        stmt = db.prepare.return_value
        assert stmt.bind.called
        bind_args = stmt.bind.call_args[0]
        assert len(bind_args) == 5

    @pytest.mark.asyncio
    async def test_null_dup_rationale_stored_as_none(self):
        """None duplicate_rationale stores NULL (None) in D1 via bind 4th arg."""
        from tests.utils import make_d1_mock

        db = make_d1_mock()
        trace = build_confidence_trace(
            redaction_entity_count=0,
            redaction_confidence_min=1.0,
            summary_confidence=0.8,
        )
        await store_rationale(db, "evt-002", [], None, trace)

        stmt = db.prepare.return_value
        bind_args = stmt.bind.call_args[0]
        # bind_args: (id, triage_event_id, cwe_json, dup_json, trace_json) — index 3 is dup_json
        assert bind_args[3] is None

    @pytest.mark.asyncio
    async def test_cwe_rationale_serialised_as_json_array(self):
        """cwe_rationale param is a valid JSON array string."""
        from tests.utils import make_d1_mock

        db = make_d1_mock()
        cwe_r = [
            CWERationale(
                cwe_id="CWE-79",
                label="Cross-Site Scripting (XSS)",
                evidence_snippets=[],
                confidence=0.75,
                reasoning="Unescaped output detected.",
            )
        ]
        trace = build_confidence_trace(
            redaction_entity_count=1,
            redaction_confidence_min=0.99,
            summary_confidence=0.75,
        )
        await store_rationale(db, "evt-003", cwe_r, None, trace)

        stmt = db.prepare.return_value
        bind_args = stmt.bind.call_args[0]
        cwe_json = bind_args[2]
        parsed = json.loads(cwe_json)
        assert isinstance(parsed, list)
        assert parsed[0]["cwe_id"] == "CWE-79"

    @pytest.mark.asyncio
    async def test_uses_insert_or_replace(self):
        """SQL statement uses INSERT OR REPLACE for idempotency."""
        from tests.utils import make_d1_mock

        db = make_d1_mock()
        trace = build_confidence_trace(
            redaction_entity_count=0,
            redaction_confidence_min=1.0,
            summary_confidence=0.7,
        )
        await store_rationale(db, "evt-004", [], None, trace)

        sql = db.prepare.call_args[0][0]
        assert "INSERT OR REPLACE" in sql


class MockResponse:
    def __init__(self, body, status, headers=None):
        self._body = body
        self.status = status
        self.headers = headers

    async def text(self):
        return self._body

    @classmethod
    def new(cls, body, status=200, headers=None):
        return cls(body, status, headers)


# Mock Cloudflare Workers environment (js, pyodide) before importing worker
import sys  # noqa: E402

js_mock = MagicMock()
js_mock.Response = MockResponse
sys.modules["js"] = js_mock
sys.modules["pyodide"] = MagicMock()
sys.modules["pyodide.ffi"] = MagicMock()
from worker import handle_rationale  # noqa: E402


# ---------------------------------------------------------------------------
# handle_rationale
# ---------------------------------------------------------------------------


class TestHandleRationale:
    @pytest.mark.asyncio
    @patch("worker._authenticate_request", new_callable=AsyncMock, return_value=({"sub": "agent-test"}, None))
    async def test_returns_200_with_valid_json(self, _mock_auth):
        """Returns 200 with JSON payload when rationale exists."""
        req = AsyncMock()
        env = AsyncMock()

        # Valid JSON from the DB
        cwe_json = '[{"cwe_id": "CWE-79"}]'
        dup_json = '{"top_candidate_event_id": "evt-000"}'
        trace_json = '{"overall_confidence": 0.85}'
        db = _make_db(has_rationale=True, rationale_row=(cwe_json, dup_json, trace_json))
        env.DB = db

        resp = await handle_rationale(req, env, "evt-123")
        assert resp.status == 200

        body = json.loads(await resp.text())
        assert body["event_id"] == "evt-123"
        assert body["status"] == "complete"
        assert body["cwe_rationale"] == [{"cwe_id": "CWE-79"}]
        assert body["duplicate_rationale"] == {"top_candidate_event_id": "evt-000"}
        assert body["confidence_trace"] == {"overall_confidence": 0.85}

    @pytest.mark.asyncio
    @patch("worker._authenticate_request", new_callable=AsyncMock, return_value=({"sub": "agent-test"}, None))
    async def test_returns_200_with_null_duplicate_rationale(self, _mock_auth):
        """Handles cases where duplicate_rationale is NULL in the DB."""
        req = AsyncMock()
        env = AsyncMock()

        cwe_json = "[]"
        trace_json = "{}"
        # duplicate_rationale is NULL (None)
        db = _make_db(has_rationale=True, rationale_row=(cwe_json, None, trace_json))
        env.DB = db

        resp = await handle_rationale(req, env, "evt-123")
        assert resp.status == 200

        body = json.loads(await resp.text())
        assert body["duplicate_rationale"] is None

    @pytest.mark.asyncio
    @patch("worker._authenticate_request", new_callable=AsyncMock, return_value=({"sub": "agent-test"}, None))
    async def test_returns_424_when_missing(self, _mock_auth):
        """Returns 424 if rationale row does not exist."""
        req = AsyncMock()
        env = AsyncMock()
        db = _make_db(has_rationale=False)
        env.DB = db

        resp = await handle_rationale(req, env, "evt-404")
        assert resp.status == 424

        body = json.loads(await resp.text())
        assert "incomplete" in body["error"].lower()


# ---------------------------------------------------------------------------
# AuditIncompleteError
# ---------------------------------------------------------------------------


class TestAuditIncompleteError:
    def test_attributes(self):
        """AuditIncompleteError exposes event_id and missing_fields."""
        err = AuditIncompleteError(
            "Audit incomplete",
            event_id="evt-x",
            missing_fields=["triage_summary"],
        )
        assert err.event_id == "evt-x"
        assert err.missing_fields == ["triage_summary"]

    def test_default_missing_fields_is_empty_list(self):
        """Default missing_fields is an empty list, not None."""
        err = AuditIncompleteError("Audit incomplete", event_id="evt-y")
        assert err.missing_fields == []
