from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .enums import (
    ArtifactType,
    Confidence,
    PathSensitivity,
    ReviewStatus,
    Severity,
)


@dataclass(slots=True)
class Evidence:
    summary: str
    line_number: int | None = None
    snippet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Finding:
    rule_id: str
    title: str
    category: str
    severity: Severity
    confidence: Confidence
    description: str
    remediation: str
    artifact_path: Path
    artifact_type: ArtifactType
    path_sensitivity: PathSensitivity
    evidence: Evidence
    tags: list[str] = field(default_factory=list)
    execution_context: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    review_status: ReviewStatus = ReviewStatus.OPEN
    risk_score: float | None = None
    chain_id: str | None = None
    detected_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    finding_id: str = ""

    def __post_init__(self) -> None:
        if not self.finding_id:
            basis = "|".join(
                [
                    self.rule_id,
                    str(self.artifact_path),
                    str(self.evidence.line_number or 0),
                    self.evidence.summary,
                ]
            )
            self.finding_id = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["artifact_path"] = str(self.artifact_path)
        payload["artifact_type"] = self.artifact_type.value
        payload["path_sensitivity"] = self.path_sensitivity.value
        payload["severity"] = self.severity.value
        payload["confidence"] = self.confidence.value
        payload["review_status"] = self.review_status.value
        return payload
