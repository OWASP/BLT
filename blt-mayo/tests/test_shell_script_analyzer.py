from pathlib import Path

from blt_mayo.analyzers.shell_script import ShellScriptAnalyzer
from blt_mayo.config.models import ScanConfig
from blt_mayo.models.artifact import Artifact
from blt_mayo.models.enums import ArtifactType
from blt_mayo.scanner.classifier import classify_artifact, classify_sensitivity
from blt_mayo.scanner.metadata import extract_metadata


def make_artifact(path: Path, artifact_type: ArtifactType | None = None) -> Artifact:
    metadata = extract_metadata(path)
    return Artifact(
        path=path,
        scan_root=path.parent,
        artifact_type=artifact_type or classify_artifact(path, metadata),
        sensitivity=classify_sensitivity(path),
        metadata=metadata,
    )


def analyze(path: Path, scan_config):
    return ShellScriptAnalyzer().analyze(make_artifact(path), scan_config)


def test_analyzer_supports_only_shell_scripts(tmp_path: Path) -> None:
    shell_path = tmp_path / "tool.sh"
    shell_path.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    artifact = make_artifact(shell_path)
    analyzer = ShellScriptAnalyzer()

    assert analyzer.supports(artifact)

    python_artifact = make_artifact(shell_path, ArtifactType.PYTHON_SCRIPT)
    assert not analyzer.supports(python_artifact)
    assert analyzer.analyze(python_artifact, ScanConfig()) == []


def test_dangerous_fixture_creates_expected_findings(fixtures_dir: Path, scan_config) -> None:
    findings = analyze(fixtures_dir / "shell" / "dangerous.sh", scan_config)
    ids = {finding.rule_id for finding in findings}
    assert {
        "SHELL-PIPE-TO-SHELL",
        "SHELL-EVAL",
        "SHELL-NESTED-SHELL",
    } <= ids


def test_encoded_execution_fixture_is_detected(fixtures_dir: Path, scan_config) -> None:
    findings = analyze(fixtures_dir / "shell" / "encoded_execution.sh", scan_config)
    assert "SHELL-ENCODED-EXECUTION" in {finding.rule_id for finding in findings}


def test_reverse_shell_fixture_is_detected(fixtures_dir: Path, scan_config) -> None:
    findings = analyze(fixtures_dir / "shell" / "reverse_shell.sh", scan_config)
    assert "SHELL-REVERSE-SHELL" in {finding.rule_id for finding in findings}


def test_safe_fixture_has_no_findings(fixtures_dir: Path, scan_config) -> None:
    assert analyze(fixtures_dir / "shell" / "safe.sh", scan_config) == []


def test_findings_have_line_evidence_remediation_and_context(
    fixtures_dir: Path, scan_config
) -> None:
    findings = analyze(fixtures_dir / "shell" / "dangerous.sh", scan_config)
    assert findings
    for finding in findings:
        assert finding.evidence.line_number is not None
        assert finding.evidence.snippet
        assert len(finding.evidence.snippet) <= scan_config.masking.max_snippet_length
        assert "\n" not in finding.evidence.snippet
        assert finding.remediation
        assert finding.confidence.value in {"low", "medium", "high"}
        assert finding.artifact_path.name == "dangerous.sh"
        assert "permissions" in finding.metadata


def test_comment_only_dangerous_text_is_ignored(tmp_path: Path, scan_config) -> None:
    path = tmp_path / "comment.sh"
    path.write_text(
        "#!/bin/sh\n# curl https://example.invalid/a | bash\necho safe\n",
        encoding="utf-8",
    )
    assert analyze(path, scan_config) == []


def test_removed_file_fails_safely(tmp_path: Path, scan_config) -> None:
    path = tmp_path / "removed.sh"
    path.write_text("#!/bin/sh\neval x\n", encoding="utf-8")
    artifact = make_artifact(path)
    path.unlink()

    assert ShellScriptAnalyzer().analyze(artifact, scan_config) == []


def test_invalid_utf8_does_not_crash(tmp_path: Path, scan_config) -> None:
    path = tmp_path / "bytes.sh"
    path.write_bytes(b"#!/bin/sh\necho \xff\neval x\n")
    findings = analyze(path, scan_config)
    assert "SHELL-EVAL" in {finding.rule_id for finding in findings}
