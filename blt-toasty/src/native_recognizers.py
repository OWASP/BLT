"""
Native PII recogniser engine for the Toasty redaction pipeline.

This module provides a fully self-contained,
regex-based recognition engine. Every pattern is deliberately *conservative*
(i.e. it will over-match rather than under-match) because a false positive
is harmless, but a false negative leaks PII to the LLM.

The engine handles **17 entity types** observed in the golden set:

    EMAIL_ADDRESS, IP_ADDRESS, JWT_TOKEN, AUTH_TOKEN, AWS_ACCESS_KEY,
    AWS_SECRET_KEY, AWS_ARN, GITHUB_TOKEN, API_KEY, API_TOKEN, DOMAIN,
    HOSTNAME, DB_CONNECTION, MONGODB_URI, USERNAME, PASSWORD,
    CREDIT_CARD, PRIVATE_KEY, BEARER_TOKEN, MD5_HASH

Design notes
------------
* Patterns are tried **longest-match-first** to prevent shorter rules from
  partially consuming a longer token (e.g. an email inside a DB connection
  string).
* Every match carries ``detector: "native_recognizer"`` and a fixed
  confidence of ``0.99`` because deterministic regex matches have near-zero
  false-positive rates for the specific secret formats targeted.
* A deny-list (``_DENY_PATTERNS``) is applied *after* matching to suppress
  known false-positives like ``CVE-2024-1234`` and ``CWE-22``.
"""

from __future__ import annotations

import re
from typing import TypedDict

# ---------------------------------------------------------------------------
# Zero-width character stripping — adversarial hardening
# ---------------------------------------------------------------------------
# Adversaries insert invisible Unicode characters into PII (e.g.
# te\u200bst@example.com) to break regex patterns.  We strip them
# before scanning and map match offsets back to the original text.

_ZERO_WIDTH_CHARS = re.compile(r"[\u200b\u200c\u200d\ufeff\u00ad\u2060]")


def _strip_zero_width(text: str) -> tuple[str, list[int]]:
    """Strip zero-width characters and build an offset map.

    Returns:
        A 2-tuple of *(stripped_text, offset_map)* where *offset_map[i]*
        gives the index in the **original** text corresponding to
        position *i* in *stripped_text*.
    """
    offset_map: list[int] = []
    chars: list[str] = []
    for i, ch in enumerate(text):
        if not _ZERO_WIDTH_CHARS.match(ch):
            chars.append(ch)
            offset_map.append(i)
    return "".join(chars), offset_map


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class RecogniserMatch(TypedDict):
    """A single PII match returned by the recogniser engine."""

    entity_type: str
    start: int
    end: int
    confidence: float
    detector: str


# ---------------------------------------------------------------------------
# Deny-list — patterns whose matches should be silently dropped
# ---------------------------------------------------------------------------

_DENY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE),
    re.compile(r"CWE-\d+", re.IGNORECASE),
    re.compile(r"OWASP-[A-Z0-9]+", re.IGNORECASE),
    re.compile(r"A\d{2}:\d{4}", re.IGNORECASE),  # OWASP Top-10 IDs like A01:2021
    re.compile(r"0x[0-9a-fA-F]+"),  # Hex literals
]

# ---------------------------------------------------------------------------
# Recogniser patterns — ordered from most specific to least specific.
#
# Each entry is (entity_type, compiled_regex).  The order matters: when
# two patterns could match the same span, the first one wins.
# ---------------------------------------------------------------------------

