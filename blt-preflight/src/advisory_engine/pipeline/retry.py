"""
retry.py

Retry utilities for the BLT Preflight pipeline.

Responsibilities
----------------
- Retry transient failures
- Support configurable retry count
- Support configurable retry delay
- Retry only selected exception types

This module is generic and can be used by:
- LLM providers
- Retrievers
- GitLab API
- Future integrations
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

from advisory_engine.config.defaults import MAX_RETRIES

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryExceededError(Exception):
    """Raised when all retry attempts have failed."""


class RetryExecutor:
    """
    Execute operations with automatic retry support.
    """

    def __init__(
        self,
        retries: int = MAX_RETRIES,
        delay: float = 1.0,
        retry_exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> None:
        self.retries = retries
        self.delay = delay
        self.retry_exceptions = retry_exceptions

    def run(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Execute a callable with retry support.

        Parameters
        ----------
        func
            Function to execute.

        Returns
        -------
        T
            Function result.

        Raises
        ------
        RetryExceededError
            If every retry attempt fails.
        """

        last_exception: Exception | None = None

        for attempt in range(1, self.retries + 2):

            try:
                logger.debug(
                    "Attempt %d/%d: %s",
                    attempt,
                    self.retries + 1,
                    getattr(func, "__name__", repr(func)),
                )

                return func(*args, **kwargs)

            except self.retry_exceptions as exc:

                last_exception = exc

                if attempt > self.retries:
                    break

                logger.warning(
                    "Attempt %d failed: %s. Retrying in %.1fs...",
                    attempt,
                    exc,
                    self.delay,
                )

                time.sleep(self.delay)

        logger.error(
            "Operation failed after %d attempts.",
            self.retries + 1,
        )

        raise RetryExceededError(
            f"Operation failed after {self.retries + 1} attempts."
        ) from last_exception

    def set_retries(
        self,
        retries: int,
    ) -> None:
        """
        Update retry count.
        """

        if retries < 0:
            raise ValueError(
                "Retry count cannot be negative."
            )

        self.retries = retries

    def set_delay(
        self,
        delay: float,
    ) -> None:
        """
        Update retry delay.
        """

        if delay < 0:
            raise ValueError(
                "Delay cannot be negative."
            )

        self.delay = delay