from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from blt_mayo.config.models import ScanConfig
from blt_mayo.models.artifact import Artifact
from blt_mayo.models.scan import ScanObservation
from blt_mayo.scanner.classifier import classify_artifact, classify_sensitivity
from blt_mayo.scanner.metadata import extract_metadata


def _is_excluded(path: Path, patterns: list[str]) -> bool:
    posix = path.as_posix()
    return any(
        fnmatch.fnmatch(path.name, pattern)
        or fnmatch.fnmatch(posix, pattern)
        or any(fnmatch.fnmatch(part, pattern) for part in path.parts)
        for pattern in patterns
    )


def walk_root(root: Path, config: ScanConfig) -> tuple[list[Artifact], list[ScanObservation]]:
    artifacts: list[Artifact] = []
    observations: list[ScanObservation] = []
    root = root.expanduser().resolve()

    if not root.exists():
        observations.append(
            ScanObservation(root, "missing-root", "Configured scan root does not exist")
        )
        return artifacts, observations

    def visit(directory: Path, depth: int) -> None:
        if depth > config.max_depth:
            observations.append(
                ScanObservation(
                    directory, "max-depth", f"Skipped below configured depth {config.max_depth}"
                )
            )
            return
        try:
            entries = list(os.scandir(directory))
        except PermissionError:
            observations.append(
                ScanObservation(directory, "permission-denied", "Directory could not be read")
            )
            return
        except OSError as exc:
            observations.append(ScanObservation(directory, "scan-error", str(exc)))
            return

        for entry in entries:
            path = Path(entry.path)
            if _is_excluded(path, config.exclude_patterns):
                observations.append(ScanObservation(path, "excluded", "Matched an exclusion rule"))
                continue
            try:
                if entry.is_symlink():
                    if entry.is_dir(follow_symlinks=True) and config.follow_symlinks:
                        visit(path.resolve(), depth + 1)
                        continue
                    metadata = extract_metadata(path, follow_symlinks=False)
                    artifacts.append(
                        Artifact(
                            path=path,
                            scan_root=root,
                            artifact_type=classify_artifact(path, metadata),
                            sensitivity=classify_sensitivity(path),
                            metadata=metadata,
                            observations=["symlink-not-followed"]
                            if not config.follow_symlinks
                            else [],
                        )
                    )
                    continue
                if entry.is_dir(follow_symlinks=False):
                    visit(path, depth + 1)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    observations.append(
                        ScanObservation(path, "unsupported-entry", "Not a regular file")
                    )
                    continue
                metadata = extract_metadata(path, follow_symlinks=False)
                if metadata.size > config.max_file_size:
                    observations.append(
                        ScanObservation(
                            path, "too-large", f"File exceeds {config.max_file_size} bytes"
                        )
                    )
                    continue
                artifacts.append(
                    Artifact(
                        path=path,
                        scan_root=root,
                        artifact_type=classify_artifact(path, metadata),
                        sensitivity=classify_sensitivity(path),
                        metadata=metadata,
                    )
                )
            except PermissionError:
                observations.append(
                    ScanObservation(path, "permission-denied", "File metadata could not be read")
                )
            except OSError as exc:
                observations.append(ScanObservation(path, "scan-error", str(exc)))

    if root.is_file():
        try:
            metadata = extract_metadata(root)
            artifacts.append(
                Artifact(
                    path=root,
                    scan_root=root.parent,
                    artifact_type=classify_artifact(root, metadata),
                    sensitivity=classify_sensitivity(root),
                    metadata=metadata,
                )
            )
        except OSError as exc:
            observations.append(ScanObservation(root, "scan-error", str(exc)))
    else:
        visit(root, 0)
    return artifacts, observations
