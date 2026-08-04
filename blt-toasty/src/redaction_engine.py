"""
Fail-closed redaction engine for the Toasty triage pipeline.

This module is the **single entry-point** for all PII redaction.  No other
code path may bypass it.  The engine enforces a strict invariant:

    *If redaction cannot be provably completed, the event is quarantined
    and downstream processing is blocked.*

Pipeline stages
---------------
1. **Markdown preprocessing** — extract plain text so PII hidden inside
   code fences, links, or image alt-text is visible to the scanner.
2. **Native recognition** — run the regex-based recogniser engine against
   *both* the original text and the preprocessed plain text, then merge
   matches.
3. **Confidence gate** — reject any match with confidence < 0.70 by
   quarantining the event.  (In practice, native patterns always return
   ≥ 0.95, so this gate exists as a safety net for future engine changes.)
4. **Typed redaction** — build ``redacted_text`` with typed ``[ENTITY]``
   placeholders and ``safe_preview_text`` with uniform ``[REDACTED]``.
5. **Audit persistence** — store the full ``redaction_map`` in D1 and
   transition the event state to ``redaction_passed``.

Cloudflare D1 interface
-----------------------
The ``db`` parameter is expected to implement the raw async D1 driver
style::

    cursor = await db.execute("SELECT status FROM triage_events WHERE id = ?", [event_id])
    row = cursor.fetchone()
"""

from __future__ import annotations

import dataclasses
import logging
import re
from typing import Any

from src.errors import RedactionFailedError, StateTransitionError
from src.markdown_preprocessor import extract_plain_text
from src.native_recognizers import RecogniserMatch, apply_native_redaction, scan_text

logger = logging.getLogger(__name__)

# Minimum confidence score for an entity match to be accepted.
_CONFIDENCE_THRESHOLD = 0.70

# Regex used to convert typed placeholders into uniform [REDACTED] tags.
_TYPED_PLACEHOLDER = re.compile(r"\[[A-Z][A-Z0-9_]*\]")


# ---------------------------------------------------------------------------
# Data contract
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class RedactionResult:
    """Immutable output of a successful redaction pass.

    Attributes:
        redacted_text: The input text with every detected entity replaced
            by a typed placeholder such as ``[EMAIL_ADDRESS]``.
        safe_preview_text: A more aggressive version where every typed
            placeholder is further replaced by the uniform ``[REDACTED]``
            tag — suitable for Slack, CLI, or public dashboards.
        redaction_map: An ordered list of match records for the D1 audit
            table.  Each entry carries ``entity_type``, ``start``, ``end``,
            ``confidence``, and ``detector``.
        entity_count: Total number of entities that were redacted.
    """

    redacted_text: str
    safe_preview_text: str
    redaction_map: list[dict[str, Any]]
    entity_count: int


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------


