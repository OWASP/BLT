#!/usr/bin/env bash
# Rebuild the showcase pages and write the changed ones to KV
# (run by .forkmesh/blt-design-contest--build-showcase.yml).
#
#   scripts/refresh-kv.sh                    build, then write changed pages to KV
#   KV_PUT_DRY_RUN=1 scripts/refresh-kv.sh   build, list what would be written
#
# 1. Runs scripts/build_showcase.py into a temporary directory (not public/, nothing is committed):
#    open blt-design-contest issues from the git.owaspblt.org issue ledger plus the frozen GitLab
#    entries in data/gitlab-archive.json.
# 2. Compares each page with the live copy (SITE_URL, default https://contest.owaspblt.org),
#    ignoring the "Last updated" stamp, and writes only the pages that differ (or have no live
#    copy) with scripts/worker-data/kv-put.sh. The Worker serves them under the same URLs.
# Nothing is committed and nothing is redeployed. Requires python3, curl, jq.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(git rev-parse --show-toplevel)"
SITE_URL="${SITE_URL:-https://contest.owaspblt.org}"
PYTHON="${PYTHON:-python3}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

"$PYTHON" scripts/build_showcase.py --out "$work/pages"

normalize() { sed -E 's/Last updated [0-9]{2} [A-Za-z]{3} [0-9]{4} [0-9]{2}:[0-9]{2} UTC/Last updated -/' "$1"; }

changed=()
for page in "$work"/pages/*.html; do
  name="$(basename "$page")"
  if curl -fsSL --max-time 60 -o "$work/live" "$SITE_URL/$name" &&
     cmp -s <(normalize "$work/live") <(normalize "$page"); then
    continue
  fi
  changed+=("$page")
done
if [[ ${#changed[@]} -eq 0 ]]; then
  echo "no page changed"
  exit 0
fi
"$ROOT/scripts/worker-data/kv-put.sh" . "$work/pages" "${changed[@]}"
