"""
utils.py

Shared utilities for the BLT Preflight CLI.

Responsibilities
----------------
- Configuration loading
- File writing
- JSON serialization
- Console output
- Exit handling
- Common validation helpers

This module contains no command implementations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from advisory_engine.config.loader import ConfigurationLoader
from advisory_engine.config.validator import (
    ConfigurationValidator,
)


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------


def load_configuration() -> dict[str, Any]:
    """
    Load and validate the active configuration.
    """

    loader = ConfigurationLoader()

    config = loader.load()

    ConfigurationValidator.validate(config)

    return config


# ----------------------------------------------------------------------
# File Utilities
# ----------------------------------------------------------------------


def write_text(
    filename: str | Path,
    text: str,
) -> None:
    """
    Write UTF-8 text.
    """

    path = Path(filename)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        text,
        encoding="utf-8",
    )


def write_json(
    filename: str | Path,
    data: dict[str, Any],
) -> None:
    """
    Write formatted JSON.
    """

    path = Path(filename)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            data,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def read_json(
    filename: str | Path,
) -> dict[str, Any]:
    """
    Read JSON file.
    """

    path = Path(filename)

    return json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )


# ----------------------------------------------------------------------
# Console Helpers
# ----------------------------------------------------------------------


def success(
    message: str,
) -> None:
    """
    Print success message.
    """

    print(f"✓ {message}")


def warning(
    message: str,
) -> None:
    """
    Print warning message.
    """

    print(f"⚠ {message}")


def error(
    message: str,
) -> None:
    """
    Print error message.
    """

    print(f"✗ {message}")


def info(
    message: str,
) -> None:
    """
    Print informational message.
    """

    print(f"ℹ {message}")


# ----------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------


def parse_csv(
    value: str,
) -> list[str]:
    """
    Parse comma-separated CLI input.
    """

    if not value.strip():
        return []

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


# ----------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------


def require_file(
    filename: str | Path,
) -> Path:
    """
    Ensure a file exists.
    """

    path = Path(filename)

    if not path.exists():
        raise FileNotFoundError(
            f"{path} does not exist."
        )

    return path


def require_positive(
    value: int,
    name: str,
) -> int:
    """
    Validate positive integer.
    """

    if value <= 0:
        raise ValueError(
            f"{name} must be greater than zero."
        )

    return value


# ----------------------------------------------------------------------
# Formatting
# ----------------------------------------------------------------------


def banner() -> str:
    """
    CLI banner.
    """

    return (
        "=========================================\n"
        " BLT Preflight Security Advisory CLI\n"
        "========================================="
    )


def print_banner() -> None:
    """
    Display CLI banner.
    """

    print(banner())