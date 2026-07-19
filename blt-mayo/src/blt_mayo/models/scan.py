from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .artifact import Artifact
from .finding import Finding


@dataclass(slots=True)
class ScanObservation:
    path: Path
    kind: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"path": str(self.path), "kind": self.kind, "message": self.message}


@dataclass(slots=True)
class ScanResult:
    roots: list[Path]
    artifacts: list[Artifact] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    observations: list[ScanObservation] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    finished_at: str | None = None

    def finish(self) -> None:
        self.finished_at = datetime.now(UTC).isoformat()

    @property
    def summary(self) -> dict[str, int]:
        severity_counts: dict[str, int] = {}
        for finding in self.findings:
            key = finding.severity.value
            severity_counts[key] = severity_counts.get(key, 0) + 1
        return {
            "roots": len(self.roots),
            "artifacts": len(self.artifacts),
            "findings": len(self.findings),
            "observations": len(self.observations),
            **{f"severity_{key}": value for key, value in sorted(severity_counts.items())},
        }

    def to_dict(self, include_artifacts: bool = True) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "roots": [str(path) for path in self.roots],
            "summary": self.summary,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts]
            if include_artifacts
            else [],
            "findings": [finding.to_dict() for finding in self.findings],
            "observations": [observation.to_dict() for observation in self.observations],
        }
