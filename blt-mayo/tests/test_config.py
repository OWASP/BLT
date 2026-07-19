from pathlib import Path

import pytest

from blt_mayo.config.loader import ConfigError, load_config


def test_load_relative_paths_from_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yml"
    config_file.write_text("profile: quick\ninclude_paths:\n  - sample\n", encoding="utf-8")
    config = load_config(config_file)
    assert config.profile == "quick"
    assert config.max_depth == 5
    assert config.include_paths == [(tmp_path / "sample").resolve()]


def test_invalid_profile_is_rejected(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yml"
    config_file.write_text("profile: impossible\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="Unknown profile"):
        load_config(config_file)


def test_overrides_replace_file_values(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yml"
    config_file.write_text("profile: quick\nfollow_symlinks: false\n", encoding="utf-8")
    config = load_config(config_file, {"profile": "deep", "follow_symlinks": True})
    assert config.profile == "deep"
    assert config.max_depth == 30
    assert config.follow_symlinks is True
