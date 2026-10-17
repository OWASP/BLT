#!/usr/bin/env bash
# Package the macOS SafeCloak app bundle for GitLab CI.
set -euo pipefail

BUILD_DIR="${1:-client/build}"
DIST_DIR="${2:-client/dist}"
APP_PATH="$BUILD_DIR/SafeCloak.app"
APP_EXEC="$APP_PATH/Contents/MacOS/SafeCloak"
ARCHIVE="$DIST_DIR/safecloak-macos-arm64.zip"

fail() { printf '[safecloak] ERROR: %s\n' "$*" >&2; exit 1; }
info() { printf '[safecloak] %s\n' "$*"; }

[ "$(uname -s)" = "Darwin" ] || fail "macOS packaging must run on Darwin."
[ -d "$APP_PATH" ] || fail "Missing app bundle: $APP_PATH"
[ -x "$APP_EXEC" ] || fail "Missing app executable: $APP_EXEC"

QT_PREFIX="${QT_PREFIX:-}"
if [ -z "$QT_PREFIX" ] && command -v brew >/dev/null 2>&1; then
    QT_PREFIX="$(brew --prefix qt 2>/dev/null || true)"
fi

MACDEPLOYQT="${MACDEPLOYQT:-}"
if [ -z "$MACDEPLOYQT" ] && [ -n "$QT_PREFIX" ]; then
    MACDEPLOYQT="$QT_PREFIX/bin/macdeployqt"
fi

[ -x "$MACDEPLOYQT" ] || fail "macdeployqt was not found. Install Qt with Homebrew or set MACDEPLOYQT."

info "Bundling Qt frameworks with macdeployqt..."
"$MACDEPLOYQT" "$APP_PATH" -verbose=1

OPENSSL_PREFIX="${OPENSSL_ROOT_DIR:-${OPENSSL_PREFIX:-}}"
if [ -z "$OPENSSL_PREFIX" ] && command -v brew >/dev/null 2>&1; then
    OPENSSL_PREFIX="$(brew --prefix openssl@3 2>/dev/null || true)"
fi

bundle_dylib() {
    local ref="$1"
    local target="$2"
    local source="$ref"

    case "$ref" in
        @rpath/*|@loader_path/*|@executable_path/*)
            [ -n "$OPENSSL_PREFIX" ] || return 0
            source="$OPENSSL_PREFIX/lib/$(basename "$ref")"
            ;;
    esac

    [ -f "$source" ] || return 0

    local frameworks_dir="$APP_PATH/Contents/Frameworks"
    local name dest loader_ref
    name="$(basename "$source")"
    dest="$frameworks_dir/$name"
    loader_ref="@executable_path/../Frameworks/$name"

    mkdir -p "$frameworks_dir"
    if [ ! -f "$dest" ]; then
        cp "$source" "$dest"
        chmod u+w "$dest"
    fi

    install_name_tool -change "$ref" "$loader_ref" "$target"
    install_name_tool -id "$loader_ref" "$dest" 2>/dev/null || true
}

info "Bundling OpenSSL runtime libraries..."
while IFS= read -r lib; do
    bundle_dylib "$lib" "$APP_EXEC"
done < <(otool -L "$APP_EXEC" | awk '/openssl|libcrypto|libssl/ {print $1}')

if command -v codesign >/dev/null 2>&1; then
    info "Applying ad-hoc signature..."
    codesign --force --deep --sign - "$APP_PATH"
fi

mkdir -p "$DIST_DIR"
rm -f "$ARCHIVE"
ditto -c -k --keepParent "$APP_PATH" "$ARCHIVE"
info "Created $ARCHIVE"
