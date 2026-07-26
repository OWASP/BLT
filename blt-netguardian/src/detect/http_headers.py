"""HTTP security-header detector.

Deliberately split from network I/O: :func:`scan_headers` is a pure function
over an already-fetched status/header pair. That keeps the rules unit-testable
with no sockets in CI, and lets the same logic run against a live fetch, a
cached response, or a fixture.

Rules follow OWASP Secure Headers guidance. Each returns a
:class:`~detect.normalize.DetectionFinding` whose ``locator`` is the header
name, so the fingerprint stays stable per (target, header) pair.
"""

from __future__ import annotations

import re
from typing import Iterable, Mapping, Optional

from detect.normalize import DetectionFinding

# HSTS below ~180 days is treated as too short to protect a returning visitor.
MIN_HSTS_MAX_AGE = 15_552_000

_MAX_AGE = re.compile(r"max-age\s*=\s*(\d+)", re.IGNORECASE)
_VERSIONED_SERVER = re.compile(r"[0-9]+\.[0-9]+")

HEADER_RULES = (
    "http.missing-hsts",
    "http.weak-hsts-max-age",
    "http.missing-csp",
    "http.unsafe-csp-directive",
    "http.missing-x-content-type-options",
    "http.missing-clickjacking-protection",
    "http.missing-referrer-policy",
    "http.server-version-disclosure",
    "http.insecure-cookie-flags",
)


def _get(headers: Mapping[str, str], name: str) -> Optional[str]:
    """Case-insensitive header lookup (HTTP field names are case-insensitive)."""
    target = name.lower()
    for key, value in headers.items():
        if str(key).lower() == target:
            return str(value)
    return None


def _is_https(url: str) -> bool:
    return url.strip().lower().startswith("https://")


def _hsts_findings(url: str, headers: Mapping[str, str]) -> Iterable[DetectionFinding]:
    # HSTS is ignored by browsers without TLS; never evaluate it for http://.
    if not _is_https(url):
        return

    hsts = _get(headers, "Strict-Transport-Security")
    if hsts is None:
        yield DetectionFinding(
            rule_id="http.missing-hsts",
            severity="high",
            title="Missing Strict-Transport-Security header",
            target=url,
            locator="Strict-Transport-Security",
            remediation="Send Strict-Transport-Security with max-age of at least 15552000.",
        )
        return

    match = _MAX_AGE.search(hsts)
    max_age = int(match.group(1)) if match else 0
    if max_age < MIN_HSTS_MAX_AGE:
        yield DetectionFinding(
            rule_id="http.weak-hsts-max-age",
            severity="medium",
            title="Strict-Transport-Security max-age is too short",
            target=url,
            locator="Strict-Transport-Security",
            evidence={"max_age": max_age, "minimum": MIN_HSTS_MAX_AGE},
            remediation=f"Raise max-age to at least {MIN_HSTS_MAX_AGE} seconds.",
        )


def _csp_findings(url: str, headers: Mapping[str, str]) -> Iterable[DetectionFinding]:
    csp = _get(headers, "Content-Security-Policy")
    if csp is None:
        yield DetectionFinding(
            rule_id="http.missing-csp",
            severity="medium",
            title="Missing Content-Security-Policy header",
            target=url,
            locator="Content-Security-Policy",
            remediation="Add a Content-Security-Policy restricting script and object sources.",
        )
        return

    unsafe = [d for d in ("unsafe-inline", "unsafe-eval") if d in csp.lower()]
    if unsafe:
        yield DetectionFinding(
            rule_id="http.unsafe-csp-directive",
            severity="medium",
            title="Content-Security-Policy allows unsafe script execution",
            target=url,
            locator="Content-Security-Policy",
            evidence={"directives": unsafe},
            remediation="Remove unsafe-inline/unsafe-eval; use nonces or hashes instead.",
        )


_PROTECTIVE_XFO = frozenset({"deny", "sameorigin"})
_FRAME_ANCESTORS = re.compile(
    r"(?:^|;)\s*frame-ancestors\s+([^;]+)",
    re.IGNORECASE,
)


def _xfo_is_protective(value: Optional[str]) -> bool:
    """True only for DENY / SAMEORIGIN — not ALLOWALL or empty presence."""
    if value is None:
        return False
    token = value.strip().split(None, 1)[0].lower()
    return token in _PROTECTIVE_XFO


