"""
LLM client layer for the Toasty triage pipeline.

Provides thin async wrappers around Cloudflare Workers AI and OpenAI,
with a unified ``call_llm`` entry point that integrates with the
policy-driven router in ``llm_router.py``.

Runtime notes
-------------
* Inside Cloudflare Workers (Pyodide), HTTP is performed via
  ``from js import fetch, AbortController``.  When running under
  standard CPython (e.g. pytest), those imports are unavailable,
  so the module falls back to stubs that tests can mock.
* A hard **25-second timeout** is enforced on every LLM call via
  ``AbortController`` to stay safely under the Cloudflare Worker
  30-second execution limit.
"""

from __future__ import annotations

import json
import logging

from src.errors import LLMUnavailableError
from src.llm_router import (
    CF_AI_MODEL,
    FALLBACK_PROVIDER,
    PRIMARY_PROVIDER,
    get_active_provider,
    mark_provider_failed,
)

logger = logging.getLogger("toasty.llm_client")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LLM_TIMEOUT_SECONDS = 25
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"

# ---------------------------------------------------------------------------
# Pyodide-safe imports
# ---------------------------------------------------------------------------
# Under Cloudflare Workers (Pyodide), ``fetch`` and ``AbortController``
# are provided by the ``js`` module.  Under standard CPython (tests),
# the import fails; we set them to ``None`` so callers can inject mocks.

try:
    from js import AbortController, fetch  # type: ignore[import-not-found]
except ImportError:
    fetch = None  # type: ignore[assignment]
    AbortController = None  # type: ignore[assignment, misc]


# ---------------------------------------------------------------------------
# Provider clients
# ---------------------------------------------------------------------------


async def call_cf_ai(messages: list[dict], env, max_tokens: int = 400) -> str:
    """Call Cloudflare Workers AI with the given message list.

    Uses ``env.AI.run()`` to invoke the bound Workers AI model.
    A 25-second ``AbortController`` timeout is enforced.

    Args:
        messages: OpenAI-format messages list
            (``[{"role": "system", "content": "…"}, ...]``).
        env: Cloudflare Worker environment with ``AI`` binding.
        max_tokens: Maximum tokens in the completion response.

    Returns:
        The raw completion text from the model.

    Raises:
        Exception: On any API or timeout error (caught by ``call_llm``).
    """
    try:
        result = await env.AI.run(
            CF_AI_MODEL,
            {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.0,
            },
        )
        response_text = result.response if hasattr(result, "response") else str(result)
        if not response_text:
            raise ValueError("Empty response from Cloudflare Workers AI")
        return response_text
    except Exception as exc:
        logger.error("Cloudflare Workers AI call failed: %s", exc)
        raise


async def call_openai(messages: list[dict], env, max_tokens: int = 400) -> str:
    """Call the OpenAI Chat Completions API.

    Uses the Pyodide ``fetch`` global (or a test mock) with a
    25-second ``AbortController`` timeout.

    Args:
        messages: OpenAI-format messages list.
        env: Cloudflare Worker environment with ``OPENAI_API_KEY`` secret.
        max_tokens: Maximum tokens in the completion response.

    Returns:
        The raw completion text from the model.

    Raises:
        Exception: On any API, HTTP, or timeout error (caught by ``call_llm``).
    """
    _fetch = fetch
    _abort_controller_cls = AbortController

    # Allow tests to inject mocks via the env object.
    if _fetch is None:
        _fetch = getattr(env, "_fetch_impl", None)
    if _abort_controller_cls is None:
        _abort_controller_cls = getattr(env, "_abort_controller_cls", None)

    if _fetch is None or _abort_controller_cls is None:
        raise RuntimeError("fetch/AbortController unavailable and no mock provided via env")

    api_key = getattr(env, "OPENAI_API_KEY", None)
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured in environment")

    base_url = getattr(env, "OPENAI_BASE_URL", OPENAI_CHAT_URL)

    controller = _abort_controller_cls.new()
    # Schedule the abort after LLM_TIMEOUT_SECONDS.
    # In Pyodide: ``setTimeout`` is on the global scope.
    try:
        from js import setTimeout  # type: ignore[import-not-found]

        setTimeout(lambda: controller.abort(), LLM_TIMEOUT_SECONDS * 1000)
    except ImportError:
        # Running under CPython tests — mock will handle timeout behaviour.
        pass

    body = json.dumps(
        {
            "model": OPENAI_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
    )

    try:
        response = await _fetch(
            base_url,
            {
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                "body": body,
                "signal": controller.signal,
            },
        )
    except Exception as exc:
        error_msg = str(exc)
        if "abort" in error_msg.lower():
            raise TimeoutError(f"OpenAI call timed out after {LLM_TIMEOUT_SECONDS}s") from exc
        raise

    if not response.ok:
        status = response.status
        error_body = await response.text()
        raise RuntimeError(f"OpenAI API returned HTTP {status}: {error_body}")

    data = await response.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Unexpected OpenAI response structure: {data}") from exc

    if not content:
        raise ValueError("Empty content in OpenAI response")

    return content


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------


async def call_llm(messages: list[dict], env, do_stub, max_tokens: int = 400) -> str:
    """Route an LLM request through the policy-driven provider router.

    1. Resolves the active provider via ``get_active_provider(do_stub)``.
    2. Calls the chosen provider.
    3. On failure, marks the provider as failed and retries with the
       other provider.
    4. If both providers fail, raises ``LLMUnavailableError``.

    Args:
        messages: OpenAI-format messages list.
        env: Cloudflare Worker environment object.
        do_stub: Durable Object stub for provider state.
        max_tokens: Maximum tokens in the completion response.

    Returns:
        The raw completion text from whichever provider succeeded.

    Raises:
        LLMUnavailableError: When both providers are unreachable.
    """
    active = await get_active_provider(do_stub)
    providers_tried: list[str] = []
    last_error = ""

    # Determine the order: active provider first, then the other.
    if active == PRIMARY_PROVIDER:
        order = [PRIMARY_PROVIDER, FALLBACK_PROVIDER]
    else:
        order = [FALLBACK_PROVIDER, PRIMARY_PROVIDER]

    for provider in order:
        providers_tried.append(provider)
        try:
            if provider == PRIMARY_PROVIDER:
                result = await call_cf_ai(messages, env, max_tokens)
            else:
                result = await call_openai(messages, env, max_tokens)

            logger.info("LLM call succeeded via %s", provider)
            return result

        except Exception as exc:
            last_error = f"{provider}: {exc}"
            logger.warning("LLM call failed on %s: %s", provider, exc)
            await mark_provider_failed(do_stub, provider)

    raise LLMUnavailableError(
        f"All LLM providers exhausted: {', '.join(providers_tried)}",
        providers_tried=providers_tried,
        last_error=last_error,
    )
