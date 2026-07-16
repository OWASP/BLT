"""
timeout.py

Timeout utilities for the BLT Preflight pipeline.

Responsibilities
----------------
- Execute operations with a timeout
- Raise consistent timeout exceptions
- Support synchronous callables
- Provide reusable timeout handling across the pipeline

This module is provider-independent and can be used by
retrievers, LLM providers, cache refreshes, and future
pipeline stages.
"""

from __future__ import annotations

import concurrent.futures
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from advisory_engine.config.defaults import LLM_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PipelineTimeoutError(TimeoutError):
    """Raised when a pipeline operation exceeds the configured timeout."""


class TimeoutExecutor:
    """
    Executes callables with timeout protection.

    Example
    -------
    >>> executor = TimeoutExecutor()
    >>> result = executor.run(provider.generate, prompt)
    """

    def __init__(
        self,
        timeout: int = LLM_TIMEOUT_SECONDS,
    ) -> None:
        self.timeout = timeout

    def run(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Execute a callable with timeout protection.

        Parameters
        ----------
        func
            Function to execute.

        Returns
        -------
        Any
            Result returned by the callable.

        Raises
        ------
        PipelineTimeoutError
            If execution exceeds the timeout.
        """

        logger.debug(
            "Executing %s with timeout=%ss",
            getattr(func, "__name__", repr(func)),
            self.timeout,
        )

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=1
        ) as executor:

            future = executor.submit(func, *args, **kwargs)

            try:
                result = future.result(timeout=self.timeout)

                logger.debug("Execution completed successfully.")

                return result

            except concurrent.futures.TimeoutError as exc:

                future.cancel()

                logger.warning(
                    "Pipeline stage exceeded timeout (%ss).",
                    self.timeout,
                )

                raise PipelineTimeoutError(
                    f"Execution exceeded {self.timeout} seconds."
                ) from exc

    def set_timeout(
        self,
        timeout: int,
    ) -> None:
        """
        Update timeout value.
        """

        if timeout <= 0:
            raise ValueError(
                "Timeout must be greater than zero."
            )

        logger.info(
            "Updating timeout from %ss to %ss",
            self.timeout,
            timeout,
        )

        self.timeout = timeout