"""
Duplicate intelligence detector for the Toasty triage pipeline.

Implements a 3-tier duplicate scoring strategy:
    - **≥ 0.85** → accept as duplicate candidate (retrieval-only, no LLM)
    - **0.80 – 0.84** → LLM adjudication required
    - **< 0.80** → discarded (already filtered by ``find_duplicates``)

Security invariants
-------------------
* ``assert_redacted_before_downstream`` is the **first** call inside
  ``detect_duplicates()`` — it gates all processing.
* ``adjudicate_duplicate`` ONLY receives already-redacted text.
  **NEVER** pass raw payload to any function in this module.

Pipeline position
-----------------
``pending → redaction_passed → summarized → embedded → exported``

This module operates on events that have reached at least
``redaction_passed`` status.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import uuid
from typing import Any

from src.errors import LLMUnavailableError
from src.llm_client import call_llm
from src.redaction_engine import assert_redacted_before_downstream
from src.summarizer import truncate_to_token_budget
from src.vectorize_client import find_duplicates

logger = logging.getLogger("toasty.duplicate_detector")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AUTO_ACCEPT_THRESHOLD = 0.85
ADJUDICATION_THRESHOLD = 0.80
LLM_CONFIDENCE_THRESHOLD = 0.80
MAX_ADJUDICATION_TOKENS = 400
ADJUDICATION_TEXT_TOKEN_BUDGET = 400

# ---------------------------------------------------------------------------
# Adjudication system prompt
# ---------------------------------------------------------------------------

ADJUDICATION_SYSTEM_PROMPT = """You are a security issue triage assistant for OWASP BLT.
Determine if two vulnerability reports describe the same underlying issue.

RULES:
1. You MUST respond with valid JSON only. No prose. No markdown.
2. Focus on: same vulnerability type, same affected component, same root cause.
3. Superficial similarities (same language, same project) are NOT enough.
4. If uncertain, set is_duplicate to false. False negatives are safer than false positives.

