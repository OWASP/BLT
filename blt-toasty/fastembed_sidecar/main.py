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

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastembed import TextEmbedding
from pydantic import BaseModel, field_validator

logger = logging.getLogger("fastembed_sidecar")

# ---------------------------------------------------------------------------
# Application & model
# ---------------------------------------------------------------------------

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384


# Global reference populated during lifespan
model: TextEmbedding | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    logger.info("Initializing TextEmbedding model %s...", MODEL_NAME)
    model = TextEmbedding(MODEL_NAME)
    logger.info("Model loaded successfully.")
    yield
    logger.info("Shutting down FastEmbed sidecar.")


app = FastAPI(
    title="FastEmbed Sidecar",
    version="1.0.0",
    description="Generates sentence embeddings for BLT-Toasty duplicate detection.",
    lifespan=lifespan,
)


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
        if model is None:
            raise RuntimeError("Model is not initialized")
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
