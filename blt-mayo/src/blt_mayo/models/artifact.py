from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .enums import ArtifactType, PathSensitivity


@dataclass(slots=True)
class FileMetadata:
    owner: str | None
    group: str | None
    uid: int | None
    gid: int | None
    mode: int
    permissions: str
    size: int
    modified_at: float
    created_at: float
    is_symlink: bool
    symlink_target: str | None
    is_executable: bool
    is_world_writable: bool
    is_group_writable: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Artifact:
    path: Path
    scan_root: Path
    artifact_type: ArtifactType
    sensitivity: PathSensitivity
    metadata: FileMetadata
    observations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["path"] = str(self.path)
        payload["scan_root"] = str(self.scan_root)
        payload["artifact_type"] = self.artifact_type.value
        payload["sensitivity"] = self.sensitivity.value
        return payload
