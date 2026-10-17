#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8000}"
HOST="${HOST:-127.0.0.1}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT_DIR"

if command -v python3 >/dev/null 2>&1; then
    echo "Serving BLT-GSOC from $ROOT_DIR"
    echo "Open: http://$HOST:$PORT/gsoc2026.html"
    exec python3 -m http.server "$PORT" --bind "$HOST"
elif command -v python >/dev/null 2>&1; then
    echo "Serving BLT-GSOC from $ROOT_DIR"
    echo "Open: http://$HOST:$PORT/gsoc2026.html"
    exec python -m SimpleHTTPServer "$PORT"
else
    echo "Error: Python is required (python3 preferred)." >&2
    exit 1
fi
