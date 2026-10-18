#!/bin/sh
# Regenerates the dashboard data into public/ (run from blt-waypoint/). The daily workflow
# (.forkmesh/blt-waypoint--build-site.yml) runs only generate_forge_data.py and writes the result
# to KV; generate_main_data.py derives the committed main_data files from github_data.json.
set -eu

PYTHON_BIN="${PYTHON:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN=python
fi

mkdir -p public

"$PYTHON_BIN" scripts/generate_forge_data.py || echo "Keeping existing forge_data.json"
"$PYTHON_BIN" scripts/generate_main_data.py || echo "Keeping existing main data files"
