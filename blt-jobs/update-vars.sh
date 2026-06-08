#!/usr/bin/env bash
set -euo pipefail

WORKER_NAME="blt-jobs"
ENV_FILE="${ENV_FILE:-.env.production}"
WRANGLER_CONFIG="${WRANGLER_CONFIG:-wrangler.toml}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

if [[ ! -f "$WRANGLER_CONFIG" ]]; then
  echo "Missing $WRANGLER_CONFIG" >&2
  exit 1
fi

if [[ -n "${WRANGLER:-}" ]]; then
  read -r -a WRANGLER_CMD <<< "$WRANGLER"
elif [[ -x "./node_modules/.bin/wrangler" ]]; then
  WRANGLER_CMD=(./node_modules/.bin/wrangler)
elif command -v wrangler >/dev/null 2>&1; then
  WRANGLER_CMD=(wrangler)
else
  WRANGLER_CMD=(npx wrangler@4)
fi

echo "Checking Cloudflare authentication..."
"${WRANGLER_CMD[@]}" whoami

echo "Checking that Worker '$WORKER_NAME' exists..."
if "${WRANGLER_CMD[@]}" versions list --name "$WORKER_NAME" --config "$WRANGLER_CONFIG" >/dev/null 2>&1; then
  :
elif "${WRANGLER_CMD[@]}" deployments list --name "$WORKER_NAME" --config "$WRANGLER_CONFIG" >/dev/null 2>&1; then
  :
else
  echo "Could not find Worker '$WORKER_NAME' or could not verify it exists. No variables were uploaded." >&2
  exit 1
fi

uploaded=0
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%$'\r'}"

  if [[ -z "$line" || "$line" == \#* ]]; then
    continue
  fi

  if [[ "$line" != *=* ]]; then
    echo "Skipping malformed line in $ENV_FILE" >&2
    continue
  fi

  key="${line%%=*}"
  value="${line#*=}"

  if [[ ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    echo "Skipping invalid variable name '$key'" >&2
    continue
  fi

  if [[ -z "$value" ]]; then
    echo "Skipping $key because it has no value."
    continue
  fi

  echo "Uploading $key..."
  printf '%s' "$value" | "${WRANGLER_CMD[@]}" secret put "$key" --name "$WORKER_NAME" --config "$WRANGLER_CONFIG"
  uploaded=$((uploaded + 1))
done < "$ENV_FILE"

echo "Uploaded $uploaded variables to '$WORKER_NAME'."
