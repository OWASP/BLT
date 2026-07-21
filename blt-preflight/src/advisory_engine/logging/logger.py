"""
logger.py

Central logging configuration for BLT Preflight.

Responsibilities
----------------
- Configure application logging
- Create named loggers
- Configure console/file handlers
- Prevent duplicate handlers

Uses the standard Python logging library.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


DEFAULT_FORMAT = (
    "%(asctime)s | "
    "%(levelname)-8s | "
    "%(name)s | "
    "%(message)s"
)

DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    level: str = "INFO",
    log_file: str | None = None,
) -> None:
    """
    Configure global logging.

    This function is safe to call multiple times.
    """

    root = logging.getLogger()

    numeric_level = getattr(
        logging,
        level.upper(),
        logging.INFO,
    )

    root.setLevel(numeric_level)

    # Prevent duplicate handlers
    if root.handlers:
        root.handlers.clear()

    formatter = logging.Formatter(
        fmt=DEFAULT_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT,
    )

    # Console handler
    console_handler = logging.StreamHandler(
        sys.stdout
    )

    console_handler.setFormatter(formatter)

    root.addHandler(console_handler)

    # Optional file logging
    if log_file:

        path = Path(log_file)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_handler = logging.FileHandler(
            path,
            encoding="utf-8",
        )

        file_handler.setFormatter(formatter)

        root.addHandler(file_handler)


def get_logger(
    name: str,
) -> logging.Logger:
    """
    Return a configured logger.
    """

    return logging.getLogger(name)


class PipelineLogger:
    """
    Convenience wrapper around logging.Logger.

    Used by the advisory pipeline.
    """

    def __init__(
        self,
        name: str = "preflight",
    ):

        self.logger = get_logger(name)

    def debug(
        self,
        message: str,
    ) -> None:
        self.logger.debug(message)

    def info(
        self,
        message: str,
    ) -> None:
        self.logger.info(message)

    def warning(
        self,
        message: str,
    ) -> None:
        self.logger.warning(message)

    def error(
        self,
        message: str,
    ) -> None:
        self.logger.error(message)

    def exception(
        self,
        message: str,
    ) -> None:
        self.logger.exception(message)


# Configure a default logger when imported.
configure_logging()