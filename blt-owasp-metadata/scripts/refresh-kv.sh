#!/usr/bin/env bash
# Rebuild the metadata dataset into KV (run by .forkmesh/blt-owasp-metadata--scraper.yml).
#
#   scripts/refresh-kv.sh                    scrape, then write public/data/* to KV
#   KV_PUT_DRY_RUN=1 scripts/refresh-kv.sh   scrape, list what would be written
#
# scrape_metadata.py rebuilds every file from the OWASP repositories (it reads no previous output),
# so nothing is seeded. The five generated files are written to KV together, and only when
# metadata.json and metadata_matrix.json each list at least half as many repositories as the
# checked-out copies, so a failed GitHub listing (which yields an empty dataset) never replaces
# good data. metadata_checklist.csv is not generated and stays a committed file.
# Nothing is committed and nothing is redeployed.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(git rev-parse --show-toplevel)"
PYTHON="${PYTHON:-python3}"
PUB="${PUBLIC_DIR:-public}"
export METADATA_DATA_DIR="$PUB/data"
FILES=(metadata.json metadata_matrix.json metadata.csv metadata_matrix.csv metadata_summary.md)
mkdir -p "$METADATA_DATA_DIR"

count() { jq 'if type == "array" then length else 0 end' "$1" 2>/dev/null || echo 0; }
declare -A before
for f in metadata.json metadata_matrix.json; do before[$f]="$(count "$METADATA_DATA_DIR/$f")"; done

"$PYTHON" scripts/scrape_metadata.py

for f in metadata.json metadata_matrix.json; do
  after="$(count "$METADATA_DATA_DIR/$f")"
  if (( after == 0 || after * 2 < before[$f] )); then
    echo "not writing the dataset: $f lists $after repositories (was ${before[$f]})" >&2
    exit 1
  fi
done
paths=()
for f in "${FILES[@]}"; do paths+=("$METADATA_DATA_DIR/$f"); done
"$ROOT/scripts/worker-data/kv-put.sh" . "$PUB" "${paths[@]}"
