"""
main.py

Command-line interface entry point for BLT Preflight.

Responsibilities
----------------
- Parse command-line arguments
- Register available commands
- Dispatch commands to their implementations
- Return appropriate exit codes

Business logic belongs in commands.py.
"""

from __future__ import annotations

import argparse
import sys

from advisory_engine.cli.commands import (
    benchmark_command,
    config_command,
    retrieve_command,
    advise_command,
    validate_command,
    version_command,
)


def build_parser() -> argparse.ArgumentParser:
    """
    Build the root CLI parser.
    """

    parser = argparse.ArgumentParser(
        prog="preflight",
        description="BLT Preflight Security Advisory CLI",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # ------------------------------------------------------------------
    # advise
    # ------------------------------------------------------------------

    advise = subparsers.add_parser(
        "advise",
        help="Generate a security advisory.",
    )

    advise.add_argument(
        "--labels",
        default="",
        help="Comma-separated labels.",
    )

    advise.add_argument(
        "--files",
        default="",
        help="Comma-separated changed files.",
    )

    advise.add_argument(
        "--repo",
        default="",
        help="Repository path.",
    )

    advise.add_argument(
        "--output",
        required=True,
        help="Markdown output file.",
    )

    advise.add_argument(
        "--json",
        required=False,
        help="Optional JSON output file.",
    )

    advise.set_defaults(func=advise_command)

    # ------------------------------------------------------------------
    # retrieve
    # ------------------------------------------------------------------

    retrieve = subparsers.add_parser(
        "retrieve",
        help="Retrieve matching security guidance.",
    )

    retrieve.add_argument(
        "query",
        help="Search query.",
    )

    retrieve.add_argument(
        "--top-k",
        type=int,
        default=5,
    )

    retrieve.set_defaults(func=retrieve_command)

    # ------------------------------------------------------------------
    # benchmark
    # ------------------------------------------------------------------

    benchmark = subparsers.add_parser(
        "benchmark",
        help="Run pipeline benchmarks.",
    )

    benchmark.set_defaults(
        func=benchmark_command,
    )

    # ------------------------------------------------------------------
    # config
    # ------------------------------------------------------------------

    config = subparsers.add_parser(
        "config",
        help="Show loaded configuration.",
    )

    config.set_defaults(
        func=config_command,
    )

    # ------------------------------------------------------------------
    # validate
    # ------------------------------------------------------------------

    validate = subparsers.add_parser(
        "validate",
        help="Validate configuration.",
    )

    validate.set_defaults(
        func=validate_command,
    )

    # ------------------------------------------------------------------
    # version
    # ------------------------------------------------------------------

    version = subparsers.add_parser(
        "version",
        help="Show version information.",
    )

    version.set_defaults(
        func=version_command,
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point.
    """

    parser = build_parser()

    args = parser.parse_args(argv)

    try:
        return args.func(args)

    except KeyboardInterrupt:
        print("Interrupted.")
        return 130

    except Exception as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())