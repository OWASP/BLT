#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ -z "${CLOUDFLARE_ACCOUNT_ID:-}" && -n "${CF_ACCOUNT_ID:-}" ]]; then
  export CLOUDFLARE_ACCOUNT_ID="$CF_ACCOUNT_ID"
fi

if [[ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]]; then
  cat >&2 <<'EOF'
Missing Cloudflare account ID.

Set one of these environment variables before deploying:
  export CLOUDFLARE_ACCOUNT_ID="your-account-id"
  export CF_ACCOUNT_ID="your-account-id"

For CI, also set CLOUDFLARE_API_TOKEN with Worker deploy permissions.
EOF
  exit 1
fi

if [[ ! -f wrangler.toml ]]; then
  echo "wrangler.toml not found. Run this script from the repository root." >&2
  exit 1
fi

echo "Checking Cloudflare authentication..."
npx wrangler whoami >/dev/null

if [[ "${SKIP_TESTS:-0}" != "1" ]]; then
  echo "Running test suite before production deploy..."
  python -m unittest discover tests
fi

echo "Deploying BLT Sizzle to Cloudflare production..."
npx wrangler deploy --config wrangler.toml "$@"
