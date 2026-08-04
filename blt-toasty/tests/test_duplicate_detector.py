"""Tests for the duplicate detector.

Covers:
    1. Security guard blocks non-redacted events
    2. High score (≥ 0.85) accepted without LLM
    3. Borderline score (0.80–0.84) triggers LLM adjudication
    4. LLM confirms borderline candidate
    5. LLM rejects borderline candidate
    6. LLM low confidence rejects even if is_duplicate=True
    7. No duplicates returns empty result
    8. LLM unavailable fails safe (no auto-confirm)
    9. Candidates stored in D1
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.duplicate_detector import (
    detect_duplicates,
    validate_adjudication_output,
)
from src.errors import LLMUnavailableError, StateTransitionError


# ---------------------------------------------------------------------------
# Helpers: mock D1 database
# ---------------------------------------------------------------------------


class MockCursor:
    """Mock D1 cursor with fetchone support."""

    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


def _make_db(*, status="redaction_passed", row_exists=True, summary_text="Mock executive summary"):
    """Build a mock D1 database handle.

    The mock supports two query patterns:
    - SELECT status FROM triage_events → returns (status,)
    - SELECT executive_summary FROM triage_summaries → returns (summary_text,)
    - INSERT INTO duplicate_candidates → no-op
    """
    db = AsyncMock()

    async def mock_execute(sql, params=None):
        if "SELECT status FROM triage_events" in sql:
            row = (status,) if row_exists else None
            return MockCursor(row=row)
        if "SELECT executive_summary FROM triage_summaries" in sql:
            return MockCursor(row=(summary_text,) if summary_text else None)
        # INSERT or UPDATE — return a no-op cursor
        return MockCursor(row=None)

    db.execute = AsyncMock(side_effect=mock_execute)
    db.batch = AsyncMock()
    
    mock_stmt = MagicMock()
    mock_stmt.bind.return_value = mock_stmt
    db.prepare = MagicMock(return_value=mock_stmt)
    
    return db


def _make_env():
    """Build a mock env."""
    env = MagicMock()
    env.FASTEMBED_URL = "http://localhost:5003"
    return env


def _make_do_stub():
    """Build a mock Durable Object stub."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Tests: validate_adjudication_output
# ---------------------------------------------------------------------------


class TestValidateAdjudicationOutput:
    """Tests for the adjudication output validator."""

    def test_valid_output_passes(self):
        """A well-formed adjudication response passes validation."""
        data = {"is_duplicate": True, "confidence": 0.85, "rationale": "Same XSS in login form."}
        is_valid, errors = validate_adjudication_output(data)
        assert is_valid
        assert errors == []

    def test_missing_is_duplicate_fails(self):
        """Missing is_duplicate field fails validation."""
        data = {"confidence": 0.85, "rationale": "Same issue."}
        is_valid, errors = validate_adjudication_output(data)
        assert not is_valid
        assert any("is_duplicate" in e for e in errors)

    def test_confidence_out_of_range_fails(self):
        """Confidence outside [0.0, 1.0] fails validation."""
        data = {"is_duplicate": True, "confidence": 1.5, "rationale": "Same issue."}
        is_valid, errors = validate_adjudication_output(data)
        assert not is_valid
        assert any("confidence" in e for e in errors)

    def test_empty_rationale_fails(self):
        """Empty rationale string fails validation."""
        data = {"is_duplicate": True, "confidence": 0.85, "rationale": ""}
        is_valid, errors = validate_adjudication_output(data)
        assert not is_valid
        assert any("rationale" in e for e in errors)


# ---------------------------------------------------------------------------
# Tests: detect_duplicates
# ---------------------------------------------------------------------------


