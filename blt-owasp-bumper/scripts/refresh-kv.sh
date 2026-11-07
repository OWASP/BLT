#!/usr/bin/env bash
# Regenerate the repository data and the sweep into KV (run by .forkmesh/blt-owasp-bumper--generate-repo-list.yml).
#
#   scripts/refresh-kv.sh                    generate, then write public/data/repos.json to KV
#   KV_PUT_DRY_RUN=1 scripts/refresh-kv.sh   generate, show what would be written
#
# generate_repo_list.py rebuilds the whole file from the GitHub API (it reads no previous output),
# so nothing is seeded. The file is written to KV only when it lists at least half as many
# repositories as the checked-out copy ("total"), so a failed or truncated fetch never replaces
# good data. Nothing is committed and nothing is redeployed.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(git rev-parse --show-toplevel)"
PYTHON="${PYTHON:-python3}"
PUB="${PUBLIC_DIR:-public}"
data="$PUB/data/repos.json"

total() { grep -o '"total": *[0-9]*' "$1" 2>/dev/null | head -1 | tr -dc '0-9' || true; }
before="$(total "$data")"
before="${before:-0}"

OUTPUT_FILE="$data" "$PYTHON" generate_repo_list.py

after="$(total "$data")"
after="${after:-0}"
if (( after == 0 || after * 2 < before )); then
  echo "not writing data/repos.json: $after repositories (was $before)" >&2
  exit 1
fi
# The sweep (sweep.html) joins this data with the OWASP Project Matrix's; when that fails, the
# repository list is still written.
sweep="$PUB/data/sweep.json"
if REPOS_FILE="$data" OUTPUT_FILE="$sweep" "$PYTHON" generate_sweep.py; then
  "$ROOT/scripts/worker-data/kv-put.sh" . "$PUB" "$data" "$sweep"
else
  echo "warning: generate_sweep.py failed; writing data/repos.json only" >&2
  "$ROOT/scripts/worker-data/kv-put.sh" . "$PUB" "$data"
fi