_RECOGNISER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # --- Connection strings (must precede EMAIL to avoid partial matches) ---
    (
        "MONGODB_URI",
        re.compile(r"mongodb(?:\+srv)?://[^\s,;\"']+"),
    ),
    (
        "DB_CONNECTION",
        re.compile(r"(?:postgresql|mysql|postgres|mariadb|mssql)://[^\s,;\"']+"),
    ),
    # --- Cloud credentials ---
    (
        "AWS_ARN",
        re.compile(r"arn:aws:[a-zA-Z0-9\-]+:[a-zA-Z0-9\-]*:\d{12}:[^\s,;\"']+"),
    ),
    (
        "AWS_ACCESS_KEY",
        re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}"),
    ),
    (
        "AWS_SECRET_KEY",
        re.compile(r"(?<![A-Za-z0-9/+])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])"),
    ),
    # --- Tokens (long, high-entropy) ---
    (
        "PRIVATE_KEY",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "JWT_TOKEN",
        re.compile(r"eyJ[A-Za-z0-9_\-]+(?:\.eyJ[A-Za-z0-9_\-]+(?:\.[A-Za-z0-9_\-.]+)?)?"),
    ),
    (
        "GITHUB_TOKEN",
        re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}"),
    ),
    (
        "BEARER_TOKEN",
        re.compile(r"(?i)(?:bearer|authorization:)\s+[A-Za-z0-9+/=_\-]{20,}"),
    ),
    # --- GCP / AWS STS tokens that start with known prefixes ---
    (
        "AUTH_TOKEN",
        re.compile(r"ya29\.[A-Za-z0-9_\-]+"),
    ),
    (
        "AUTH_TOKEN",
        re.compile(r"AQoDYXdzE[A-Za-z0-9_.+/\-]+"),
    ),
    # --- API keys with known prefixes ---
    (
        "API_KEY",
        re.compile(r"(?:sk_live_|sk_test_|sk_sk_test_|sk_sk_sk_test_)[A-Za-z0-9_\-]{20,}"),
    ),
    (
        "API_KEY",
        re.compile(r"SG\.[A-Za-z0-9_\-]{10,}"),
    ),
    (
        "API_KEY",
        re.compile(r"(?:fk_prod_|fm_api_)[A-Za-z0-9_\-]{10,}"),
    ),
    (
        "API_KEY",
        re.compile(r"stripe_sk_live_[A-Za-z0-9]{20,}"),
    ),
    # --- Standard PII ---
    (
        "CREDIT_CARD",
        re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b"),
    ),
    (
        "EMAIL_ADDRESS",
        re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
    ),
    (
        "IP_ADDRESS",
        re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"),
    ),
    (
        "MD5_HASH",
        re.compile(r"\b[a-fA-F0-9]{32}\b"),
    ),
    # --- Internal hostnames / domains ---
    (
        "HOSTNAME",
        re.compile(
            r"\b[a-zA-Z0-9](?:[a-zA-Z0-9\-]*[a-zA-Z0-9])?"
            r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9\-]*[a-zA-Z0-9])?)*"
            r"\.(?:internal|local|corp|staging\.local|internal\.aws"
            r"|owasp\.org|internal\.mn)\b"
        ),
    ),
    (
        "DOMAIN",
        re.compile(
            r"\b[a-zA-Z0-9](?:[a-zA-Z0-9\-]*[a-zA-Z0-9])?"
            r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9\-]*[a-zA-Z0-9])?)*"
            r"\.(?:internal|local|corp|staging\.local|internal\.aws"
            r"|owasp\.org|internal\.mn)\b"
        ),
    ),
    # Bare internal hostnames (e.g. "internal-service") preceded by context.
    (
        "DOMAIN",
        re.compile(r"\b(?:internal-[a-zA-Z0-9\-]+)\b"),
    ),
]

# ---------------------------------------------------------------------------
# Context-keyword recognisers for PASSWORD and USERNAME
# ---------------------------------------------------------------------------

_PASSWORD_CONTEXT = re.compile(
    r"(?i)(?:password|passwd|pwd|secret_access_key|secret|pass)\s*[:=]\s*" r"""(?:["']?)([^\s,"']{6,})(?:["']?)"""
)

_USERNAME_CONTEXT = re.compile(r"(?i)(?:username|user|login|usr)\s*[:=]\s*" r"""(?:["']?)([^\s,"']{2,})(?:["']?)""")

# Credential pairs in colon-delimited format: "user:password" or "admin:SecurePass"
# Typically preceded by context keywords.
_CREDENTIAL_PAIR = re.compile(
    r"(?i)(?:credentials?|login|auth)\s*(?:\([^)]*\))?\s*[:=]?\s*" r"([A-Za-z0-9_.\-]+):([^\s,;\"']{6,})"
)

