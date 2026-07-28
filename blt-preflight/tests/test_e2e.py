"""
End-to-end integration tests for BLT Preflight.

These tests verify that the major Week 6 components
work together correctly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from advisory_engine.benchmark.runner import BenchmarkRunner
from advisory_engine.benchmark.metrics import (
    BenchmarkMetricsCalculator,
)
from advisory_engine.benchmark.report import (
    BenchmarkReportGenerator,
)
from advisory_engine.cli.commands import advise_command
from advisory_engine.logging.logger import (
    PipelineLogger,
)


# ---------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------


class DummyArgs:
    """
    Simulates argparse.Namespace.
    """

    labels = "security,authentication"

    files = "src/auth.py,src/login.py"

    repo = "owasp/blt"

    output = ""

    json = ""


def benchmark_pipeline():
    """
    Simple workload for benchmarking.
    """

    total = 0

    for value in range(2000):
        total += value

    return total


# ---------------------------------------------------------------------
# Advisory Pipeline
# ---------------------------------------------------------------------


def test_generate_complete_advisory(tmp_path):
    """
    Verify advisory generation.
    """

    args = DummyArgs()

    args.output = str(
        tmp_path / "advisory.md"
    )

    args.json = str(
        tmp_path / "advisory.json"
    )

    exit_code = advise_command(args)

    assert exit_code == 0

    assert Path(args.output).exists()

    assert Path(args.json).exists()

    markdown = Path(args.output).read_text()

    assert "BLT Preflight Advisory" in markdown


# ---------------------------------------------------------------------
# Benchmark Pipeline
# ---------------------------------------------------------------------


def test_complete_benchmark_pipeline(tmp_path):
    """
    Verify benchmark execution and report generation.
    """

    runner = BenchmarkRunner(
        iterations=5,
    )

    result = runner.run(
        benchmark_pipeline,
    )

    metrics = (
        BenchmarkMetricsCalculator.calculate(
            result
        )
    )

    markdown = tmp_path / "benchmark.md"

    report = tmp_path / "benchmark.json"

    BenchmarkReportGenerator.save_markdown(
        str(markdown),
        result,
        metrics,
    )

    BenchmarkReportGenerator.save_json(
        str(report),
        result,
        metrics,
    )

    assert markdown.exists()

    assert report.exists()


# ---------------------------------------------------------------------
# JSON Output
# ---------------------------------------------------------------------


def test_generated_json_report(tmp_path):
    """
    Verify JSON report structure.
    """

    runner = BenchmarkRunner(
        iterations=3,
    )

    result = runner.run()

    metrics = (
        BenchmarkMetricsCalculator.calculate(
            result
        )
    )

    report = tmp_path / "report.json"

    BenchmarkReportGenerator.save_json(
        str(report),
        result,
        metrics,
    )

    data = json.loads(
        report.read_text()
    )

    assert "summary" in data

    assert "metrics" in data

    assert "results" in data


# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------


def test_pipeline_logger():
    """
    Verify logging integration.
    """

    logger = PipelineLogger()

    logger.info("Pipeline started.")

    logger.info("Pipeline finished.")


# ---------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------


def test_benchmark_metrics():
    """
    Verify benchmark metrics are valid.
    """

    runner = BenchmarkRunner(
        iterations=10,
    )

    result = runner.run()

    metrics = (
        BenchmarkMetricsCalculator.calculate(
            result
        )
    )

    assert metrics.average_ms >= 0

    assert metrics.maximum_ms >= metrics.minimum_ms

    assert metrics.success_rate == 100.0


# ---------------------------------------------------------------------
# Multiple Runs
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "iterations",
    [
        1,
        3,
        5,
        10,
    ],
)
def test_multiple_iteration_counts(
    iterations,
):
    """
    Verify runner supports different iteration counts.
    """

    runner = BenchmarkRunner(
        iterations=iterations,
    )

    result = runner.run()

    assert result.iterations == iterations


# ---------------------------------------------------------------------
# Report Consistency
# ---------------------------------------------------------------------


def test_markdown_json_consistency(tmp_path):
    """
    Verify both reports are generated from the same benchmark.
    """

    runner = BenchmarkRunner(
        iterations=4,
    )

    result = runner.run()

    metrics = (
        BenchmarkMetricsCalculator.calculate(
            result
        )
    )

    md = tmp_path / "benchmark.md"

    js = tmp_path / "benchmark.json"

    BenchmarkReportGenerator.save_markdown(
        str(md),
        result,
        metrics,
    )

    BenchmarkReportGenerator.save_json(
        str(js),
        result,
        metrics,
    )

    markdown = md.read_text()

    data = json.loads(
        js.read_text()
    )

    assert (
        str(data["summary"]["iterations"])
        in markdown
    )


# ---------------------------------------------------------------------
# Failure Handling
# ---------------------------------------------------------------------


def test_failed_pipeline_benchmark():
    """
    Failed benchmark executions should be recorded.
    """

    def failing_pipeline():
        raise RuntimeError(
            "Pipeline failed."
        )

    runner = BenchmarkRunner(
        iterations=3,
    )

    result = runner.run(
        failing_pipeline,
    )

    assert result.failed == 3

    assert result.successful == 0