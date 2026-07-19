from __future__ import annotations

from blt_mayo.analyzers.base import Analyzer
from blt_mayo.analyzers.shell_script import ShellScriptAnalyzer
from blt_mayo.config.models import ScanConfig
from blt_mayo.models.artifact import Artifact
from blt_mayo.models.finding import Finding


class AnalyzerRegistry:
    """Dispatch artifacts to analyzers enabled in configuration."""

    def __init__(self, analyzers: list[Analyzer] | None = None) -> None:
        # PR 1 registers only shell-script analysis. Python AST, cron, systemd,
        # startup-hook, and SSH analysis are intentionally outside this PR.
        self.analyzers = analyzers or [ShellScriptAnalyzer()]

    def analyze(self, artifact: Artifact, config: ScanConfig) -> list[Finding]:
        findings: list[Finding] = []
        for analyzer in self.analyzers:
            if analyzer.name in config.enabled_analyzers and analyzer.supports(artifact):
                findings.extend(analyzer.analyze(artifact, config))
        return findings
