"""Tests for the Vectorize client.

Covers:
    1. Guard blocks non-summarized events
    2. index_report inserts correct metadata into Vectorize
    3. index_report transitions state to 'embedded'
    4. Sidecar failure sets 'embedded_pending'
    5. find_duplicates filters by repo
    6. find_duplicates filters by score threshold (>= 0.80)
    7. find_duplicates returns empty on sidecar failure
    8. delete_vector calls Vectorize deleteByIds
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.errors import EmbeddingServiceError, StateTransitionError
from src.vectorize_client import (
    DUPLICATE_SCORE_THRESHOLD,
    assert_summarized_before_embedding,
    delete_vector,
    find_duplicates,
    index_report,
)


# ---------------------------------------------------------------------------
# Helpers: mock D1 database
# ---------------------------------------------------------------------------


class MockCursor:
    """Mock D1 cursor with fetchone support."""

    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


def _make_db(*, status="summarized", row_exists=True):
    """Build a mock D1 database handle (D1 prepare/bind API).

    Args:
        status: The status value returned by SELECT queries.
        row_exists: Whether the event row exists.
    """
    from tests.utils import make_d1_mock

    first_return = {"status": status} if row_exists else None
    return make_d1_mock(first_return=first_return)


def _make_vectorize_binding():
    """Build a mock Vectorize binding with insert, query, deleteByIds."""
    vectorize = AsyncMock()
    vectorize.insert = AsyncMock()
    vectorize.query = AsyncMock()
    vectorize.deleteByIds = AsyncMock()
    return vectorize


def _make_env(*, vectorize=None):
    """Build a mock env with Vectorize binding."""
    env = MagicMock()
    env.VECTORIZE = vectorize or _make_vectorize_binding()
    env.FASTEMBED_URL = "http://localhost:5003"
    return env


def _make_vectorize_match(event_id, score, repo):
    """Create a mock Vectorize match result."""
    match = MagicMock()
    match.id = event_id
    match.score = score
    match.metadata = {"repo": repo, "event_id": event_id, "model_version": "all-MiniLM-L6-v2"}
    return match


# ---------------------------------------------------------------------------
# Tests: assert_summarized_before_embedding
# ---------------------------------------------------------------------------


class TestAssertSummarizedBeforeEmbedding:
    """Tests for the embedding security guard."""

    @pytest.mark.asyncio
    async def test_allows_summarized_event(self):
        """Event with status 'summarized' passes the guard."""
        db = _make_db(status="summarized")
        await assert_summarized_before_embedding("evt-001", db)
        # No exception raised = pass

    @pytest.mark.asyncio
    async def test_blocks_pending_event(self):
        """Event with status 'pending' is blocked."""
        db = _make_db(status="pending")
        with pytest.raises(StateTransitionError) as exc_info:
            await assert_summarized_before_embedding("evt-001", db)
        assert exc_info.value.http_status == 423
        assert exc_info.value.current_status == "pending"

    @pytest.mark.asyncio
    async def test_blocks_redaction_passed_event(self):
        """Event with status 'redaction_passed' is blocked (must be summarized)."""
        db = _make_db(status="redaction_passed")
        with pytest.raises(StateTransitionError) as exc_info:
            await assert_summarized_before_embedding("evt-001", db)
        assert exc_info.value.http_status == 423

    @pytest.mark.asyncio
    async def test_missing_event_raises_404(self):
        """Non-existent event raises StateTransitionError with 404."""
        db = _make_db(row_exists=False)
        with pytest.raises(StateTransitionError) as exc_info:
            await assert_summarized_before_embedding("evt-missing", db)
        assert exc_info.value.http_status == 404
        assert exc_info.value.current_status == "missing"


# ---------------------------------------------------------------------------
# Tests: index_report
# ---------------------------------------------------------------------------


class TestIndexReport:
    """Tests for the index_report function."""

    @pytest.mark.asyncio
    @patch("src.vectorize_client.get_embedding", new_callable=AsyncMock)
    async def test_inserts_with_correct_metadata(self, mock_get_embedding):
        """Vectorize.insert() is called with repo, event_id, model_version, created_at."""
        mock_get_embedding.return_value = [0.1] * 384
        db = _make_db(status="summarized")
        env = _make_env()

        await index_report("evt-001", "redacted text", "owasp/blt", env, db)

        env.VECTORIZE.insert.assert_awaited_once()
        insert_args = env.VECTORIZE.insert.call_args[0][0]
        assert len(insert_args) == 1
        vec = insert_args[0]
        assert vec["id"] == "evt-001"
        assert len(vec["values"]) == 384
        assert vec["metadata"]["repo"] == "owasp/blt"
        assert vec["metadata"]["event_id"] == "evt-001"
        assert vec["metadata"]["model_version"] == "all-MiniLM-L6-v2"
        assert "created_at" in vec["metadata"]

    @pytest.mark.asyncio
    @patch("src.vectorize_client.get_embedding", new_callable=AsyncMock)
    async def test_transitions_state_to_embedded(self, mock_get_embedding):
        """After successful insert, D1 status transitions to 'embedded'."""
        mock_get_embedding.return_value = [0.1] * 384
        db = _make_db(status="summarized")
        env = _make_env()

        await index_report("evt-001", "redacted text", "owasp/blt", env, db)

        # State UPDATE goes via prepare(sql).bind("embedded", event_id).run()
        stmt = db.prepare.return_value
        bind_calls = [str(c) for c in stmt.bind.call_args_list if "embedded" in str(c) and "evt-001" in str(c)]
        assert len(bind_calls) >= 1

    @pytest.mark.asyncio
    @patch("src.vectorize_client.get_embedding", new_callable=AsyncMock)
    async def test_sidecar_failure_sets_embedded_pending(self, mock_get_embedding):
        """On EmbeddingServiceError, state becomes 'embedded_pending' without re-raise."""
        mock_get_embedding.side_effect = EmbeddingServiceError("sidecar down", status_code=503)
        db = _make_db(status="summarized")
        env = _make_env()

        # Should NOT raise
        await index_report("evt-001", "redacted text", "owasp/blt", env, db)

        # State UPDATE goes via prepare(sql).bind("embedded_pending", event_id).run()
        stmt = db.prepare.return_value
        bind_calls = [str(c) for c in stmt.bind.call_args_list if "embedded_pending" in str(c)]
        assert len(bind_calls) >= 1

        # Verify Vectorize.insert was NOT called
        env.VECTORIZE.insert.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("src.vectorize_client.get_embedding", new_callable=AsyncMock)
    async def test_generic_exception_sets_embedded_pending(self, mock_get_embedding):
        """On generic Exception during Vectorize API call, state becomes 'embedded_pending' and raises."""
        mock_get_embedding.return_value = [0.1] * 384
        db = _make_db(status="summarized")
        env = _make_env()
        env.VECTORIZE.insert.side_effect = Exception("Generic insert error")

        with pytest.raises(Exception, match="Generic insert error"):
            await index_report("evt-001", "redacted text", "owasp/blt", env, db)

        stmt = db.prepare.return_value
        bind_calls = [str(c) for c in stmt.bind.call_args_list if "embedded_pending" in str(c)]
        assert len(bind_calls) >= 1

    @pytest.mark.asyncio
    async def test_guard_blocks_non_summarized(self):
        """index_report raises StateTransitionError for non-summarized events."""
        db = _make_db(status="pending")
        env = _make_env()

        with pytest.raises(StateTransitionError):
            await index_report("evt-001", "redacted text", "owasp/blt", env, db)


# ---------------------------------------------------------------------------
# Tests: find_duplicates
# ---------------------------------------------------------------------------


class TestFindDuplicates:
    """Tests for the find_duplicates function."""

    @pytest.mark.asyncio
    @patch("src.vectorize_client.get_embedding", new_callable=AsyncMock)
    async def test_filters_by_repo(self, mock_get_embedding):
        """Only results matching the repo filter are returned."""
        mock_get_embedding.return_value = [0.1] * 384
        env = _make_env()

        # Mock Vectorize.query to return matches from different repos
        query_result = MagicMock()
        query_result.matches = [
            _make_vectorize_match("evt-001", 0.95, "owasp/blt"),
            _make_vectorize_match("evt-002", 0.90, "other/repo"),
        ]
        env.VECTORIZE.query = AsyncMock(return_value=query_result)

        # The Vectorize query itself filters by repo via metadata filter,
        # so both results would be from the same repo in practice.
        # Here we test that the function passes the filter correctly.
        results = await find_duplicates("redacted query text", "owasp/blt", env)

        env.VECTORIZE.query.assert_awaited_once()
        query_args = env.VECTORIZE.query.call_args
        assert query_args[0][1]["filter"] == {"repo": "owasp/blt", "model_version": "all-MiniLM-L6-v2"}
        assert len(results) == 1
        assert results[0]["event_id"] == "evt-001"

    @pytest.mark.asyncio
    @patch("src.vectorize_client.get_embedding", new_callable=AsyncMock)
    async def test_filters_by_score_threshold(self, mock_get_embedding):
        """Only results with score >= 0.80 are included."""
        mock_get_embedding.return_value = [0.1] * 384
        env = _make_env()

        query_result = MagicMock()
        query_result.matches = [
            _make_vectorize_match("evt-high", 0.95, "owasp/blt"),
            _make_vectorize_match("evt-mid", 0.82, "owasp/blt"),
            _make_vectorize_match("evt-low", 0.65, "owasp/blt"),
            _make_vectorize_match("evt-border", 0.80, "owasp/blt"),
        ]
        env.VECTORIZE.query = AsyncMock(return_value=query_result)

        results = await find_duplicates("redacted query text", "owasp/blt", env)

        assert len(results) == 3  # evt-high, evt-mid, evt-border (not evt-low)
        assert all(r["score"] >= DUPLICATE_SCORE_THRESHOLD for r in results)
        # Should be sorted descending by score
        assert results[0]["score"] >= results[1]["score"] >= results[2]["score"]

    @pytest.mark.asyncio
    @patch("src.vectorize_client.get_embedding", new_callable=AsyncMock)
    async def test_sidecar_failure_returns_empty(self, mock_get_embedding):
        """On EmbeddingServiceError, returns empty list (degraded mode)."""
        mock_get_embedding.side_effect = EmbeddingServiceError("sidecar down", status_code=503)
        env = _make_env()

        results = await find_duplicates("redacted query text", "owasp/blt", env)

        assert results == []
        env.VECTORIZE.query.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("src.vectorize_client.get_embedding", new_callable=AsyncMock)
    async def test_returns_sorted_by_score_descending(self, mock_get_embedding):
        """Results are sorted by score in descending order."""
        mock_get_embedding.return_value = [0.1] * 384
        env = _make_env()

        query_result = MagicMock()
        query_result.matches = [
            _make_vectorize_match("evt-a", 0.82, "owasp/blt"),
            _make_vectorize_match("evt-b", 0.99, "owasp/blt"),
            _make_vectorize_match("evt-c", 0.91, "owasp/blt"),
        ]
        env.VECTORIZE.query = AsyncMock(return_value=query_result)

        results = await find_duplicates("test", "owasp/blt", env)

        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)
        assert results[0]["event_id"] == "evt-b"


# ---------------------------------------------------------------------------
# Tests: delete_vector
# ---------------------------------------------------------------------------


class TestDeleteVector:
    """Tests for the delete_vector function."""

    @pytest.mark.asyncio
    async def test_calls_vectorize_delete(self):
        """delete_vector calls Vectorize.deleteByIds with the event ID."""
        env = _make_env()
        await delete_vector("evt-quarantined", env)
        env.VECTORIZE.deleteByIds.assert_awaited_once_with(["evt-quarantined"])
