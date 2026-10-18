#!/usr/bin/env bash
# Read one key from a Worker's KV namespace through the Cloudflare API into a file.
#
#   scripts/worker-data/kv-get.sh <project-dir> <key> <output-file>
#
# The namespace is found like kv-put.sh does (binding "DATA" or $KV_BINDING in
# <project-dir>/wrangler.toml, or KV_NAMESPACE_ID). Exits 0 and writes the file when the key
# exists, 3 when it does not, 1 on any other error (missing credentials included), leaving the
# output file untouched. Needs CLOUDFLARE_API_TOKEN (Workers KV Storage: Read or Edit) and
# CLOUDFLARE_ACCOUNT_ID. KV_GET_FROM=<file> copies that file instead (tests, dry runs).
set -euo pipefail

[[ $# -eq 3 ]] || { sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }
project="$1"; key="$2"; out="$3"
binding="${KV_BINDING:-DATA}"

if [[ -n "${KV_GET_FROM:-}" ]]; then
  [[ -f "$KV_GET_FROM" ]] || exit 3
  cp "$KV_GET_FROM" "$out"
  exit 0
fi

ns="${KV_NAMESPACE_ID:-$(awk -v want="$binding" '
  /^\[\[kv_namespaces\]\]/ { inblock = 1; b = ""; id = ""; next }
  /^\[/ { if (inblock && b == want && id != "") { print id; exit } inblock = 0 }
  inblock && /^[[:space:]]*binding[[:space:]]*=/ { b = $0; sub(/^[^"]*"/, "", b); sub(/".*/, "", b) }
  inblock && /^[[:space:]]*id[[:space:]]*=/ { id = $0; sub(/^[^"]*"/, "", id); sub(/".*/, "", id) }
  END { if (inblock && b == want && id != "") print id }
' "$project/wrangler.toml" | head -1)}"
[[ -n "$ns" && "$ns" != REPLACE_WITH_KV_ID* ]] || { echo "kv-get: no KV id for binding $binding" >&2; exit 1; }
[[ -n "${CLOUDFLARE_API_TOKEN:-}" && -n "${CLOUDFLARE_ACCOUNT_ID:-}" ]] || {
  echo "kv-get: CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID is not set" >&2; exit 1; }

encoded="$(jq -rn --arg k "$key" '$k | @uri')"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
code="$(curl -sS -o "$tmp" -w '%{http_code}' \
  "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/storage/kv/namespaces/$ns/values/$encoded" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN")" || { echo "kv-get: request failed" >&2; exit 1; }
case "$code" in
  200) mv "$tmp" "$out"; trap - EXIT ;;
  404) exit 3 ;;
  *) echo "kv-get: Cloudflare API answered HTTP $code for $key" >&2; exit 1 ;;
esac
