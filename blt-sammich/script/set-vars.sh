#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.production"

if ! command -v wrangler >/dev/null 2>&1; then
  echo "wrangler CLI is required but not found in PATH." >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}" >&2
  exit 1
fi

while IFS= read -r line || [[ -n "$line" ]]; do
  [[ -z "$line" ]] && continue
  [[ "$line" =~ ^[[:space:]]*# ]] && continue

  key="${line%%=*}"
  value="${line#*=}"

  if [[ -z "$key" ]]; then
    continue
  fi

  printf '%s' "$value" | wrangler secret put "$key"
  echo "Set secret: $key"
done < "$ENV_FILE"

echo "Done. Wrangler secrets updated from .env.production."
