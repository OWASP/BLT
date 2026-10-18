#!/usr/bin/env bash
# Refresh the leaderboard into KV (run by .forkmesh/blt-pages--update-leaderboard.yml).
#
#   scripts/refresh-kv.sh                    generate, then write the files to KV
#   KV_PUT_DRY_RUN=1 scripts/refresh-kv.sh   generate, list what would be written
#
# Reads the blt-pages bug reports and the leadership nominations from git.owaspblt.org
# (scripts/generate_leaderboard.py), which writes public/data/leaderboard.json and
# public/data/leaders.json and pre-renders public/index.html and public/leaderboard.html in this
# checkout. Those four files go to the Worker's KV (scripts/worker-data/kv-put.sh); nothing is
# committed and nothing is redeployed. Curated elections stay in git (public/data/leaders.json).
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(git rev-parse --show-toplevel)"
PYTHON="${PYTHON:-python3}"

"$PYTHON" scripts/generate_leaderboard.py
for f in public/data/leaderboard.json public/data/leaders.json; do jq -e . "$f" >/dev/null; done
grep -q 'id="leaderboard-inline-data"' public/index.html
"$ROOT/scripts/worker-data/kv-put.sh" . public \
  public/data/leaderboard.json public/data/leaders.json public/index.html public/leaderboard.html
