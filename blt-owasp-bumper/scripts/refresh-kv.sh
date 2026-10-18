#!/usr/bin/env bash
# Regenerate the dashboard page into KV (run by .forkmesh/blt-owasp-bumper--generate-repo-list.yml).
#
#   scripts/refresh-kv.sh                    generate, then write public/index.html to KV
#   KV_PUT_DRY_RUN=1 scripts/refresh-kv.sh   generate, show what would be written
#
# generate_repo_list.py rebuilds the whole page from the GitHub API (it reads no previous output),
# so nothing is seeded. The page is written to KV only when it lists at least half as many
# repositories as the checked-out page ("Total: N repositories"), so a failed or truncated fetch
# never replaces a good page. Nothing is committed and nothing is redeployed.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(git rev-parse --show-toplevel)"
PYTHON="${PYTHON:-python3}"
PUB="${PUBLIC_DIR:-public}"
page="$PUB/index.html"

total() { grep -o 'Total: [0-9]* repositories' "$1" 2>/dev/null | head -1 | tr -dc '0-9' || true; }
before="$(total "$page")"
before="${before:-0}"

OUTPUT_FILE="$page" "$PYTHON" generate_repo_list.py

after="$(total "$page")"
after="${after:-0}"
if (( after == 0 || after * 2 < before )); then
  echo "not writing index.html: $after repositories (was $before)" >&2
  exit 1
fi
"$ROOT/scripts/worker-data/kv-put.sh" . "$PUB" "$page"
