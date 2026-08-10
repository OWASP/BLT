"""Minimal pure-Python PDF report builder (Workers-safe, no native deps)."""

from __future__ import annotations

import json
import re
from typing import Any, Iterable, Mapping, Optional, Sequence
from urllib.parse import urlsplit, urlunsplit

from payload_redact import REDACT_KEYS, redact_payload

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN_LEFT = 50
MARGIN_TOP = 750
LINE_HEIGHT = 14
MAX_LINES_PER_PAGE = 48
MAX_FINDINGS = 200
MAX_LINE_CHARS = 95

_SECRET_KV_RE = re.compile(
    r"(?i)\b(" + "|".join(re.escape(k) for k in sorted(REDACT_KEYS, key=len, reverse=True)) + r")"
    r"\b\s*[=:]\s*\S+"
)
_URL_IN_TEXT_RE = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s<>\"']+")


def _pdf_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _clip(text: str, limit: int = MAX_LINE_CHARS) -> str:
    value = " ".join(str(text).split())
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)] + "…"


def _wrap(text: str, width: int = MAX_LINE_CHARS) -> list[str]:
    words = str(text).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def sanitize_target(target: Any) -> str:
    """Strip URL credentials, query strings, and fragments from a finding target."""
    raw = str(target or "").strip()
    if not raw:
        return ""
    parts = urlsplit(raw)
    if parts.scheme and parts.netloc:
        netloc = parts.netloc.rsplit("@", 1)[-1]
        return urlunsplit((parts.scheme, netloc, parts.path, "", ""))
    # Non-URL / relative locators: still drop query/fragment and userinfo-looking prefixes.
    without_frag = raw.split("#", 1)[0]
    without_query = without_frag.split("?", 1)[0]
    if "@" in without_query and "://" not in without_query:
        without_query = without_query.rsplit("@", 1)[-1]
    return without_query


def redact_secret_bearing_text(value: Any) -> str:
    """Redact key=value secret patterns and sanitize embedded URLs in free text."""
    text = str(value or "")
    if not text:
        return ""

    def _replace_url(match: re.Match[str]) -> str:
        return sanitize_target(match.group(0))

    text = _URL_IN_TEXT_RE.sub(_replace_url, text)
    text = _SECRET_KV_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    return text


def presentation_finding(finding: Mapping[str, Any]) -> dict[str, Any]:
    """Return a PDF-safe copy of finding metadata (never mutates the input)."""
    return {
        "id": finding.get("id"),
        "org_id": finding.get("org_id"),
        "severity": finding.get("severity"),
        "status": finding.get("status"),
        "cve_id": finding.get("cve_id"),
        "cve_score": finding.get("cve_score"),
        "blt_issue_id": finding.get("blt_issue_id"),
        "created_at": finding.get("created_at"),
        "updated_at": finding.get("updated_at"),
        "title": redact_secret_bearing_text(finding.get("title")),
        "rule_id": redact_secret_bearing_text(finding.get("rule_id")),
        "target": sanitize_target(finding.get("target")),
        "fingerprint": redact_secret_bearing_text(finding.get("fingerprint") or "—"),
    }


def finding_lines(finding: Mapping[str, Any], *, include_snippet: Optional[Mapping[str, Any]] = None) -> list[str]:
    """Render one finding as report lines (metadata only; secrets redacted)."""
    safe = presentation_finding(finding)
    lines = [
        f"Finding: {safe.get('id') or ''}",
        f"Title: {_clip(safe.get('title') or '')}",
        f"Rule: {_clip(safe.get('rule_id') or '')}",
        f"Severity: {safe.get('severity') or ''}",
        f"Status: {safe.get('status') or ''}",
        f"Target: {_clip(safe.get('target') or '')}",
        f"CVE: {safe.get('cve_id') or '—'}  score={safe.get('cve_score') if safe.get('cve_score') is not None else '—'}",
        f"Issue: {safe.get('blt_issue_id') or '—'}",
        f"Org: {safe.get('org_id') or ''}",
        f"Fingerprint: {_clip(safe.get('fingerprint') or '—')}",
        f"Created: {safe.get('created_at') or ''}  Updated: {safe.get('updated_at') or ''}",
    ]
    if include_snippet is not None:
        redacted = redact_payload(dict(include_snippet))
        snippet = json.dumps(redacted, separators=(",", ":"), ensure_ascii=False, sort_keys=True)
        lines.append("Evidence (redacted):")
        for part in _wrap(_clip(snippet, 800), width=MAX_LINE_CHARS):
            lines.append(f"  {part}")
    lines.append("")
    return lines


