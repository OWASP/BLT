"""
report.py

Benchmark report generation for BLT Preflight.

Responsibilities
----------------
- Generate Markdown benchmark reports
- Generate JSON benchmark reports
- Export benchmark summaries

This module is presentation-only.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from typing import Any

from advisory_engine.benchmark.metrics import (
    BenchmarkMetrics,
)
from advisory_engine.benchmark.runner import (
    BenchmarkResult,
)


class BenchmarkReportGenerator:
    """
    Generates benchmark reports.
    """

    @staticmethod
    def markdown(
        result: BenchmarkResult,
        metrics: BenchmarkMetrics,
    ) -> str:
        """
        Generate a Markdown report.
        """

        lines = [
            "# BLT Preflight Benchmark Report",
            "",
            f"Generated: {datetime.utcnow().isoformat()}Z",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|------:|",
            f"| Iterations | {result.iterations} |",
            f"| Successful | {result.successful} |",
            f"| Failed | {result.failed} |",
            f"| Success Rate | {metrics.success_rate:.2f}% |",
            f"| Failure Rate | {metrics.failure_rate:.2f}% |",
            "",
            "## Timing",
            "",
            "| Metric | Time (ms) |",
            "|--------|----------:|",
            f"| Average | {metrics.average_ms:.2f} |",
            f"| Median | {metrics.median_ms:.2f} |",
            f"| Minimum | {metrics.minimum_ms:.2f} |",
            f"| Maximum | {metrics.maximum_ms:.2f} |",
            f"| Std Dev | {metrics.std_deviation_ms:.2f} |",
            f"| P95 | {metrics.p95_ms:.2f} |",
            f"| P99 | {metrics.p99_ms:.2f} |",
            "",
            "## Throughput",
            "",
            f"- **{metrics.throughput_per_second:.2f} iterations/sec**",
            "",
            "## Individual Runs",
            "",
            "| # | Time (ms) | Status |",
            "|--:|----------:|--------|",
        ]

        for iteration in result.results:
            status = "PASS" if iteration.success else "FAIL"

            lines.append(
                f"| {iteration.iteration} | "
                f"{iteration.elapsed_ms:.2f} | "
                f"{status} |"
            )

        return "\n".join(lines)

    @staticmethod
    def json(
        result: BenchmarkResult,
        metrics: BenchmarkMetrics,
    ) -> dict[str, Any]:
        """
        Generate JSON benchmark report.
        """

        return {
            "generated_at": (
                datetime.utcnow().isoformat() + "Z"
            ),
            "summary": {
                "iterations": result.iterations,
                "successful": result.successful,
                "failed": result.failed,
            },
            "metrics": asdict(metrics),
            "results": [
                asdict(item)
                for item in result.results
            ],
        }

    @staticmethod
    def save_markdown(
        filename: str,
        result: BenchmarkResult,
        metrics: BenchmarkMetrics,
    ) -> None:
        """
        Save Markdown report.
        """

        with open(
            filename,
            "w",
            encoding="utf-8",
        ) as fp:
            fp.write(
                BenchmarkReportGenerator.markdown(
                    result,
                    metrics,
                )
            )

    @staticmethod
    def save_json(
        filename: str,
        result: BenchmarkResult,
        metrics: BenchmarkMetrics,
    ) -> None:
        """
        Save JSON report.
        """

        with open(
            filename,
            "w",
            encoding="utf-8",
        ) as fp:
            json.dump(
                BenchmarkReportGenerator.json(
                    result,
                    metrics,
                ),
                fp,
                indent=2,
            )