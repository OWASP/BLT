"""
confidence.py

Confidence scoring for the BLT Preflight advisory pipeline.

Responsibilities
----------------
- Calculate advisory confidence
- Combine retrieval and generation quality
- Penalize fallback execution
- Produce confidence levels
- Remain independent of any LLM provider
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConfidenceInputs:
    """
    Inputs required to compute advisory confidence.
    """

    similarity_score: float

    retrieval_quality: float

    validation_score: float

    fallback_used: bool = False

    retries: int = 0

    timeout_occurred: bool = False


@dataclass(slots=True)
class ConfidenceResult:
    """
    Final confidence assessment.
    """

    score: float

    level: str

    explanation: str


class ConfidenceEvaluator:
    """
    Computes advisory confidence.

    Score Range
    -----------
    0.00 - 1.00
    """

    HIGH_THRESHOLD = 0.80
    MEDIUM_THRESHOLD = 0.60
    LOW_THRESHOLD = 0.40

    @classmethod
    def evaluate(
        cls,
        inputs: ConfidenceInputs,
    ) -> ConfidenceResult:
        """
        Calculate confidence score.
        """

        score = (
            (inputs.similarity_score * 0.45)
            + (inputs.retrieval_quality * 0.35)
            + (inputs.validation_score * 0.20)
        )

        if inputs.fallback_used:
            score *= 0.60

        if inputs.timeout_occurred:
            score *= 0.90

        score -= min(inputs.retries * 0.02, 0.10)

        score = max(0.0, min(score, 1.0))

        level = cls._level(score)

        explanation = cls._explanation(
            score,
            level,
            inputs,
        )

        return ConfidenceResult(
            score=round(score, 3),
            level=level,
            explanation=explanation,
        )

    @classmethod
    def _level(
        cls,
        score: float,
    ) -> str:
        """
        Convert numerical confidence to category.
        """

        if score >= cls.HIGH_THRESHOLD:
            return "High"

        if score >= cls.MEDIUM_THRESHOLD:
            return "Medium"

        if score >= cls.LOW_THRESHOLD:
            return "Low"

        return "Very Low"

    @staticmethod
    def _explanation(
        score: float,
        level: str,
        inputs: ConfidenceInputs,
    ) -> str:
        """
        Produce a human-readable explanation.
        """

        reasons: list[str] = []

        if inputs.similarity_score < 0.60:
            reasons.append(
                "retrieval similarity was below the preferred threshold"
            )

        if inputs.retrieval_quality < 0.60:
            reasons.append(
                "retrieval quality was moderate"
            )

        if inputs.validation_score < 0.75:
            reasons.append(
                "advisory validation reduced confidence"
            )

        if inputs.fallback_used:
            reasons.append(
                "fallback generation was used"
            )

        if inputs.timeout_occurred:
            reasons.append(
                "a timeout occurred during execution"
            )

        if inputs.retries:
            reasons.append(
                f"{inputs.retries} retry attempt(s) were required"
            )

        if not reasons:
            reasons.append(
                "all pipeline stages completed successfully"
            )

        return (
            f"Confidence {level} ({score:.3f}). "
            + "; ".join(reasons)
            + "."
        )