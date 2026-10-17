#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# BLT-Preflight – Native Python setup (Linux / macOS)
# Run once:  bash setup.sh
# Then:      source .venv/bin/activate && python src/main.py
# ---------------------------------------------------------------------------
set -euo pipefail

PYTHON=${PYTHON:-python3}
VENV_DIR=".venv"
CHROMA_INDEX_DIR="chroma_index"

echo "==> BLT-Preflight native setup"

# ── 1. Python version guard ───────────────────────────────────────────────────
MIN_MAJOR=3
MIN_MINOR=10

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt "$MIN_MAJOR" ] || { [ "$PY_MAJOR" -eq "$MIN_MAJOR" ] && [ "$PY_MINOR" -lt "$MIN_MINOR" ]; }; then
    echo "ERROR: Python $MIN_MAJOR.$MIN_MINOR+ required (found $PY_VERSION)."
    exit 1
fi
echo "    Python $PY_VERSION — OK"

# ── 2. Virtual environment ────────────────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "==> Creating virtual environment in $VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo "==> Virtual environment activated"

# ── 3. Dependencies ───────────────────────────────────────────────────────────
echo "==> Installing dependencies"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# ── 4. Pre-download embedding model ──────────────────────────────────────────
echo "==> Downloading sentence-transformers model (all-MiniLM-L6-v2)"
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── 5. ChromaDB index ─────────────────────────────────────────────────────────
if [ ! -d "$CHROMA_INDEX_DIR" ] || [ -z "$(ls -A "$CHROMA_INDEX_DIR" 2>/dev/null)" ]; then
    echo "==> No pre-built ChromaDB index found — running ingest pipeline"
    PYTHONPATH=src python src/scripts/ingest.py
else
    echo "==> Pre-built ChromaDB index found — skipping ingest"
fi

# ── 6. .env reminder ──────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || true
    echo ""
    echo "  ACTION REQUIRED: edit .env and add your GEMINI_API_KEY"
    echo "  (or set LLM_PROVIDER=ollama for fully offline operation)"
    echo ""
fi

echo ""
echo "==> Setup complete!"
echo "    Start the server:  source $VENV_DIR/bin/activate && PYTHONPATH=src uvicorn main:app --host 0.0.0.0 --port 8000"
echo "    Health check:      curl http://localhost:8000/health"