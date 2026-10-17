from __future__ import annotations

from pathlib import Path

from blt_mayo.analyzers.registry import AnalyzerRegistry
from blt_mayo.config.models import ScanConfig
from blt_mayo.models.scan import ScanResult
from blt_mayo.scanner.traversal import walk_root


class ScanOrchestrator:
    def __init__(self, config: ScanConfig, registry: AnalyzerRegistry | None = None) -> None:
        self.config = config
        self.registry = registry or AnalyzerRegistry()

    def scan(self, roots: list[Path] | None = None) -> ScanResult:
        scan_roots = roots or self.config.include_paths
        if not scan_roots:
            raise ValueError("At least one scan root is required")
        result = ScanResult(roots=[path.expanduser().resolve() for path in scan_roots])
        for root in result.roots:
            artifacts, observations = walk_root(root, self.config)
            result.artifacts.extend(artifacts)
            result.observations.extend(observations)
        seen: set[str] = set()
        for artifact in result.artifacts:
            for finding in self.registry.analyze(artifact, self.config):
                if finding.finding_id not in seen:
                    seen.add(finding.finding_id)
                    result.findings.append(finding)
        result.findings.sort(
            key=lambda finding: (finding.severity.value, str(finding.artifact_path))
        )
        result.finish()
        return result
