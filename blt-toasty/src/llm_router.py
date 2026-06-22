"""
Policy-driven LLM provider router for the Toasty triage pipeline.

This module tracks the health of LLM providers using Cloudflare Durable
Objects and implements an automatic failover strategy:

    Primary:   Cloudflare Workers AI  (@cf/meta/llama-3.1-8b-instruct)
    Fallback:  OpenAI                 (gpt-4o-mini)

The router switches to the fallback provider after 3 consecutive failures
on the primary and supports automatic recovery once the primary is healthy
again.

Design notes
------------
* Provider state is persisted in a Durable Object so that it survives
  across individual Worker invocations.
* ``get_active_provider`` is the single entry point that downstream code
  should call; it never raises.
* Health checks run a minimal one-token prompt and are designed to be
  called from a Cron Trigger for proactive recovery.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("toasty.llm_router")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRIMARY_PROVIDER = "cf_ai"
FALLBACK_PROVIDER = "openai"
FAILURE_THRESHOLD = 3
CF_AI_MODEL = "@cf/meta/llama-3.1-8b-instruct"

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class ProviderStatus:
    """Tracks the operational health of a single LLM provider.

    Attributes:
        provider: Identifier string (``"cf_ai"`` or ``"openai"``).
        healthy: Whether the provider is currently considered healthy.
        last_checked: ISO-8601 timestamp of the last health evaluation.
        failure_count: Number of consecutive failures observed.
    """

    provider: str
    healthy: bool = True
    last_checked: str = ""
    failure_count: int = 0

    def to_dict(self) -> dict:
        """Serialise to a plain dict suitable for Durable Object storage."""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ProviderStatus":
        """Deserialise from a plain dict read from Durable Object storage."""
        return cls(
            provider=data.get("provider", PRIMARY_PROVIDER),
            healthy=data.get("healthy", True),
            last_checked=data.get("last_checked", ""),
            failure_count=data.get("failure_count", 0),
        )


# ---------------------------------------------------------------------------
# Durable Object helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


async def _read_status(do_stub, provider: str) -> ProviderStatus:
    """Read provider status from the Durable Object storage.

    If the key does not exist yet, a default healthy status is returned.

    Args:
        do_stub: The Durable Object stub providing ``storage.get()``.
        provider: The provider identifier to look up.

    Returns:
        The current ``ProviderStatus`` for the given provider.
    """
    key = f"provider_status:{provider}"
    try:
        raw = await do_stub.storage.get(key)
        if raw is None:
            return ProviderStatus(provider=provider)
        if isinstance(raw, str):
            return ProviderStatus.from_dict(json.loads(raw))
        return ProviderStatus.from_dict(raw)
    except Exception:
        logger.warning("Failed to read DO status for %s, returning default", provider)
        return ProviderStatus(provider=provider)


async def _write_status(do_stub, status: ProviderStatus) -> None:
    """Persist provider status into the Durable Object storage.

    Args:
        do_stub: The Durable Object stub providing ``storage.put()``.
        status: The ``ProviderStatus`` to persist.
    """
    key = f"provider_status:{status.provider}"
    try:
        await do_stub.storage.put(key, json.dumps(status.to_dict()))
    except Exception:
        logger.error("Failed to write DO status for %s", status.provider)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_active_provider(do_stub) -> str:
    """Return the identifier of the LLM provider that should handle the next request.

    The router defaults to ``"cf_ai"`` (Cloudflare Workers AI).  If the
    primary provider has accumulated ``>= 3`` consecutive failures, the
    router switches to ``"openai"`` until the primary is explicitly
    recovered via ``reset_provider``.

    Args:
        do_stub: The Durable Object stub for reading provider state.

    Returns:
        ``"cf_ai"`` or ``"openai"``.
    """
    status = await _read_status(do_stub, PRIMARY_PROVIDER)
    if status.failure_count >= FAILURE_THRESHOLD:
        logger.info(
            "Primary provider %s has %d failures (>= %d), routing to fallback %s",
            PRIMARY_PROVIDER,
            status.failure_count,
            FAILURE_THRESHOLD,
            FALLBACK_PROVIDER,
        )
        return FALLBACK_PROVIDER
    return PRIMARY_PROVIDER


async def mark_provider_failed(do_stub, provider: str) -> None:
    """Record a failure for the given provider.

    Increments the ``failure_count`` by 1 and marks the provider as
    unhealthy once the count reaches ``FAILURE_THRESHOLD``.  The
    ``last_fallback_reason`` is stored in the Durable Object for
    observability.

    Args:
        do_stub: The Durable Object stub for reading/writing state.
        provider: The provider that just failed (``"cf_ai"`` or ``"openai"``).
    """
    status = await _read_status(do_stub, provider)
    status.failure_count += 1
    status.last_checked = _now_iso()

    if status.failure_count >= FAILURE_THRESHOLD:
        status.healthy = False
        reason = (
            f"{provider} marked unhealthy after {status.failure_count} consecutive failures at {status.last_checked}"
        )
        logger.warning(reason)
        try:
            await do_stub.storage.put("last_fallback_reason", reason)
        except Exception:  # nosec B110 — logging failure must not crash the router
            pass

    await _write_status(do_stub, status)


async def reset_provider(do_stub, provider: str) -> None:
    """Reset the failure count for the given provider, marking it healthy.

    Typically called after a successful health check confirms the
    provider has recovered.

    Args:
        do_stub: The Durable Object stub for reading/writing state.
        provider: The provider to reset (``"cf_ai"`` or ``"openai"``).
    """
    status = await _read_status(do_stub, provider)
    status.failure_count = 0
    status.healthy = True
    status.last_checked = _now_iso()
    await _write_status(do_stub, status)
    logger.info("Provider %s reset to healthy", provider)


async def check_cf_ai_health(env) -> bool:
    """Run a minimal probe against Cloudflare Workers AI.

    Executes a trivial one-token prompt to determine whether the
    ``env.AI.run`` binding is operational.  This function **never**
    raises an exception — it returns ``False`` on any error.

    Args:
        env: The Cloudflare Worker environment object providing ``AI``.

    Returns:
        ``True`` if the probe succeeded, ``False`` otherwise.
    """
    try:
        result = await env.AI.run(CF_AI_MODEL, {"prompt": "1", "max_tokens": 1})
        return result is not None
    except Exception as exc:
        logger.warning("CF AI health check failed: %s", exc)
        return False
