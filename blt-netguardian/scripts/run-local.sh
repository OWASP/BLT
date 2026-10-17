#!/usr/bin/env bash
# Start NetGuardian local API + triage UI and print smoke-test commands.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PORT=8787
HOST=127.0.0.1

if lsof -iTCP:"$PORT" -sTCP:LISTEN -n -P 2>/dev/null | grep -q .; then
  echo "Port $PORT already in use — assuming serve.py is running."
else
  echo "Starting local server on http://$HOST:$PORT ..."
  python3 local_dev/serve.py &
  sleep 1
fi

if curl -sf "http://$HOST:$PORT/api/health" >/dev/null; then
  echo "OK  GET /api/health"
else
  echo "FAIL  server not responding on http://$HOST:$PORT" >&2
  echo "Run manually: python3 local_dev/serve.py" >&2
  exit 1
fi

cat <<EOF

=== NetGuardian local stack ===
Triage UI:  http://$HOST:$PORT/triage.html
Health:     http://$HOST:$PORT/api/health
Token:      triage-token  (org org-demo)

Smoke (server):
  python3 local_dev/send_finding.py
  python3 scripts/detect_export.py --url https://example.com

Smoke (client — pick ONE):
  # macOS desktop (needs full Xcode from App Store, not only CLT):
  cd client && flutter pub get && flutter run -d macos

  # Chrome (no Xcode):
  cd client && flutter pub get && flutter run -d chrome --web-port=8888

If macOS fails with xcodebuild:
  sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
  sudo xcodebuild -runFirstLaunch

Do NOT open proposal-vinamra/public/triage.html as a file — use the URL above.
EOF
