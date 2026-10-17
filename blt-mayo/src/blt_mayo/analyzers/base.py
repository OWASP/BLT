from __future__ import annotations

from abc import ABC, abstractmethod

from blt_mayo.config.models import ScanConfig
from blt_mayo.models.artifact import Artifact
from blt_mayo.models.finding import Finding


class Analyzer(ABC):
    name: str

    @abstractmethod
    def supports(self, artifact: Artifact) -> bool:
        raise NotImplementedError

    @abstractmethod
    def analyze(self, artifact: Artifact, config: ScanConfig) -> list[Finding]:
        raise NotImplementedError
