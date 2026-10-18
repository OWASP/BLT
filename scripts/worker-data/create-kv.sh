#!/usr/bin/env bash
# Create the KV namespaces for the Workers that keep their data in KV, and write their ids into
# each project's wrangler.toml (replacing the REPLACE_WITH_KV_ID_<title> placeholder).
#
#   scripts/worker-data/create-kv.sh            create missing namespaces, patch wrangler.toml
#   scripts/worker-data/create-kv.sh --list     show the table and the current ids only
#
# Safe to run again: an existing namespace with the same title is reused. Needs
# CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID; when they are not set, they are loaded from
# ~/.config/blt/cloudflare.env (if present). Commit the patched wrangler.toml files afterwards.
set -euo pipefail

ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
WRANGLER="${WRANGLER:-npx --yes wrangler@4}"

# project  binding  namespace title
NAMESPACES=(
  "blt-hackathons DATA blt-hackathons-data"
  "blt-gsoc DATA blt-gsoc-data"
  "my-gsoc-tool DATA my-gsoc-tool-data"
  "blt-pages DATA blt-pages-data"
  "blt-design-contest DATA blt-design-contest-data"
)

if [[ "${1:-}" == --list ]]; then
  for row in "${NAMESPACES[@]}"; do
    read -r project binding title <<<"$row"
    printf '%-16s %-6s %-22s %s\n' "$project" "$binding" "$title" \
      "$(grep -A2 "binding = \"$binding\"" "$ROOT/$project/wrangler.toml" | sed -n 's/^id = "\(.*\)"/\1/p' | head -1)"
  done
  exit 0
fi

if [[ -z "${CLOUDFLARE_API_TOKEN:-}" && -f "$HOME/.config/blt/cloudflare.env" ]]; then
  set -a; . "$HOME/.config/blt/cloudflare.env"; set +a
fi
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN is not set}"

list_json() { $WRANGLER kv namespace list 2>/dev/null | sed -n '/^\[/,$p'; }

existing="$(list_json)"
for row in "${NAMESPACES[@]}"; do
  read -r project binding title <<<"$row"
  id="$(jq -r --arg t "$title" '.[] | select(.title == $t) | .id' <<<"$existing" | head -1)"
  if [[ -z "$id" ]]; then
    echo "creating KV namespace $title"
    $WRANGLER kv namespace create "$title" >/dev/null
    existing="$(list_json)"
    id="$(jq -r --arg t "$title" '.[] | select(.title == $t) | .id' <<<"$existing" | head -1)"
  fi
  [[ "$id" =~ ^[0-9a-f]{32}$ ]] || { echo "could not find the id of $title" >&2; exit 1; }
  toml="$ROOT/$project/wrangler.toml"
  if grep -q "REPLACE_WITH_KV_ID_$title" "$toml"; then
    sed -i "s/REPLACE_WITH_KV_ID_$title/$id/" "$toml"
    echo "$project: $binding -> $title ($id)"
  else
    echo "$project: no placeholder for $title in wrangler.toml (already patched?)"
  fi
done
