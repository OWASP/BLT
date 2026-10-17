import json
from pathlib import Path

from blt_mayo.config.models import ScanConfig
from blt_mayo.reporting.json_report import write_json_report
from blt_mayo.scanner.orchestrator import ScanOrchestrator


def test_end_to_end_shell_scan(fixtures_dir: Path) -> None:
    shell_fixtures = fixtures_dir / "shell"
    result = ScanOrchestrator(ScanConfig()).scan([shell_fixtures])
    rule_ids = {finding.rule_id for finding in result.findings}

    assert {
        "SHELL-PIPE-TO-SHELL",
        "SHELL-EVAL",
        "SHELL-NESTED-SHELL",
        "SHELL-ENCODED-EXECUTION",
        "SHELL-REVERSE-SHELL",
    } <= rule_ids
    assert result.finished_at is not None
    assert len({finding.finding_id for finding in result.findings}) == len(result.findings)


def test_json_report_round_trip(fixtures_dir: Path, tmp_path: Path) -> None:
    result = ScanOrchestrator(ScanConfig()).scan([fixtures_dir / "shell"])
    output = write_json_report(result, tmp_path / "report.json")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "1.0"
    assert payload["summary"]["findings"] == len(result.findings)
    assert payload["findings"]
    assert all("remediation" in finding for finding in payload["findings"])
    assert all(finding["artifact_type"] == "shell_script" for finding in payload["findings"])
