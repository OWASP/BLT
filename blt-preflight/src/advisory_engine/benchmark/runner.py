"""
runner.py

Benchmark runner for the BLT Preflight advisory pipeline.

Responsibilities
----------------
- Execute benchmark iterations
- Measure execution times
- Aggregate raw metrics
- Produce benchmark results

This module is independent of any specific LLM provider.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from statistics import mean
from time import perf_counter
from typing import Any, Callable


@dataclass(slots=True)
class BenchmarkIteration:
    """
    Result of a single benchmark iteration.
    """

    iteration: int
    elapsed_ms: float
    success: bool


@dataclass(slots=True)
class BenchmarkResult:
    """
    Aggregated benchmark statistics.
    """

    iterations: int

    successful: int

    failed: int

    average_ms: float

    minimum_ms: float

    maximum_ms: float

    total_ms: float

    results: list[BenchmarkIteration]


class BenchmarkRunner:
    """
    Executes benchmark runs.
    """

    def __init__(
        self,
        iterations: int = 10,
    ):
        if iterations <= 0:
            raise ValueError(
                "iterations must be positive."
            )

        self.iterations = iterations

    def run(
        self,
        pipeline: Callable[[], Any] | None = None,
    ) -> BenchmarkResult:
        """
        Execute benchmark.

        If no pipeline is provided,
        a simulated workload is used.
        """

        results: list[
            BenchmarkIteration
        ] = []

        successful = 0
        failed = 0

        for index in range(
            self.iterations
        ):

            start = perf_counter()

            success = True

            try:

                if pipeline is not None:
                    pipeline()

            except Exception:

                success = False

            elapsed = (
                perf_counter() - start
            ) * 1000

            if success:
                successful += 1
            else:
                failed += 1

            results.append(
                BenchmarkIteration(
                    iteration=index + 1,
                    elapsed_ms=elapsed,
                    success=success,
                )
            )

        timings = [
            r.elapsed_ms
            for r in results
        ]

        return BenchmarkResult(
            iterations=self.iterations,
            successful=successful,
            failed=failed,
            average_ms=mean(timings),
            minimum_ms=min(timings),
            maximum_ms=max(timings),
            total_ms=sum(timings),
            results=results,
        )

    @staticmethod
    def to_dict(
        result: BenchmarkResult,
    ) -> dict[str, Any]:
        """
        Convert benchmark results
        into a serializable dictionary.
        """

        return {
            "iterations": result.iterations,
            "successful": result.successful,
            "failed": result.failed,
            "average_ms": result.average_ms,
            "minimum_ms": result.minimum_ms,
            "maximum_ms": result.maximum_ms,
            "total_ms": result.total_ms,
            "results": [
                asdict(r)
                for r in result.results
            ],
        }