"""
test_config.py

Tests for configuration loading and validation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from advisory_engine.config.loader import ConfigurationLoader
from advisory_engine.config.validator import (
    ConfigurationValidationError,
    ConfigurationValidator,
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def write_config(path: Path, data: dict) -> Path:
    """Write a temporary configuration file."""

    config_file = path / ".preflight.yaml"

    with config_file.open("w", encoding="utf-8") as fp:
        yaml.safe_dump(data, fp)

    return config_file


# ---------------------------------------------------------------------
# Loader Tests
# ---------------------------------------------------------------------


def test_load_defaults_when_file_missing(tmp_path):
    loader = ConfigurationLoader(tmp_path / ".preflight.yaml")

    config = loader.load()

    assert "retrieval" in config
    assert "llm" in config
    assert "cache" in config
    assert "validation" in config
    assert "pipeline" in config


def test_load_valid_configuration(tmp_path):
    config_file = write_config(
        tmp_path,
        {
            "retrieval": {
                "top_k": 10,
            },
            "llm": {
                "timeout_seconds": 30,
            },
        },
    )

    loader = ConfigurationLoader(config_file)

    config = loader.load()

    assert config["retrieval"]["top_k"] == 10
    assert config["llm"]["timeout_seconds"] == 30


def test_recursive_merge_preserves_defaults(tmp_path):
    config_file = write_config(
        tmp_path,
        {
            "retrieval": {
                "top_k": 8,
            }
        },
    )

    loader = ConfigurationLoader(config_file)

    config = loader.load()

    assert config["retrieval"]["top_k"] == 8
    assert "similarity_threshold" in config["retrieval"]
    assert "max_results" in config["retrieval"]


def test_nested_get_returns_value():
    config = {
        "a": {
            "b": {
                "c": 42,
            }
        }
    }

    assert (
        ConfigurationLoader.get(
            config,
            "a",
            "b",
            "c",
        )
        == 42
    )


def test_nested_get_returns_default():
    config = {}

    value = ConfigurationLoader.get(
        config,
        "missing",
        default=123,
    )

    assert value == 123


# ---------------------------------------------------------------------
# Validator Tests
# ---------------------------------------------------------------------


@pytest.fixture
def valid_config():
    return {
        "retrieval": {
            "similarity_threshold": 0.7,
            "top_k": 5,
            "max_results": 10,
        },
        "llm": {
            "timeout_seconds": 20,
            "temperature": 0.2,
            "max_retries": 3,
        },
        "cache": {
            "embedding_size": 100,
            "retrieval_size": 100,
            "ttl_seconds": 3600,
        },
        "validation": {
            "validate_schema": True,
            "validate_metadata": True,
            "remove_duplicates": True,
        },
        "pipeline": {
            "enable_metrics": True,
            "enable_fallback": True,
            "timing": True,
        },
    }


def test_valid_configuration(valid_config):
    result = ConfigurationValidator.validate(valid_config)

    assert result == valid_config


@pytest.mark.parametrize(
    "threshold",
    [
        -0.1,
        1.5,
    ],
)
def test_invalid_similarity_threshold(
    valid_config,
    threshold,
):
    valid_config["retrieval"][
        "similarity_threshold"
    ] = threshold

    with pytest.raises(ConfigurationValidationError):
        ConfigurationValidator.validate(valid_config)


def test_similarity_threshold_type(valid_config):
    valid_config["retrieval"][
        "similarity_threshold"
    ] = "high"

    with pytest.raises(ConfigurationValidationError):
        ConfigurationValidator.validate(valid_config)


def test_invalid_top_k(valid_config):
    valid_config["retrieval"]["top_k"] = 0

    with pytest.raises(ConfigurationValidationError):
        ConfigurationValidator.validate(valid_config)


def test_max_results_smaller_than_top_k(valid_config):
    valid_config["retrieval"]["top_k"] = 10
    valid_config["retrieval"]["max_results"] = 5

    with pytest.raises(ConfigurationValidationError):
        ConfigurationValidator.validate(valid_config)


def test_invalid_timeout(valid_config):
    valid_config["llm"]["timeout_seconds"] = -1

    with pytest.raises(ConfigurationValidationError):
        ConfigurationValidator.validate(valid_config)


def test_invalid_temperature(valid_config):
    valid_config["llm"]["temperature"] = 5

    with pytest.raises(ConfigurationValidationError):
        ConfigurationValidator.validate(valid_config)


def test_invalid_retry_count(valid_config):
    valid_config["llm"]["max_retries"] = -2

    with pytest.raises(ConfigurationValidationError):
        ConfigurationValidator.validate(valid_config)


@pytest.mark.parametrize(
    "field",
    [
        "embedding_size",
        "retrieval_size",
        "ttl_seconds",
    ],
)
def test_invalid_cache_values(
    valid_config,
    field,
):
    valid_config["cache"][field] = 0

    with pytest.raises(ConfigurationValidationError):
        ConfigurationValidator.validate(valid_config)


@pytest.mark.parametrize(
    "field",
    [
        "validate_schema",
        "validate_metadata",
        "remove_duplicates",
    ],
)
def test_validation_flags_must_be_boolean(
    valid_config,
    field,
):
    valid_config["validation"][field] = "true"

    with pytest.raises(ConfigurationValidationError):
        ConfigurationValidator.validate(valid_config)


@pytest.mark.parametrize(
    "field",
    [
        "enable_metrics",
        "enable_fallback",
        "timing",
    ],
)
def test_pipeline_flags_must_be_boolean(
    valid_config,
    field,
):
    valid_config["pipeline"][field] = 1

    with pytest.raises(ConfigurationValidationError):
        ConfigurationValidator.validate(valid_config)


def test_partial_configuration_load(tmp_path):
    config_file = write_config(
        tmp_path,
        {
            "pipeline": {
                "enable_metrics": False,
            }
        },
    )

    loader = ConfigurationLoader(config_file)

    config = loader.load()

    assert config["pipeline"]["enable_metrics"] is False

    ConfigurationValidator.validate(config)


def test_empty_yaml_file(tmp_path):
    config_file = tmp_path / ".preflight.yaml"

    config_file.write_text("", encoding="utf-8")

    loader = ConfigurationLoader(config_file)

    config = loader.load()

    assert "retrieval" in config

    ConfigurationValidator.validate(config)


def test_unknown_keys_are_preserved(tmp_path):
    config_file = write_config(
        tmp_path,
        {
            "custom": {
                "my_setting": 123,
            }
        },
    )

    loader = ConfigurationLoader(config_file)

    config = loader.load()

    assert config["custom"]["my_setting"] == 123


def test_multiple_overrides(tmp_path):
    config_file = write_config(
        tmp_path,
        {
            "retrieval": {
                "top_k": 20,
                "similarity_threshold": 0.85,
            },
            "llm": {
                "timeout_seconds": 45,
            },
        },
    )

    loader = ConfigurationLoader(config_file)

    config = loader.load()

    assert config["retrieval"]["top_k"] == 20
    assert config["retrieval"]["similarity_threshold"] == 0.85
    assert config["llm"]["timeout_seconds"] == 45

    ConfigurationValidator.validate(config)