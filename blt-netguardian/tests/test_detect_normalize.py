"""Detector normalization contract: severity, fingerprints, payload shape."""

from __future__ import annotations

import pytest

from detect.normalize import (
    DEFAULT_SEVERITY,
    SEVERITIES,
    DetectionFinding,
    compute_fingerprint,
    normalize_severity,
)


@pytest.mark.parametrize("raw,expected", [
    ("CRITICAL", "critical"),
    ("High", "high"),
    ("  medium  ", "medium"),
    ("low", "low"),
    ("info", "info"),
    ("bogus", DEFAULT_SEVERITY),
    (None, DEFAULT_SEVERITY),
    ("", DEFAULT_SEVERITY),
])
def test_normalize_severity(raw, expected):
    assert normalize_severity(raw) == expected
    assert normalize_severity(raw) in SEVERITIES


def test_fingerprint_is_deterministic_across_runs():
    first = compute_fingerprint(rule_id="http.missing-csp", target="https://a.example", locator="CSP")
    second = compute_fingerprint(rule_id="http.missing-csp", target="https://a.example", locator="CSP")
    assert first == second
    assert first.startswith("fp-")


def test_fingerprint_differs_by_target_and_locator():
    base = dict(rule_id="http.missing-csp", target="https://a.example", locator="CSP")
    assert compute_fingerprint(**base) != compute_fingerprint(**{**base, "target": "https://b.example"})
    assert compute_fingerprint(**base) != compute_fingerprint(**{**base, "locator": "HSTS"})


def test_fingerprint_parts_cannot_collide_across_boundaries():
    """NUL separator stops 'a'+'bc' from hashing the same as 'ab'+'c'."""
    left = compute_fingerprint(rule_id="a", target="bc")
    right = compute_fingerprint(rule_id="ab", target="c")
    assert left != right


def test_to_payload_omits_absent_optionals():
    finding = DetectionFinding(
        rule_id="http.missing-csp",
        severity="medium",
        title="Missing CSP",
        target="https://a.example",
    )
    payload = finding.to_payload()
    assert payload["rule_id"] == "http.missing-csp"
    assert payload["severity"] == "medium"
    assert payload["fingerprint"] == finding.fingerprint
    # D1 rejects bound None, so optional keys must be absent rather than null.
    for key in ("cve_id", "locator", "remediation", "evidence"):
        assert key not in payload


def test_to_payload_includes_populated_optionals():
    finding = DetectionFinding(
        rule_id="semgrep.python.sqli",
        severity="ERROR",
        title="SQL injection",
        target="github.com/acme/app",
        locator="src/db.py:42",
        cve_id="CVE-2024-0001",
        evidence={"lines": "cursor.execute(q)"},
        remediation="Use parameterized queries.",
    )
    payload = finding.to_payload()
    assert payload["severity"] == "info"  # 'ERROR' is not a canonical severity
    assert payload["locator"] == "src/db.py:42"
    assert payload["cve_id"] == "CVE-2024-0001"
    assert payload["evidence"]["lines"] == "cursor.execute(q)"


def test_required_fields_are_enforced():
    with pytest.raises(ValueError):
        DetectionFinding(rule_id="", severity="low", title="x", target="t")
    with pytest.raises(ValueError):
        DetectionFinding(rule_id="r", severity="low", title="", target="t")
