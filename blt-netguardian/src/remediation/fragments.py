"""Static markdown remediation fragments keyed by rule_id / prefix.

Fragments are trusted static content (not user input). Callers must still
render as text/markdown safely (no raw HTML injection into the DOM).
"""

from __future__ import annotations

from typing import Any, Optional

# Exact rule_id → fragment. Keep short; OWASP links are the deep references.
_FRAGMENTS: dict[str, dict[str, Any]] = {
    "http.missing-hsts": {
        "why": "Without HSTS, browsers can be downgraded to cleartext HTTP on first visit or via SSL stripping.",
        "markdown": (
            "### Fix\n"
            "- Send `Strict-Transport-Security: max-age=15552000; includeSubDomains` (or longer).\n"
            "- Serve the site exclusively over HTTPS before enabling HSTS.\n\n"
            "### References\n"
            "- [OWASP HTTP Strict Transport Security](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Strict_Transport_Security_Cheat_Sheet.html)\n"
            "- [OWASP Secure Headers](https://owasp.org/www-project-secure-headers/)\n"
        ),
        "owasp": [
            "https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Strict_Transport_Security_Cheat_Sheet.html",
            "https://owasp.org/www-project-secure-headers/",
        ],
    },
    "http.weak-hsts-max-age": {
        "why": "A short max-age expires quickly, so returning users lose HSTS protection.",
        "markdown": (
            "### Fix\n"
            "- Raise `max-age` to at least **15552000** (180 days); 31536000 (1 year) is preferred.\n\n"
            "### References\n"
            "- [OWASP HSTS Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Strict_Transport_Security_Cheat_Sheet.html)\n"
        ),
        "owasp": [
            "https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Strict_Transport_Security_Cheat_Sheet.html",
        ],
    },
    "http.missing-csp": {
        "why": "Without a Content-Security-Policy, XSS and data injection have fewer browser-side brakes.",
        "markdown": (
            "### Fix\n"
            "- Add a restrictive `Content-Security-Policy` (start in report-only if needed).\n"
            "- Avoid `unsafe-inline` / `unsafe-eval` except with a documented exception.\n\n"
            "### References\n"
            "- [OWASP CSP Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)\n"
        ),
        "owasp": [
            "https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html",
        ],
    },
    "http.unsafe-csp-directive": {
        "why": "Overly permissive CSP directives weaken XSS defenses even when a policy header is present.",
        "markdown": (
            "### Fix\n"
            "- Remove `unsafe-inline` / `unsafe-eval` where possible; prefer nonces or hashes.\n\n"
            "### References\n"
            "- [OWASP CSP Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)\n"
        ),
        "owasp": [
            "https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html",
        ],
    },
    "http.missing-x-content-type-options": {
        "why": "Missing `nosniff` allows MIME sniffing that can turn non-script responses into executable content.",
        "markdown": (
            "### Fix\n"
            "- Send `X-Content-Type-Options: nosniff` on all responses.\n\n"
            "### References\n"
            "- [OWASP Secure Headers](https://owasp.org/www-project-secure-headers/)\n"
        ),
        "owasp": ["https://owasp.org/www-project-secure-headers/"],
    },
    "http.missing-clickjacking-protection": {
        "why": "Without frame protections, the UI can be embedded and clickjacked.",
        "markdown": (
            "### Fix\n"
            "- Prefer `Content-Security-Policy: frame-ancestors 'none'` (or an allowlist).\n"
            "- Legacy: `X-Frame-Options: DENY` or `SAMEORIGIN`.\n\n"
            "### References\n"
            "- [OWASP Clickjacking](https://owasp.org/www-community/attacks/Clickjacking)\n"
        ),
        "owasp": ["https://owasp.org/www-community/attacks/Clickjacking"],
    },
    "http.missing-referrer-policy": {
        "why": "Default referrer behavior can leak path/query data to third parties.",
        "markdown": (
            "### Fix\n"
            "- Send `Referrer-Policy: strict-origin-when-cross-origin` (or stricter).\n\n"
            "### References\n"
            "- [OWASP Secure Headers](https://owasp.org/www-project-secure-headers/)\n"
        ),
        "owasp": ["https://owasp.org/www-project-secure-headers/"],
    },
    "http.server-version-disclosure": {
        "why": "Server/version banners help attackers fingerprint known vulnerabilities.",
        "markdown": (
            "### Fix\n"
            "- Remove or genericize `Server` / `X-Powered-By` version tokens.\n\n"
            "### References\n"
            "- [OWASP Information Exposure](https://owasp.org/www-community/vulnerabilities/Information_exposure_through_query_string_in_url)\n"
        ),
        "owasp": [
            "https://owasp.org/www-project-secure-headers/",
        ],
    },
    "http.insecure-cookie-flags": {
        "why": "Cookies without Secure/HttpOnly/SameSite are easier to steal or misuse.",
        "markdown": (
            "### Fix\n"
            "- Set `Secure; HttpOnly; SameSite=Lax` (or `Strict`) on session cookies.\n\n"
            "### References\n"
            "- [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)\n"
        ),
        "owasp": [
            "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html",
        ],
    },
}

_PREFIX_DEFAULTS: list[tuple[str, dict[str, Any]]] = [
    (
        "semgrep.",
        {
            "why": "Static analysis flagged a code pattern associated with a known weakness class.",
            "markdown": (
                "### Fix\n"
                "- Review the Semgrep rule guidance and apply the suggested safe API or pattern.\n"
                "- Add a regression test that fails if the anti-pattern returns.\n\n"
                "### References\n"
                "- [OWASP Code Review Guide](https://owasp.org/www-project-code-review-guide/)\n"
                "- [CWE Top 25](https://cwe.mitre.org/top25/)\n"
            ),
            "owasp": ["https://owasp.org/www-project-code-review-guide/"],
        },
    ),
    (
        "http.",
        {
            "why": "HTTP response hardening reduces common web client-side attack paths.",
            "markdown": (
                "### Fix\n"
                "- Apply the OWASP Secure Headers baseline for this response class.\n\n"
                "### References\n"
                "- [OWASP Secure Headers](https://owasp.org/www-project-secure-headers/)\n"
            ),
            "owasp": ["https://owasp.org/www-project-secure-headers/"],
        },
    ),
]


def lookup_remediation(rule_id: Optional[str], *, cve_id: Optional[str] = None) -> dict[str, Any]:
    """Return a remediation block for a rule (and optional CVE enrichment)."""
    rid = (rule_id or "").strip()
    fragment = _FRAGMENTS.get(rid)
    if fragment is None:
        for prefix, default in _PREFIX_DEFAULTS:
            if rid.startswith(prefix):
                fragment = default
                break
    if fragment is None:
        fragment = {
            "why": "This finding should be triaged against the owning service's security baseline.",
            "markdown": (
                "### Fix\n"
                "- Confirm impact, apply the vendor/OWASP guidance for this rule class, and retest.\n\n"
                "### References\n"
                "- [OWASP Top Ten](https://owasp.org/www-project-top-ten/)\n"
            ),
            "owasp": ["https://owasp.org/www-project-top-ten/"],
        }

    result = {
        "rule_id": rid or None,
        "why": fragment["why"],
        "markdown": fragment["markdown"],
        "owasp_links": list(fragment.get("owasp") or []),
        "cve_links": [],
    }
    if cve_id:
        cve = str(cve_id).strip().upper()
        if cve.startswith("CVE-"):
            result["cve_links"] = [
                f"https://nvd.nist.gov/vuln/detail/{cve}",
                f"https://www.cve.org/CVERecord?id={cve}",
            ]
    return result
