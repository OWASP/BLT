"""
fallback.py

Deterministic fallback advisory generation for the BLT Preflight pipeline.

Responsibilities
----------------
- Produce advisories when AI generation cannot be used
- Handle retrieval failures
- Handle timeout failures
- Handle low similarity retrieval
- Return advisories compatible with AdvisorySchema

This module never calls an LLM.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from advisory_engine.config.defaults import DEFAULT_SEVERITY

logger = logging.getLogger(__name__)


class FallbackReason(str, Enum):
    """Reasons for generating a fallback advisory."""

    LOW_SIMILARITY = "low_similarity"
    NO_RETRIEVAL_RESULTS = "no_retrieval_results"
    RETRIEVAL_FAILURE = "retrieval_failure"
    LLM_TIMEOUT = "llm_timeout"
    LLM_FAILURE = "llm_failure"
    PIPELINE_FAILURE = "pipeline_failure"


class FallbackGenerator:
    """
    Generates deterministic advisories when the
    normal advisory pipeline cannot complete.
    """

    def __init__(
        self,
        default_severity: str = DEFAULT_SEVERITY,
    ) -> None:
        self.default_severity = default_severity

    def generate(
        self,
        *,
        reason: FallbackReason,
        context: dict[str, Any] | None = None,
        details: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a deterministic advisory.

        Parameters
        ----------
        reason
            Why the fallback was triggered.

        context
            Optional pipeline context.

        details
            Optional implementation-specific information.
        """

        logger.warning(
            "Generating fallback advisory (%s)",
            reason.value,
        )

        recommendation = self._recommendation(reason)

        explanation = self._explanation(reason, details)

        return {
            "severity": self.default_severity,
            "category": "Pipeline Reliability",
            "title": "Automated advisory unavailable",
            "explanation": explanation,
            "recommendation": recommendation,
            "references": [],
            "metadata": {
                "fallback": True,
                "reason": reason.value,
                "repository": (
                    context.get("repository")
                    if context
                    else None
                ),
            },
        }

    @staticmethod
    def _recommendation(
        reason: FallbackReason,
    ) -> str:
        """
        Return deterministic recommendation text.
        """

        recommendations = {
            FallbackReason.LOW_SIMILARITY:
                "The retrieved documentation was not sufficiently relevant. Review the merge request manually.",

            FallbackReason.NO_RETRIEVAL_RESULTS:
                "No supporting security documentation was retrieved. Manual review is recommended.",

            FallbackReason.RETRIEVAL_FAILURE:
                "The retrieval stage failed. Verify the knowledge base and vector index.",

            FallbackReason.LLM_TIMEOUT:
                "The language model did not respond within the configured timeout. Retry later or inspect manually.",

            FallbackReason.LLM_FAILURE:
                "The configured language model failed unexpectedly. Review the logs for additional details.",

            FallbackReason.PIPELINE_FAILURE:
                "The advisory pipeline encountered an unexpected error. Manual security review is recommended.",
        }

        return recommendations[reason]

    @staticmethod
    def _explanation(
        reason: FallbackReason,
        details: str | None,
    ) -> str:
        """
        Build explanation message.
        """

        explanation = (
            f"Preflight could not generate an AI-assisted advisory "
            f"because '{reason.value}' occurred."
        )

        if details:
            explanation += f" Details: {details}"

        return explanation