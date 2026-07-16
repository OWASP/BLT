"""
metrics.py

Performance metrics collection for the BLT Preflight pipeline.

Responsibilities
----------------
- Measure pipeline execution times
- Track cache performance
- Track retrieval statistics
- Track advisory generation statistics
- Provide aggregated metrics

This module performs no logging or persistence.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(slots=True)
class Timer:
    """
    Represents timing information for a pipeline stage.
    """

    start: float = 0.0
    end: float = 0.0

    def begin(self) -> None:
        self.start = time.perf_counter()

    def stop(self) -> None:
        self.end = time.perf_counter()

    @property
    def duration_ms(self) -> float:
        return round((self.end - self.start) * 1000, 2)


@dataclass(slots=True)
class PipelineMetrics:
    """
    Metrics collected for a single pipeline execution.
    """

    retrieval_time_ms: float = 0.0

    generation_time_ms: float = 0.0

    validation_time_ms: float = 0.0

    total_pipeline_time_ms: float = 0.0

    similarity_score: float = 0.0

    retrieved_chunks: int = 0

    accepted_chunks: int = 0

    cache_hit: bool = False

    fallback_used: bool = False

    retries: int = 0


class MetricsCollector:
    """
    Collects metrics across multiple pipeline executions.
    """

    def __init__(self) -> None:

        self.execution_count = 0

        self._metrics: list[PipelineMetrics] = []

        self._timers: dict[str, Timer] = defaultdict(Timer)

    def start(self, stage: str) -> None:
        """
        Start timing a pipeline stage.
        """

        self._timers[stage].begin()

    def stop(self, stage: str) -> float:
        """
        Stop timing a pipeline stage.
        """

        self._timers[stage].stop()

        return self._timers[stage].duration_ms

    def record(
        self,
        metrics: PipelineMetrics,
    ) -> None:
        """
        Store one pipeline execution.
        """

        self.execution_count += 1

        self._metrics.append(metrics)

    def summary(self) -> dict[str, float]:
        """
        Aggregate metrics across executions.
        """

        if not self._metrics:

            return {
                "executions": 0,
            }

        total = len(self._metrics)

        avg_retrieval = sum(
            m.retrieval_time_ms for m in self._metrics
        ) / total

        avg_generation = sum(
            m.generation_time_ms for m in self._metrics
        ) / total

        avg_pipeline = sum(
            m.total_pipeline_time_ms for m in self._metrics
        ) / total

        avg_similarity = sum(
            m.similarity_score for m in self._metrics
        ) / total

        cache_hits = sum(
            int(m.cache_hit)
            for m in self._metrics
        )

        fallbacks = sum(
            int(m.fallback_used)
            for m in self._metrics
        )

        return {
            "executions": total,
            "average_retrieval_ms": round(avg_retrieval, 2),
            "average_generation_ms": round(avg_generation, 2),
            "average_pipeline_ms": round(avg_pipeline, 2),
            "average_similarity": round(avg_similarity, 3),
            "cache_hit_rate": round(cache_hits / total, 3),
            "fallback_rate": round(fallbacks / total, 3),
        }

    def reset(self) -> None:
        """
        Clear all metrics.
        """

        self.execution_count = 0

        self._metrics.clear()

        self._timers.clear()