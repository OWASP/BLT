"""
Prompt construction and response parsing for the `draft_vision_issue` tool.

Key Items:
- `VISION_PROMPT`: Strict plain-text prompt requiring exactly a `TITLE:` field followed by a `DESCRIPTION:` field.
- `NO_ISSUE_TITLE` / `NO_ISSUE_DESCRIPTION`: Deterministic fallback used when no bug is visible.
- `parse_vision_response(text) -> str`: Validates model output and returns it in the canonical
  `TITLE: ...\\nDESCRIPTION: ...` form, or raises `ValueError` when the output cannot be trusted.

Design Notes:
- Generative output is never trusted: markers must appear once, in order, with non-empty values.
- Only a wrapping code fence and bold/heading decoration around the markers are tolerated.
- Malformed output is rejected rather than repaired, so no plausible-looking bug is fabricated.
"""

import re

NO_ISSUE_TITLE = "No clear issue identified"
NO_ISSUE_DESCRIPTION = "The screenshot does not provide sufficient visual evidence to identify a specific bug."

VISION_PROMPT = (
    "You are analyzing a single screenshot of a web application to draft a bug report.\n\n"
    "Rules for the analysis:\n"
    "- Describe only bugs or UI problems that are directly visible in the screenshot.\n"
    "- Never invent application behavior, hidden state, error messages, root causes, or any detail "
    "that cannot be established from the screenshot.\n"
    "- Distinguish an observable defect from an unusual design or a subjective preference; "
    "only report the former.\n"
    "- If no clear issue is visible, or the screenshot is ambiguous or insufficient, do not guess "
    "and do not invent a bug. Respond with exactly this fallback:\n"
    f"TITLE: {NO_ISSUE_TITLE}\n"
    f"DESCRIPTION: {NO_ISSUE_DESCRIPTION}\n\n"
    "Output format: respond with exactly two fields and nothing else, in this order:\n"
    "TITLE: <concise plain-text issue title>\n"
    "DESCRIPTION: <concise, factual description of the visually observable issue>\n\n"
    "Format requirements:\n"
    "- TITLE: must appear first and exactly once. DESCRIPTION: must appear second and exactly once.\n"
    "- Both fields must be present and non-empty.\n"
    "- Do not add any other fields, headings, sections, explanations, labels, metadata, "
    "confidence scores, or recommendations.\n"
    "- Do not add an introduction or a conclusion such as 'Here is the analysis'.\n"
    "- Output plain text only, not Markdown. Do not use headings (#), bold or italic markers (* or _), "
    "bullet or numbered lists, links, images, backticks, code fences, HTML tags, decorative "
    "separators, or quotation marks around the response."
)

_MARKER_RE = re.compile(
    r"^[\s>#*_]*(TITLE|DESCRIPTION)[\s*_]*:[\s*_]*(.*)$", re.IGNORECASE
)
_FENCE_RE = re.compile(r"^\s*```[\w-]*\s*$")
_DECORATION = " \t*_`"


def build_vision_prompt(context: str | None = None) -> str:
    """Return the vision prompt, appending optional user context."""
    prompt = VISION_PROMPT
    if context and context.strip():
        prompt += f"\n\nAdditional user context about this image:\n{context}"
    return prompt


def parse_vision_response(text: object) -> str:
    """Validate model output and return it as canonical `TITLE:`/`DESCRIPTION:` text.

    Raises:
        ValueError: If the output is empty, not a string, or does not follow the contract.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty vision response")

    lines = [line for line in text.strip().splitlines() if not _FENCE_RE.match(line)]

    title_lines: list[str] = []
    desc_lines: list[str] = []
    current: list[str] | None = None
    seen: list[str] = []

    for line in lines:
        match = _MARKER_RE.match(line)
        if match:
            marker = match.group(1).upper()
            if marker in seen:
                raise ValueError(f"duplicate {marker} marker")
            if marker == "DESCRIPTION" and "TITLE" not in seen:
                raise ValueError("DESCRIPTION appears before TITLE")
            seen.append(marker)
            current = title_lines if marker == "TITLE" else desc_lines
            current.append(match.group(2))
        elif current is None:
            if line.strip():
                raise ValueError("unexpected text before TITLE")
        elif current is title_lines:
            if line.strip():
                raise ValueError("TITLE spans multiple lines")
        else:
            current.append(line)

    if seen != ["TITLE", "DESCRIPTION"]:
        raise ValueError("missing TITLE or DESCRIPTION marker")

    title = " ".join(title_lines).strip(_DECORATION)
    description = "\n".join(desc_lines).strip().strip(_DECORATION).strip()
    if not title or not description:
        raise ValueError("empty TITLE or DESCRIPTION")

    return f"TITLE: {title}\nDESCRIPTION: {description}"
