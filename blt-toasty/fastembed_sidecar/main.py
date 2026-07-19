"""FastEmbed sidecar service for OWASP BLT-Toasty.

Exposes a minimal REST API to generate 384-dimensional sentence embeddings
using the ``sentence-transformers/all-MiniLM-L6-v2`` model via the FastEmbed library.

This service runs as a standalone container because FastEmbed requires
NumPy C extensions that are unavailable in the Pyodide runtime used by
Cloudflare Workers.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, HTTPException
from fastembed import TextEmbedding
from pydantic import BaseModel, field_validator

logger = logging.getLogger("fastembed_sidecar")

# ---------------------------------------------------------------------------
# Application & model
# ---------------------------------------------------------------------------

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384

app = FastAPI(
    title="FastEmbed Sidecar",
    version="1.0.0",
    description="Generates sentence embeddings for BLT-Toasty duplicate detection.",
)

# Load model at startup — singleton for the lifetime of the process.
model = TextEmbedding(MODEL_NAME)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class EmbedRequest(BaseModel):
    """Request body for the ``/embed`` endpoint."""

    texts: list[str]

    @field_validator("texts")
    @classmethod
    def texts_must_not_be_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("texts list must contain at least one string")
        return v


class EmbedResponse(BaseModel):
    """Response body for the ``/embed`` endpoint."""

    embeddings: list[list[float]]
    model: str
    dimensions: int


class HealthResponse(BaseModel):
    """Response body for the ``/health`` endpoint."""

    status: str
    model: str
    dimensions: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Readiness probe returning model metadata."""
    return HealthResponse(status="ok", model=MODEL_NAME, dimensions=EMBEDDING_DIMENSIONS)


@app.post("/embed", response_model=EmbedResponse)
async def embed(body: EmbedRequest) -> EmbedResponse:
    """Generate embeddings for the provided texts.

    Args:
        body: JSON body containing a ``texts`` list of strings.

    Returns:
        A response containing the embedding vectors, model name, and dimensions.
    """
    try:
        embeddings = await asyncio.to_thread(lambda: [e.tolist() for e in model.embed(body.texts)])
    except Exception as exc:
        logger.error("Embedding generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {exc}") from exc

    dims = len(embeddings[0]) if embeddings else EMBEDDING_DIMENSIONS
    return EmbedResponse(
        embeddings=embeddings,
        model=MODEL_NAME,
        dimensions=dims,
    )
