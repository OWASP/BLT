"""
Native PII detection and redaction engine for BLT-Toasty.

This module provides the primary redaction logic, allowing all operations
to run natively within the Cloudflare Worker Pyodide environment. It uses compiled
regular expressions and technical deny-lists to detect and redact sensitive developer
secrets and standard PII.

SECURITY CONTRACT:
  - The raw text passed to this engine is NEVER stored or logged.
  - Matches are redacted deterministically with `<REDACTED>`.
"""

import re

# ─── PII and Secrets Regex Patterns ──────────────────────────────────────────

RECOGNIZER_PATTERNS: dict[str, dict] = {
    # Custom Developer Secrets
    "JWT_TOKEN": {
        "regex": r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+",
        "score": 0.95,
    },
    "AWS_ACCESS_KEY": {
        "regex": r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])",
        "score": 0.99,
    },
    "AWS_SECRET_KEY": {
        "regex": r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])",
        "score": 0.85,
    },
    "GITHUB_TOKEN": {
        "regex": r"gh[pousr]_[A-Za-z0-9_]{36,255}",
        "score": 0.99,
    },
    "BEARER_TOKEN": {
        "regex": r"(?i)(?:Bearer|Authorization:)\s+[A-Za-z0-9+/=_\-]{20,}",
        "score": 0.85,
    },
    "PRIVATE_KEY": {
        "regex": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----",
        "score": 1.0,
    },
    # Standard PII
    "EMAIL_ADDRESS": {
        "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "score": 1.0,
    },
    "IP_ADDRESS": {
        "regex": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
        "score": 0.9,
    },
    "CREDIT_CARD": {
        # Basic major card formats (Visa, Mastercard, Amex, Discover)
        "regex": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|(?:2131|1800|35\d{3})\d{11})\b",
        "score": 1.0,
    },
    "PHONE_NUMBER": {
        # Basic North American / International phone number match
        "regex": r"(?:\+?\d{1,3}[-. (]*)?\b\d{3}[-. )]*\d{3}[-. ]*\d{4}\b",
        "score": 0.85,
    },
}

# Compile all regexes at module load time for performance
_COMPILED_RECOGNIZERS = {
    entity_type: (re.compile(config["regex"]), config["score"]) for entity_type, config in RECOGNIZER_PATTERNS.items()
}

# ─── Shared Deny-list ────────────────────────────────────────────────────────
# Any string matching these patterns is explicitly excluded from detection
# to prevent false positives on technical references found in bug reports.
TECHNICAL_REFERENCE_DENY_LIST: list[str] = [
    r"CVE-\d{4}-\d{4,7}",
    r"CWE-\d+",
    r"OWASP-[A-Z0-9]+",
    r"0x[0-9a-fA-F]+",
    r"GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}",
]

_DENY_LIST_COMPILED = [re.compile(p) for p in TECHNICAL_REFERENCE_DENY_LIST]


def is_deny_listed(text: str) -> bool:
    """Check if a candidate string matches any deny-list pattern."""
    return any(p.fullmatch(text) for p in _DENY_LIST_COMPILED)


# ─── Core Engine API ─────────────────────────────────────────────────────────


async def analyze_text(text: str, env=None) -> list[dict]:
    """Analyze text natively and return detected PII entities.

    This function runs entirely in Python memory using pre-compiled regular expressions.

    Args:
        text: The plain text to analyze.
        env: The Cloudflare Worker environment (unused, kept for compatibility).

    Returns:
        list[dict]: A list of entity dicts, each containing:
            ``entity_type`` (str), ``start`` (int), ``end`` (int), ``score`` (float).
    """
    entities = []

    for entity_type, (pattern, score) in _COMPILED_RECOGNIZERS.items():
        for match in pattern.finditer(text):
            matched_string = match.group(0)

            # Skip if the matched string is a known technical reference
            if is_deny_listed(matched_string):
                continue

            entities.append({"entity_type": entity_type, "start": match.start(), "end": match.end(), "score": score})

    # Resolve overlaps: if two entities overlap, keep the one with the higher score
    entities.sort(key=lambda x: (x["start"], -x["score"]))

    resolved_entities = []
    for current in entities:
        if not resolved_entities:
            resolved_entities.append(current)
            continue

        previous = resolved_entities[-1]

        # Check for overlap
        if current["start"] < previous["end"]:
            # They overlap. Keep the one with the higher score, or the longer one if scores are equal
            if current["score"] > previous["score"]:
                resolved_entities[-1] = current
            elif current["score"] == previous["score"]:
                if (current["end"] - current["start"]) > (previous["end"] - previous["start"]):
                    resolved_entities[-1] = current
        else:
            resolved_entities.append(current)

    return resolved_entities


async def anonymize_text(text: str, analyzer_results: list[dict], env=None) -> dict:
    """Anonymize text locally by replacing detected entities with `<REDACTED>`.

    Args:
        text: The original plain text.
        analyzer_results: The list of entity dicts returned by analyze_text.
        env: The Cloudflare Worker environment (unused, kept for compatibility).

    Returns:
        dict: A dict with keys:
            ``text`` (str): The redacted text.
            ``items`` (list): List of anonymized entity records.
    """
    # Sort results in reverse order by start index so we can replace substrings
    # without breaking the string indices of subsequent replacements.
    sorted_results = sorted(analyzer_results, key=lambda x: x["start"], reverse=True)

    redacted_text = text
    items = []

    for entity in sorted_results:
        start = entity["start"]
        end = entity["end"]

        # Slicing the string to replace the specific byte range
        redacted_text = redacted_text[:start] + "<REDACTED>" + redacted_text[end:]

        items.append(
            {
                "start": start,
                "end": start + len("<REDACTED>"),
                "entity_type": entity["entity_type"],
                "text": "<REDACTED>",
                "operator": "replace",
            }
        )

    # Reverse items to match original ascending order
    items.reverse()

    return {"text": redacted_text, "items": items}


async def build_redaction_map(original_text: str, analyzer_results: list[dict]) -> list[dict]:
    """Transform analyzer results into the D1 redaction_audit schema.

    Args:
        original_text: The original text (unused, kept for API compatibility).
        analyzer_results: The list of entity dicts returned by analyze_text.

    Returns:
        list[dict]: Sorted list of redaction audit records.
    """
    redaction_map = []
    for entity in analyzer_results:
        start = int(entity.get("start", 0))
        end = int(entity.get("end", 0))
        redaction_map.append(
            {
                "entity_type": entity.get("entity_type", "UNKNOWN"),
                "detector": "native_regex",
                "confidence": float(entity.get("score", 0.0)),
                "byte_start": start,
                "byte_end": end,
                "original_length": end - start,
            }
        )

    redaction_map.sort(key=lambda r: r["byte_start"])
    return redaction_map
