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

from embedding_client import get_embedding
from errors import EmbeddingServiceError, StateTransitionError

logger = logging.getLogger("toasty.vectorize_client")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DUPLICATE_SCORE_THRESHOLD = 0.80
MODEL_VERSION = "all-MiniLM-L6-v2"
SHADOW_EVENT_PREFIX = "shadow:"


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

    meta = result.meta if hasattr(result, "meta") else (result.get("meta", {}) if isinstance(result, dict) else {})
    if hasattr(meta, "changes"):
        changes = meta.changes
    elif isinstance(meta, dict):
        changes = meta.get("changes", 0)
    else:
        changes = 0
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

    if row.__class__.__name__ == "JsProxy":
        row = row.to_py()
    status = (
        row.get("status")
        if hasattr(row, "get")
        else (
            row["status"]
            if hasattr(row, "__getitem__")
            else getattr(row, "status", row[0] if isinstance(row, (list, tuple)) else None)
        )
    )
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
        current_status = (
            dict(row.to_py()).get("status")
            if row.__class__.__name__ == "JsProxy"
            else (
                row.get("status")
                if hasattr(row, "get")
                else getattr(row, "status", row[0] if isinstance(row, (list, tuple)) else None)
            )
        )
        await _transition_state(db, event_id, "embedded_pending", expected_status=current_status)
        return  # Do NOT re-raise — Cron Trigger will retry.

    # ── Insert into Vectorize ─────────────────────────────────────────────
    now = datetime.now(timezone.utc).isoformat()
    try:
        payload = [
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

        # In Pyodide, nested arrays/dicts passed to JS bindings can cause "not expected format"
        # errors if not explicitly converted to JS types.
        if hasattr(env, "VECTORIZE") and env.__class__.__name__ != "MagicMock":
            try:
                import json
                import js

                payload = js.JSON.parse(json.dumps(payload))
            except Exception:
                pass  # not running in pyodide (e.g. tests)  # nosec

        await env.VECTORIZE.upsert(payload)
    except Exception as exc:
        logger.error("Failed to insert event %s into Vectorize: %s", event_id, exc)
        row = await db.prepare("SELECT status FROM triage_events WHERE id = ?").bind(event_id).first()
        current_status = (
            dict(row.to_py()).get("status")
            if row.__class__.__name__ == "JsProxy"
            else (
                row.get("status")
                if hasattr(row, "get")
                else getattr(row, "status", row[0] if isinstance(row, (list, tuple)) else None)
            )
        )
        await _transition_state(db, event_id, "embedded_pending", expected_status=current_status)
        raise

    # ── Advance state machine ─────────────────────────────────────────────
    try:
        row = await db.prepare("SELECT status FROM triage_events WHERE id = ?").bind(event_id).first()
        current_status = (
            dict(row.to_py()).get("status")
            if row.__class__.__name__ == "JsProxy"
            else (
                row.get("status")
                if hasattr(row, "get")
                else getattr(row, "status", row[0] if isinstance(row, (list, tuple)) else None)
            )
        )
        await _transition_state(db, event_id, "embedded", expected_status=current_status)
    except StateTransitionError:
        logger.error("State transition failed after Vectorize insert for event %s. Cleaning up vector.", event_id)

        # Concurrent winner check
        try:
            row = await db.prepare("SELECT status FROM triage_events WHERE id = ?").bind(event_id).first()
            current_status = (
                row["status"]
                if hasattr(row, "__getitem__")
                else (getattr(row, "status") if hasattr(row, "status") else None)
            )
            if current_status == "embedded":
                logger.info("Concurrent indexing succeeded for event %s; preserving vector.", event_id)
                raise
        except Exception as check_exc:
            if isinstance(check_exc, StateTransitionError):
                raise
            logger.warning("Failed to check status for event %s during cleanup: %s", event_id, check_exc)

        # Retry logic: attempt cleanup twice
        try:
            await delete_vector(event_id, env)
            cleanup_success = True
        except Exception as cleanup_exc:
            logger.error("Failed to cleanup vector for event %s: %s", event_id, cleanup_exc)

        if not cleanup_success:
            # Mark the event so a cron trigger can clean up the phantom vector later
            try:
                await db.prepare(
                    "UPDATE triage_events SET quarantine_reason = COALESCE(quarantine_reason, '') || '; vector_cleanup_pending' WHERE id = ?"
                ).bind(event_id).run()
            except Exception as flag_exc:
                logger.error("Failed to set vector_cleanup_pending flag for event %s: %s", event_id, flag_exc)

        raise

    logger.info("Indexed event %s in Vectorize (repo=%s)", event_id, repo_full_name)


async def find_duplicates(
    redacted_text: str,
    repo_full_name: str,
    env: Any,
    top_k: int = 20,
    include_shadow: bool = False,
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
        options = {
            "topK": top_k,
            "filter": {
                "repo": repo_full_name,
                "model_version": MODEL_VERSION,
            },
            "returnMetadata": "all",
        }

        # Convert both embedding AND options to native JS types.
        # Vectorize.query cannot interpret a PyProxy-wrapped Python list
        # as a vector — it silently returns 0 matches.
        if hasattr(env, "VECTORIZE") and env.__class__.__name__ != "MagicMock":
            try:
                import json
                import js

                options = js.JSON.parse(json.dumps(options))
                embedding = js.JSON.parse(json.dumps(embedding))
            except Exception:
                pass  # nosec

        result = await env.VECTORIZE.query(
            embedding,
            options,
        )
    except Exception as exc:
        logger.warning("Vectorize query failed for duplicate search — returning empty: %s", exc)
        return []

    matches = []

    result_py = result.to_py() if result.__class__.__name__ == "JsProxy" else result
    if isinstance(result_py, dict):
        raw_matches = result_py.get("matches", [])
    else:
        raw_matches = getattr(result_py, "matches", None) or []

    for match in raw_matches:
        if isinstance(match, dict):
            score = match.get("score", 0.0)
            metadata = match.get("metadata") or {}
            match_id = match.get("id", "")
        else:
            score = getattr(match, "score", 0.0)
            metadata = getattr(match, "metadata", None) or {}
            match_id = getattr(match, "id", "")

        if score >= DUPLICATE_SCORE_THRESHOLD and metadata.get("repo") == repo_full_name:
            # Skip shadow mode entries unless explicitly requested
            if not include_shadow and match_id.startswith(SHADOW_EVENT_PREFIX):
                continue
            matches.append(
                {
                    "event_id": match_id,
                    "score": score,
                    "metadata": metadata,
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
    for attempt in range(2):
        try:
            ids = [event_id]
            if hasattr(env, "VECTORIZE") and env.__class__.__name__ != "MagicMock":
                try:
                    import json
                    import js

                    ids = js.JSON.parse(json.dumps(ids))
                except Exception:
                    pass  # nosec
            await env.VECTORIZE.deleteByIds(ids)
            logger.info("Deleted vector for event %s from Vectorize", event_id)
            return
        except Exception as exc:
            logger.warning("Failed to delete vector for event %s on attempt %d: %s", event_id, attempt + 1, exc)

    logger.error("Vector cleanup completely failed for event %s after 2 attempts", event_id)
    raise Exception("Vector deletion failed after retries")
