from pathlib import Path

from blt_mayo.config.models import ScanConfig
from blt_mayo.scanner.traversal import walk_root


def test_traversal_respects_exclusions(tmp_path: Path) -> None:
    (tmp_path / "keep.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    excluded = tmp_path / ".git"
    excluded.mkdir()
    (excluded / "ignore.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    artifacts, observations = walk_root(tmp_path, ScanConfig(exclude_patterns=[".git"]))
    assert [artifact.path.name for artifact in artifacts] == ["keep.sh"]
    assert any(item.kind == "excluded" for item in observations)


def test_traversal_does_not_follow_symlink_by_default(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "file.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    artifacts, _ = walk_root(tmp_path, ScanConfig(follow_symlinks=False))
    paths = {artifact.path for artifact in artifacts}
    assert link in paths
    assert not any(path.as_posix().endswith("link/file.sh") for path in paths)


def test_traversal_records_too_large_file(tmp_path: Path) -> None:
    large = tmp_path / "large.txt"
    large.write_text("x" * 20, encoding="utf-8")
    artifacts, observations = walk_root(tmp_path, ScanConfig(max_file_size=5))
    assert not artifacts
    assert any(item.kind == "too-large" for item in observations)


def test_missing_root_is_observation(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    artifacts, observations = walk_root(missing, ScanConfig())
    assert not artifacts
    assert observations[0].kind == "missing-root"