OUTPUT SCHEMA:
{
  "is_duplicate": true,
  "confidence": 0.85,
  "rationale": "Both reports describe an XSS vulnerability in the login form's email field."
}"""

# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class DuplicateCandidate:
    """A single candidate from the duplicate detection pipeline.

    Attributes:
        event_id: The candidate event ID (the potential duplicate).
        similarity_score: Vectorize cosine similarity (0.0–1.0).
        llm_confirmed: Whether the LLM confirmed this as a duplicate.
        llm_confidence: LLM self-reported confidence (None if LLM not called).
        llm_rationale: LLM explanation (None if LLM not called).
        detection_method: One of ``retrieval_only``, ``retrieval_plus_llm``,
            or ``llm_rejected``.
    """

    event_id: str
    similarity_score: float
    llm_confirmed: bool
    llm_confidence: float | None
    llm_rationale: str | None
    detection_method: str


@dataclasses.dataclass(frozen=True, slots=True)
class DuplicateDetectionResult:
    """Full result of the duplicate detection pipeline for one event.

    Attributes:
        event_id: The query event ID.
        candidates: All confirmed duplicate candidates, sorted by score.
        top_candidate: The highest-scoring confirmed candidate, or None.
        detection_method: Overall method: ``retrieval_only``,
            ``retrieval_plus_llm``, or ``no_duplicates``.
    """

    event_id: str
    candidates: list[DuplicateCandidate]
    top_candidate: DuplicateCandidate | None
    detection_method: str


# ---------------------------------------------------------------------------
# Output validation
# ---------------------------------------------------------------------------


def validate_adjudication_output(data: dict) -> tuple[bool, list[str]]:
    """Validate the LLM adjudication JSON against the expected schema.

    Args:
        data: Parsed JSON dict from the LLM response.

    Returns:
        A tuple of ``(is_valid, error_messages)``.
    """
    errors: list[str] = []

    is_dup = data.get("is_duplicate")
    if not isinstance(is_dup, bool):
        errors.append("is_duplicate: missing or not a boolean")

    conf = data.get("confidence")
    if conf is None:
        errors.append("confidence: missing")
    elif not isinstance(conf, (int, float)):
        errors.append(f"confidence: not a number (got {type(conf).__name__})")
    elif not 0.0 <= float(conf) <= 1.0:
        errors.append(f"confidence: out of range [0.0, 1.0] (got {conf})")

    rationale = data.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        errors.append("rationale: missing or not a non-empty string")

    return (len(errors) == 0, errors)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_candidate_summary_text(candidate_event_id: str, db: Any) -> str | None:
    """Fetch the executive summary for a candidate event from D1.

    Since ``redacted_text`` is returned in-memory by the redaction engine
    but NOT persisted as a column on ``triage_events``, we use the
    ``executive_summary`` from ``triage_summaries`` as the best available
    proxy text for LLM comparison.

    Args:
        candidate_event_id: The event ID to look up.
        db: A Cloudflare D1 database handle.

    Returns:
        The executive summary string, or ``None`` if not found.
    """
    cursor = await db.execute(
        "SELECT executive_summary FROM triage_summaries WHERE triage_event_id = ?",
        [candidate_event_id],
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return row[0]


async def _store_candidates(db: Any, event_id: str, candidates: list[DuplicateCandidate]) -> None:
    """Persist duplicate candidates to D1.

    Args:
        db: A Cloudflare D1 database handle.
        event_id: The query event ID.
        candidates: The candidates to persist.
    """
    for candidate in candidates:
        row_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO duplicate_candidates "
            "(id, triage_event_id, candidate_event_id, similarity_score, "
            "llm_confirmed, llm_confidence, llm_rationale, detection_method) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                row_id,
                event_id,
                candidate.event_id,
                candidate.similarity_score,
                1 if candidate.llm_confirmed else 0,
                candidate.llm_confidence,
                candidate.llm_rationale,
                candidate.detection_method,
            ],
        )


# ---------------------------------------------------------------------------
# LLM adjudication
# ---------------------------------------------------------------------------


async def adjudicate_duplicate(
    query_text: str,
    candidate_text: str,
    env: Any,
    do_stub: Any,
) -> dict:
    """Ask the LLM whether two vulnerability reports are duplicates.

    Args:
        query_text: Redacted text of the query report.
            **MUST be redacted_text, never raw payload.**
        candidate_text: Redacted text of the candidate report.
            **MUST be redacted_text, never raw payload.**
        env: Cloudflare Worker environment object.
        do_stub: Durable Object stub for the LLM router.

    Returns:
        A dict ``{"is_duplicate": bool, "confidence": float, "rationale": str}``.
        On any failure, returns a safe default
        ``{"is_duplicate": False, "confidence": 0.0, "rationale": "..."}``.
    """
    safe_default = {"is_duplicate": False, "confidence": 0.0, "rationale": "LLM unavailable or parse failure"}

    truncated_query = truncate_to_token_budget(query_text, ADJUDICATION_TEXT_TOKEN_BUDGET)
    truncated_candidate = truncate_to_token_budget(candidate_text, ADJUDICATION_TEXT_TOKEN_BUDGET)

    messages = [
        {"role": "system", "content": ADJUDICATION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (f"REPORT A (query):\n{truncated_query}\n\n" f"REPORT B (candidate):\n{truncated_candidate}"),
        },
    ]

    try:
        raw_response = await call_llm(messages, env, do_stub, max_tokens=MAX_ADJUDICATION_TOKENS)
    except LLMUnavailableError:
        logger.warning("LLM unavailable for adjudication — returning safe default")
        return safe_default

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON for adjudication — returning safe default")
        return safe_default

    is_valid, validation_errors = validate_adjudication_output(parsed)
    if not is_valid:
        logger.warning("Adjudication output failed validation: %s", validation_errors)
        return safe_default

    return {
        "is_duplicate": bool(parsed["is_duplicate"]),
        "confidence": float(parsed["confidence"]),
        "rationale": str(parsed["rationale"]),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def detect_duplicates(
    event_id: str,
    redacted_text: str,
    repo_full_name: str,
    env: Any,
    db: Any,
    do_stub: Any,
) -> DuplicateDetectionResult:
    """Detect duplicate vulnerability reports using 3-tier scoring.

    1. Calls ``assert_redacted_before_downstream`` (**first**, non-negotiable).
    2. Retrieves top-k nearest neighbours via ``find_duplicates``.
    3. For each candidate:
        - ``score ≥ 0.85``: accept without LLM (retrieval-only).
        - ``0.80 ≤ score < 0.85``: adjudicate via LLM.
        - ``score < 0.80``: already filtered by ``find_duplicates``.
    4. Persists all candidates to D1.

    Args:
        event_id: The triage event ID.
        redacted_text: The PII-redacted report text (**NEVER** raw payload).
        repo_full_name: Repository scope for Vectorize filtering.
        env: Cloudflare Worker environment object.
        db: Cloudflare D1 database handle.
        do_stub: Durable Object stub for the LLM router.

    Returns:
        A ``DuplicateDetectionResult`` with sorted candidates.

    Raises:
        StateTransitionError: If the event has not passed redaction.
    """
    # ── Gate: security invariant ──────────────────────────────────────────
    await assert_redacted_before_downstream(event_id, db)

    # ── Retrieve candidates from Vectorize ────────────────────────────────
    raw_matches = await find_duplicates(redacted_text, repo_full_name, env, top_k=20)

    if not raw_matches:
        return DuplicateDetectionResult(
            event_id=event_id,
            candidates=[],
            top_candidate=None,
            detection_method="no_duplicates",
        )

    # ── 3-tier scoring ────────────────────────────────────────────────────
    candidates: list[DuplicateCandidate] = []
    used_llm = False

    for match in raw_matches:
        candidate_event_id = match["event_id"]
        score = match["score"]

        # Skip self-matches
        if candidate_event_id == event_id:
            continue

        if score >= AUTO_ACCEPT_THRESHOLD:
            # Tier 1: High confidence — accept without LLM
            candidates.append(
                DuplicateCandidate(
                    event_id=candidate_event_id,
                    similarity_score=score,
                    llm_confirmed=True,
                    llm_confidence=None,
                    llm_rationale=None,
                    detection_method="retrieval_only",
                )
            )
        elif score >= ADJUDICATION_THRESHOLD:
            # Tier 2: Borderline — LLM adjudication required
            candidate_text = await _get_candidate_summary_text(candidate_event_id, db)
            if candidate_text is None:
                logger.warning(
                    "No summary text found for candidate %s — skipping adjudication",
                    candidate_event_id,
                )
                continue

            adjudication = await adjudicate_duplicate(redacted_text, candidate_text, env, do_stub)
            used_llm = True

            if adjudication["is_duplicate"] and adjudication["confidence"] >= LLM_CONFIDENCE_THRESHOLD:
                candidates.append(
                    DuplicateCandidate(
                        event_id=candidate_event_id,
                        similarity_score=score,
                        llm_confirmed=True,
                        llm_confidence=adjudication["confidence"],
                        llm_rationale=adjudication["rationale"],
                        detection_method="retrieval_plus_llm",
                    )
                )
            else:
                candidates.append(
                    DuplicateCandidate(
                        event_id=candidate_event_id,
                        similarity_score=score,
                        llm_confirmed=False,
                        llm_confidence=adjudication["confidence"],
                        llm_rationale=adjudication["rationale"],
                        detection_method="llm_rejected",
                    )
                )

    # ── Sort by similarity score descending ───────────────────────────────
    candidates.sort(key=lambda c: c.similarity_score, reverse=True)

    # ── Persist to D1 ─────────────────────────────────────────────────────
    confirmed = [c for c in candidates if c.llm_confirmed]
    await _store_candidates(db, event_id, candidates)

    # ── Build result ──────────────────────────────────────────────────────
    if not confirmed:
        overall_method = "no_duplicates"
    elif used_llm:
        overall_method = "retrieval_plus_llm"
    else:
        overall_method = "retrieval_only"

    return DuplicateDetectionResult(
        event_id=event_id,
        candidates=confirmed,
        top_candidate=confirmed[0] if confirmed else None,
        detection_method=overall_method,
    )
