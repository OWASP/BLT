"""
metrics.py

Performance metrics for the BLT Preflight benchmark system.

Responsibilities
----------------
- Calculate benchmark statistics
- Compute percentiles
- Calculate throughput
- Measure execution stability
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from statistics import mean, median, pstdev
from typing import Any

from advisory_engine.benchmark.runner import BenchmarkResult


@dataclass(slots=True)
class BenchmarkMetrics:
    """
    Derived benchmark metrics.
    """

    success_rate: float

    failure_rate: float

    average_ms: float

    median_ms: float

    minimum_ms: float

    maximum_ms: float

    std_deviation_ms: float

    p95_ms: float

    p99_ms: float

    throughput_per_second: float


class BenchmarkMetricsCalculator:
    """
    Computes derived benchmark metrics.
    """

    @staticmethod
    def calculate(
        result: BenchmarkResult,
    ) -> BenchmarkMetrics:

        timings = sorted(
            iteration.elapsed_ms
            for iteration in result.results
        )

        if not timings:
            raise ValueError(
                "Benchmark contains no timing data."
            )

        total = len(timings)

        success_rate = (
            result.successful / total
        ) * 100

        failure_rate = (
            result.failed / total
        ) * 100

        total_seconds = result.total_ms / 1000

        throughput = (
            total / total_seconds
            if total_seconds > 0
            else 0.0
        )

        return BenchmarkMetrics(
            success_rate=success_rate,
            failure_rate=failure_rate,
            average_ms=mean(timings),
            median_ms=median(timings),
            minimum_ms=min(timings),
            maximum_ms=max(timings),
            std_deviation_ms=(
                pstdev(timings)
                if total > 1
                else 0.0
            ),
            p95_ms=_percentile(
                timings,
                95,
            ),
            p99_ms=_percentile(
                timings,
                99,
            ),
            throughput_per_second=throughput,
        )

    @staticmethod
    def to_dict(
        metrics: BenchmarkMetrics,
    ) -> dict[str, Any]:
        return asdict(metrics)


def _percentile(
    values: list[float],
    percentile: int,
) -> float:
    """
    Calculate percentile using
    nearest-rank interpolation.
    """

    if not values:
        return 0.0

    if percentile <= 0:
        return values[0]

    if percentile >= 100:
        return values[-1]

    index = (
        (len(values) - 1)
        * percentile
        / 100
    )

    lower = int(index)
    upper = min(
        lower + 1,
        len(values) - 1,
    )

    weight = index - lower

    return (
        values[lower] * (1 - weight)
        + values[upper] * weight
    )