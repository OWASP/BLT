"""
BLT Preflight Command Line Interface.

This package provides the command-line interface for interacting
with the BLT Preflight advisory engine.

Modules
-------
main
    CLI entry point.

commands
    Command implementations.

utils
    Shared helper functions.
"""

from .main import main

__all__ = [
    "main",
]