#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

BASE_URL="${BASE_URL:-http://localhost:8787}"
PUBLIC_PATH="${PUBLIC_PATH:-/health}"
PROTECTED_PATH="${PROTECTED_PATH:-/routes}"

read_env_value() {
  local file="$1"
  local key="$2"

  [[ -f "$file" ]] || return 0

  awk -F= -v key="$key" '
    /^[[:space:]]*#/ || /^[[:space:]]*$/ { next }
    {
      name = $1
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", name)
      if (name == key) {
        value = substr($0, index($0, "=") + 1)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
        if (value ~ /^".*"$/ || value ~ /^\047.*\047$/) {
          value = substr(value, 2, length(value) - 2)
        }
        print value
        exit
      }
    }
  ' "$file"
}

resolve_api_key() {
  if [[ -n "${BLT_API_KEY:-}" ]]; then
    API_KEY="$BLT_API_KEY"
    API_KEY_SOURCE="BLT_API_KEY environment variable"
    return
  fi

  if [[ -n "${API_KEY:-}" ]]; then
    API_KEY="$API_KEY"
    API_KEY_SOURCE="API_KEY environment variable"
    return
  fi

  local env_files=()
  if [[ -n "${API_KEY_ENV_FILE:-}" ]]; then
    env_files=("$API_KEY_ENV_FILE")
  else
    env_files=("$REPO_ROOT/.dev.vars" "$REPO_ROOT/.env.local" "$REPO_ROOT/.env")
  fi

  local env_file value
  for env_file in "${env_files[@]}"; do
    value="$(read_env_value "$env_file" "BLT_API_KEY")"
    if [[ -n "$value" ]]; then
      API_KEY="$value"
      API_KEY_SOURCE="$env_file"
      return
    fi
  done

  echo "Error: BLT_API_KEY was not found." >&2
  echo "Set BLT_API_KEY in your shell, API_KEY in your shell, or BLT_API_KEY in .dev.vars/.env.local/.env." >&2
  exit 2
}

request() {
  local label="$1"
  local path="$2"
  local expected_status="$3"
  shift 3

  local body_file
  body_file="$(mktemp)"
  local status
  local curl_exit

  set +e
  status="$(curl -sS -o "$body_file" -w "%{http_code}" "$@" "${BASE_URL}${path}")"
  curl_exit=$?
  set -e

  echo "== ${label} =="
  echo "GET ${BASE_URL}${path}"
  echo "HTTP ${status}"
  cat "$body_file"
  echo
  if [[ "$curl_exit" -eq 0 && "$status" == "$expected_status" ]]; then
    echo "PASS expected HTTP ${expected_status}"
  else
    echo "FAIL expected HTTP ${expected_status}"
    failures=1
  fi
  echo
  rm -f "$body_file"
}

failures=0
API_KEY=""
API_KEY_SOURCE=""
resolve_api_key

echo "BLT API static key smoke test"
echo "BASE_URL=${BASE_URL}"
echo "PROTECTED_PATH=${PROTECTED_PATH}"
echo "API key source: ${API_KEY_SOURCE}"
echo

request "Public route without API key" "$PUBLIC_PATH" "200"
request "Protected route without API key" "$PROTECTED_PATH" "401"
request "Protected route with wrong API key" "$PROTECTED_PATH" "401" -H "X-BLT-API-Key: wrong-key"
request "Protected route with correct API key" "$PROTECTED_PATH" "200" -H "X-BLT-API-Key: ${API_KEY}"

exit "$failures"
