"""
loader.py

Configuration loader for the BLT Preflight advisory pipeline.

Responsibilities
----------------
- Load project configuration from .preflight.yaml
- Merge user configuration with defaults
- Validate configuration structure
- Provide a single configuration interface

This module intentionally does not perform schema validation.
Validation belongs to validator.py.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from advisory_engine.config import defaults

logger = logging.getLogger(__name__)


DEFAULT_CONFIG_FILE = ".preflight.yaml"


class ConfigurationLoader:
    """
    Loads configuration from .preflight.yaml and merges
    it with the built-in defaults.
    """

    def __init__(
        self,
        config_path: str | Path = DEFAULT_CONFIG_FILE,
    ) -> None:

        self.config_path = Path(config_path)

    def load(self) -> dict[str, Any]:
        """
        Load configuration.

        Returns
        -------
        dict
            Final merged configuration.
        """

        config = self._default_config()

        if not self.config_path.exists():

            logger.info(
                "Configuration file '%s' not found. Using defaults.",
                self.config_path,
            )

            return config

        logger.info(
            "Loading configuration from %s",
            self.config_path,
        )

        with self.config_path.open(
            "r",
            encoding="utf-8",
        ) as fp:

            user_config = yaml.safe_load(fp) or {}

        self._merge(config, user_config)

        return config

    def _default_config(self) -> dict[str, Any]:
        """
        Build configuration dictionary from defaults.py.
        """

        return {
            "retrieval": {
                "similarity_threshold": defaults.SIMILARITY_THRESHOLD,
                "top_k": defaults.TOP_K,
                "max_results": defaults.MAX_RETRIEVAL_RESULTS,
            },
            "llm": {
                "timeout_seconds": defaults.LLM_TIMEOUT_SECONDS,
                "temperature": defaults.DEFAULT_TEMPERATURE,
                "max_retries": defaults.MAX_RETRIES,
            },
            "cache": {
                "embedding_size": defaults.EMBEDDING_CACHE_SIZE,
                "retrieval_size": defaults.RETRIEVAL_CACHE_SIZE,
                "ttl_seconds": defaults.CACHE_TTL_SECONDS,
            },
            "validation": {
                "validate_schema": defaults.VALIDATE_SCHEMA,
                "validate_metadata": defaults.VALIDATE_METADATA,
                "remove_duplicates": defaults.REMOVE_DUPLICATES,
            },
            "pipeline": {
                "enable_metrics": defaults.ENABLE_METRICS,
                "enable_fallback": defaults.ENABLE_FALLBACK,
                "timing": defaults.ENABLE_PIPELINE_TIMING,
            },
        }

    def _merge(
        self,
        base: dict[str, Any],
        override: dict[str, Any],
    ) -> None:
        """
        Recursively merge user configuration into defaults.
        """

        for key, value in override.items():

            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                self._merge(base[key], value)

            else:
                base[key] = value

    @staticmethod
    def get(
        config: dict[str, Any],
        *keys: str,
        default: Any = None,
    ) -> Any:
        """
        Retrieve nested configuration values.

        Example
        -------
        get(config, "llm", "timeout_seconds")
        """

        current: Any = config

        for key in keys:

            if not isinstance(current, dict):
                return default

            current = current.get(key)

            if current is None:
                return default

        return current