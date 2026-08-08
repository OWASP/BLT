"""Cloudflare Vectorize client for OWASP BLT-Toasty.

Provides functions to index redacted triage reports as vector embeddings
in Cloudflare Vectorize and to query for semantically similar (duplicate)
reports within a repository scope.

SECURITY
--------
Only ``redacted_text`` is ever embedded.  The ``assert_summarized_before_embedding``
guard is the **first** call inside ``index_report()`` and blocks execution
unless the event has reached the ``summarized`` state — which is only
reachable after successfully passing the redaction gate.

Pipeline position
-----------------
``pending → redaction_passed → summarized → embedded → exported``

This module owns the ``summarized → embedded`` transition (happy path)
and the ``summarized → embedded_pending`` transition (sidecar failure,
retried later via Cron Trigger).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.embedding_client import get_embedding
from src.errors import EmbeddingServiceError, StateTransitionError

logger = logging.getLogger("toasty.vectorize_client")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DUPLICATE_SCORE_THRESHOLD = 0.80
MODEL_VERSION = "all-MiniLM-L6-v2"


# ---------------------------------------------------------------------------
# Internal helpers (same inline pattern as summarizer.py / redaction_engine.py)
# ---------------------------------------------------------------------------


async def _transition_state(db: Any, event_id: str, new_status: str, expected_status: str) -> None:
    """Advance the triage event state machine to *new_status*.

    Args:
        db: A Cloudflare D1 database handle.
        event_id: The event to transition.
        new_status: The target state (e.g. ``"embedded"``).
        expected_status: The expected current status to enforce optimistic concurrency.
    """
    result = (
        await db.prepare(
            "UPDATE triage_events SET status = ?, updated_at = datetime('now') WHERE id = ? AND status = ?"
        )
        .bind(new_status, event_id, expected_status)
        .run()
    )

    meta = result.meta if hasattr(result, "meta") else result.get("meta", {})
    changes = getattr(meta, "changes", meta.get("changes", 0))
    if changes == 0:
        raise StateTransitionError(
            f"Failed to transition event {event_id} to {new_status} (expected {expected_status})",
            event_id=event_id,
            current_status="unknown_or_concurrent_modification",
        )


# ---------------------------------------------------------------------------
# Security guard
# ---------------------------------------------------------------------------


async def assert_summarized_before_embedding(event_id: str, db: Any) -> None:
    """Block embedding unless the event has been summarized.

    This function **must** be called at the top of ``index_report()``.
    It queries D1 for the event's current status and raises
    ``StateTransitionError`` if the status is anything other than
    ``summarized``.

    The ``summarized`` state is only reachable after ``redaction_passed``,
    so this guard implicitly guarantees that PII redaction has already
    been applied.

    Args:
        event_id: The triage event ID to verify.
        db: A Cloudflare D1 database handle.

    Raises:
        StateTransitionError: If the event status is not ``summarized``.
    """
    row = await db.prepare("SELECT status FROM triage_events WHERE id = ?").bind(event_id).first()

    if row is None:
        raise StateTransitionError(
            f"Event {event_id} not found in triage_events",
            event_id=event_id,
            current_status="missing",
            http_status=404,
        )

    status = row["status"] if hasattr(row, "__getitem__") else row[0]
    if status not in ("summarized", "embedded_pending"):
        raise StateTransitionError(
            f"Event {event_id} has status '{status}'; expected 'summarized' or 'embedded_pending'. "
            f"Embedding is blocked until summarization completes.",
            event_id=event_id,
            current_status=status,
            http_status=423,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def index_report(
    event_id: str,
    redacted_text: str,
    repo_full_name: str,
    env: Any,
    db: Any,
) -> None:
    """Embed redacted text and index it in Cloudflare Vectorize.

    1. Guards via ``assert_summarized_before_embedding`` (**first** call).
    2. Obtains a 384-dim embedding from the FastEmbed sidecar.
    3. Inserts the vector into Vectorize with repo-scoped metadata.
    4. Transitions the event state to ``embedded``.

    On sidecar failure the state is set to ``embedded_pending`` and the
    error is logged but **not** re-raised — a Cron Trigger will retry.

    Args:
        event_id: The triage event ID.
        redacted_text: PII-free text to embed (**NEVER** raw text).
        repo_full_name: Full repository name for metadata filtering.
        env: Cloudflare Worker environment with ``VECTORIZE`` binding.
        db: A Cloudflare D1 database handle.
    """
    # ── Gate: security invariant ──────────────────────────────────────────
    await assert_summarized_before_embedding(event_id, db)

    # ── Embed ─────────────────────────────────────────────────────────────
    try:
        embedding = await get_embedding(redacted_text, env)
    except EmbeddingServiceError as exc:
        logger.warning(
            "Sidecar unavailable for event %s — setting embedded_pending: %s",
            event_id,
            exc,
        )
        # expected_status could be summarized or embedded_pending, we don't strictly know which without querying,
        # but the only valid entry points are those two. For simplicity, we just use the expected state transition.
        # Actually, let's fetch current status to be safe.
        row = await db.prepare("SELECT status FROM triage_events WHERE id = ?").bind(event_id).first()
        current_status = row["status"] if hasattr(row, "__getitem__") else row[0]
        await _transition_state(db, event_id, "embedded_pending", expected_status=current_status)
        return  # Do NOT re-raise — Cron Trigger will retry.

    # ── Insert into Vectorize ─────────────────────────────────────────────
    now = datetime.now(timezone.utc).isoformat()
    try:
        await env.VECTORIZE.upsert(
            [
                {
                    "id": event_id,
                    "values": embedding,
                    "metadata": {
                        "repo": repo_full_name,
                        "event_id": event_id,
                        "model_version": MODEL_VERSION,
                        "created_at": now,
                    },
                }
            ]
        )
    except Exception as exc:
        logger.error("Failed to insert event %s into Vectorize: %s", event_id, exc)
        row = await db.prepare("SELECT status FROM triage_events WHERE id = ?").bind(event_id).first()
        current_status = row["status"] if hasattr(row, "__getitem__") else row[0]
        await _transition_state(db, event_id, "embedded_pending", expected_status=current_status)
        raise

    # ── Advance state machine ─────────────────────────────────────────────
    try:
        row = await db.prepare("SELECT status FROM triage_events WHERE id = ?").bind(event_id).first()
        current_status = row["status"] if hasattr(row, "__getitem__") else row[0]
        await _transition_state(db, event_id, "embedded", expected_status=current_status)
    except StateTransitionError:
        logger.error("State transition failed after Vectorize insert for event %s. Cleaning up vector.", event_id)
        try:
            await env.VECTORIZE.deleteByIds([event_id])
        except Exception as cleanup_exc:
            logger.error("Failed to cleanup vector for event %s after transition failure: %s", event_id, cleanup_exc)
        raise

    logger.info("Indexed event %s in Vectorize (repo=%s)", event_id, repo_full_name)


async def find_duplicates(
    redacted_text: str,
    repo_full_name: str,
    env: Any,
    top_k: int = 20,
) -> list[dict]:
    """Find semantically similar reports in the same repository.

    Args:
        redacted_text: PII-free text to use as the query vector.
        repo_full_name: Repository scope filter for the Vectorize query.
        env: Cloudflare Worker environment with ``VECTORIZE`` binding.
        top_k: Maximum number of nearest neighbours to retrieve.

    Returns:
        A list of dicts ``{"event_id": str, "score": float, "metadata": dict}``
        sorted by descending similarity score.  Only results with
        ``score >= 0.80`` are included.

        Returns an empty list on sidecar failure (degraded mode).
    """
    top_k = min(top_k, 20)
    try:
        embedding = await get_embedding(redacted_text, env)
    except EmbeddingServiceError as exc:
        logger.warning("Sidecar unavailable for duplicate search — returning empty: %s", exc)
        return []

    try:
        result = await env.VECTORIZE.query(
            embedding,
            {
                "topK": top_k,
                "filter": {
                    "repo": repo_full_name,
                    "model_version": MODEL_VERSION,
                },
                "returnMetadata": "all",
            },
        )
    except Exception as exc:
        logger.warning("Vectorize query failed for duplicate search — returning empty: %s", exc)
        return []

    matches = []
    raw_matches = getattr(result, "matches", None) or []
    for match in raw_matches:
        score = match.score
        metadata = match.metadata or {}
        if score >= DUPLICATE_SCORE_THRESHOLD and metadata.get("repo") == repo_full_name:
            matches.append(
                {
                    "event_id": match.id,
                    "score": score,
                    "metadata": match.metadata,
                }
            )

    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches


async def delete_vector(event_id: str, env: Any) -> None:
    """Remove a vector from Vectorize.

    Used when an event is quarantined — its vector must not remain
    in the index.

    Args:
        event_id: The triage event ID whose vector should be deleted.
        env: Cloudflare Worker environment with ``VECTORIZE`` binding.
    """
    try:
        await env.VECTORIZE.deleteByIds([event_id])
        logger.info("Deleted vector for event %s from Vectorize", event_id)
    except Exception as exc:
        logger.error("Failed to delete vector for event %s: %s", event_id, exc)
        raise
