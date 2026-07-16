"""
validator.py

Configuration validation for the BLT Preflight advisory pipeline.

Responsibilities
----------------
- Validate .preflight.yaml
- Validate configuration types
- Validate configuration ranges
- Validate required sections

This module performs no configuration loading.
"""

from __future__ import annotations

from typing import Any


class ConfigurationValidationError(ValueError):
    """Raised when configuration validation fails."""


class ConfigurationValidator:
    """
    Validates the merged pipeline configuration.
    """

    @staticmethod
    def validate(config: dict[str, Any]) -> dict[str, Any]:
        """
        Validate the complete configuration.

        Parameters
        ----------
        config
            Merged configuration dictionary.

        Returns
        -------
        dict
            Validated configuration.
        """

        ConfigurationValidator._validate_retrieval(
            config.get("retrieval", {})
        )

        ConfigurationValidator._validate_llm(
            config.get("llm", {})
        )

        ConfigurationValidator._validate_cache(
            config.get("cache", {})
        )

        ConfigurationValidator._validate_validation(
            config.get("validation", {})
        )

        ConfigurationValidator._validate_pipeline(
            config.get("pipeline", {})
        )

        return config

    @staticmethod
    def _validate_retrieval(
        retrieval: dict[str, Any],
    ) -> None:

        threshold = retrieval.get("similarity_threshold")

        if not isinstance(threshold, (float, int)):
            raise ConfigurationValidationError(
                "retrieval.similarity_threshold must be numeric."
            )

        if not 0 <= threshold <= 1:
            raise ConfigurationValidationError(
                "retrieval.similarity_threshold must be between 0 and 1."
            )

        top_k = retrieval.get("top_k")

        if not isinstance(top_k, int) or top_k <= 0:
            raise ConfigurationValidationError(
                "retrieval.top_k must be greater than zero."
            )

        max_results = retrieval.get("max_results")

        if not isinstance(max_results, int):
            raise ConfigurationValidationError(
                "retrieval.max_results must be an integer."
            )

        if max_results < top_k:
            raise ConfigurationValidationError(
                "retrieval.max_results must be >= retrieval.top_k."
            )

    @staticmethod
    def _validate_llm(
        llm: dict[str, Any],
    ) -> None:

        timeout = llm.get("timeout_seconds")

        if not isinstance(timeout, int) or timeout <= 0:
            raise ConfigurationValidationError(
                "llm.timeout_seconds must be greater than zero."
            )

        retries = llm.get("max_retries")

        if not isinstance(retries, int) or retries < 0:
            raise ConfigurationValidationError(
                "llm.max_retries must be >= 0."
            )

        temperature = llm.get("temperature")

        if not isinstance(temperature, (int, float)):
            raise ConfigurationValidationError(
                "llm.temperature must be numeric."
            )

        if not 0 <= temperature <= 2:
            raise ConfigurationValidationError(
                "llm.temperature must be between 0 and 2."
            )

    @staticmethod
    def _validate_cache(
        cache: dict[str, Any],
    ) -> None:

        for key in (
            "embedding_size",
            "retrieval_size",
            "ttl_seconds",
        ):
            value = cache.get(key)

            if not isinstance(value, int):
                raise ConfigurationValidationError(
                    f"cache.{key} must be an integer."
                )

            if value <= 0:
                raise ConfigurationValidationError(
                    f"cache.{key} must be greater than zero."
                )

    @staticmethod
    def _validate_validation(
        validation: dict[str, Any],
    ) -> None:

        for key in (
            "validate_schema",
            "validate_metadata",
            "remove_duplicates",
        ):
            value = validation.get(key)

            if not isinstance(value, bool):
                raise ConfigurationValidationError(
                    f"validation.{key} must be boolean."
                )

    @staticmethod
    def _validate_pipeline(
        pipeline: dict[str, Any],
    ) -> None:

        for key in (
            "enable_metrics",
            "enable_fallback",
            "timing",
        ):
            value = pipeline.get(key)

            if not isinstance(value, bool):
                raise ConfigurationValidationError(
                    f"pipeline.{key} must be boolean."
                )