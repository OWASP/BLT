#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.production"
WRANGLER_CONFIG="${ROOT_DIR}/wrangler.toml"
WRANGLER_ARGS=(--config "${WRANGLER_CONFIG}")

if [[ -n "${WRANGLER_ENV:-}" ]]; then
  WRANGLER_ARGS+=(--env "${WRANGLER_ENV}")
fi

if ! command -v wrangler >/dev/null 2>&1; then
  echo "wrangler CLI is required but not found in PATH." >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}" >&2
  exit 1
fi

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

secret_count=0

while IFS= read -r line || [[ -n "$line" ]]; do
  [[ -z "$line" ]] && continue
  [[ "$line" =~ ^[[:space:]]*# ]] && continue
  [[ "$line" == export[[:space:]]* ]] && line="${line#export }"

  key="${line%%=*}"
  value="${line#*=}"
  key="$(trim "$key")"
  value="$(trim "$value")"

  if [[ "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi

  if [[ -z "$key" || ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    echo "Skipping invalid env key: ${key:-<empty>}" >&2
    continue
  fi

  printf '%s' "$value" | wrangler secret put "$key" "${WRANGLER_ARGS[@]}"
  echo "Uploaded Cloudflare secret: $key"
  secret_count=$((secret_count + 1))
done < "$ENV_FILE"

echo "Done. Uploaded ${secret_count} Cloudflare secrets from .env.production."
