"""
Unit tests for the BLT Preflight CLI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from advisory_engine.cli.main import build_parser
from advisory_engine.cli.commands import (
    advise_command,
    config_command,
    retrieve_command,
    validate_command,
    version_command,
)


# ---------------------------------------------------------------------
# Parser Tests
# ---------------------------------------------------------------------


def test_parser_builds():
    """
    Verify the CLI parser is created successfully.
    """

    parser = build_parser()

    assert parser is not None


def test_advise_command_parsing():
    """
    Verify advise arguments are parsed correctly.
    """

    parser = build_parser()

    args = parser.parse_args(
        [
            "advise",
            "--labels",
            "security,authentication",
            "--files",
            "src/auth.py",
            "--repo",
            "owasp/blt",
            "--output",
            "advisory.md",
        ]
    )

    assert args.command == "advise"

    assert args.repo == "owasp/blt"

    assert args.output == "advisory.md"


def test_retrieve_command_parsing():
    parser = build_parser()

    args = parser.parse_args(
        [
            "retrieve",
            "authentication",
        ]
    )

    assert args.command == "retrieve"

    assert args.query == "authentication"


def test_version_command_parsing():
    parser = build_parser()

    args = parser.parse_args(
        [
            "version",
        ]
    )

    assert args.command == "version"


# ---------------------------------------------------------------------
# Command Tests
# ---------------------------------------------------------------------


class DummyArgs:
    """
    Simple argparse replacement.
    """

    labels = "security"

    files = "src/auth.py"

    repo = "owasp/blt"

    output = "test_advisory.md"

    json = "test_advisory.json"


def test_advise_command(tmp_path):
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


def test_retrieve_command():
    class Args:
        query = "authentication"

        top_k = 5

    assert retrieve_command(Args()) == 0


def test_version_command(capsys):
    class Args:
        pass

    assert version_command(Args()) == 0

    captured = capsys.readouterr()

    assert "BLT Preflight" in captured.out


def test_config_command():
    """
    Config command should execute successfully.
    """

    class Args:
        pass

    try:

        config_command(Args())

    except FileNotFoundError:

        pytest.skip(
            "Configuration file not present."
        )


def test_validate_command():
    """
    Validation command should execute successfully.
    """

    class Args:
        pass

    try:

        validate_command(Args())

    except FileNotFoundError:

        pytest.skip(
            "Configuration file not present."
        )


# ---------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------


def test_invalid_cli_command():
    """
    Unknown command should exit.
    """

    parser = build_parser()

    with pytest.raises(SystemExit):

        parser.parse_args(
            [
                "does-not-exist",
            ]
        )