def build_report_lines(
    findings: Sequence[Mapping[str, Any]],
    *,
    title: str = "NetGuardian Findings Report",
    org_id: str = "",
    snippet_by_id: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> list[str]:
    header = [
        title,
        f"Organization: {org_id or '—'}",
        f"Findings: {len(findings)}",
        "Note: secrets/tokens are redacted; ciphertext is never included.",
        "",
    ]
    body: list[str] = []
    for finding in findings[:MAX_FINDINGS]:
        fid = str(finding.get("id") or "")
        snippet = None
        if snippet_by_id and fid in snippet_by_id:
            snippet = snippet_by_id[fid]
        body.extend(finding_lines(finding, include_snippet=snippet))
    if len(findings) > MAX_FINDINGS:
        body.append(f"… truncated; {len(findings) - MAX_FINDINGS} additional findings omitted.")
    return header + body


def _content_stream(page_lines: Sequence[str]) -> bytes:
    commands = ["BT", "/F1 11 Tf", f"{MARGIN_LEFT} {MARGIN_TOP} Td", f"{LINE_HEIGHT} TL"]
    first = True
    for line in page_lines:
        escaped = _pdf_escape(line)
        if first:
            commands.append(f"({escaped}) Tj")
            first = False
        else:
            commands.append("T*")
            commands.append(f"({escaped}) Tj")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1", errors="replace")


def _chunk_pages(lines: Sequence[str]) -> list[list[str]]:
    if not lines:
        return [[]]
    pages: list[list[str]] = []
    for i in range(0, len(lines), MAX_LINES_PER_PAGE):
        pages.append(list(lines[i : i + MAX_LINES_PER_PAGE]))
    return pages


def render_pdf(lines: Sequence[str]) -> bytes:
    """Build a multi-page PDF 1.4 document from plain-text lines."""
    pages = _chunk_pages(lines)
    objects: list[bytes] = []

    # 1: Catalog
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    # 2: Pages (kids filled later)
    kids_placeholder = b"__KIDS__"
    objects.append(b"<< /Type /Pages /Kids [" + kids_placeholder + b"] /Count " + str(len(pages)).encode() + b" >>")
    # 3: Font
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_obj_nums: list[int] = []
    content_obj_nums: list[int] = []

    for page_lines in pages:
        content = _content_stream(page_lines)
        content_num = len(objects) + 2  # after page object
        page_num = len(objects) + 1
        page_obj_nums.append(page_num)
        content_obj_nums.append(content_num)
        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_num} 0 R >>"
        ).encode("ascii")
        objects.append(page_dict)
        objects.append(f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"\nendstream")

    kids = " ".join(f"{n} 0 R" for n in page_obj_nums).encode("ascii")
    objects[1] = objects[1].replace(kids_placeholder, kids)

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{idx} 0 obj\n".encode("ascii"))
        out.extend(obj)
        out.extend(b"\nendobj\n")

    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(out)


def build_findings_pdf(
    findings: Iterable[Mapping[str, Any]],
    *,
    org_id: str = "",
    title: str = "NetGuardian Findings Report",
    snippet_by_id: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> bytes:
    rows = list(findings)
    lines = build_report_lines(rows, title=title, org_id=org_id, snippet_by_id=snippet_by_id)
    return render_pdf(lines)


def pdf_contains_plaintext_secret(pdf_bytes: bytes, secrets: Sequence[str]) -> list[str]:
    """Return any secret strings that appear as literal PDF content (test helper)."""
    haystack = pdf_bytes.decode("latin-1", errors="ignore")
    return [secret for secret in secrets if secret and secret in haystack]
