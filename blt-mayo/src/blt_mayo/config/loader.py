from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import PROFILE_DEFAULTS, MaskingConfig, ScanConfig


class ConfigError(ValueError):
    """Raised when the configuration is invalid."""


def _as_path_list(values: Any, base_dir: Path) -> list[Path]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ConfigError("include_paths must be a list")
    paths: list[Path] = []
    for value in values:
        path = Path(str(value)).expanduser()
        if not path.is_absolute():
            path = (base_dir / path).resolve()
        paths.append(path)
    return paths


def load_config(path: Path | None = None, overrides: dict[str, Any] | None = None) -> ScanConfig:
    data: dict[str, Any] = {}
    base_dir = Path.cwd()
    if path is not None:
        config_path = path.expanduser().resolve()
        if not config_path.exists():
            raise ConfigError(f"Configuration file does not exist: {config_path}")
        base_dir = config_path.parent
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ConfigError("Configuration root must be a mapping")
        data.update(loaded)
    if overrides:
        data.update({key: value for key, value in overrides.items() if value is not None})

    profile = str(data.get("profile", "standard"))
    if profile not in PROFILE_DEFAULTS:
        raise ConfigError(f"Unknown profile: {profile}")
    defaults = PROFILE_DEFAULTS[profile]

    masking_data = data.get("masking") or {}
    if not isinstance(masking_data, dict):
        raise ConfigError("masking must be a mapping")

    enabled = data.get("enabled_analyzers", ["shell"])
    if not isinstance(enabled, (list, set, tuple)):
        raise ConfigError("enabled_analyzers must be a list")

    return ScanConfig(
        include_paths=_as_path_list(data.get("include_paths"), base_dir),
        exclude_patterns=[
            str(item) for item in data.get("exclude_patterns", ScanConfig().exclude_patterns)
        ],
        follow_symlinks=bool(data.get("follow_symlinks", False)),
        max_depth=int(data.get("max_depth", defaults["max_depth"])),
        max_file_size=int(data.get("max_file_size", defaults["max_file_size"])),
        enabled_analyzers={str(item) for item in enabled},
        profile=profile,
        masking=MaskingConfig(
            enabled=bool(masking_data.get("enabled", True)),
            max_snippet_length=int(masking_data.get("max_snippet_length", 180)),
        ),
    )
