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


async def _transition_state(db: Any, event_id: str, new_status: str) -> None:
    """Advance the triage event state machine to *new_status*.

    Args:
        db: A Cloudflare D1 database handle.
        event_id: The event to transition.
        new_status: The target state (e.g. ``"embedded"``).
    """
    await db.execute(
        "UPDATE triage_events SET status = ?, updated_at = datetime('now') WHERE id = ?",
        [new_status, event_id],
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
    cursor = await db.execute(
        "SELECT status FROM triage_events WHERE id = ?",
        [event_id],
    )
    row = cursor.fetchone()

    if row is None:
        raise StateTransitionError(
            f"Event {event_id} not found in triage_events",
            event_id=event_id,
            current_status="missing",
            http_status=404,
        )

    status = row[0]
    if status != "summarized":
        raise StateTransitionError(
            f"Event {event_id} has status '{status}'; expected 'summarized'. "
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
        await _transition_state(db, event_id, "embedded_pending")
        return  # Do NOT re-raise — Cron Trigger will retry.

    # ── Insert into Vectorize ─────────────────────────────────────────────
    now = datetime.now(timezone.utc).isoformat()
    await env.VECTORIZE.insert(
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

    # ── Advance state machine ─────────────────────────────────────────────
    await _transition_state(db, event_id, "embedded")
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
    try:
        embedding = await get_embedding(redacted_text, env)
    except EmbeddingServiceError as exc:
        logger.warning("Sidecar unavailable for duplicate search — returning empty: %s", exc)
        return []

    result = await env.VECTORIZE.query(
        embedding,
        {
            "topK": top_k,
            "filter": {"repo": repo_full_name},
            "returnMetadata": "all",
        },
    )

    matches = []
    for match in result.matches:
        score = match.score
        if score >= DUPLICATE_SCORE_THRESHOLD:
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
    await env.VECTORIZE.deleteByIds([event_id])
    logger.info("Deleted vector for event %s from Vectorize", event_id)
