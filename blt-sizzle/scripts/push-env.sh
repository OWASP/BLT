#!/usr/bin/env bash
# scripts/push-env.sh
# Reads .env.production and uploads every key/value as a Wrangler secret.
#
# Usage:
#   bash scripts/push-env.sh                  # uses .env.production
#   bash scripts/push-env.sh .env.staging     # uses a different file

set -euo pipefail

ENV_FILE="${1:-.env.production}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: $ENV_FILE not found."
  echo "Copy .env.production.example to .env.production and fill in your values."
  exit 1
fi

if ! command -v wrangler &>/dev/null; then
  echo "Error: wrangler CLI not found. Install it with: npm install -g wrangler"
  exit 1
fi

echo "Reading $ENV_FILE …"

while IFS= read -r line || [[ -n "$line" ]]; do
  # Skip blank lines and comments
  [[ -z "$line" || "$line" == \#* ]] && continue

  # Split on first '='
  key="${line%%=*}"
  value="${line#*=}"

  # Skip if value is empty
  if [[ -z "$value" ]]; then
    echo "  Skipping $key (no value set)"
    continue
  fi

  echo "  Uploading secret: $key"
  # Support \n-escaped multi-line values (e.g. PEM private keys)
  printf '%b' "$value" | wrangler secret put "$key" 2>&1 | grep -v "^$" || true

done < "$ENV_FILE"

echo ""
echo "Done. Verify with: wrangler secret list"