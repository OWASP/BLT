"""
Token-optimized triage summarizer for the Toasty pipeline.

This module is the **sole consumer** of LLM output in the triage flow.
It receives ``redacted_text`` (never raw payload), builds a token-budgeted
prompt, calls the LLM via the policy-driven router, validates the JSON
response against a strict schema, and persists the result in D1.

Security invariants
-------------------
* ``assert_redacted_before_downstream`` is the **first** call inside
  ``summarize()`` — it gates all downstream processing.
* Every extracted reproduction step is re-redacted through the native
  regex engine before storage.
* The LLM is constrained to the OWASP Top 25 CWEs; any hallucinated
  CWE ID is replaced with ``CWE-UNKNOWN``.

Token budget
------------
* Model input ceiling: **1200 tokens**
* Report body allocation: **550 tokens**
* Duplicate snippets allocation: **250 tokens**
* System prompt + policy: ~**200 tokens** (fixed overhead)
* Executive summary output: **≤ 150 words**
* Reviewer pack output: **≤ 400 words**
"""

from __future__ import annotations

import dataclasses
import json
import logging
import math
import re
import uuid
from typing import Any

from src.errors import LLMUnavailableError
from src.llm_client import call_llm
from src.native_recognizers import apply_native_redaction
from src.redaction_engine import assert_redacted_before_downstream

logger = logging.getLogger("toasty.summarizer")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOKEN_MULTIPLIER = 1.3  # conservative word → token ratio
MAX_INPUT_TOKENS = 1200
REPORT_TOKEN_BUDGET = 550
DUPLICATE_TOKEN_BUDGET = 250
MAX_EXECUTIVE_WORDS = 150
MAX_REVIEWER_WORDS = 400
MAX_REPRO_STEPS = 5
MAX_REPRO_STEP_CHARS = 200
CONVERSATION_TOKEN_BUDGET = 200

# ---------------------------------------------------------------------------
# OWASP Top 25 CWE allow-list
# ---------------------------------------------------------------------------

ALLOWED_CWES: frozenset[str] = frozenset(
    {
        "CWE-20",  # Improper Input Validation
        "CWE-22",  # Path Traversal
        "CWE-77",  # Command Injection
        "CWE-78",  # OS Command Injection
        "CWE-79",  # Cross-site Scripting (XSS)
        "CWE-89",  # SQL Injection
        "CWE-94",  # Code Injection
        "CWE-116",  # Improper Encoding or Escaping
        "CWE-119",  # Buffer Overflow
        "CWE-125",  # Out-of-bounds Read
        "CWE-190",  # Integer Overflow
        "CWE-200",  # Exposure of Sensitive Information
        "CWE-269",  # Improper Privilege Management
        "CWE-276",  # Incorrect Default Permissions
        "CWE-287",  # Improper Authentication
        "CWE-306",  # Missing Authentication for Critical Function
        "CWE-352",  # Cross-Site Request Forgery (CSRF)
        "CWE-362",  # Race Condition
        "CWE-416",  # Use After Free
        "CWE-434",  # Unrestricted File Upload
        "CWE-476",  # NULL Pointer Dereference
        "CWE-502",  # Deserialization of Untrusted Data
        "CWE-611",  # XML External Entity (XXE)
        "CWE-787",  # Out-of-bounds Write
        "CWE-798",  # Use of Hard-coded Credentials
        "CWE-862",  # Missing Authorization
        "CWE-863",  # Incorrect Authorization
        "CWE-918",  # Server-Side Request Forgery (SSRF)
        "CWE-UNKNOWN",
    }
)

_CWE_PATTERN = re.compile(r"^CWE-\d+$")

# ---------------------------------------------------------------------------
# System prompt — hardcoded for Pyodide compatibility (no fs reads)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a security triage assistant for OWASP BLT.
You analyze redacted vulnerability reports and produce structured JSON summaries.

RULES:
1. You MUST respond with valid JSON only. No prose. No markdown. No explanation.
2. Never generate, guess, or reconstruct any personal information.
3. If uncertain about any field, use null.
4. CWE hints MUST be from this list ONLY: CWE-20, CWE-22, CWE-77, CWE-78, CWE-79, CWE-89, CWE-94, CWE-116, CWE-119, CWE-125, CWE-190, CWE-200, CWE-269, CWE-276, CWE-287, CWE-306, CWE-352, CWE-362, CWE-416, CWE-434, CWE-476, CWE-502, CWE-611, CWE-787, CWE-798, CWE-862, CWE-863, CWE-918. If unsure, use "CWE-UNKNOWN".