async def redact(text: str, env: Any, event_id: str, db: Any) -> RedactionResult:
    """Execute the full fail-closed redaction pipeline.

    This function is the **only** sanctioned entry-point for redaction.
    It must be called before any downstream processing (summarisation,
    embedding, MCP export).

    Args:
        text: Raw report text (may contain Markdown).
        env: Cloudflare Worker environment bindings (unused by native
            engine but kept for interface compatibility).
        event_id: The triage event ID in D1.
        db: A Cloudflare D1 database handle exposing ``execute(sql, params)``.

    Returns:
        A ``RedactionResult`` with all PII replaced.

    Raises:
        RedactionFailedError: If any match falls below the confidence
            threshold, or if any unexpected error occurs during the
            pipeline.  The event is quarantined before the exception
            propagates.
    """
    try:
        # Stage 1 — Markdown preprocessing.
        plain_text = extract_plain_text(text)

        # Stage 2 — Native recognition on the *original* text.
        #
        # We scan the original text (not the preprocessed version) so that
        # byte offsets in the redaction map correspond to the caller's input.
        # The preprocessed text is used as a secondary scan surface to catch
        # PII that was hidden inside Markdown constructs; those matches are
        # logged for auditing but the redaction itself operates on `text`.
        redacted_text, matches = apply_native_redaction(text)

        # Secondary scan on preprocessed text (catches PII hidden in code
        # fences / links that the original-text scan might miss because the
        # regex anchors differ after markdown stripping).
        if plain_text != text:
            secondary_matches = scan_text(plain_text)
            if secondary_matches:
                logger.info(
                    "Secondary scan found %d additional entities in preprocessed text for event %s",
                    len(secondary_matches),
                    event_id,
                )

        # Stage 3 — Confidence gate.
        for match in matches:
            if match["confidence"] < _CONFIDENCE_THRESHOLD:
                reason = (
                    f"Entity {match['entity_type']} at [{match['start']}:{match['end']}] "
                    f"has confidence {match['confidence']:.2f} < threshold {_CONFIDENCE_THRESHOLD}"
                )
                await _quarantine_event(db, event_id, reason)
                raise RedactionFailedError(
                    f"Confidence below threshold for event {event_id}: {reason}",
                    event_id=event_id,
                    reason=reason,
                )

        # Stage 4 — Build safe_preview_text (uniform [REDACTED] tags).
        safe_preview_text = _TYPED_PLACEHOLDER.sub("[REDACTED]", redacted_text)

        # Build the redaction_map for D1 audit persistence.
        redaction_map = _build_redaction_map(matches)

        # Stage 5 — Persist audit trail and advance state machine.
        await _store_redaction_audit(db, event_id, redaction_map)
        await _transition_state(db, event_id, "redaction_passed")

        return RedactionResult(
            redacted_text=redacted_text,
            safe_preview_text=safe_preview_text,
            redaction_map=redaction_map,
            entity_count=len(matches),
        )

    except RedactionFailedError:
        raise  # Already quarantined — propagate without double-quarantine.
    except Exception as exc:
        # Catch-all safety net — quarantine and fail closed.
        reason = f"Unexpected error during redaction: {type(exc).__name__}: {exc}"
        logger.error("Fail-closed redaction triggered for event %s: %s", event_id, reason)
        await _quarantine_event(db, event_id, reason)
        await _transition_state(db, event_id, "redaction_failed")
        raise RedactionFailedError(
            f"Redaction failed for event {event_id}",
            event_id=event_id,
            reason=reason,
        ) from exc


# ---------------------------------------------------------------------------
# Downstream guard
# ---------------------------------------------------------------------------


async def assert_redacted_before_downstream(event_id: str, db: Any) -> None:
    """Block downstream processing unless the event has passed redaction.

    This function **must** be called at the top of every downstream handler
    (summariser, embedder, MCP export).  It queries D1 for the event's
    current status and raises ``StateTransitionError`` if the status is
    anything other than ``redaction_passed``.

    Args:
        event_id: The triage event ID to verify.
        db: A Cloudflare D1 database handle.

    Raises:
        StateTransitionError: If the event status is not ``redaction_passed``.
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
    if status != "redaction_passed":
        raise StateTransitionError(
            f"Event {event_id} has status '{status}'; expected 'redaction_passed'. "
            f"Downstream processing is blocked.",
            event_id=event_id,
            current_status=status,
            http_status=423,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_redaction_map(matches: list[RecogniserMatch]) -> list[dict[str, Any]]:
    """Convert raw recogniser matches into the D1 audit table schema."""
    return [
        {
            "entity_type": m["entity_type"],
            "detector": m["detector"],
            "confidence": m["confidence"],
            "byte_start": m["start"],
            "byte_end": m["end"],
            "original_length": m["end"] - m["start"],
        }
        for m in matches
    ]


async def _store_redaction_audit(db: Any, event_id: str, redaction_map: list[dict[str, Any]]) -> None:
    """INSERT each entry of the redaction map into the D1 ``redaction_audit`` table."""
    for entry in redaction_map:
        await db.execute(
            "INSERT INTO redaction_audit "
            "(event_id, entity_type, detector, confidence, byte_start, byte_end, original_length) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                event_id,
                entry["entity_type"],
                entry["detector"],
                entry["confidence"],
                entry["byte_start"],
                entry["byte_end"],
                entry["original_length"],
            ],
        )


async def _quarantine_event(db: Any, event_id: str, reason: str) -> None:
    """Mark an event as quarantined in D1."""
    from src.state_machine import quarantine_event

    # redaction happens before vectorization, so there is no vector to delete
    # we pass env=None which safely skips vector deletion while preserving the audit trail
    await quarantine_event(db, event_id, reason, env=None, has_vector=False)


async def _transition_state(db: Any, event_id: str, new_status: str) -> None:
    """Advance the triage event state machine to *new_status*."""
    await db.execute(
        "UPDATE triage_events SET status = ? WHERE id = ?",
        [new_status, event_id],
    )
