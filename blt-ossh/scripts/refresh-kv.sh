#!/usr/bin/env bash
# Refresh the community catalog into KV (run by .forkmesh/blt-ossh--update-catalog.yml).
#
#   scripts/refresh-kv.sh                    fetch, then write data/ossh_catalog.json to KV if it changed
#   KV_PUT_DRY_RUN=1 scripts/refresh-kv.sh   fetch, show what would be written
#
# 1. Seeds public/data/ossh_catalog.json with the copy in KV (scripts/worker-data/kv-get.sh),
#    because KV, not git, holds the latest catalog and each fetch script replaces only its own
#    section of the previous file. Without a KV copy yet, the checked-out file is the base; when
#    KV cannot be read, the run stops so a stale base never replaces newer data.
# 2. Runs fetch_articles.py (DEV.to), fetch_discord.py (only with DISCORD_BOT_TOKEN) and
#    fetch_reddit.py. Each keeps its section when it fetched nothing or less than half as much.
# 3. Drops repos hosted under gitlab.com/owasp-blt (the group is closed; BLT lives on
#    git.owaspblt.org) and writes the catalog to KV when it changed.
# Nothing is committed and nothing is redeployed. Requires python3 (with requests), curl, jq.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(git rev-parse --show-toplevel)"
PYTHON="${PYTHON:-python3}"
PUB="${PUBLIC_DIR:-public}"
export OSSH_CATALOG_PATH="$PUB/data/ossh_catalog.json"
CATALOG_OK='type == "object" and (.repos | type == "array" and length > 0)'
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$PUB/data"

status=0
"$ROOT/scripts/worker-data/kv-get.sh" . data/ossh_catalog.json "$work/seed" || status=$?
if [[ $status -eq 0 ]] && jq -e "$CATALOG_OK" "$work/seed" >/dev/null 2>&1; then
  mv "$work/seed" "$OSSH_CATALOG_PATH"
  echo "seeded data/ossh_catalog.json from KV"
elif [[ $status -eq 3 ]]; then
  echo "no catalog in KV yet; using the checked-out file"
else
  echo "could not read a valid catalog from KV; stopping" >&2
  exit 1
fi
cp "$OSSH_CATALOG_PATH" "$work/before.json"

"$PYTHON" scripts/fetch_articles.py || echo "warning: fetch_articles.py failed"
if [[ -n "${DISCORD_BOT_TOKEN:-}" ]]; then
  "$PYTHON" scripts/fetch_discord.py || echo "warning: fetch_discord.py failed"
fi
"$PYTHON" scripts/fetch_reddit.py || echo "warning: fetch_reddit.py failed"

if ! jq -e "$CATALOG_OK" "$OSSH_CATALOG_PATH" >/dev/null 2>&1; then
  echo "not writing data/ossh_catalog.json: not a catalog with repos" >&2
  exit 1
fi
jq '.repos |= map(select((.url // "") | startswith("https://gitlab.com/owasp-blt/") | not))' \
  "$OSSH_CATALOG_PATH" > "$work/catalog.json"
mv "$work/catalog.json" "$OSSH_CATALOG_PATH"

if cmp -s <(jq -S . "$work/before.json") <(jq -S . "$OSSH_CATALOG_PATH"); then
  echo "catalog unchanged"
  exit 0
fi
"$ROOT/scripts/worker-data/kv-put.sh" . "$PUB" "$OSSH_CATALOG_PATH"
