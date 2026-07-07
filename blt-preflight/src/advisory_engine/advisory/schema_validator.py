"""
schema_validator.py

Validates advisory responses produced by the LLM.

Responsibilities
----------------
- Validate required fields
- Validate field types
- Validate severity values
- Validate references
- Ensure advisory conforms to AdvisorySchema

This module intentionally performs NO retrieval,
NO LLM calls and NO prompt generation.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from advisory_engine.rag.schema import AdvisorySchema

logger = logging.getLogger(__name__)


class AdvisoryValidationError(Exception):
    """Raised when an advisory fails schema validation."""


class SchemaValidator:
    """
    Validates generated advisories against
    the project's canonical AdvisorySchema.
    """

    REQUIRED_SEVERITIES = {
        "LOW",
        "MEDIUM",
        "HIGH",
    }

    def validate(
        self,
        advisory: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate advisory.

        Parameters
        ----------
        advisory:
            Dictionary returned from the LLM provider.

        Returns
        -------
        dict
            Validated advisory.

        Raises
        ------
        AdvisoryValidationError
        """

        logger.info("Validating advisory schema")

        try:
            validated = AdvisorySchema(**advisory)

        except ValidationError as exc:
            logger.exception("Schema validation failed")
            raise AdvisoryValidationError(str(exc)) from exc

        severity = validated.severity.upper()

        if severity not in self.REQUIRED_SEVERITIES:
            raise AdvisoryValidationError(
                f"Unsupported severity '{severity}'."
            )

        references = getattr(validated, "references", [])

        if references is None:
            references = []

        if not isinstance(references, list):
            raise AdvisoryValidationError(
                "references must be a list."
            )

        recommendation = getattr(
            validated,
            "recommendation",
            "",
        )

        if not recommendation.strip():
            raise AdvisoryValidationError(
                "Recommendation cannot be empty."
            )

        explanation = getattr(
            validated,
            "explanation",
            "",
        )

        if not explanation.strip():
            raise AdvisoryValidationError(
                "Explanation cannot be empty."
            )

        logger.info("Advisory schema validation passed")

        return validated.model_dump()

    @staticmethod
    def is_valid(
        advisory: dict[str, Any],
    ) -> bool:
        """
        Convenience validation helper.

        Returns
        -------
        bool
            True if advisory is valid.
        """

        try:
            SchemaValidator().validate(advisory)
            return True

        except AdvisoryValidationError:
            return False