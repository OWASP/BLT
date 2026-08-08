"""
commands.py

CLI command implementations for BLT Preflight.

Responsibilities
----------------
- Execute CLI commands
- Coordinate pipeline components
- Handle file output
- Return process exit codes

This module should not parse command-line arguments.
"""

from __future__ import annotations

import json
from pathlib import Path
from pprint import pprint

from advisory_engine.config.loader import ConfigurationLoader
from advisory_engine.config.validator import ConfigurationValidator
from advisory_engine.gitlab.formatter import GitLabAdvisoryFormatter
from advisory_engine.benchmark.runner import BenchmarkRunner


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


from advisory_engine.cli.utils import write_text, write_json

def _write(path: str | None, content: str) -> None:
    if path:
        write_text(path, content)


def _write_json(path: str | None, data: dict) -> None:
    if path:
        write_json(path, data)

# ---------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------


def advise_command(args) -> int:
    """
    Generate a security advisory.

    NOTE:
    This currently creates a deterministic advisory.
    The real advisory engine can replace this later.
    """

    labels = [
        label.strip()
        for label in args.labels.split(",")
        if label.strip()
    ]

    files = [
        file.strip()
        for file in args.files.split(",")
        if file.strip()
    ]

    advisory = {
        "severity": "Medium",
        "category": "General Security",
        "title": "BLT Preflight Advisory",
        "explanation": (
            "A deterministic advisory was generated "
            "by the CLI."
        ),
        "recommendation": (
            "Review modified files for common "
            "OWASP security issues."
        ),
        "references": [
            "OWASP Top 10",
            "OWASP ASVS",
        ],
        "metadata": {
            "repository": args.repo,
            "labels": labels,
            "changed_files": len(files),
        },
    }

    markdown = GitLabAdvisoryFormatter.format(
        advisory
    )

    _write(args.output, markdown)

    if args.json:
        _write_json(
            args.json,
            advisory,
        )

    print(
        f"Advisory written to {args.output}"
    )

    return 0



def retrieve_command(args) -> int:
    """
    Retrieve relevant security guidance.

    Placeholder until Retriever is connected.
    """

    print(
        f"Searching knowledge base for: "
        f"{args.query}"
    )

    print(
        f"Top-K Results: {args.top_k}"
    )

    return 0



def benchmark_command(args) -> int:
    """
    Run pipeline benchmark.
    """

    runner = BenchmarkRunner()

    report = runner.run()

    pprint(report)

    return 0



def config_command(args) -> int:
    """
    Display active configuration.
    """

    loader = ConfigurationLoader()

    config = loader.load()

    pprint(config)

    return 0



def validate_command(args) -> int:
    """
    Validate .preflight.yaml.
    """

    loader = ConfigurationLoader()

    config = loader.load()

    ConfigurationValidator.validate(
        config
    )

    print(
        "Configuration is valid."
    )

    return 0



def version_command(args) -> int:
    """
    Display version.
    """

    print(
        "BLT Preflight 1.0.0"
    )

    return 0