#!/usr/bin/env python3
"""
benchmark.py

Run the BLT Preflight benchmark suite.

Usage
-----
python scripts/benchmark.py

Outputs
-------
benchmark.md
benchmark.json
"""

from __future__ import annotations

from pathlib import Path

from advisory_engine.benchmark.metrics import (
    BenchmarkMetricsCalculator,
)
from advisory_engine.benchmark.report import (
    BenchmarkReportGenerator,
)
from advisory_engine.benchmark.runner import (
    BenchmarkRunner,
)


OUTPUT_DIRECTORY = Path("benchmark_output")


def dummy_pipeline() -> None:
    """
    Placeholder workload.

    Replace this with the actual advisory pipeline
    once integrated.
    """
    total = 0

    for value in range(5000):
        total += value

    return None


def main() -> int:
    """
    Execute benchmark suite.
    """

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 60)
    print("BLT Preflight Benchmark")
    print("=" * 60)

    runner = BenchmarkRunner(
        iterations=20,
    )

    result = runner.run(
        pipeline=dummy_pipeline,
    )

    metrics = (
        BenchmarkMetricsCalculator.calculate(
            result
        )
    )

    markdown_file = (
        OUTPUT_DIRECTORY / "benchmark.md"
    )

    json_file = (
        OUTPUT_DIRECTORY / "benchmark.json"
    )

    BenchmarkReportGenerator.save_markdown(
        str(markdown_file),
        result,
        metrics,
    )

    BenchmarkReportGenerator.save_json(
        str(json_file),
        result,
        metrics,
    )

    print()

    print("Benchmark completed successfully.\n")

    print(f"Iterations : {result.iterations}")
    print(f"Success    : {result.successful}")
    print(f"Failures   : {result.failed}")

    print()

    print(
        f"Average    : {metrics.average_ms:.2f} ms"
    )

    print(
        f"Median     : {metrics.median_ms:.2f} ms"
    )

    print(
        f"P95        : {metrics.p95_ms:.2f} ms"
    )

    print(
        f"P99        : {metrics.p99_ms:.2f} ms"
    )

    print(
        f"Throughput : "
        f"{metrics.throughput_per_second:.2f} "
        f"runs/sec"
    )

    print()

    print(f"Markdown report : {markdown_file}")

    print(f"JSON report     : {json_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())