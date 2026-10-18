#!/usr/bin/env bash
# Refresh the dashboard data into KV (run by .forkmesh/blt-owasp-projects--refresh-data.yml).
#
#   scripts/refresh-kv.sh                    fetch, then write the changed files to KV
#   KV_PUT_DRY_RUN=1 scripts/refresh-kv.sh   fetch, list what would be written
#
# 1. Seeds public/ with the live copies (SITE_URL, default https://projects.owaspblt.org) of the
#    data files, because KV, not git, holds the latest data: main.py compares with the previous
#    www_project_repos.json and fetch_issues.py keeps known_issue_ids.json (both for Slack alerts).
# 2. Runs the four generators into public/ (a failing one is reported and its files are skipped).
# 3. Writes each data file that is a non-empty JSON array, not less than half as long as before,
#    and changed, to KV with scripts/worker-data/kv-put.sh. repo_status.json also needs at least
#    one repository read successfully (a bad token makes every entry "Bad credentials").
# Nothing is committed and nothing is redeployed. Requires python3, curl, jq.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(git rev-parse --show-toplevel)"
SITE_URL="${SITE_URL:-https://projects.owaspblt.org}"
PYTHON="${PYTHON:-python3}"
PUB="${PUBLIC_DIR:-public}"
export OUTPUT_DIR="$PUB"
FILES=(www_project_repos.json repo_status.json issues.json known_issue_ids.json project_repos_links.json)
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/before" "$PUB"

for f in "${FILES[@]}"; do
  if curl -fsS --max-time 60 -o "$work/seed" "$SITE_URL/$f" && jq -e 'type == "array"' "$work/seed" >/dev/null 2>&1; then
    mv "$work/seed" "$PUB/$f"
    echo "seeded $f from $SITE_URL"
  else
    echo "no live copy of $f; using the checked-out file"
  fi
  if [[ -f "$PUB/$f" ]]; then cp "$PUB/$f" "$work/before/$f"; else echo '[]' > "$work/before/$f"; fi
done

for script in main.py fetch_repo_status.py fetch_issues.py scrape_github_links.py; do
  "$PYTHON" "scripts/$script" || echo "warning: scripts/$script failed; keeping the previous data"
done

changed=()
for f in "${FILES[@]}"; do
  before="$(jq 'length' "$work/before/$f" 2>/dev/null || echo 0)"
  if ! jq -e --argjson before "$before" \
      'type == "array" and length > 0 and length * 2 >= $before' "$PUB/$f" >/dev/null 2>&1; then
    echo "skipping $f: empty, invalid or less than half of the previous $before entries"
  elif [[ "$f" == repo_status.json ]] && ! jq -e 'any(.[]; .github_status == "success")' "$PUB/$f" >/dev/null; then
    echo "skipping $f: no repository was read successfully"
  elif cmp -s <(jq -S . "$work/before/$f") <(jq -S . "$PUB/$f"); then
    echo "$f unchanged"
  else
    changed+=("$PUB/$f")
  fi
done
if [[ ${#changed[@]} -eq 0 ]]; then
  echo "no data changed"
  exit 0
fi
"$ROOT/scripts/worker-data/kv-put.sh" . "$PUB" "${changed[@]}"
