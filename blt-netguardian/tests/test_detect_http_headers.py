"""HTTP security-header detector rules."""

from __future__ import annotations

from detect.http_headers import MIN_HSTS_MAX_AGE, scan_headers

URL = "https://app.example"

SECURE_HEADERS = {
    "Strict-Transport-Security": f"max-age={MIN_HSTS_MAX_AGE}; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


def _rules(findings):
    return {f.rule_id for f in findings}


def test_fully_hardened_response_yields_no_findings():
    assert scan_headers(URL, SECURE_HEADERS) == []


def test_bare_response_flags_all_missing_headers():
    rules = _rules(scan_headers(URL, {}))
    assert "http.missing-hsts" in rules
    assert "http.missing-csp" in rules
    assert "http.missing-clickjacking-protection" in rules
    assert "http.missing-x-content-type-options" in rules
    assert "http.missing-referrer-policy" in rules


def test_header_lookup_is_case_insensitive():
    lowered = {key.lower(): value for key, value in SECURE_HEADERS.items()}
    assert scan_headers(URL, lowered) == []


def test_hsts_not_flagged_over_plain_http():
    """HSTS is meaningless without TLS; flagging it on http:// would be noise."""
    rules = _rules(scan_headers("http://app.example", {}))
    assert "http.missing-hsts" not in rules


def test_weak_hsts_not_flagged_over_plain_http():
    """Even a short max-age on http:// must not emit weak-HSTS (HTTPS-only rule)."""
    headers = {**SECURE_HEADERS, "Strict-Transport-Security": "max-age=60"}
    rules = _rules(scan_headers("http://app.example", headers))
    assert "http.missing-hsts" not in rules
    assert "http.weak-hsts-max-age" not in rules


def test_short_hsts_max_age_is_flagged():
    headers = {**SECURE_HEADERS, "Strict-Transport-Security": "max-age=3600"}
    findings = [f for f in scan_headers(URL, headers) if f.rule_id == "http.weak-hsts-max-age"]
    assert len(findings) == 1
    assert findings[0].evidence["max_age"] == 3600


def test_unsafe_csp_directives_are_flagged():
    headers = {**SECURE_HEADERS, "Content-Security-Policy": "default-src 'self' 'unsafe-inline'"}
    findings = [f for f in scan_headers(URL, headers) if f.rule_id == "http.unsafe-csp-directive"]
    assert findings and findings[0].evidence["directives"] == ["unsafe-inline"]


def test_csp_frame_ancestors_satisfies_clickjacking_rule():
    headers = dict(SECURE_HEADERS)
    assert "X-Frame-Options" not in headers
    assert "http.missing-clickjacking-protection" not in _rules(scan_headers(URL, headers))


def test_x_frame_options_alone_satisfies_clickjacking_rule():
    headers = {**SECURE_HEADERS, "Content-Security-Policy": "default-src 'self'", "X-Frame-Options": "DENY"}
    assert "http.missing-clickjacking-protection" not in _rules(scan_headers(URL, headers))


def test_ineffective_xfo_allowall_is_not_protection():
    headers = {
        **SECURE_HEADERS,
        "Content-Security-Policy": "default-src 'self'",
        "X-Frame-Options": "ALLOWALL",
    }
    assert "http.missing-clickjacking-protection" in _rules(scan_headers(URL, headers))


def test_permissive_frame_ancestors_star_is_not_protection():
    headers = {
        **SECURE_HEADERS,
        "Content-Security-Policy": "default-src 'self'; frame-ancestors *",
    }
    assert "http.missing-clickjacking-protection" in _rules(scan_headers(URL, headers))


def test_insecure_cookie_flags():
    headers = {**SECURE_HEADERS, "Set-Cookie": "sid=abc; Path=/"}
    findings = [f for f in scan_headers(URL, headers) if f.rule_id == "http.insecure-cookie-flags"]
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert set(findings[0].evidence["missing_flags"]) == {"secure", "httponly"}
    assert findings[0].locator == "Set-Cookie:sid"


def test_cookie_value_containing_secure_substring_is_still_flagged():
    """Attribute match must be exact — 'notsecure' must not satisfy Secure."""
    headers = {**SECURE_HEADERS, "Set-Cookie": "sid=notsecure; HttpOnly"}
    findings = [f for f in scan_headers(URL, headers) if f.rule_id == "http.insecure-cookie-flags"]
    assert len(findings) == 1
    assert findings[0].evidence["missing_flags"] == ["secure"]


def test_secure_httponly_cookie_is_not_flagged():
    headers = {**SECURE_HEADERS, "Set-Cookie": "sid=abc; Secure; HttpOnly; SameSite=Lax"}
    assert "http.insecure-cookie-flags" not in _rules(scan_headers(URL, headers))


def test_server_version_disclosure():
    headers = {**SECURE_HEADERS, "Server": "nginx/1.25.3"}
    findings = [f for f in scan_headers(URL, headers) if f.rule_id == "http.server-version-disclosure"]
    assert len(findings) == 1
    assert findings[0].evidence["value"] == "nginx/1.25.3"


def test_generic_server_header_is_not_flagged():
    headers = {**SECURE_HEADERS, "Server": "cloudflare"}
    assert "http.server-version-disclosure" not in _rules(scan_headers(URL, headers))


def test_error_responses_are_skipped():
    assert scan_headers(URL, {}, status=503) == []


def test_findings_carry_stable_fingerprints():
    first = scan_headers(URL, {})
    second = scan_headers(URL, {})
    assert [f.fingerprint for f in first] == [f.fingerprint for f in second]
    # Distinct rules on the same target must not collapse into one finding.
    assert len({f.fingerprint for f in first}) == len(first)
