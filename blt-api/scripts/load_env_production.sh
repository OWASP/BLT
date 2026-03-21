#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env.production}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: $ENV_FILE not found."
  echo "Usage: $0 [path-to-.env.production]"
  exit 1
fi

if ! command -v wrangler >/dev/null 2>&1; then
  echo "Error: wrangler CLI is not installed or not in PATH."
  exit 1
fi

echo "Loading vars from $ENV_FILE into Wrangler production secrets..."

while IFS= read -r line || [[ -n "$line" ]]; do
  # Skip comments and blank lines
  [[ -z "${line//[[:space:]]/}" ]] && continue
  [[ "$line" =~ ^[[:space:]]*# ]] && continue

  if [[ "$line" != *=* ]]; then
    continue
  fi

  key="${line%%=*}"
  value="${line#*=}"

  # Trim key/value whitespace
  key="$(echo "$key" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
  value="$(echo "$value" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"

  # Remove surrounding single/double quotes if present
  if [[ "$value" =~ ^\".*\"$ ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "$value" =~ ^\'.*\'$ ]]; then
    value="${value:1:${#value}-2}"
  fi

  if [[ -z "$key" ]]; then
    continue
  fi

  printf '%s' "$value" | wrangler secret put "$key" --env production >/dev/null
  echo "Set secret: $key"
done < "$ENV_FILE"

echo "Done. All vars from $ENV_FILE were sent to Wrangler as production secrets."
