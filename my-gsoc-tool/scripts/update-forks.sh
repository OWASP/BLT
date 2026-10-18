#!/usr/bin/env bash
# Rewrites the section between FORKS_START and FORKS_END in README.md with the forks of the
# GitHub repository FORKS_REPO (default OWASP-BLT/MY-GSOC-TOOL, where the template is forked).
# Run by .forkmesh/my-gsoc-tool--update-forks.yml (was inline in the GitHub workflow update-forks.yml).
set -euo pipefail
cd "$(dirname "$0")/.."

REPO="${FORKS_REPO:-OWASP-BLT/MY-GSOC-TOOL}"
auth=()
[[ -n "${GITHUB_TOKEN:-}" ]] && auth=(-H "Authorization: token $GITHUB_TOKEN")

if ! grep -q "FORKS_START" README.md || ! grep -q "FORKS_END" README.md; then
  echo "Forks section markers not found in README.md"
  exit 0
fi

FORKS_JSON=$(curl -fsS "${auth[@]}" -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/${REPO}/forks?per_page=100&sort=stargazers")
if ! jq -e 'type == "array"' >/dev/null <<<"$FORKS_JSON"; then
  echo "unexpected response from the GitHub API; README.md left unchanged" >&2
  exit 1
fi
FORKS_LIST=$(jq -r 'if length == 0 then "No forks yet. Be the first to fork this project!" else .[] | "- [" + .full_name + "](" + .html_url + ") - ⭐ " + (.stargazers_count | tostring) + " stars" end' <<<"$FORKS_JSON")
TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M:%S UTC')

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
{
  echo "## 🍴 Project Forks"
  echo ""
  echo "The following users have forked this project:"
  echo ""
  echo "$FORKS_LIST"
  echo ""
  echo "_Last updated: ${TIMESTAMP}_"
} > "$tmp/section"
START_LINE=$(grep -n "FORKS_START" README.md | head -1 | cut -d: -f1)
END_LINE=$(grep -n "FORKS_END" README.md | head -1 | cut -d: -f1)
head -n "$START_LINE" README.md > "$tmp/top"
tail -n +"$END_LINE" README.md > "$tmp/bottom"
cat "$tmp/top" "$tmp/section" "$tmp/bottom" > README.md