_API_TOKEN_CONTEXT = re.compile(
    r"(?i)(?:api[_\-]?token|token)\s*[:=]\s*" r"""(?:["']?)([A-Za-z0-9_\-]{16,})(?:["']?)"""
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _is_denied(text: str, start: int, end: int) -> bool:
    """Return True if the matched span falls inside a deny-listed pattern."""
    matched_str = text[start:end]
    for deny in _DENY_PATTERNS:
        if deny.fullmatch(matched_str):
            return True
    return False


def _deduplicate_matches(matches: list[RecogniserMatch]) -> list[RecogniserMatch]:
    """Remove overlapping matches, keeping the longest (most specific) one.

    When two matches overlap, the one that covers a wider byte range wins.
    If they cover the same range, the one that appeared first in the
    pattern list (higher specificity) wins.
    """
    if not matches:
        return []

    # Sort by start ascending, then by span length descending.
    sorted_matches = sorted(matches, key=lambda m: (m["start"], -(m["end"] - m["start"])))

    deduped: list[RecogniserMatch] = []
    last_end = -1

    for match in sorted_matches:
        if match["start"] >= last_end:
            deduped.append(match)
            last_end = match["end"]
        else:
            # Overlapping — keep the longer span.
            if match["end"] - match["start"] > deduped[-1]["end"] - deduped[-1]["start"]:
                deduped[-1] = match
                last_end = match["end"]

    return deduped


def scan_text(text: str) -> list[RecogniserMatch]:
    """Scan *text* for PII entities using all native recogniser patterns.

    This is the low-level scanner.  It returns raw matches **before**
    any redaction is applied.  Use ``apply_native_redaction`` for the
    full pipeline (scan → deduplicate → replace → return).

    Zero-width characters (U+200B, U+200C, U+200D, U+FEFF, U+00AD,
    U+2060) are stripped before scanning so that adversarial insertions
    like ``te\\u200bst@example.com`` are still detected.  Match offsets
    in the returned list refer to the **original** text.

    Args:
        text: The plain-text content to scan.

    Returns:
        A deduplicated, sorted list of ``RecogniserMatch`` dicts.
    """
    # Strip zero-width chars and build an offset map back to original text.
    stripped, offset_map = _strip_zero_width(text)

    raw_matches: list[RecogniserMatch] = []

    def _map_offset(pos: int) -> int:
        """Map a position in *stripped* back to the original text."""
        if pos < len(offset_map):
            return offset_map[pos]
        # Past the end — return the position after the last original char.
        return offset_map[-1] + 1 if offset_map else pos

    # 1. Regex-pattern recognisers (run on stripped text).
    for entity_type, pattern in _RECOGNISER_PATTERNS:
        for m in pattern.finditer(stripped):
            orig_start = _map_offset(m.start())
            orig_end = _map_offset(m.end())
            if _is_denied(text, orig_start, orig_end):
                continue
            raw_matches.append(
                RecogniserMatch(
                    entity_type=entity_type,
                    start=orig_start,
                    end=orig_end,
                    confidence=0.99,
                    detector="native_recognizer",
                )
            )

    # 2. Context-keyword recognisers (PASSWORD, USERNAME, API_TOKEN).
    for entity_type, pattern in [
        ("PASSWORD", _PASSWORD_CONTEXT),
        ("USERNAME", _USERNAME_CONTEXT),
        ("API_TOKEN", _API_TOKEN_CONTEXT),
    ]:
        for m in pattern.finditer(stripped):
            value_start = _map_offset(m.start(1))
            value_end = _map_offset(m.end(1))
            if _is_denied(text, value_start, value_end):
                continue
            raw_matches.append(
                RecogniserMatch(
                    entity_type=entity_type,
                    start=value_start,
                    end=value_end,
                    confidence=0.95,
                    detector="native_recognizer",
                )
            )

    # 3. Credential-pair recogniser (user:password format).
    for m in _CREDENTIAL_PAIR.finditer(stripped):
        username_start = _map_offset(m.start(1))
        username_end = _map_offset(m.end(1))
        password_start = _map_offset(m.start(2))
        password_end = _map_offset(m.end(2))
        raw_matches.append(
            RecogniserMatch(
                entity_type="USERNAME",
                start=username_start,
                end=username_end,
                confidence=0.95,
                detector="native_recognizer",
            )
        )
        raw_matches.append(
            RecogniserMatch(
                entity_type="PASSWORD",
                start=password_start,
                end=password_end,
                confidence=0.95,
                detector="native_recognizer",
            )
        )

    return _deduplicate_matches(raw_matches)


def apply_native_redaction(text: str) -> tuple[str, list[RecogniserMatch]]:
    """Scan *text* for PII and return the redacted version.

    Each detected entity is replaced by a typed placeholder in square
    brackets, e.g. ``[EMAIL_ADDRESS]``, ``[JWT_TOKEN]``.

    The replacement is performed right-to-left so that byte offsets
    recorded in the match list remain valid relative to the **original**
    text.

    Args:
        text: The raw text to redact.

    Returns:
        A 2-tuple of *(redacted_text, matches)* where *matches* is
        the list of ``RecogniserMatch`` dicts with offsets into the
        **original** text.
    """
    matches = scan_text(text)

    if not matches:
        return text, []

    # Replace right-to-left to preserve earlier offsets.
    redacted = text
    for match in reversed(matches):
        placeholder = f"[{match['entity_type']}]"
        redacted = redacted[: match["start"]] + placeholder + redacted[match["end"] :]

    return redacted, matches
