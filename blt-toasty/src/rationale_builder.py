"""Rationale builder for the Toasty triage explainability layer.

This module implements the Label Rationale API (Issue #10).  Every triage
decision — CWE classification, duplicate detection — must carry a
machine-readable rationale backed by evidence extracted exclusively from
``redacted_text``.  The ``audit_completeness_check()`` gate blocks MCP
export with HTTP 424 when any required audit record is absent from D1.

Security invariants
-------------------
* Evidence snippets are **always** extracted from ``redacted_text``, never
  from the raw payload.  A ``ValueError`` is raised at call-time if the
  caller passes ``None`` or an empty string as the text source.
* Each extracted snippet is validated through ``apply_native_redaction()``.
  If the regex engine detects any PII in a snippet, that snippet is
  **dropped entirely** — it is never truncated or partially scrubbed.

Audit completeness rule
-----------------------
MCP export is blocked (HTTP 424) unless ALL three of the following exist
in D1 for the given ``event_id``:

1. A row in ``triage_summaries`` (summarizer ran successfully).
2. A row in ``triage_rationale`` (this module wrote it).
3. At least one row in ``redaction_audit`` (redaction engine ran).

The ``audit_completeness_check()`` function returns a ``(bool, list[str])``
tuple so the route handler can report exactly which fields are missing.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import re
from typing import Any

from src.native_recognizers import apply_native_redaction

logger = logging.getLogger("toasty.rationale_builder")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_EVIDENCE_SNIPPETS = 3
MAX_SNIPPET_CHARS = 150
MAX_REASONING_CHARS = 300

# Human-readable labels for the OWASP Top 25 CWEs.
CWE_LABELS: dict[str, str] = {
    "CWE-20": "Improper Input Validation",
    "CWE-22": "Path Traversal",
    "CWE-77": "Command Injection",
    "CWE-78": "OS Command Injection",
    "CWE-79": "Cross-Site Scripting (XSS)",
    "CWE-89": "SQL Injection",
    "CWE-94": "Code Injection",
    "CWE-116": "Improper Encoding or Escaping",
    "CWE-119": "Buffer Overflow",
    "CWE-125": "Out-of-bounds Read",
    "CWE-190": "Integer Overflow or Wraparound",
    "CWE-200": "Exposure of Sensitive Information",
    "CWE-269": "Improper Privilege Management",
    "CWE-276": "Incorrect Default Permissions",
    "CWE-287": "Improper Authentication",
    "CWE-306": "Missing Authentication for Critical Function",
    "CWE-352": "Cross-Site Request Forgery (CSRF)",
    "CWE-362": "Race Condition",
    "CWE-416": "Use After Free",
    "CWE-434": "Unrestricted File Upload",
    "CWE-476": "NULL Pointer Dereference",
    "CWE-502": "Deserialization of Untrusted Data",
    "CWE-611": "XML External Entity (XXE)",
    "CWE-787": "Out-of-bounds Write",
    "CWE-798": "Use of Hard-coded Credentials",
    "CWE-862": "Missing Authorization",
    "CWE-863": "Incorrect Authorization",
    "CWE-918": "Server-Side Request Forgery (SSRF)",
    "CWE-UNKNOWN": "Unknown / Unclassified",
}

# Per-CWE keyword lists used to locate supporting evidence in redacted_text.
# Keywords are case-insensitive and matched as substrings within a 200-char
# window around each match site.
_CWE_KEYWORDS: dict[str, list[str]] = {
    "CWE-20": ["input", "validation", "sanitiz", "unvalidated", "user-supplied", "user_input"],
    "CWE-22": ["../", "..\\", "%2e%2e", "path traversal", "/etc/", "directory", "file path"],
    "CWE-77": ["exec(", "system(", "popen", "shell", "command injection", "cmd"],
    "CWE-78": ["os.system", "subprocess", "exec(", "popen", "shell=true", "; rm", "| cat", "cmd /c"],
    "CWE-79": ["<script", "onerror=", "onclick=", "javascript:", "alert(", "innerhtml", "document.cookie", "xss"],
    "CWE-89": ["select ", "insert ", "update ", "delete from", "where ", "union ", "drop ", "sql", "query"],
    "CWE-94": ["eval(", "exec(", "compile(", "__import__", "code injection", "dynamic eval"],
    "CWE-116": ["encod", "escap", "htmlentities", "urlencode", "base64", "encoding"],
    "CWE-119": ["buffer", "overflow", "strcpy", "sprintf", "gets(", "memcpy", "bounds"],
    "CWE-125": ["out-of-bounds read", "buffer over-read", "read past", "oob read"],
    "CWE-190": ["integer overflow", "wraparound", "int overflow", "arithmetic overflow"],
    "CWE-200": ["sensitive", "information disclosure", "leak", "exposure", "password", "secret"],
    "CWE-269": ["privilege", "escalation", "root", "admin", "permission", "sudo"],
    "CWE-276": ["default permission", "chmod", "world-writable", "umask"],
    "CWE-287": ["authentication", "bypass", "login", "credential", "token", "session"],
    "CWE-306": ["unauthenticated", "no auth", "missing authentication", "without login"],
    "CWE-352": ["csrf", "cross-site request", "forged request", "token mismatch"],
    "CWE-362": ["race condition", "toctou", "time-of-check", "concurrent", "thread"],
    "CWE-416": ["use after free", "use-after-free", "dangling pointer", "uaf"],
    "CWE-434": ["file upload", "unrestricted upload", "multipart", "extension check"],
    "CWE-476": ["null pointer", "null dereference", "segfault", "nullptr", "nullpointerexception"],
    "CWE-502": ["pickle", "yaml.load", "deserializ", "marshal", "unserializ"],
    "CWE-611": ["xxe", "xml external entity", "<!entity", "doctype", "external entity"],
    "CWE-787": ["out-of-bounds write", "buffer write", "stack overflow", "heap overflow"],
    "CWE-798": ["hardcoded", "hard-coded", "hardcode", "credential", "api key", "password ="],
    "CWE-862": ["missing authorization", "no authorization", "access control", "unauthorized"],
    "CWE-863": ["incorrect authorization", "privilege check", "permission check", "wrong role"],
    "CWE-918": ["ssrf", "server-side request", "internal", "169.254", "metadata", "localhost"],
}

# Window (in characters) around each keyword match from which to extract a snippet.
_SNIPPET_CONTEXT_WINDOW = 100

# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class CWERationale:
    """Rationale record for a single CWE hint.

    Attributes:
        cwe_id: The CWE identifier (e.g. ``"CWE-89"``).
        label: Human-readable CWE name.
        evidence_snippets: Up to three text excerpts from ``redacted_text``
            that support this classification.  Each snippet is at most
            150 characters and contains no raw PII.
        confidence: Propagated from the summarizer's ``TriageSummary.confidence``.
        reasoning: One or two sentence plain-language explanation.
    """

    cwe_id: str
    label: str
    evidence_snippets: list[str]
    confidence: float
    reasoning: str


@dataclasses.dataclass(frozen=True, slots=True)
class DuplicateRationale:
    """Rationale record for the duplicate detection decision.

    Attributes:
        top_candidate_event_id: The highest-scoring candidate event ID, or
            ``None`` when no duplicate was found.
        similarity_score: Vectorize cosine similarity (0.0–1.0), or ``None``.
        llm_confirmed: Whether LLM adjudication confirmed the duplicate.
        llm_confidence: LLM self-reported confidence, or ``None`` if not called.
        llm_rationale: LLM explanation string, or ``None`` if not called.
        detection_method: One of ``"retrieval_only"``, ``"retrieval_plus_llm"``,
            ``"llm_rejected"``, or ``"no_duplicates"``.
    """

    top_candidate_event_id: str | None
    similarity_score: float | None
    llm_confirmed: bool
    llm_confidence: float | None
    llm_rationale: str | None
    detection_method: str


@dataclasses.dataclass(frozen=True, slots=True)
class ConfidenceTrace:
    """Per-component confidence breakdown for the full triage pipeline.

    Attributes:
        redaction_entity_count: Total entities redacted in stage 1.
        redaction_confidence_min: Minimum confidence score across all
            ``redaction_audit`` entries (proxy for worst-case redaction quality).
        summary_confidence: LLM self-reported confidence from ``TriageSummary``.
        duplicate_similarity_score: Highest vectorize similarity score seen,
            or ``None`` if no candidate met the threshold.
        llm_adjudication_confidence: LLM adjudication confidence, or ``None``
            if LLM was not invoked for duplicate detection.
        overall_triage_confidence: Geometric mean of the non-None component
            scores, clamped to ``[0.0, 1.0]``.
    """

    redaction_entity_count: int
    redaction_confidence_min: float
    summary_confidence: float
    duplicate_similarity_score: float | None
    llm_adjudication_confidence: float | None
    overall_triage_confidence: float


# ---------------------------------------------------------------------------
# Evidence extraction (PII-safe)
# ---------------------------------------------------------------------------


def _is_pii_free(snippet: str) -> bool:
    """Return True only if the snippet contains no detectable PII.

    Runs the snippet through ``apply_native_redaction()``; if any entity is
    detected the snippet is considered tainted.

    Args:
        snippet: The candidate evidence string.

    Returns:
        ``True`` when no PII patterns match; ``False`` otherwise.
    """
    _redacted, matches = apply_native_redaction(snippet)
    return len(matches) == 0


def _extract_snippets_for_cwe(cwe_id: str, redacted_text: str) -> list[str]:
    """Extract up to ``MAX_EVIDENCE_SNIPPETS`` evidence snippets for *cwe_id*.

    Each snippet is a ``MAX_SNIPPET_CHARS``-character excerpt from
    ``redacted_text`` centred around a keyword match.  Snippets that fail the
    PII check are silently dropped; the resulting list may be empty.

    Args:
        cwe_id: A valid CWE identifier.
        redacted_text: PII-free vulnerability report text.

    Returns:
        A deduplicated list of safe evidence snippets.
    """
    keywords = _CWE_KEYWORDS.get(cwe_id, [])
    snippets: list[str] = []
    seen_starts: set[int] = set()

    for keyword in keywords:
        if len(snippets) >= MAX_EVIDENCE_SNIPPETS:
            break

        for match in re.finditer(re.escape(keyword), redacted_text, re.IGNORECASE):
            start = max(0, match.start() - _SNIPPET_CONTEXT_WINDOW)
            end = min(len(redacted_text), match.end() + _SNIPPET_CONTEXT_WINDOW)

            # Avoid overlapping snippets (deduplicate by window origin).
            if start in seen_starts:
                continue
            seen_starts.add(start)

            raw_snippet = redacted_text[start:end].strip()
            # Truncate to MAX_SNIPPET_CHARS.
            if len(raw_snippet) > MAX_SNIPPET_CHARS:
                raw_snippet = raw_snippet[:MAX_SNIPPET_CHARS]

            # PII safety gate — drop the snippet if any PII is detected.
            if not _is_pii_free(raw_snippet):
                logger.debug("Dropped tainted snippet for %s at offset %d", cwe_id, start)
                continue

            snippets.append(raw_snippet)
            if len(snippets) >= MAX_EVIDENCE_SNIPPETS:
                break

    return snippets


# ---------------------------------------------------------------------------
# Builder functions
# ---------------------------------------------------------------------------


def build_cwe_rationale(
    cwe_hints: list[str],
    redacted_text: str,
    summary_confidence: float,
) -> list[CWERationale]:
    """Build a ``CWERationale`` record for each CWE hint.

    Evidence snippets are extracted exclusively from ``redacted_text`` and
    validated for PII absence before inclusion.

    Args:
        cwe_hints: Validated CWE identifiers from the summarizer output.
        redacted_text: The PII-free vulnerability report text.  Must be
            non-empty — a ``ValueError`` is raised otherwise.
        summary_confidence: The summarizer's self-reported confidence score
            (propagated into each ``CWERationale.confidence``).

    Returns:
        A list of ``CWERationale`` objects, one per hint.

    Raises:
        ValueError: If ``redacted_text`` is empty or ``None``.
    """
    if not redacted_text or not redacted_text.strip():
        raise ValueError("redacted_text must be non-empty; raw payload must never be passed here")

    rationales: list[CWERationale] = []
    for cwe_id in cwe_hints:
        label = CWE_LABELS.get(cwe_id, "Unknown")
        snippets = _extract_snippets_for_cwe(cwe_id, redacted_text)

        # Build a concise reasoning sentence based on snippet availability.
        if snippets:
            reasoning = (
                f"The report contains language consistent with {label} ({cwe_id}). "
                f"Evidence was identified in {len(snippets)} excerpt(s) from the redacted text."
            )
        else:
            reasoning = (
                f"The classifier flagged {label} ({cwe_id}) based on overall report context; "
                "no specific keyword-matched excerpt was isolated."
            )

        # Truncate reasoning to MAX_REASONING_CHARS for storage safety.
        if len(reasoning) > MAX_REASONING_CHARS:
            reasoning = reasoning[:MAX_REASONING_CHARS]

        rationales.append(
            CWERationale(
                cwe_id=cwe_id,
                label=label,
                evidence_snippets=snippets,
                confidence=round(max(0.0, min(1.0, float(summary_confidence))), 4),
                reasoning=reasoning,
            )
        )

    return rationales


def build_duplicate_rationale(dup_result: Any | None) -> DuplicateRationale | None:
    """Build a ``DuplicateRationale`` from a ``DuplicateDetectionResult``.

    Args:
        dup_result: A ``DuplicateDetectionResult`` instance, or ``None`` when
            duplicate detection was skipped.

    Returns:
        A ``DuplicateRationale`` if a duplicate candidate exists, otherwise
        ``None``.
    """
    if dup_result is None:
        return None

    if dup_result.detection_method == "no_duplicates" or dup_result.top_candidate is None:
        return None

    top = dup_result.top_candidate
    return DuplicateRationale(
        top_candidate_event_id=top.event_id,
        similarity_score=round(top.similarity_score, 4),
        llm_confirmed=top.llm_confirmed,
        llm_confidence=round(top.llm_confidence, 4) if top.llm_confidence is not None else None,
        llm_rationale=top.llm_rationale,
        detection_method=dup_result.detection_method,
    )


def build_confidence_trace(
    *,
    redaction_entity_count: int,
    redaction_confidence_min: float,
    summary_confidence: float,
    dup_result: Any | None = None,
) -> ConfidenceTrace:
    """Compute a ``ConfidenceTrace`` for the full triage pipeline.

    ``overall_triage_confidence`` is the geometric mean of all non-None
    component scores, clamped to ``[0.0, 1.0]``.

    Args:
        redaction_entity_count: Total number of entities redacted.
        redaction_confidence_min: Minimum per-entity confidence from
            ``redaction_audit`` (use ``1.0`` if no entities were detected).
        summary_confidence: The summarizer's self-reported confidence.
        dup_result: Optional ``DuplicateDetectionResult`` for the event.

    Returns:
        A ``ConfidenceTrace`` with a computed ``overall_triage_confidence``.
    """
    dup_sim: float | None = None
    dup_llm_conf: float | None = None

    if dup_result is not None and dup_result.top_candidate is not None:
        dup_sim = dup_result.top_candidate.similarity_score
        dup_llm_conf = dup_result.top_candidate.llm_confidence

    # Gather all non-None score components for the geometric mean.
    component_scores: list[float] = [
        max(0.0, min(1.0, float(redaction_confidence_min))),
        max(0.0, min(1.0, float(summary_confidence))),
    ]
    if dup_sim is not None:
        component_scores.append(max(0.0, min(1.0, float(dup_sim))))
    if dup_llm_conf is not None:
        component_scores.append(max(0.0, min(1.0, float(dup_llm_conf))))

    if any(s == 0.0 for s in component_scores):
        overall = 0.0
    else:
        product = 1.0
        for score in component_scores:
            product *= score
        overall = round(product ** (1.0 / len(component_scores)), 4)

    return ConfidenceTrace(
        redaction_entity_count=redaction_entity_count,
        redaction_confidence_min=round(max(0.0, min(1.0, float(redaction_confidence_min))), 4),
        summary_confidence=round(max(0.0, min(1.0, float(summary_confidence))), 4),
        duplicate_similarity_score=round(dup_sim, 4) if dup_sim is not None else None,
        llm_adjudication_confidence=round(dup_llm_conf, 4) if dup_llm_conf is not None else None,
        overall_triage_confidence=max(0.0, min(1.0, overall)),
    )


# ---------------------------------------------------------------------------
# Audit completeness gate
# ---------------------------------------------------------------------------


async def audit_completeness_check(event_id: str, db: Any) -> tuple[bool, list[str]]:
    """Verify that all required audit records exist in D1 for *event_id*.

    Queries three tables in parallel (sequential awaits on the D1 driver):

    1. ``triage_summaries`` — the summarizer must have run.
    2. ``triage_rationale`` — this module must have persisted a rationale.
    3. ``redaction_audit`` — the redaction engine must have fired.

    If any record is absent the function returns ``(False, missing_field_names)``
    so the caller can surface a targeted 424 response.  This function does
    **not** raise ``AuditIncompleteError`` itself — that is left to the caller
    so it can decide the appropriate HTTP behaviour.

    Args:
        event_id: The triage event ID to inspect.
        db: An async Cloudflare D1 database handle.

    Returns:
        A tuple ``(is_complete, missing_fields)``.  ``is_complete`` is
        ``True`` iff all three audit records exist.  ``missing_fields`` is an
        empty list when complete.
    """
    missing: list[str] = []

    # 1. triage_summaries
    cursor = await db.execute(
        "SELECT id FROM triage_summaries WHERE triage_event_id = ? LIMIT 1",
        [event_id],
    )
    if cursor.fetchone() is None:
        missing.append("triage_summary")

    # 2. triage_rationale
    cursor = await db.execute(
        "SELECT id FROM triage_rationale WHERE triage_event_id = ? LIMIT 1",
        [event_id],
    )
    if cursor.fetchone() is None:
        missing.append("triage_rationale")

    # 3. redaction_audit — uses triage_event_id per migrations/0001_initial.sql
    cursor = await db.execute(
        "SELECT COUNT(*) FROM redaction_audit WHERE triage_event_id = ?",
        [event_id],
    )
    row = cursor.fetchone()
    if row is None or row[0] == 0:
        missing.append("redaction_audit")

    return (len(missing) == 0, missing)


# ---------------------------------------------------------------------------
# D1 persistence
# ---------------------------------------------------------------------------


async def store_rationale(
    db: Any,
    event_id: str,
    cwe_rationale: list[CWERationale],
    duplicate_rationale: DuplicateRationale | None,
    confidence_trace: ConfidenceTrace,
) -> None:
    """Persist the rationale records to the ``triage_rationale`` D1 table.

    This function is idempotent: if a row already exists for *event_id*
    it is replaced (``INSERT OR REPLACE``), ensuring retries are safe.

    Args:
        db: An async Cloudflare D1 database handle.
        event_id: The triage event ID this rationale belongs to.
        cwe_rationale: List of ``CWERationale`` objects to serialize.
        duplicate_rationale: A ``DuplicateRationale`` or ``None``.
        confidence_trace: The ``ConfidenceTrace`` for this event.
    """
    # id == triage_event_id: deterministic key guarantees INSERT OR REPLACE
    # targets the same row on every retry rather than always inserting a new row.
    cwe_json = json.dumps(
        [dataclasses.asdict(r) for r in cwe_rationale],
        separators=(",", ":"),
    )
    dup_json = (
        json.dumps(dataclasses.asdict(duplicate_rationale), separators=(",", ":")) if duplicate_rationale else None
    )
    trace_json = json.dumps(dataclasses.asdict(confidence_trace), separators=(",", ":"))

    await db.execute(
        "INSERT OR REPLACE INTO triage_rationale "
        "(id, triage_event_id, cwe_rationale, duplicate_rationale, confidence_trace) "
        "VALUES (?, ?, ?, ?, ?)",
        [event_id, event_id, cwe_json, dup_json, trace_json],
    )
    logger.info("Stored rationale for event %s (%d CWEs)", event_id, len(cwe_rationale))


# ---------------------------------------------------------------------------
# Route response helpers
# ---------------------------------------------------------------------------


def build_rationale_response(
    event_id: str,
    cwe_rationale: list[CWERationale],
    duplicate_rationale: DuplicateRationale | None,
    confidence_trace: ConfidenceTrace,
) -> dict[str, Any]:
    """Assemble the JSON-serialisable rationale response dict.

    The response intentionally omits raw ``redaction_map`` content — only
    aggregate counts and entity types are exposed.

    Args:
        event_id: The triage event ID.
        cwe_rationale: List of ``CWERationale`` dataclasses.
        duplicate_rationale: A ``DuplicateRationale`` or ``None``.
        confidence_trace: The ``ConfidenceTrace`` for this event.

    Returns:
        A dict ready for ``json.dumps()``.
    """
    return {
        "event_id": event_id,
        "status": "complete",
        "cwe_rationale": [dataclasses.asdict(r) for r in cwe_rationale],
        "duplicate_rationale": dataclasses.asdict(duplicate_rationale) if duplicate_rationale else None,
        "confidence_trace": dataclasses.asdict(confidence_trace),
    }
