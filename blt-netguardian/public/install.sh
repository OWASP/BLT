#!/bin/sh
# NetGuardian one-line client: scan from THIS machine, HMAC-sign, POST ingest.
# No signup. The install key signs envelopes; this origin does not fetch targets.
#
#   curl -fsSL https://blt-netguardian.preethampujari395.workers.dev/install.sh | sh -s -- https://your-site.example
set -eu

API="${NG_API:-https://blt-netguardian.preethampujari395.workers.dev}"
# Public demo HMAC + AES key (same as Worker NG_SENDER_SECRETS / NG_PAYLOAD_KEYS).
INSTALL_SECRET_HEX="${NG_SECRET_HEX:-736563726574}"
INSTALL_PAYLOAD_KEY_B64="${NG_PAYLOAD_KEY_B64:-bmV0Z3VhcmRpYW4tZGVtby1hZXNnY20ta2V5LTAwMzI=}"
SRC_TARBALL="${NG_SRC_TARBALL:-https://gitlab.com/Pritz395/blt-netguardian/-/archive/main/blt-netguardian-main.tar.gz}"

TARGET="${1:-}"

usage() {
  echo "Scan a URL from your machine (browser-like GET), sign, and send findings." >&2
  echo "" >&2
  echo "  curl -fsSL ${API}/install.sh | sh -s -- https://your-site.example" >&2
  echo "" >&2
  echo "Pass a site you are allowed to test. Deeper/frequent scans need the owner's permission." >&2
  exit 1
}

if [ -z "$TARGET" ] || [ "$TARGET" = "-h" ] || [ "$TARGET" = "--help" ]; then
  usage
fi

case "$TARGET" in
  http://*|https://*) ;;
  *)
    echo "target must be an http(s) URL, got: $TARGET" >&2
    exit 1
    ;;
esac

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required on PATH" >&2
  exit 1
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required on PATH" >&2
  exit 1
fi
if ! command -v tar >/dev/null 2>&1; then
  echo "tar is required on PATH" >&2
  exit 1
fi

WORKDIR=$(mktemp -d)
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT INT HUP

echo "==> NetGuardian client (local header scan → signed ingest)"
echo "    target: $TARGET"
echo "    api:    $API"
echo "    fetch is from this computer, not from $API"

curl -fsSL "$SRC_TARBALL" -o "$WORKDIR/ng.tgz"
tar -xzf "$WORKDIR/ng.tgz" -C "$WORKDIR"
ROOT=$(find "$WORKDIR" -maxdepth 1 -type d -name 'blt-netguardian-*' | head -n 1)
if [ -z "$ROOT" ] || [ ! -f "$ROOT/scripts/detect_export.py" ]; then
  echo "failed to unpack scanner sources" >&2
  exit 1
fi

python3 "$ROOT/scripts/detect_export.py" \
  --url "$TARGET" \
  --base-url "$API" \
  --secret-hex "$INSTALL_SECRET_HEX" \
  --payload-key-b64 "$INSTALL_PAYLOAD_KEY_B64"

echo ""
echo "Review findings: ${API}/triage"
