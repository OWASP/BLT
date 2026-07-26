"""Semgrep report parsing and normalization."""

from __future__ import annotations

import json

import pytest

from detect.semgrep import parse_semgrep_json, scan_semgrep_results

TARGET = "github.com/acme/app"

REPORT = {
    "results": [
        {
            "check_id": "python.lang.security.audit.dangerous-subprocess-use",
            "path": "src/runner.py",
            "start": {"line": 42, "col": 5},
            "extra": {
                "message": "Detected subprocess call with user-controlled input",
                "severity": "ERROR",
                "lines": "subprocess.call(user_input, shell=True)",
                "metadata": {"cwe": ["CWE-78"], "owasp": ["A03:2021"]},
            },
        },
        {
            "check_id": "python.requests.security.no-verify",
            "path": "src/client.py",
            "start": {"line": 7},
            "extra": {"message": "TLS verification disabled", "severity": "WARNING"},
        },
        {
            "check_id": "generic.secrets.hardcoded",
            "path": "src/config.py",
            "start": {"line": 3},
            "extra": {"severity": "INFO", "metadata": {"cve": ["CVE-2023-9999"]}},
        },
    ],
    "errors": [],
}


def test_parse_returns_results_array():
    assert len(parse_semgrep_json(json.dumps(REPORT))) == 3


def test_parse_handles_missing_results_key():
    assert parse_semgrep_json(json.dumps({"errors": []})) == []


def test_parse_rejects_invalid_json():
    with pytest.raises(ValueError):
        parse_semgrep_json("{not json")


def test_parse_rejects_non_object_report():
    with pytest.raises(ValueError):
        parse_semgrep_json("[1, 2, 3]")


def test_parse_rejects_non_array_results():
    with pytest.raises(ValueError):
        parse_semgrep_json(json.dumps({"results": {"a": 1}}))


def test_severity_mapping_across_scales():
    findings = scan_semgrep_results(REPORT["results"], target=TARGET)
    severities = {f.rule_id: f.severity for f in findings}
    assert severities["semgrep.python.lang.security.audit.dangerous-subprocess-use"] == "high"
    assert severities["semgrep.python.requests.security.no-verify"] == "medium"
    assert severities["semgrep.generic.secrets.hardcoded"] == "low"


def test_rule_ids_are_namespaced():
    findings = scan_semgrep_results(REPORT["results"], target=TARGET)
    assert all(f.rule_id.startswith("semgrep.") for f in findings)


def test_locator_is_path_and_line():
    findings = scan_semgrep_results(REPORT["results"], target=TARGET)
    assert findings[0].locator == "src/runner.py:42"


def test_title_falls_back_to_rule_name_when_message_absent():
    findings = scan_semgrep_results(REPORT["results"], target=TARGET)
    hardcoded = next(f for f in findings if f.rule_id.endswith("secrets.hardcoded"))
    assert hardcoded.title == "hardcoded"


def test_cve_extracted_from_metadata_list():
    findings = scan_semgrep_results(REPORT["results"], target=TARGET)
    hardcoded = next(f for f in findings if f.rule_id.endswith("secrets.hardcoded"))
    assert hardcoded.cve_id == "CVE-2023-9999"


def test_evidence_carries_snippet_and_taxonomy():
    findings = scan_semgrep_results(REPORT["results"], target=TARGET)
    evidence = findings[0].evidence
    assert evidence["lines"].startswith("subprocess.call(")
    assert evidence["cwe"] == ["CWE-78"]


def test_results_without_check_id_are_skipped():
    findings = scan_semgrep_results([{"path": "a.py", "extra": {}}], target=TARGET)
    assert findings == []


def test_long_messages_are_truncated():
    long_message = "x" * 400
    findings = scan_semgrep_results(
        [{"check_id": "r", "path": "a.py", "extra": {"message": long_message, "severity": "INFO"}}],
        target=TARGET,
    )
    assert len(findings[0].title) <= 160
    assert findings[0].title.endswith("...")


def test_same_result_rescanned_keeps_fingerprint():
    first = scan_semgrep_results(REPORT["results"], target=TARGET)
    second = scan_semgrep_results(REPORT["results"], target=TARGET)
    assert [f.fingerprint for f in first] == [f.fingerprint for f in second]
