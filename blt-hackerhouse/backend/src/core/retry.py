"""Exponential backoff with jitter (VF18).

Used by the GitLab Events API gap detector and the BLT polling adapter
for any outbound HTTP call that may experience transient failures.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

import httpx

from core.logging import get_logger


logger = get_logger(__name__)


T = TypeVar("T")


class RetryableHTTPError(Exception):
    """Raised when an HTTP call has exhausted all retry attempts."""

    def __init__(self, message: str, *, last_status: int | None = None,
                 last_exception: Exception | None = None) -> None:
        super().__init__(message)
        self.last_status = last_status
        self.last_exception = last_exception


@dataclass(frozen=True)
class RetryConfig:
    """Retry policy for outbound HTTP calls.

    Delays (seconds): 1 -> 2 -> 4 -> 8 -> max 32 (then capped).
    Jitter: ±500ms.
    """

    max_attempts: int = 5
    base_delay: float = 1.0
    max_delay: float = 32.0
    jitter: float = 0.5


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    config: RetryConfig | None = None,
    description: str = "operation",
    on_failure: Callable[[Exception], Awaitable[None]] | None = None,
) -> T:
    """Run ``operation`` with exponential backoff.

    Retries on ``httpx.HTTPError`` (incl. timeouts, connection errors,
    5xx, 429). 4xx (other than 429) are treated as terminal — the
    caller passed bad data and retrying will not help.
    """
    cfg = config or RetryConfig()
    last_exc: Exception | None = None

    for attempt in range(1, cfg.max_attempts + 1):
        try:
            return await operation()
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            status = exc.response.status_code if exc.response is not None else None
            if status is not None and 400 <= status < 500 and status != 429:
                logger.warning(
                    "retry_async terminal",
                    extra={"op": description, "status": status, "attempt": attempt},
                )
                raise
            logger.warning(
                "retry_async http_error",
                extra={"op": description, "status": status, "attempt": attempt},
            )
        except httpx.HTTPError as exc:
            last_exc = exc
            logger.warning(
                "retry_async transport_error",
                extra={"op": description, "error": repr(exc), "attempt": attempt},
            )

        if on_failure is not None and last_exc is not None:
            try:
                await on_failure(last_exc)
            except Exception as hook_exc:  # noqa: BLE001
                logger.error(
                    "retry_async on_failure hook raised",
                    extra={"op": description, "error": repr(hook_exc)},
                )

        if attempt >= cfg.max_attempts:
            break

        delay = min(cfg.base_delay * (2 ** (attempt - 1)), cfg.max_delay)
        delay += random.uniform(-cfg.jitter, cfg.jitter)
        delay = max(0.0, delay)
        logger.info(
            "retry_async sleeping",
            extra={"op": description, "delay_s": round(delay, 3), "attempt": attempt},
        )
        await asyncio.sleep(delay)

    raise RetryableHTTPError(
        f"{description} failed after {cfg.max_attempts} attempts",
        last_status=getattr(last_exc, "status_code", None)
        if isinstance(last_exc, httpx.HTTPStatusError)
        else None,
        last_exception=last_exc,
    )