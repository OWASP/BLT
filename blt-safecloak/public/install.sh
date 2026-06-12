#!/usr/bin/env bash
# SafeCloak Chat installer — encrypted LAN chat desktop client (Qt 6).
#
#   curl -fsSL https://<this-site>/install.sh | bash
#
# Tries the prebuilt Linux binary from GitLab CI first; if it can't run on
# this machine (e.g. missing Qt 6 runtime) it builds from source instead.
# Installs to ~/.local/bin/safecloak (override with SAFECLOAK_BIN_DIR).
set -euo pipefail

REPO_URL="https://gitlab.com/owasp-blt/blt-safecloak"
ARTIFACT_URL="$REPO_URL/-/jobs/artifacts/main/raw/client/build/safecloak?job=build-client"
BIN_DIR="${SAFECLOAK_BIN_DIR:-$HOME/.local/bin}"
BIN_PATH="$BIN_DIR/safecloak"

info() { printf '\033[1;31m[safecloak]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[safecloak] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(uname -s)" = "Linux" ] || fail "This installer currently supports Linux only."
command -v curl >/dev/null 2>&1 || fail "curl is required."
mkdir -p "$BIN_DIR"

try_prebuilt() {
    info "Downloading the latest prebuilt binary from GitLab CI..."
    local tmp
    tmp=$(mktemp)
    if ! curl -fsSL -o "$tmp" "$ARTIFACT_URL"; then
        rm -f "$tmp"
        info "No prebuilt binary available."
        return 1
    fi
    chmod +x "$tmp"
    if ldd "$tmp" 2>/dev/null | grep -q "not found"; then
        rm -f "$tmp"
        info "Prebuilt binary needs libraries this system doesn't have" \
             "(install the Qt 6 runtime, e.g. 'sudo apt install libqt6widgets6 libqt6network6')."
        return 1
    fi
    mv "$tmp" "$BIN_PATH"
}

build_from_source() {
    info "Building from source instead..."
    local tool
    for tool in git cmake g++ make openssl; do
        command -v "$tool" >/dev/null 2>&1 ||
            fail "'$tool' is required to build from source. On Debian/Ubuntu: sudo apt install build-essential cmake git qt6-base-dev openssl"
    done
    local src
    src=$(mktemp -d)
    trap 'rm -rf "$src"' EXIT
    git clone --quiet --depth 1 "$REPO_URL.git" "$src"
    cmake -S "$src/client" -B "$src/client/build" -DCMAKE_BUILD_TYPE=Release \
          -DSAFECLOAK_BUILD_TESTS=OFF ||
        fail "CMake configure failed — is Qt 6 installed? On Debian/Ubuntu: sudo apt install qt6-base-dev"
    cmake --build "$src/client/build" -j"$(nproc)"
    cp "$src/client/build/safecloak" "$BIN_PATH"
}

try_prebuilt || build_from_source

info "Installed: $BIN_PATH"
case ":$PATH:" in
    *":$BIN_DIR:"*) info "Run it with: safecloak" ;;
    *) info "Note: $BIN_DIR is not on your PATH. Run it with: $BIN_PATH" ;;
esac
