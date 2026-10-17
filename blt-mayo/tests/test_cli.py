from pathlib import Path

from typer.testing import CliRunner

from blt_mayo.cli.app import app

runner = CliRunner()


def test_cli_help_exposes_week1_command_contract() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in [
        "scan",
        "report",
        "compare",
        "review",
        "bundle",
        "export",
        "blt-submit",
        "doctor",
    ]:
        assert command in result.stdout


def test_doctor_succeeds() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "BLT-MAYO doctor" in result.stdout


def test_scan_writes_json(fixtures_dir: Path, tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    result = runner.invoke(app, ["scan", str(fixtures_dir), "--output", str(output)])
    assert result.exit_code == 0, result.stdout
    assert output.exists()
    assert "BLT-MAYO scan complete" in result.stdout


def test_planned_command_is_explicit() -> None:
    result = runner.invoke(app, ["compare"])
    assert result.exit_code == 0
    assert "planned for Week 9" in result.stdout
