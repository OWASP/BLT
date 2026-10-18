#!/usr/bin/env bash
# Refresh the Slack apps list into KV (run by .forkmesh/blt-panini--update_slack_apps.yml).
#
#   scripts/refresh-kv.sh                    scrape, then write slack_apps.json to KV if it changed
#   KV_PUT_DRY_RUN=1 scripts/refresh-kv.sh   scrape, show what would be written
#
# update_slack_apps.py merges newly listed Slack apps into the previous slack_apps.json (it never
# removes one), so the base is the copy in KV (scripts/worker-data/kv-get.sh) with the committed
# entries laid over it: apps found by earlier runs are kept, and curated fields edited in git
# (security_rating, permissions, ...) win. Without a KV copy yet, the committed file is the base;
# when KV cannot be read, the run stops so apps found earlier are never dropped. The result is
# written to KV when it differs from the KV copy. Nothing is committed and nothing is redeployed.
# Requires python3 (with requests, beautifulsoup4), curl, jq.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(git rev-parse --show-toplevel)"
PYTHON="${PYTHON:-python3}"
PUB="${PUBLIC_DIR:-public}"
export SLACK_APPS_PATH="$PUB/slack_apps.json"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

status=0
"$ROOT/scripts/worker-data/kv-get.sh" . slack_apps.json "$work/kv.json" || status=$?
if [[ $status -eq 0 ]] && jq -e 'type == "array"' "$work/kv.json" >/dev/null 2>&1; then
  jq -s '(.[1] | map({key: (.app_name | ascii_downcase), value: true}) | from_entries) as $git
    | .[1] + (.[0] | map(select($git[.app_name | ascii_downcase] | not)))' \
    "$work/kv.json" "$SLACK_APPS_PATH" > "$work/base.json"
  mv "$work/base.json" "$SLACK_APPS_PATH"
  echo "seeded slack_apps.json from KV ($(jq length "$work/kv.json") apps) with the committed entries over it"
elif [[ $status -eq 3 ]]; then
  echo "no slack_apps.json in KV yet; using the committed file"
  echo '[]' > "$work/kv.json"
else
  echo "could not read slack_apps.json from KV; stopping" >&2
  exit 1
fi

"$PYTHON" scripts/update_slack_apps.py || echo "warning: update_slack_apps.py failed; keeping the previous list"

if ! jq -e 'type == "array" and length > 0' "$SLACK_APPS_PATH" >/dev/null 2>&1; then
  echo "not writing slack_apps.json: not a non-empty list" >&2
  exit 1
fi
if cmp -s <(jq -S . "$work/kv.json") <(jq -S . "$SLACK_APPS_PATH"); then
  echo "slack_apps.json unchanged"
  exit 0
fi
"$ROOT/scripts/worker-data/kv-put.sh" . "$PUB" "$SLACK_APPS_PATH"
