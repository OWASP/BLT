#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WRANGLER_TOML="$REPO_ROOT/wrangler.toml"
ENV_FILE="${1:-$REPO_ROOT/.env.production}"

if [[ ! -f "$WRANGLER_TOML" ]]; then
  echo "Error: wrangler.toml not found at $WRANGLER_TOML"
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: env file not found at $ENV_FILE"
  exit 1
fi

if ! command -v npx >/dev/null 2>&1; then
  echo "Error: npx is required but not installed."
  exit 1
fi

CONFIG_WORKER_NAME="$({ awk -F '"' '/^name\s*=\s*"/{ print $2; exit }' "$WRANGLER_TOML"; } || true)"
if [[ -z "$CONFIG_WORKER_NAME" ]]; then
  echo "Error: could not parse Worker name from $WRANGLER_TOML"
  exit 1
fi

declare -a ENV_KEYS=()
declare -A ENV_VALUES=()

while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
  line="${raw_line%$'\r'}"

  # Skip blank lines and comments.
  if [[ -z "${line//[[:space:]]/}" ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
    continue
  fi

  if [[ ! "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
    continue
  fi

  key="${line%%=*}"
  value="${line#*=}"
  ENV_KEYS+=("$key")
  ENV_VALUES["$key"]="$value"
done < "$ENV_FILE"

TARGET_WORKER_NAME="${ENV_VALUES[CLOUDFLARE_WORKER_NAME]-}"
if [[ -z "$TARGET_WORKER_NAME" ]]; then
  echo "Error: CLOUDFLARE_WORKER_NAME is required in $ENV_FILE"
  exit 1
fi

TARGET_ACCOUNT_ID="${ENV_VALUES[CLOUDFLARE_ACCOUNT_ID]-}"
if [[ -z "$TARGET_ACCOUNT_ID" ]]; then
  echo "Error: CLOUDFLARE_ACCOUNT_ID is required in $ENV_FILE"
  exit 1
fi

if [[ "$TARGET_WORKER_NAME" != "$CONFIG_WORKER_NAME" ]]; then
  echo "Error: worker mismatch."
  echo "  wrangler.toml name: $CONFIG_WORKER_NAME"
  echo "  $ENV_FILE CLOUDFLARE_WORKER_NAME: $TARGET_WORKER_NAME"
  echo "Refusing to upload secrets to the wrong Worker."
  exit 1
fi

whoami_output="$(npx wrangler whoami 2>&1 || true)"
if ! grep -q "$TARGET_ACCOUNT_ID" <<< "$whoami_output"; then
  echo "Error: current Wrangler credentials do not have access to account $TARGET_ACCOUNT_ID"
  echo ""
  echo "Switch Wrangler auth to the correct account, then retry:"
  echo "  1) npx wrangler logout"
  echo "  2) npx wrangler login"
  echo "     - Complete browser auth with the Cloudflare user that owns account $TARGET_ACCOUNT_ID"
  echo "  3) npx wrangler whoami"
  echo "     - Confirm account $TARGET_ACCOUNT_ID appears in the account list"
  echo "  4) ./scripts/upload-production-vars.sh"
  exit 1
fi

if [[ ${#ENV_KEYS[@]} -eq 0 ]]; then
  echo "Error: no variables found in $ENV_FILE"
  exit 1
fi

echo "Verified Worker: $TARGET_WORKER_NAME"
echo "Using Cloudflare account: $TARGET_ACCOUNT_ID"
echo "Uploading non-empty variables from: $ENV_FILE"

uploaded=0
skipped=0
for key in "${ENV_KEYS[@]}"; do
  if [[ "$key" == "CLOUDFLARE_WORKER_NAME" || "$key" == "CLOUDFLARE_ACCOUNT_ID" ]]; then
    continue
  fi

  value="${ENV_VALUES[$key]-}"
  if [[ -z "$value" ]]; then
    echo "- Skipping $key (empty)"
    skipped=$((skipped + 1))
    continue
  fi

  # Common format for PEM in .env is escaped newlines (\n).
  if [[ "$key" == "PRIVATE_KEY" ]]; then
    value="${value//\\n/$'\n'}"
  fi

  echo "- Uploading $key"
  printf '%s' "$value" | CLOUDFLARE_ACCOUNT_ID="$TARGET_ACCOUNT_ID" npx wrangler secret put "$key" --name "$TARGET_WORKER_NAME"
  uploaded=$((uploaded + 1))
done

echo
echo "Completed. Uploaded: $uploaded, Skipped (empty): $skipped"