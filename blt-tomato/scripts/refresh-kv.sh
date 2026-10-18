#!/usr/bin/env bash
# Rebuild the funding list into KV (run by .forkmesh/blt-tomato--scrape_funding.yml).
#
#   scripts/refresh-kv.sh                    scrape, then write the page and its JSON to KV
#   KV_PUT_DRY_RUN=1 scripts/refresh-kv.sh   scrape, list what would be written
#
# owasp_funding_yml_scraper.py rebuilds project_repos_links.json and index.html from the OWASP
# repositories (it reads no previous output), so nothing is seeded. Both files are written to KV
# together, and only when the new list has at least half as many projects as the checked-out one,
# so a failed or truncated scrape never replaces a good page. Nothing is committed and nothing is
# redeployed. Requires python3 (with requests, PyYAML) and jq.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(git rev-parse --show-toplevel)"
PYTHON="${PYTHON:-python3}"
PUB="${PUBLIC_DIR:-public}"
export OUTPUT_DIR="$PUB"
mkdir -p "$PUB"

count() { jq 'if type == "array" then length else 0 end' "$1" 2>/dev/null || echo 0; }
before="$(count "$PUB/project_repos_links.json")"

"$PYTHON" .github/scripts/funding/owasp_funding_yml_scraper.py

after="$(count "$PUB/project_repos_links.json")"
if (( after == 0 || after * 2 < before )); then
  echo "not writing the funding list: $after projects (was $before)" >&2
  exit 1
fi
"$ROOT/scripts/worker-data/kv-put.sh" . "$PUB" "$PUB/project_repos_links.json" "$PUB/index.html"
