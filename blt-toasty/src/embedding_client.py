"""Async embedding client for Cloudflare Workers (Pyodide runtime).

Calls the FastEmbed sidecar to generate 384-dimensional embeddings.

SECURITY
--------
This module ONLY accepts ``redacted_text``.  Raw text must **never**
be passed to any function in this module.  The caller (``vectorize_client``)
enforces this invariant via ``assert_summarized_before_embedding``.

Runtime notes
-------------
* Inside Cloudflare Workers (Pyodide), HTTP is performed via
  ``from js import fetch, AbortController``.  When running under
  standard CPython (e.g. pytest), those imports are unavailable,
  so the module falls back to stubs that tests can mock.
* A hard **5-second timeout** is enforced on every sidecar call via
  ``AbortController`` to avoid blocking the Worker.
"""

from __future__ import annotations

import json
import logging

from src.errors import EmbeddingServiceError

logger = logging.getLogger("toasty.embedding_client")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EMBEDDING_DIMENSIONS = 384
EMBEDDING_TIMEOUT_SECONDS = 5
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

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
# Public API
# ---------------------------------------------------------------------------


async def get_embedding(text: str, env) -> list[float]:
    """Get a 384-dimensional embedding vector from the FastEmbed sidecar.

    Args:
        text: Redacted text to embed (**NEVER** raw text).
        env: Cloudflare Worker environment with ``FASTEMBED_URL`` var.
            Tests may also attach ``_fetch_impl`` and
            ``_abort_controller_cls`` to inject mocks.

    Returns:
        A list of 384 floats representing the sentence embedding.

    Raises:
        EmbeddingServiceError: On timeout, network error, non-200 response,
            or unexpected embedding dimensions.
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

    sidecar_url = getattr(env, "FASTEMBED_URL", None)
    if not sidecar_url:
        raise EmbeddingServiceError("FASTEMBED_URL not configured in environment", status_code=503)

    controller = _abort_controller_cls.new()
    # Schedule the abort after EMBEDDING_TIMEOUT_SECONDS.
    # In Pyodide: ``setTimeout`` is on the global scope.
    timer_id = None
    try:
        from js import setTimeout, clearTimeout  # type: ignore[import-not-found]

        timer_id = setTimeout(lambda: controller.abort(), EMBEDDING_TIMEOUT_SECONDS * 1000)
    except ImportError:
        # Running under CPython tests — mock will handle timeout behaviour.
        pass

    body = json.dumps({"texts": [text]})

    try:
        response = await _fetch(
            f"{sidecar_url}/embed",
            {
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": body,
                "signal": controller.signal,
            },
        )
    except Exception as exc:
        error_msg = str(exc)
        if "abort" in error_msg.lower():
            raise EmbeddingServiceError(
                f"FastEmbed sidecar timed out after {EMBEDDING_TIMEOUT_SECONDS}s",
                status_code=408,
            ) from exc
        raise EmbeddingServiceError(
            f"FastEmbed sidecar unreachable: {exc}",
            status_code=503,
        ) from exc
    finally:
        if timer_id is not None:
            try:
                clearTimeout(timer_id)
            except Exception:
                pass  # nosec B110

    if not response.ok:
        error_body = await response.text()
        raise EmbeddingServiceError(
            f"FastEmbed sidecar HTTP {response.status}: {error_body}",
            status_code=response.status,
        )

    try:
        data = await response.json()
    except Exception:
        raise EmbeddingServiceError(
            "FastEmbed sidecar returned non-JSON response",
            status_code=500,
        )

    if not isinstance(data, dict) or not isinstance(data.get("embeddings"), list) or not data["embeddings"]:
        raise EmbeddingServiceError(
            "FastEmbed sidecar returned invalid or empty embeddings list",
            status_code=500,
        )

    embedding = data["embeddings"][0]

    if not isinstance(embedding, list):
        raise EmbeddingServiceError(
            f"FastEmbed sidecar: first embedding is not a list (got {type(embedding).__name__})",
            status_code=500,
        )

    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise EmbeddingServiceError(
            f"Expected {EMBEDDING_DIMENSIONS} dimensions, got {len(embedding)}",
            status_code=500,
        )

    return embedding
