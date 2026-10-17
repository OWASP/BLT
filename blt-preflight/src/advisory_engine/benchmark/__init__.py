"""
Benchmark package for BLT Preflight.

This package contains components for measuring the performance
of the advisory pipeline, including retrieval, generation,
validation, formatting, and overall execution metrics.

Modules
-------
runner
    Executes benchmark runs.

metrics
    Performance metric calculations.

report
    Benchmark report generation.
"""

from .runner import BenchmarkRunner

__all__ = [
    "BenchmarkRunner",
]