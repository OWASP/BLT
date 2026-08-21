#!/usr/bin/env bash
# Deploy personal staging Worker + D1 (blt-netguardian.preethampujari395.workers.dev).
# Prerequisite: wrangler logged in to the personal Cloudflare account.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
CFG="$ROOT/wrangler.staging.toml"
BASE="${DEPLOY_URL:-https://blt-netguardian.preethampujari395.workers.dev}"

if [ -f "$HOME/.nvm/nvm.sh" ]; then
  # shellcheck source=/dev/null
  source "$HOME/.nvm/nvm.sh"
  nvm use 20 >/dev/null 2>&1 || nvm use 22 >/dev/null 2>&1 || true
fi

WRANGLER=(npx --yes wrangler@3)

echo "==> Cloudflare account"
"${WRANGLER[@]}" whoami

echo "==> D1 migrations (remote, staging)"
"${WRANGLER[@]}" d1 migrations apply blt-netguardian --remote --config "$CFG"

echo "==> Secrets (pilot org — rotate before any external org)"
printf '%s' '{"triage-token":"org-demo"}' | "${WRANGLER[@]}" secret put NG_ORG_API_TOKENS --config "$CFG"
printf '%s' '{"org-demo:scanner-1:k1":"736563726574"}' | "${WRANGLER[@]}" secret put NG_SENDER_SECRETS --config "$CFG"
printf '%s' '{"org-demo":"bmV0Z3VhcmRpYW4tZGVtby1hZXNnY20ta2V5LTAwMzI="}' | "${WRANGLER[@]}" secret put NG_PAYLOAD_KEYS --config "$CFG"

cp "$ROOT/scripts/install.sh" "$ROOT/public/install.sh"
chmod +x "$ROOT/public/install.sh"

echo "==> Deploy Worker + public/ assets"
REQ_BAK=""
if [ -f requirements.txt ]; then
  REQ_BAK="$(mktemp)"
  mv requirements.txt "$REQ_BAK"
fi
"${WRANGLER[@]}" deploy --config "$CFG"
if [ -n "$REQ_BAK" ]; then
  mv "$REQ_BAK" requirements.txt
fi

echo ""
echo "==> Smoke checks ($BASE)"
curl -sf "$BASE/api/health" | head -c 300 && echo ""
curl -sf -o /dev/null -w "home: %{http_code}\n" "$BASE/"
curl -sf -o /dev/null -w "triage: %{http_code}\n" "$BASE/triage"
curl -sf -o /dev/null -w "get-client: %{http_code}\n" "$BASE/get-client"
echo ""
echo "Home:    $BASE/"
echo "Triage:  $BASE/triage"
echo "Client:  $BASE/get-client"
echo "Docs:    see docs/spec/quickstart.md"
