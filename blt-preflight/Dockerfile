# ---------------------------------------------------------------------------
# BLT-Preflight Advisory Server – Docker image
# Runs identically on Linux, macOS (Docker Desktop), and Windows (WSL2).
# ---------------------------------------------------------------------------
FROM python:3.11-slim

# ── system deps ──────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Python deps (cached layer) ────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model so the container starts instantly.
# all-MiniLM-L6-v2 is ~90 MB; cached in the image layer.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── application code ──────────────────────────────────────────────────────────
COPY src/ ./src/

# ── knowledge base (OWASP corpus + metadata) ──────────────────────────────────
# Copy only if the directory exists — won't fail on first clone.
COPY knowledge_base/ ./knowledge_base/

# ── pre-built ChromaDB index ──────────────────────────────────────────────────
# Committed artifact; avoids per-run re-embedding on GitHub Actions runners.
# Created at first run by ingest.py if missing — safe to be absent on build.
# Using a placeholder RUN so Docker doesn't fail when chroma_index/ is absent.
RUN mkdir -p /app/chroma_index /app/data

# ── environment defaults (overridable via docker-compose / -e flags) ──────────
ENV PYTHONPATH=/app/src \
    PREFLIGHT_SERVER_PORT=8000 \
    PREFLIGHT_DEBUG=false \
    CHROMA_PERSIST_DIR=/app/chroma_index \
    EMBEDDING_MODEL=all-MiniLM-L6-v2

EXPOSE 8000

# ── entrypoint ────────────────────────────────────────────────────────────────
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]