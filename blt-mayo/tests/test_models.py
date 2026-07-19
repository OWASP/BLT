from pathlib import Path

from blt_mayo.models.enums import ArtifactType, Confidence, PathSensitivity, Severity
from blt_mayo.models.finding import Evidence, Finding


def test_finding_serializes_with_stable_id() -> None:
    finding = Finding(
        rule_id="TEST-1",
        title="Test",
        category="test",
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        description="description",
        remediation="remediation",
        artifact_path=Path("/tmp/example"),
        artifact_type=ArtifactType.SHELL_SCRIPT,
        path_sensitivity=PathSensitivity.HIGH,
        evidence=Evidence("matched", 1, "eval x"),
    )
    payload = finding.to_dict()
    assert len(finding.finding_id) == 16
    assert payload["severity"] == "high"
    assert payload["artifact_path"] == "/tmp/example"


def test_same_finding_input_produces_same_id() -> None:
    kwargs = dict(
        rule_id="TEST-1",
        title="Test",
        category="test",
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        description="description",
        remediation="remediation",
        artifact_path=Path("/tmp/example"),
        artifact_type=ArtifactType.SHELL_SCRIPT,
        path_sensitivity=PathSensitivity.HIGH,
        evidence=Evidence("matched", 1, "eval x"),
    )
    assert Finding(**kwargs).finding_id == Finding(**kwargs).finding_id