OUTPUT SCHEMA (respond with EXACTLY this structure):
{
  "executive_summary": "<concise summary, max 150 words>",
  "reviewer_pack": "<detailed analysis for security reviewers, max 400 words>",
  "cwe_hints": ["CWE-XX", ...],
  "repro_steps": ["step 1", "step 2", ...],
  "confidence": 0.85
}"""

# ---------------------------------------------------------------------------
# Data contract
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class TriageSummary:
    """Immutable output of the triage summarizer.

    Attributes:
        event_id: The triage event this summary belongs to.
        executive_summary: Concise summary (≤ 150 words).
        reviewer_pack: Detailed reviewer analysis (≤ 400 words).
        cwe_hints: Validated CWE identifiers from the OWASP Top 25.
        repro_steps: Reproduction steps, re-redacted via regex fallback.
        confidence: LLM self-reported confidence score (0.0–1.0).
        model_used: Provider and model identifier string.
        token_usage: Prompt and completion token counts.
    """

    event_id: str
    executive_summary: str
    reviewer_pack: str
    cwe_hints: list[str]
    repro_steps: list[str]
    confidence: float
    model_used: str
    token_usage: dict[str, int]


# ---------------------------------------------------------------------------
# Token estimation and truncation
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Estimate the token count for a text string.

    Uses a conservative word-based heuristic: each word maps to
    approximately 1.3 tokens on average for English text.

    Args:
        text: The input text to estimate.

    Returns:
        Estimated token count (rounded up).
    """
    if not text or not text.strip():
        return 0
    return math.ceil(len(text.split()) * TOKEN_MULTIPLIER)


