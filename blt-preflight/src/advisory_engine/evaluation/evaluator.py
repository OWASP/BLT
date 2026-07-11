"""
evaluator.py

Pipeline evaluation for the BLT Preflight advisory system.

Responsibilities
----------------
- Evaluate advisory generation quality
- Aggregate pipeline metrics
- Produce execution reports
- Support future benchmarking

This module does not modify pipeline behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from advisory_engine.evaluation.confidence import (
    ConfidenceEvaluator,
    ConfidenceInputs,
    ConfidenceResult,
)


@dataclass(slots=True)
class EvaluationInput:
    """
    Inputs collected after one pipeline execution.
    """

    similarity_score: float

    retrieval_quality: float

    validation_score: float

    retrieval_time_ms: float

    generation_time_ms: float

    validation_time_ms: float

    total_pipeline_time_ms: float

    cache_hit: bool

    fallback_used: bool

    retries: int

    timeout_occurred: bool

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvaluationReport:
    """
    Complete evaluation report.
    """

    timestamp: str

    confidence: ConfidenceResult

    metrics: dict[str, Any]

    summary: dict[str, Any]


class PipelineEvaluator:
    """
    Evaluates pipeline executions.
    """

    @staticmethod
    def evaluate(
        execution: EvaluationInput,
    ) -> EvaluationReport:
        """
        Evaluate one advisory execution.
        """

        confidence = ConfidenceEvaluator.evaluate(
            ConfidenceInputs(
                similarity_score=execution.similarity_score,
                retrieval_quality=execution.retrieval_quality,
                validation_score=execution.validation_score,
                fallback_used=execution.fallback_used,
                retries=execution.retries,
                timeout_occurred=execution.timeout_occurred,
            )
        )

        metrics = {
            "retrieval": {
                "quality": execution.retrieval_quality,
                "similarity": execution.similarity_score,
                "time_ms": execution.retrieval_time_ms,
            },
            "generation": {
                "time_ms": execution.generation_time_ms,
            },
            "validation": {
                "score": execution.validation_score,
                "time_ms": execution.validation_time_ms,
            },
            "pipeline": {
                "time_ms": execution.total_pipeline_time_ms,
                "cache_hit": execution.cache_hit,
                "fallback_used": execution.fallback_used,
                "retries": execution.retries,
                "timeout_occurred": execution.timeout_occurred,
            },
        }

        summary = {
            "pipeline_status": (
                "Fallback"
                if execution.fallback_used
                else "Success"
            ),
            "confidence": confidence.level,
            "confidence_score": confidence.score,
            "cache": (
                "Hit"
                if execution.cache_hit
                else "Miss"
            ),
            "execution_time_ms": execution.total_pipeline_time_ms,
        }

        return EvaluationReport(
            timestamp=datetime.utcnow().isoformat() + "Z",
            confidence=confidence,
            metrics=metrics,
            summary=summary,
        )

    @staticmethod
    def to_dict(
        report: EvaluationReport,
    ) -> dict[str, Any]:
        """
        Convert report into a serializable dictionary.
        """

        return {
            "timestamp": report.timestamp,
            "confidence": {
                "score": report.confidence.score,
                "level": report.confidence.level,
                "explanation": report.confidence.explanation,
            },
            "metrics": report.metrics,
            "summary": report.summary,
        }