#!/bin/sh
set -eu

PYTHON_BIN="${PYTHON:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN=python
fi

mkdir -p public

"$PYTHON_BIN" scripts/generate_gitlab_data.py || echo "Keeping existing gitlab_data.json"
"$PYTHON_BIN" scripts/generate_main_data.py || echo "Keeping existing main data files"