class TestDetectDuplicates:
    """Tests for the 3-tier duplicate detection pipeline."""

    @pytest.mark.asyncio
    async def test_guard_blocks_non_redacted_event(self):
        """Event with status 'pending' is blocked by the security guard."""
        db = _make_db(status="pending")
        env = _make_env()
        do_stub = _make_do_stub()

        with pytest.raises(StateTransitionError) as exc_info:
            await detect_duplicates("evt-001", "redacted text", "owasp/blt", env, db, do_stub)
        assert exc_info.value.http_status == 423

    @pytest.mark.asyncio
    @patch("src.duplicate_detector.find_duplicates", new_callable=AsyncMock)
    async def test_high_score_accepted_without_llm(self, mock_find_duplicates):
        """Score ≥ 0.85 is accepted as retrieval_only without calling the LLM."""
        mock_find_duplicates.return_value = [
            {"event_id": "evt-dup", "score": 0.90, "metadata": {"repo": "owasp/blt"}},
        ]
        db = _make_db(status="redaction_passed")
        env = _make_env()
        do_stub = _make_do_stub()

        with patch("src.duplicate_detector.call_llm", new_callable=AsyncMock) as mock_call_llm:
            result = await detect_duplicates("evt-001", "redacted text", "owasp/blt", env, db, do_stub)

            mock_call_llm.assert_not_awaited()

        assert len(result.candidates) == 1
        assert result.candidates[0].detection_method == "retrieval_only"
        assert result.candidates[0].llm_confirmed is True
        assert result.detection_method == "retrieval_only"

    @pytest.mark.asyncio
    @patch("src.duplicate_detector.call_llm", new_callable=AsyncMock)
    @patch("src.duplicate_detector.find_duplicates", new_callable=AsyncMock)
    async def test_borderline_score_triggers_llm(self, mock_find_duplicates, mock_call_llm):
        """Score between 0.80 and 0.85 triggers LLM adjudication."""
        mock_find_duplicates.return_value = [
            {"event_id": "evt-dup", "score": 0.82, "metadata": {"repo": "owasp/blt"}},
        ]
        mock_call_llm.return_value = json.dumps(
            {"is_duplicate": True, "confidence": 0.90, "rationale": "Same XSS vulnerability."}
        )
        db = _make_db(status="redaction_passed", summary_text="Candidate executive summary")
        env = _make_env()
        do_stub = _make_do_stub()

        await detect_duplicates("evt-001", "redacted text", "owasp/blt", env, db, do_stub)

        mock_call_llm.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("src.duplicate_detector.call_llm", new_callable=AsyncMock)
    @patch("src.duplicate_detector.find_duplicates", new_callable=AsyncMock)
    async def test_llm_confirms_borderline_candidate(self, mock_find_duplicates, mock_call_llm):
        """LLM confirms duplicate with high confidence → candidate promoted."""
        mock_find_duplicates.return_value = [
            {"event_id": "evt-dup", "score": 0.82, "metadata": {"repo": "owasp/blt"}},
        ]
        mock_call_llm.return_value = json.dumps(
            {"is_duplicate": True, "confidence": 0.90, "rationale": "Same XSS vulnerability."}
        )
        db = _make_db(status="redaction_passed", summary_text="Candidate executive summary")
        env = _make_env()
        do_stub = _make_do_stub()

        result = await detect_duplicates("evt-001", "redacted text", "owasp/blt", env, db, do_stub)

        assert len(result.candidates) == 1
        assert result.candidates[0].llm_confirmed is True
        assert result.candidates[0].detection_method == "retrieval_plus_llm"
        assert result.candidates[0].llm_confidence == 0.90
        assert result.top_candidate is not None
        assert result.detection_method == "retrieval_plus_llm"

    @pytest.mark.asyncio
    @patch("src.duplicate_detector.call_llm", new_callable=AsyncMock)
    @patch("src.duplicate_detector.find_duplicates", new_callable=AsyncMock)
    async def test_llm_rejects_borderline_candidate(self, mock_find_duplicates, mock_call_llm):
        """LLM says is_duplicate=False → candidate NOT promoted."""
        mock_find_duplicates.return_value = [
            {"event_id": "evt-dup", "score": 0.82, "metadata": {"repo": "owasp/blt"}},
        ]
        mock_call_llm.return_value = json.dumps(
            {"is_duplicate": False, "confidence": 0.90, "rationale": "Different root cause."}
        )
        db = _make_db(status="redaction_passed", summary_text="Candidate summary")
        env = _make_env()
        do_stub = _make_do_stub()

        result = await detect_duplicates("evt-001", "redacted text", "owasp/blt", env, db, do_stub)

        assert len(result.candidates) == 0
        assert result.top_candidate is None
        assert result.detection_method == "no_duplicates"

    @pytest.mark.asyncio
    @patch("src.duplicate_detector.call_llm", new_callable=AsyncMock)
    @patch("src.duplicate_detector.find_duplicates", new_callable=AsyncMock)
    async def test_llm_low_confidence_rejects(self, mock_find_duplicates, mock_call_llm):
        """LLM says is_duplicate=True but confidence < 0.80 → candidate NOT promoted."""
        mock_find_duplicates.return_value = [
            {"event_id": "evt-dup", "score": 0.82, "metadata": {"repo": "owasp/blt"}},
        ]
        mock_call_llm.return_value = json.dumps(
            {"is_duplicate": True, "confidence": 0.60, "rationale": "Possibly similar."}
        )
        db = _make_db(status="redaction_passed", summary_text="Candidate summary")
        env = _make_env()
        do_stub = _make_do_stub()

        result = await detect_duplicates("evt-001", "redacted text", "owasp/blt", env, db, do_stub)

        assert len(result.candidates) == 0
        assert result.top_candidate is None

    @pytest.mark.asyncio
    @patch("src.duplicate_detector.find_duplicates", new_callable=AsyncMock)
    async def test_no_duplicates_returns_empty(self, mock_find_duplicates):
        """Empty find_duplicates result → no_duplicates."""
        mock_find_duplicates.return_value = []
        db = _make_db(status="redaction_passed")
        env = _make_env()
        do_stub = _make_do_stub()

        result = await detect_duplicates("evt-001", "redacted text", "owasp/blt", env, db, do_stub)

        assert result.candidates == []
        assert result.top_candidate is None
        assert result.detection_method == "no_duplicates"

    @pytest.mark.asyncio
    @patch("src.duplicate_detector.call_llm", new_callable=AsyncMock)
    @patch("src.duplicate_detector.find_duplicates", new_callable=AsyncMock)
    async def test_missing_summary_skips_adjudication(self, mock_find_duplicates, mock_call_llm):
        """Candidate with missing executive summary skips LLM adjudication."""
        mock_find_duplicates.return_value = [
            {"event_id": "evt-dup", "score": 0.82, "metadata": {"repo": "owasp/blt"}},
        ]
        # Return None for summary
        db = _make_db(status="redaction_passed", summary_text=None)
        env = _make_env()
        do_stub = _make_do_stub()

        result = await detect_duplicates("evt-001", "redacted text", "owasp/blt", env, db, do_stub)

        mock_call_llm.assert_not_awaited()
        assert len(result.candidates) == 0
        assert result.top_candidate is None

    @pytest.mark.asyncio
    @patch("src.duplicate_detector.call_llm", new_callable=AsyncMock)
    @patch("src.duplicate_detector.find_duplicates", new_callable=AsyncMock)
    async def test_llm_unavailable_fails_safe(self, mock_find_duplicates, mock_call_llm):
        """LLMUnavailableError → candidate NOT promoted (fail-safe)."""
        mock_find_duplicates.return_value = [
            {"event_id": "evt-dup", "score": 0.82, "metadata": {"repo": "owasp/blt"}},
        ]
        mock_call_llm.side_effect = LLMUnavailableError("All providers down", providers_tried=["cf_ai", "openai"])
        db = _make_db(status="redaction_passed", summary_text="Candidate summary")
        env = _make_env()
        do_stub = _make_do_stub()

        result = await detect_duplicates("evt-001", "redacted text", "owasp/blt", env, db, do_stub)

        # Fail-safe: LLM failure means candidate is NOT confirmed
        assert len(result.candidates) == 0
        assert result.top_candidate is None

    @pytest.mark.asyncio
    @patch("src.duplicate_detector.call_llm", new_callable=AsyncMock)
    @patch("src.duplicate_detector.find_duplicates", new_callable=AsyncMock)
    async def test_candidates_stored_in_d1(self, mock_find_duplicates, mock_call_llm):
        """All candidates (confirmed and rejected) are persisted to D1."""
        mock_find_duplicates.return_value = [
            {"event_id": "evt-high", "score": 0.90, "metadata": {"repo": "owasp/blt"}},
            {"event_id": "evt-border", "score": 0.82, "metadata": {"repo": "owasp/blt"}},
        ]
        mock_call_llm.return_value = json.dumps({"is_duplicate": False, "confidence": 0.40, "rationale": "Different."})
        db = _make_db(status="redaction_passed", summary_text="Candidate summary")
        env = _make_env()
        do_stub = _make_do_stub()

        await detect_duplicates("evt-001", "redacted text", "owasp/blt", env, db, do_stub)

        # Ensure batch was called
        db.batch.assert_awaited_once()
        batch_args = db.batch.call_args[0][0]
        assert len(batch_args) == 2  # One high-score, one borderline