def truncate_to_token_budget(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token budget.

    Breaks on sentence boundaries when possible.  If the text is
    already within budget, it is returned unchanged.

    Args:
        text: The input text to truncate.
        max_tokens: Maximum allowed tokens.

    Returns:
        The (possibly truncated) text that fits within *max_tokens*.
    """
    if not text or not text.strip():
        return ""

    if estimate_tokens(text) <= max_tokens:
        return text

    # Convert token budget to approximate word count.
    max_words = int(max_tokens / TOKEN_MULTIPLIER)
    words = text.split()
    truncated_words = words[:max_words]
    truncated = " ".join(truncated_words)

    # Try to break on a sentence boundary (last sentence-ending punctuation).
    last_sentence_end = max(
        truncated.rfind(". "),
        truncated.rfind("! "),
        truncated.rfind("? "),
        truncated.rfind(".\n"),
        truncated.rfind("!\n"),
        truncated.rfind("?\n"),
    )

    if last_sentence_end > len(truncated) // 3:
        # Only break on sentence boundary if it preserves at least 1/3 of content.
        truncated = truncated[: last_sentence_end + 1]

    return truncated.strip()


def _truncate_to_word_limit(text: str, max_words: int) -> str:
    """Truncate text to a maximum word count.

    Args:
        text: The input text.
        max_words: Maximum number of words.

    Returns:
        The truncated text.
    """
    if not text:
        return ""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------


def build_triage_messages(
    redacted_text: str,
    duplicate_snippets: list[str] | None = None,
    conversation_turns: list[dict] | None = None,
) -> list[dict[str, str]]:
    """Build an OpenAI-format messages list for the triage summarizer.

    Enforces strict token budgets:
        - ``redacted_text``: ≤ 550 tokens (reduced to 350 when conversation context present)
        - ``duplicate_snippets``: ≤ 250 tokens total
        - ``conversation_turns``: ≤ 200 tokens (when provided)
        - System prompt: ~200 tokens (fixed)
        - Total input: ≤ 1200 tokens

    Args:
        redacted_text: The PII-redacted vulnerability report text.
        duplicate_snippets: Optional list of related report snippets
            for context.
        conversation_turns: Optional list of conversation turn dicts
            with ``role`` and ``content`` keys for multi-turn context.

    Returns:
        A list of message dicts with ``role`` and ``content`` keys.
    """
    # When conversation context is present, reduce report budget to make room
    report_budget = REPORT_TOKEN_BUDGET - CONVERSATION_TOKEN_BUDGET if conversation_turns else REPORT_TOKEN_BUDGET
    truncated_report = truncate_to_token_budget(redacted_text, report_budget)

    duplicate_context = ""
    if duplicate_snippets:
        joined = "\n---\n".join(duplicate_snippets)
        duplicate_context = truncate_to_token_budget(joined, DUPLICATE_TOKEN_BUDGET)

    user_content_parts = [f"REPORT:\n{truncated_report}"]
    if duplicate_context:
        user_content_parts.append(f"\nDUPLICATE_CONTEXT:\n{duplicate_context}")

    if conversation_turns:
        retained_lines = []
        current_tokens = 0
        for turn in reversed(conversation_turns):
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            turn_line = f"[{role}] {content}"

            line_tokens = estimate_tokens(turn_line)
            if current_tokens + line_tokens > CONVERSATION_TOKEN_BUDGET:
                if not retained_lines:
                    retained_lines.append(truncate_to_token_budget(turn_line, CONVERSATION_TOKEN_BUDGET))
                break

            retained_lines.append(turn_line)
            current_tokens += line_tokens

        retained_lines.reverse()
        conversation_text = "\n".join(retained_lines)
        user_content_parts.append(f"\nCONVERSATION_CONTEXT:\n{conversation_text}")

    user_content = "\n".join(user_content_parts)

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


# ---------------------------------------------------------------------------
# Output validation
# ---------------------------------------------------------------------------


def validate_triage_output(data: dict) -> tuple[bool, list[str]]:
    """Validate LLM output against the triage JSON schema.

    Checks presence and types of all required fields, enforces
    word limits on summary fields, and validates CWE format.

    Args:
        data: The parsed JSON dict from the LLM response.

    Returns:
        A tuple of ``(is_valid, error_messages)``.  If valid, the
        error list is empty.
    """
    errors: list[str] = []

    # --- executive_summary ---
    es = data.get("executive_summary")
    if not isinstance(es, str) or not es.strip():
        errors.append("executive_summary: missing or not a non-empty string")
    elif len(es.split()) > MAX_EXECUTIVE_WORDS:
        errors.append(f"executive_summary: exceeds {MAX_EXECUTIVE_WORDS} words ({len(es.split())} found)")

    # --- reviewer_pack ---
    rp = data.get("reviewer_pack")
    if rp is not None and not isinstance(rp, str):
        errors.append("reviewer_pack: must be a string or null")
    elif isinstance(rp, str) and len(rp.split()) > MAX_REVIEWER_WORDS:
        errors.append(f"reviewer_pack: exceeds {MAX_REVIEWER_WORDS} words ({len(rp.split())} found)")

    # --- cwe_hints ---
    cwe = data.get("cwe_hints")
    if not isinstance(cwe, list):
        errors.append("cwe_hints: missing or not a list")
    else:
        for i, hint in enumerate(cwe):
            if not isinstance(hint, str):
                errors.append(f"cwe_hints[{i}]: not a string")
            elif hint != "CWE-UNKNOWN" and not _CWE_PATTERN.match(hint):
                errors.append(f"cwe_hints[{i}]: invalid format '{hint}'")

    # --- repro_steps ---
    rs = data.get("repro_steps")
    if rs is not None and not isinstance(rs, list):
        errors.append("repro_steps: must be a list or null")
    elif isinstance(rs, list):
        for i, step in enumerate(rs):
            if not isinstance(step, str):
                errors.append(f"repro_steps[{i}]: not a string")

    # --- confidence ---
    conf = data.get("confidence")
    if conf is None:
        errors.append("confidence: missing")
    elif not isinstance(conf, (int, float)):
        errors.append(f"confidence: not a number (got {type(conf).__name__})")
    elif not 0.0 <= float(conf) <= 1.0:
        errors.append(f"confidence: out of range [0.0, 1.0] (got {conf})")

    return (len(errors) == 0, errors)


def sanitize_cwe_hints(hints: list[str]) -> list[str]:
    """Replace any CWE ID not in the OWASP Top 25 with ``CWE-UNKNOWN``.

    Args:
        hints: Raw CWE hint strings from the LLM.

    Returns:
        Sanitized list where every entry is either a valid OWASP
        Top 25 CWE or ``CWE-UNKNOWN``.
    """
    sanitized: list[str] = []
    for hint in hints:
        cleaned = hint.strip().upper()
        if cleaned in ALLOWED_CWES:
            sanitized.append(cleaned)
        elif _CWE_PATTERN.match(cleaned):
            logger.warning("Hallucinated CWE rejected: %s → CWE-UNKNOWN", cleaned)
            sanitized.append("CWE-UNKNOWN")
        else:
            sanitized.append("CWE-UNKNOWN")
    return sanitized


# ---------------------------------------------------------------------------
# Reproduction step extraction
# ---------------------------------------------------------------------------

_NUMBERED_STEP = re.compile(r"^\s*\d+[.)]\s+(.+)", re.MULTILINE)
_CURL_COMMAND = re.compile(r"(curl\s+.+?)(?:\n|$)", re.IGNORECASE)
_HTTP_METHOD = re.compile(r"((?:GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+\S+)", re.MULTILINE)


def extract_repro_steps(text: str) -> list[str]:
    """Extract reproduction steps from unstructured text.

    Looks for numbered list items, ``curl`` commands, and HTTP method
    lines.  Returns at most ``MAX_REPRO_STEPS`` items, each truncated
    to ``MAX_REPRO_STEP_CHARS``.

    Args:
        text: The source text to search for reproduction steps.

    Returns:
        A deduplicated list of extracted step strings.
    """
    if not text:
        return []

    steps: list[str] = []
    seen: set[str] = set()

    for pattern in [_NUMBERED_STEP, _CURL_COMMAND, _HTTP_METHOD]:
        for match in pattern.finditer(text):
            step = match.group(1).strip() if match.lastindex else match.group(0).strip()
            step_normalised = step.lower()

            if step_normalised in seen or not step:
                continue
            seen.add(step_normalised)

            if len(step) > MAX_REPRO_STEP_CHARS:
                step = step[:MAX_REPRO_STEP_CHARS]

            steps.append(step)
            if len(steps) >= MAX_REPRO_STEPS:
                return steps

    return steps


def _re_redact_repro_steps(steps: list[str]) -> list[str]:
    """Run each reproduction step through the native redaction engine.

    This is the critical PII safety net — the LLM may reconstruct
    PII (e.g. IP addresses, emails) in its repro step output, so
    we re-redact every step before storage.

    Args:
        steps: Raw reproduction step strings.

    Returns:
        Redacted versions of each step.
    """
    redacted_steps: list[str] = []
    for step in steps:
        redacted_text, _matches = apply_native_redaction(step)
        redacted_steps.append(redacted_text)
    return redacted_steps


# ---------------------------------------------------------------------------
# Fallback summary construction
# ---------------------------------------------------------------------------


def _build_fallback_summary(event_id: str, redacted_text: str) -> TriageSummary:
    """Build a minimal TriageSummary when all LLM providers are unavailable.

    Uses the first 150 words of ``redacted_text`` as the executive
    summary.  No CWE classification is attempted.

    Args:
        event_id: The triage event ID.
        redacted_text: The PII-redacted text to excerpt from.

    Returns:
        A minimal ``TriageSummary`` with ``confidence=0.0``.
    """
    words = redacted_text.split()
    excerpt = " ".join(words[:MAX_EXECUTIVE_WORDS]) if words else ""

    return TriageSummary(
        event_id=event_id,
        executive_summary=excerpt,
        reviewer_pack="",
        cwe_hints=[],
        repro_steps=[],
        confidence=0.0,
        model_used="fallback:truncation",
        token_usage={"prompt_tokens": 0, "completion_tokens": 0},
    )


# ---------------------------------------------------------------------------
# D1 persistence
# ---------------------------------------------------------------------------


async def _store_summary(db: Any, summary: TriageSummary) -> None:
    """INSERT a TriageSummary into the D1 ``triage_summaries`` table.

    Args:
        db: The async D1 database handle.
        summary: The summary to persist.
    """
    summary_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO triage_summaries "
        "(id, triage_event_id, executive_summary, reviewer_pack, "
        "cwe_hints, repro_steps, confidence, model_used, "
        "prompt_tokens, completion_tokens) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            summary_id,
            summary.event_id,
            summary.executive_summary,
            summary.reviewer_pack,
            json.dumps(summary.cwe_hints),
            json.dumps(summary.repro_steps),
            summary.confidence,
            summary.model_used,
            summary.token_usage.get("prompt_tokens", 0),
            summary.token_usage.get("completion_tokens", 0),
        ],
    )


async def _transition_state(db: Any, event_id: str, new_status: str) -> None:
    """Advance the triage event state machine to *new_status*.

    Args:
        db: The async D1 database handle.
        event_id: The event to transition.
        new_status: The target state (e.g. ``"summarized"``).
    """
    await db.execute(
        "UPDATE triage_events SET status = ? WHERE id = ?",
        [new_status, event_id],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def summarize(
    redacted_text: str,
    env: Any,
    db: Any,
    do_stub: Any,
    event_id: str,
    duplicate_snippets: list[str] | None = None,
    conversation_turns: list[dict] | None = None,
) -> TriageSummary:
    """Produce a triage summary for a redacted vulnerability report.

    This is the main entry point for the summarizer pipeline.  It
    enforces the full security contract before processing:

    1. Calls ``assert_redacted_before_downstream`` (non-negotiable gate).
    2. Builds a token-budgeted prompt.
    3. Calls the LLM via the policy-driven router.
    4. Parses and validates the JSON response.
    5. Sanitizes CWE hints against the OWASP Top 25.
    6. Extracts and re-redacts reproduction steps.
    7. Persists the result in D1 and transitions state.

    On ``LLMUnavailableError``, a minimal fallback summary is produced
    from the first 150 words of the redacted text.

    Args:
        redacted_text: The PII-redacted vulnerability report body.
        env: Cloudflare Worker environment object.
        db: Async D1 database handle.
        do_stub: Durable Object stub for the LLM router.
        event_id: The triage event identifier.
        duplicate_snippets: Optional related report snippets.
        conversation_turns: Optional list of prior conversation turns
            for multi-turn context.

    Returns:
        A fully validated ``TriageSummary``.

    Raises:
        StateTransitionError: If the event is not in ``redaction_passed``.
    """
    # ── Gate: security invariant ──────────────────────────────────────
    await assert_redacted_before_downstream(event_id, db)

    # ── Build prompt ──────────────────────────────────────────────────
    messages = build_triage_messages(redacted_text, duplicate_snippets, conversation_turns)

    # ── Call LLM ──────────────────────────────────────────────────────
    try:
        raw_response = await call_llm(messages, env, do_stub)
    except LLMUnavailableError:
        logger.warning("All LLM providers unavailable for %s; using fallback summary", event_id)
        fallback = _build_fallback_summary(event_id, redacted_text)
        await _store_summary(db, fallback)
        await _transition_state(db, event_id, "summarized")
        return fallback

    # ── Parse JSON ────────────────────────────────────────────────────
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON for %s; using fallback summary", event_id)
        fallback = _build_fallback_summary(event_id, redacted_text)
        await _store_summary(db, fallback)
        await _transition_state(db, event_id, "summarized")
        return fallback

    # ── Validate schema ───────────────────────────────────────────────
    is_valid, validation_errors = validate_triage_output(parsed)
    if not is_valid:
        logger.warning("LLM output failed validation for %s: %s", event_id, validation_errors)
        fallback = _build_fallback_summary(event_id, redacted_text)
        await _store_summary(db, fallback)
        await _transition_state(db, event_id, "summarized")
        return fallback

    # ── Post-process: sanitize CWEs ───────────────────────────────────
    raw_cwes = parsed.get("cwe_hints", [])
    sanitized_cwes = sanitize_cwe_hints(raw_cwes)

    # ── Post-process: executive summary word limit ────────────────────
    exec_summary = _truncate_to_word_limit(
        parsed.get("executive_summary", ""),
        MAX_EXECUTIVE_WORDS,
    )

    # ── Post-process: reviewer pack word limit ────────────────────────
    reviewer_pack = _truncate_to_word_limit(
        parsed.get("reviewer_pack", "") or "",
        MAX_REVIEWER_WORDS,
    )

    # ── Post-process: extract and re-redact repro steps ───────────────
    raw_repro = parsed.get("repro_steps", []) or []
    repro_steps = _re_redact_repro_steps(raw_repro[:MAX_REPRO_STEPS])

    # ── Build result ──────────────────────────────────────────────────
    confidence = float(parsed.get("confidence", 0.0))
    confidence = max(0.0, min(1.0, confidence))  # Clamp to [0.0, 1.0]

    prompt_tokens = estimate_tokens(messages[0]["content"] + messages[1]["content"])

    summary = TriageSummary(
        event_id=event_id,
        executive_summary=exec_summary,
        reviewer_pack=reviewer_pack,
        cwe_hints=sanitized_cwes,
        repro_steps=repro_steps,
        confidence=confidence,
        model_used="llm_router",
        token_usage={
            "prompt_tokens": prompt_tokens,
            "completion_tokens": estimate_tokens(raw_response),
        },
    )

    # ── Persist and transition ────────────────────────────────────────
    await _store_summary(db, summary)
    await _transition_state(db, event_id, "summarized")
    logger.info("Summarized event %s (confidence=%.2f, cwes=%s)", event_id, confidence, sanitized_cwes)

    return summary
