"""
Unit tests for the benchmark subsystem.
"""

from __future__ import annotations

import json

import pytest

from advisory_engine.benchmark.runner import (
    BenchmarkRunner,
)

from advisory_engine.benchmark.metrics import (
    BenchmarkMetricsCalculator,
)

from advisory_engine.benchmark.report import (
    BenchmarkReportGenerator,
)


# ---------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------


def dummy_pipeline():
    """
    Simple workload for benchmarking.
    """

    total = 0

    for i in range(1000):
        total += i

    return total


# ---------------------------------------------------------------------
# Benchmark Runner
# ---------------------------------------------------------------------


def test_runner_executes_iterations():
    """
    Verify benchmark runner completes all iterations.
    """

    runner = BenchmarkRunner(iterations=5)

    result = runner.run(dummy_pipeline)

    assert result.iterations == 5

    assert result.successful == 5

    assert result.failed == 0

    assert len(result.results) == 5


def test_runner_invalid_iterations():
    """
    Runner should reject invalid iteration counts.
    """

    with pytest.raises(ValueError):
        BenchmarkRunner(iterations=0)


def test_runner_serialization():
    """
    Verify runner dictionary conversion.
    """

    runner = BenchmarkRunner(iterations=3)

    result = runner.run(dummy_pipeline)

    data = runner.to_dict(result)

    assert data["iterations"] == 3

    assert "results" in data


# ---------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------


def test_metrics_calculation():
    """
    Verify metrics are calculated.
    """

    runner = BenchmarkRunner(iterations=5)

    result = runner.run(dummy_pipeline)

    metrics = BenchmarkMetricsCalculator.calculate(
        result
    )

    assert metrics.success_rate == 100.0

    assert metrics.failure_rate == 0.0

    assert metrics.average_ms >= 0

    assert metrics.p95_ms >= metrics.minimum_ms

    assert metrics.maximum_ms >= metrics.minimum_ms


def test_metrics_dictionary():
    """
    Verify metrics serialization.
    """

    runner = BenchmarkRunner(iterations=5)

    result = runner.run(dummy_pipeline)

    metrics = BenchmarkMetricsCalculator.calculate(
        result
    )

    data = BenchmarkMetricsCalculator.to_dict(
        metrics
    )

    assert "average_ms" in data

    assert "throughput_per_second" in data


# ---------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------


def test_markdown_report():
    """
    Verify Markdown report generation.
    """

    runner = BenchmarkRunner(iterations=5)

    result = runner.run(dummy_pipeline)

    metrics = BenchmarkMetricsCalculator.calculate(
        result
    )

    report = BenchmarkReportGenerator.markdown(
        result,
        metrics,
    )

    assert "# BLT Preflight Benchmark Report" in report

    assert "Summary" in report

    assert "Timing" in report


def test_json_report():
    """
    Verify JSON report generation.
    """

    runner = BenchmarkRunner(iterations=5)

    result = runner.run(dummy_pipeline)

    metrics = BenchmarkMetricsCalculator.calculate(
        result
    )

    report = BenchmarkReportGenerator.json(
        result,
        metrics,
    )

    assert report["summary"]["iterations"] == 5

    assert "metrics" in report

    assert "results" in report


def test_save_markdown(tmp_path):
    """
    Verify Markdown report is saved.
    """

    runner = BenchmarkRunner(iterations=3)

    result = runner.run(dummy_pipeline)

    metrics = BenchmarkMetricsCalculator.calculate(
        result
    )

    output = tmp_path / "benchmark.md"

    BenchmarkReportGenerator.save_markdown(
        str(output),
        result,
        metrics,
    )

    assert output.exists()


def test_save_json(tmp_path):
    """
    Verify JSON report is saved.
    """

    runner = BenchmarkRunner(iterations=3)

    result = runner.run(dummy_pipeline)

    metrics = BenchmarkMetricsCalculator.calculate(
        result
    )

    output = tmp_path / "benchmark.json"

    BenchmarkReportGenerator.save_json(
        str(output),
        result,
        metrics,
    )

    assert output.exists()

    data = json.loads(output.read_text())

    assert "summary" in data

    assert "metrics" in data


# ---------------------------------------------------------------------
# Failure Handling
# ---------------------------------------------------------------------


def test_pipeline_failure():
    """
    Failed pipeline executions should be recorded.
    """

    def failing_pipeline():
        raise RuntimeError("failure")

    runner = BenchmarkRunner(iterations=4)

    result = runner.run(failing_pipeline)

    assert result.failed == 4

    assert result.successful == 0


def test_empty_pipeline():
    """
    Runner should support no pipeline.
    """

    runner = BenchmarkRunner(iterations=2)

    result = runner.run()

    assert result.iterations == 2