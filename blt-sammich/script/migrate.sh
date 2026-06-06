#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRANGLER_CONFIG="${ROOT_DIR}/wrangler.toml"
DATABASE_NAME="${D1_DATABASE_NAME:-blt-sammich}"

if [[ "${SKIP_D1_MIGRATIONS:-}" == "1" ]]; then
  echo "Skipping D1 migrations because SKIP_D1_MIGRATIONS=1."
  exit 0
fi

if ! command -v wrangler >/dev/null 2>&1; then
  echo "wrangler CLI is required but not found in PATH." >&2
  exit 1
fi

args=(d1 migrations apply "${DATABASE_NAME}" --remote --config "${WRANGLER_CONFIG}")

if [[ -n "${WRANGLER_ENV:-}" ]]; then
  args+=(--env "${WRANGLER_ENV}")
fi

echo "Applying D1 migrations for ${DATABASE_NAME}..."
wrangler "${args[@]}"
echo "D1 migrations applied."
