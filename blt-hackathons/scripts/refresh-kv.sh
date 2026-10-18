#!/usr/bin/env bash
# Refresh hackathon statistics into KV (run by .forkmesh/blt-hackathons--update-stats.yml).
#
#   scripts/refresh-kv.sh            fetch, then write changed files to KV
#   KV_PUT_DRY_RUN=1 scripts/refresh-kv.sh   fetch, list what would be written
#
# 1. Seeds public/ with the live copies (SITE_URL, default https://hackathons.owaspblt.org) of the
#    files of hackathons that have not ended, plus stats.json, because KV, not git, holds the
#    latest data and fetch_stats.py merges reviews incrementally from the previous file.
# 2. Runs fetch_stats.py (needs GITHUB_TOKEN / GITLAB_TOKEN for higher rate limits), which skips
#    ended hackathons.
# 3. Writes the files it rewrote to KV with scripts/worker-data/kv-put.sh. stats.json is written
#    only when something other than its lastUpdated changed.
# Nothing is committed and nothing is redeployed. Requires python3 (with PyYAML), node, curl, jq.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(git rev-parse --show-toplevel)"
SITE_URL="${SITE_URL:-https://hackathons.owaspblt.org}"
PYTHON="${PYTHON:-python3}"
PUB="${PUBLIC_DIR:-public}"   # where the data files are read and written (fetch_stats.py uses it too)
export PUBLIC_DIR="$PUB"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

node scripts/parse_hackathons_config.js public/js/hackathons-config.js "$work/config.json" >/dev/null

seed() {  # seed <path under public/>
  if curl -fsS --max-time 60 -o "$work/seed" "$SITE_URL/$1" && jq -e . "$work/seed" >/dev/null 2>&1; then
    mkdir -p "$(dirname "$PUB/$1")"
    mv "$work/seed" "$PUB/$1"
    echo "seeded $1 from $SITE_URL"
  else
    echo "no live copy of $1; using the committed file (if any)"
  fi
}

mapfile -t active < <(jq -r --arg now "${NOW:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}" \
  '.hackathons[] | select((.endTime | sub("\\.[0-9]+"; "") | fromdateiso8601) >= ($now | fromdateiso8601)) | .slug' \
  "$work/config.json")
for slug in "${active[@]}"; do
  seed "hackathon-data/$slug.json"
  seed "hackathon-data/$slug-summary.json"
done
seed stats.json
if [[ -f "$PUB/stats.json" ]]; then cp "$PUB/stats.json" "$work/stats-before.json"; else echo '{}' > "$work/stats-before.json"; fi

touch "$work/marker"
sleep 1
HACKATHONS_CONFIG_PATH="$work/config.json" "$PYTHON" fetch_stats.py

changed=()
while IFS= read -r -d '' file; do changed+=("$file"); done < <(find "$PUB/hackathon-data" -name '*.json' -newer "$work/marker" -print0)
if ! cmp -s <(jq -S 'del(.lastUpdated)' "$work/stats-before.json") <(jq -S 'del(.lastUpdated)' "$PUB/stats.json"); then
  changed+=("$PUB/stats.json")
fi
if [[ ${#changed[@]} -eq 0 ]]; then
  echo "no hackathon data changed"
  exit 0
fi
"$ROOT/scripts/worker-data/kv-put.sh" . "$PUB" "${changed[@]}"
