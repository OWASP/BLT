#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8787}"
PUBLIC_PATH="${PUBLIC_PATH:-/health}"
PROTECTED_PATH="${PROTECTED_PATH:-/routes}"
PUBLIC_BLT_API_KEY="f5537412b459790f9fa1cc47b862b9c7016471957178dc9b161d59355b6fd051"
API_KEY="${API_KEY:-$PUBLIC_BLT_API_KEY}"

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

echo "BLT API static key smoke test"
echo "BASE_URL=${BASE_URL}"
echo "PROTECTED_PATH=${PROTECTED_PATH}"
echo "API key: ${API_KEY}"
echo

request "Public route without API key" "$PUBLIC_PATH" "200"
request "Protected route without API key" "$PROTECTED_PATH" "401"
request "Protected route with wrong API key" "$PROTECTED_PATH" "401" -H "X-BLT-API-Key: wrong-key"
request "Protected route with correct API key" "$PROTECTED_PATH" "200" -H "X-BLT-API-Key: ${API_KEY}"

exit "$failures"
