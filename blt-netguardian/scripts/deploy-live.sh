#!/usr/bin/env bash
# Deploy BLT-NetGuardian to Cloudflare (Worker + D1 + secrets + static assets).
# Prerequisite: wrangler logged in — run: npx wrangler login
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f "$HOME/.nvm/nvm.sh" ]; then
  # shellcheck source=/dev/null
  source "$HOME/.nvm/nvm.sh"
  nvm use 20 >/dev/null 2>&1 || nvm use 22 >/dev/null 2>&1 || true
fi

WRANGLER=(npx --yes wrangler@3)

echo "==> Cloudflare account"
"${WRANGLER[@]}" whoami

echo "==> D1 migrations (remote)"
"${WRANGLER[@]}" d1 migrations apply blt-netguardian --remote

echo "==> Secrets (pilot org — rotate before any external org)"
# Same shape as local_dev/serve.py so triage + ingest work immediately after deploy.
printf '%s' '{"triage-token":"org-demo"}' | "${WRANGLER[@]}" secret put NG_ORG_API_TOKENS
printf '%s' '{"org-demo:scanner-1:k1":"736563726574"}' | "${WRANGLER[@]}" secret put NG_SENDER_SECRETS
printf '%s' '{"org-demo":"bmV0Z3VhcmRpYW4tZGVtby1hZXNnY20ta2V5LTAwMzI="}' | "${WRANGLER[@]}" secret put NG_PAYLOAD_KEYS
printf '%s' 'https://blt-netguardian.preethampujari395.workers.dev,http://localhost:8888,http://127.0.0.1:8888' | "${WRANGLER[@]}" secret put CORS_ALLOWED_ORIGINS
# AUTHENTICATE_READ_ENDPOINTS is a non-secret flag — set via wrangler.toml [vars]

# BLT-API — set if convert-to-issue should hit real API (optional for first boot)
if [ -n "${BLT_API_BASE_URL:-}" ]; then
  printf '%s' "$BLT_API_BASE_URL" | "${WRANGLER[@]}" secret put BLT_API_BASE_URL
fi
if [ -n "${BLT_API_KEY:-}" ]; then
  printf '%s' "$BLT_API_KEY" | "${WRANGLER[@]}" secret put BLT_API_KEY
fi

echo "==> Flutter web client → public/client/"
if command -v flutter >/dev/null 2>&1; then
  (
    cd "$ROOT/client"
    flutter build web --release --base-href /client/
  )
  rm -rf "$ROOT/public/client"
  mkdir -p "$ROOT/public/client"
  cp -R "$ROOT/client/build/web/." "$ROOT/public/client/"
else
  echo "    flutter not on PATH — deploying existing public/client if present"
fi

echo "==> Deploy Worker + public/ assets"
# Wrangler rejects pytest pins in requirements.txt; Workers uses aesgcm_pure, not cryptography.
REQ_BAK=""
if [ -f requirements.txt ]; then
  REQ_BAK="$(mktemp)"
  mv requirements.txt "$REQ_BAK"
fi
"${WRANGLER[@]}" deploy
if [ -n "$REQ_BAK" ]; then
  mv "$REQ_BAK" requirements.txt
fi

BASE="${DEPLOY_URL:-https://blt-netguardian.preethampujari395.workers.dev}"
echo ""
echo "==> Smoke checks"
curl -sf "$BASE/api/health" | head -c 200 && echo ""
curl -sf -o /dev/null -w "triage.html: %{http_code}\n" "$BASE/triage.html"
echo ""
echo "Client: $BASE/client/"
echo "Triage: $BASE/triage"
echo "Token:  triage-token"