def _csp_frame_ancestors_protective(csp: str) -> bool:
    """True when frame-ancestors is present and does not allow unrestricted framing."""
    match = _FRAME_ANCESTORS.search(csp)
    if not match:
        return False
    sources = match.group(1).split()
    if not sources:
        return False
    # '*' (with or without quotes) permits any ancestor — not protection.
    return not any(src.strip("'\"") == "*" for src in sources)


def _clickjacking_findings(url: str, headers: Mapping[str, str]) -> Iterable[DetectionFinding]:
    xfo = _get(headers, "X-Frame-Options")
    csp = _get(headers, "Content-Security-Policy") or ""
    if _xfo_is_protective(xfo) or _csp_frame_ancestors_protective(csp):
        return
    yield DetectionFinding(
        rule_id="http.missing-clickjacking-protection",
        severity="medium",
        title="No clickjacking protection (X-Frame-Options or frame-ancestors)",
        target=url,
        locator="X-Frame-Options",
        remediation="Set X-Frame-Options: DENY or a CSP frame-ancestors directive that is not '*'.",
    )


def _iter_set_cookies(headers: Mapping[str, str]) -> list[str]:
    """Return every Set-Cookie value (multi-header aware when the mapping supports it)."""
    if hasattr(headers, "get_all"):
        values = headers.get_all("Set-Cookie") or headers.get_all("set-cookie") or []
        if values:
            return [str(v) for v in values if v is not None and str(v).strip()]
    single = _get(headers, "Set-Cookie")
    if single is None:
        return []
    # Some stacks join multiple cookies with newlines when collapsing headers.
    return [part.strip() for part in single.split("\n") if part.strip()]


def _cookie_attribute_names(cookie: str) -> set[str]:
    """Exact attribute names after the cookie-pair (semicolon-delimited, not substrings)."""
    names: set[str] = set()
    parts = cookie.split(";")
    for attr in parts[1:]:
        name = attr.strip().split("=", 1)[0].strip().lower()
        if name:
            names.add(name)
    return names


def _cookie_name(cookie: str) -> str:
    pair = cookie.split(";", 1)[0]
    return pair.split("=", 1)[0].strip() or "cookie"


def _cookie_findings(url: str, headers: Mapping[str, str]) -> Iterable[DetectionFinding]:
    for cookie in _iter_set_cookies(headers):
        attrs = _cookie_attribute_names(cookie)
        missing = [flag for flag in ("secure", "httponly") if flag not in attrs]
        if not missing:
            continue
        name = _cookie_name(cookie)
        yield DetectionFinding(
            rule_id="http.insecure-cookie-flags",
            severity="high" if "secure" in missing else "medium",
            title="Set-Cookie is missing security flags",
            target=url,
            locator=f"Set-Cookie:{name}",
            evidence={"cookie": name, "missing_flags": missing},
            remediation="Add Secure and HttpOnly (and a SameSite policy) to session cookies.",
        )


def scan_headers(url: str, headers: Mapping[str, str], *, status: int = 200) -> list[DetectionFinding]:
    """Evaluate one response's headers; return normalized findings.

    Non-2xx/3xx responses are skipped: error pages routinely omit hardening
    headers and would generate findings that say nothing about the real app.
    """
    if status >= 400:
        return []

    findings: list[DetectionFinding] = []
    findings.extend(_hsts_findings(url, headers))
    findings.extend(_csp_findings(url, headers))
    findings.extend(_clickjacking_findings(url, headers))
    findings.extend(_cookie_findings(url, headers))

    if _get(headers, "X-Content-Type-Options") is None:
        findings.append(DetectionFinding(
            rule_id="http.missing-x-content-type-options",
            severity="low",
            title="Missing X-Content-Type-Options header",
            target=url,
            locator="X-Content-Type-Options",
            remediation="Set X-Content-Type-Options: nosniff.",
        ))

    if _get(headers, "Referrer-Policy") is None:
        findings.append(DetectionFinding(
            rule_id="http.missing-referrer-policy",
            severity="info",
            title="Missing Referrer-Policy header",
            target=url,
            locator="Referrer-Policy",
            remediation="Set Referrer-Policy: strict-origin-when-cross-origin.",
        ))

    for header_name in ("Server", "X-Powered-By"):
        value = _get(headers, header_name)
        if value and _VERSIONED_SERVER.search(value):
            findings.append(DetectionFinding(
                rule_id="http.server-version-disclosure",
                severity="low",
                title=f"{header_name} header discloses a software version",
                target=url,
                locator=header_name,
                evidence={"value": value[:120]},
                remediation=f"Suppress or genericize the {header_name} header.",
            ))

    return findings
