from __future__ import annotations

import re
from pathlib import Path

from blt_mayo.analyzers.base import Analyzer
from blt_mayo.config.models import ScanConfig
from blt_mayo.models.artifact import Artifact
from blt_mayo.models.enums import ArtifactType, PathSensitivity, Severity
from blt_mayo.models.finding import Evidence, Finding
from blt_mayo.rules.shell_execution import ShellExecutionRule, match_shell_execution_rules

_SEVERITY_ORDER = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


class ShellScriptAnalyzer(Analyzer):
    """Safely inspect shell scripts without sourcing or executing them."""

    name = "shell"

    def supports(self, artifact: Artifact) -> bool:
        return artifact.artifact_type == ArtifactType.SHELL_SCRIPT

    def analyze(self, artifact: Artifact, config: ScanConfig) -> list[Finding]:
        if not self.supports(artifact):
            return []

        source = _read_source(artifact.path)
        if source is None:
            return []

        findings: list[Finding] = []
        for line_number, line in enumerate(source.splitlines(), start=1):
            if _is_comment_or_blank(line):
                continue
            for rule, _match in match_shell_execution_rules(line):
                findings.append(
                    _build_finding(
                        artifact=artifact,
                        config=config,
                        line=line,
                        line_number=line_number,
                        rule=rule,
                    )
                )
        return findings


def _read_source(path: Path) -> str | None:
    """Read source text safely, replacing invalid byte sequences and never executing it."""

    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (PermissionError, OSError):
        return None


def _short_snippet(line: str, config: ScanConfig) -> str:
    """Return one normalized, length-limited evidence line."""

    cleaned = re.sub(r"\s+", " ", line.strip())
    limit = max(1, config.masking.max_snippet_length)
    if len(cleaned) <= limit:
        return cleaned
    if limit == 1:
        return "…"
    return f"{cleaned[: limit - 1]}…"


def _is_comment_or_blank(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


def _elevate_for_sensitive_path(
    severity: Severity, sensitivity: PathSensitivity
) -> Severity:
    """Raise severity by one level for high- or critical-sensitivity paths."""

    if sensitivity not in {PathSensitivity.HIGH, PathSensitivity.CRITICAL}:
        return severity
    target = min(_SEVERITY_ORDER[severity] + 1, _SEVERITY_ORDER[Severity.CRITICAL])
    return next(item for item, order in _SEVERITY_ORDER.items() if order == target)


def _build_finding(
    *,
    artifact: Artifact,
    config: ScanConfig,
    line: str,
    line_number: int,
    rule: ShellExecutionRule,
) -> Finding:
    return Finding(
        rule_id=rule.rule_id,
        title=rule.title,
        category="dangerous-execution",
        severity=_elevate_for_sensitive_path(rule.severity, artifact.sensitivity),
        confidence=rule.confidence,
        description=rule.description,
        remediation=rule.remediation,
        artifact_path=artifact.path,
        artifact_type=artifact.artifact_type,
        path_sensitivity=artifact.sensitivity,
        evidence=Evidence(
            summary=f"Matched dangerous shell construction near line {line_number}",
            line_number=line_number,
            snippet=_short_snippet(line, config),
        ),
        tags=list(rule.tags),
        metadata={
            "owner": artifact.metadata.owner,
            "group": artifact.metadata.group,
            "permissions": artifact.metadata.permissions,
            "is_world_writable": artifact.metadata.is_world_writable,
            "is_group_writable": artifact.metadata.is_group_writable,
        },
    )
