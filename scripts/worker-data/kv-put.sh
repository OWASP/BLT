#!/usr/bin/env bash
# Write files into a Worker's KV namespace through the Cloudflare API (no git, no redeploy).
#
#   scripts/worker-data/kv-put.sh <project-dir> <base-dir> <file>...
#
# The namespace is the [[kv_namespaces]] entry with binding "DATA" (or $KV_BINDING) in
# <project-dir>/wrangler.toml. Each file's key is its path relative to <base-dir> (for example
# public/hackathon-data/x.json with base public -> hackathon-data/x.json), stored with
# {"updatedAt": <now>} metadata like kv-data.js putData(). Needs CLOUDFLARE_API_TOKEN (with
# Workers KV Storage: Edit) and CLOUDFLARE_ACCOUNT_ID. KV_PUT_DRY_RUN=1 prints the keys only;
# KV_NAMESPACE_ID overrides the id read from wrangler.toml. Images, fonts and PDFs are sent
# base64-encoded ("base64": true) so their bytes arrive unchanged.
set -euo pipefail

[[ $# -ge 3 ]] || { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }
project="$1"; base="${2%/}"; shift 2
binding="${KV_BINDING:-DATA}"

namespace_id() {
  awk -v want="$binding" '
    /^\[\[kv_namespaces\]\]/ { inblock = 1; b = ""; id = ""; next }
    /^\[/ { if (inblock && b == want && id != "") { print id; exit } inblock = 0 }
    inblock && /^[[:space:]]*binding[[:space:]]*=/ { b = $0; sub(/^[^"]*"/, "", b); sub(/".*/, "", b) }
    inblock && /^[[:space:]]*id[[:space:]]*=/ { id = $0; sub(/^[^"]*"/, "", id); sub(/".*/, "", id) }
    END { if (inblock && b == want && id != "") print id }
  ' "$1"
}

ns="${KV_NAMESPACE_ID:-$(namespace_id "$project/wrangler.toml" | head -1)}"
if [[ -z "$ns" || "$ns" == REPLACE_WITH_KV_ID* ]]; then
  echo "kv-put: no KV id for binding $binding in $project/wrangler.toml (run scripts/worker-data/create-kv.sh)" >&2
  exit 1
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
keys=()
for file in "$@"; do
  [[ -f "$file" ]] || { echo "kv-put: missing $file" >&2; exit 1; }
  key="${file#"$base"/}"
  [[ "$key" != "$file" ]] || { echo "kv-put: $file is not under $base" >&2; exit 1; }
  keys+=("$key")
  case "${file##*.}" in
    jpg|jpeg|png|webp|gif|ico|woff|woff2|pdf)
      base64 -w0 "$file" > "$tmp/value.b64"
      jq -n --arg key "$key" --rawfile value "$tmp/value.b64" --arg at "$now" \
        '{key: $key, value: $value, base64: true, metadata: {updatedAt: $at}}' > "$tmp/${#keys[@]}.json"
      ;;
    *)
      jq -n --arg key "$key" --rawfile value "$file" --arg at "$now" \
        '{key: $key, value: $value, metadata: {updatedAt: $at}}' > "$tmp/${#keys[@]}.json"
      ;;
  esac
done
[[ ${#keys[@]} -gt 0 ]] || { echo "kv-put: nothing to write"; exit 0; }

if [[ "${KV_PUT_DRY_RUN:-}" == 1 ]]; then
  printf 'would write %s\n' "${keys[@]}"
  exit 0
fi
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN is not set}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID is not set}"

jq -s . "$tmp"/[0-9]*.json > "$tmp/bulk.json"
response="$(curl -sS -X PUT \
  "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/storage/kv/namespaces/$ns/bulk" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" -H "Content-Type: application/json" \
  --data-binary @"$tmp/bulk.json")"
if [[ "$(jq -r '.success' <<<"$response" 2>/dev/null)" != true ]]; then
  echo "kv-put: Cloudflare API error: $(jq -c '.errors' <<<"$response" 2>/dev/null || echo "$response")" >&2
  exit 1
fi
printf 'wrote %s\n' "${keys[@]}"
