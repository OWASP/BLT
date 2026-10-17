from pathlib import Path

from blt_mayo.models.enums import ArtifactType, PathSensitivity
from blt_mayo.scanner.classifier import classify_artifact, classify_sensitivity
from blt_mayo.scanner.metadata import extract_metadata


def test_extract_metadata_and_shell_classification(tmp_path: Path) -> None:
    script = tmp_path / "tool"
    script.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    script.chmod(0o755)
    metadata = extract_metadata(script)
    assert metadata.is_executable
    assert metadata.permissions.endswith("r-x")
    assert classify_artifact(script, metadata) == ArtifactType.SHELL_SCRIPT


def test_persistence_classification_precedes_extension(tmp_path: Path) -> None:
    cron_dir = tmp_path / "cron.d"
    cron_dir.mkdir()
    cron_file = cron_dir / "job.py"
    cron_file.write_text("* * * * * root echo ok\n", encoding="utf-8")
    metadata = extract_metadata(cron_file)
    assert classify_artifact(cron_file, metadata) == ArtifactType.CRON


def test_temp_path_is_high_sensitivity(tmp_path: Path) -> None:
    assert classify_sensitivity(tmp_path / "x") == PathSensitivity.HIGH
