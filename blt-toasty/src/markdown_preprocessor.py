"""
Markdown preprocessor for the Toasty redaction pipeline.

Extracts all human-readable text from a Markdown document so that PII
hidden inside code fences, inline code, links, or image alt-text is
still visible to the downstream recogniser engine.

Design decision: we deliberately *preserve* content from code blocks and
link URLs (rather than stripping them) because vulnerability reports
frequently embed credentials and PII inside those constructs as part of
the exploit narrative.
"""

import re

# ---------------------------------------------------------------------------
# Compiled patterns — order matters.  Fenced code blocks must be consumed
# before inline code to prevent partial matches on triple-backtick lines.
# ---------------------------------------------------------------------------

_FENCED_CODE_BLOCK = re.compile(r"```[\w]*\n?(.*?)```", re.DOTALL)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_IMAGE_TAG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_LINK_TAG = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_INLINE_CODE = re.compile(r"`([^`]+)`")
_HEADING_MARKER = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_BOLD_ITALIC = re.compile(r"(\*{1,3}|_{1,3})(.*?)\1")
_HORIZONTAL_RULE = re.compile(r"^[\s]*[-*_]{3,}[\s]*$", re.MULTILINE)
_BLOCKQUOTE = re.compile(r"^>\s?", re.MULTILINE)
_LIST_MARKER = re.compile(r"^[\s]*[-*+]\s+", re.MULTILINE)
_NUMBERED_LIST = re.compile(r"^[\s]*\d+\.\s+", re.MULTILINE)


def extract_plain_text(markdown: str) -> str:
    """Convert a Markdown document into plain text for PII scanning.

    The function walks through common Markdown constructs and replaces
    them with their textual content so that the downstream recogniser
    engine can inspect *all* human-readable strings, including those
    that Markdown renderers would otherwise hide (e.g. link URLs,
    code-block bodies, image paths).

    Args:
        markdown: Raw Markdown string, potentially containing code
            fences, links, images, headings, bold/italic markers,
            and HTML comments.

    Returns:
        A single plain-text string with all Markdown syntax stripped
        but all textual content (including code block bodies and
        link URLs) preserved, separated by spaces.
    """
    if not markdown:
        return ""

    text = markdown

    # 1. Remove HTML comments entirely — they carry no user-facing text.
    text = _HTML_COMMENT.sub("", text)

    # 1a. Strip zero-width characters used for adversarial PII obfuscation.
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad\u2060]", "", text)

    # 2. Fenced code blocks → keep the body (credentials hide here).
    text = _FENCED_CODE_BLOCK.sub(r" \1 ", text)

    # 3. Images → keep both alt-text *and* URL.
    text = _IMAGE_TAG.sub(r" \1 \2 ", text)

    # 4. Links → keep both display text *and* URL.
    text = _LINK_TAG.sub(r" \1 \2 ", text)

    # 5. Inline code → keep the content.
    text = _INLINE_CODE.sub(r" \1 ", text)

    # 6. Strip formatting markers but keep content.
    text = _HEADING_MARKER.sub("", text)
    text = _BOLD_ITALIC.sub(r"\2", text)
    text = _HORIZONTAL_RULE.sub(" ", text)
    text = _BLOCKQUOTE.sub("", text)
    text = _LIST_MARKER.sub("", text)
    text = _NUMBERED_LIST.sub("", text)

    # 7. Collapse whitespace runs into single spaces.
    text = re.sub(r"[ \t]+", " ", text)
    # Preserve paragraph breaks as single newlines.
    text = re.sub(r"\n{2,}", "\n", text)

    return text.strip()
