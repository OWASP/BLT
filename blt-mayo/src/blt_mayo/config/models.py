from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class MaskingConfig:
    enabled: bool = True
    max_snippet_length: int = 180


@dataclass(slots=True)
class ScanConfig:
    include_paths: list[Path] = field(default_factory=list)
    exclude_patterns: list[str] = field(
        default_factory=lambda: [
            ".git",
            "__pycache__",
            "*.pyc",
            "node_modules",
            ".venv",
            "venv",
        ]
    )
    follow_symlinks: bool = False
    max_depth: int = 12
    max_file_size: int = 2_000_000
    enabled_analyzers: set[str] = field(default_factory=lambda: {"shell"})
    profile: str = "standard"
    masking: MaskingConfig = field(default_factory=MaskingConfig)


PROFILE_DEFAULTS: dict[str, dict[str, int]] = {
    "quick": {"max_depth": 5, "max_file_size": 500_000},
    "standard": {"max_depth": 12, "max_file_size": 2_000_000},
    "deep": {"max_depth": 30, "max_file_size": 5_000_000},
    "policy": {"max_depth": 15, "max_file_size": 1_000_000},
}
