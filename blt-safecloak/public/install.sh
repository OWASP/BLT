#!/usr/bin/env bash
# SafeCloak installer - encrypted LAN chat desktop client (Qt 6).
#
#   curl -fsSL https://<this-site>/install.sh | bash
#
# Builds the client from source: a sparse, blob-less clone of the BLT monorepo on
# git.owaspblt.org that fetches only blt-safecloak/client (about 2 MB), or a local
# checkout when SAFECLOAK_SOURCE_DIR points at one (the blt-safecloak folder or its
# client/ folder). There are no prebuilt downloads: the old CI artifacts are gone
# and the forge has no release files yet.
# Installs the CLI launcher to ~/.local/bin/safecloak unless SAFECLOAK_BIN_DIR
# is set. On macOS, the app bundle is installed to ~/Applications/SafeCloak.app
# unless SAFECLOAK_APP_DIR is set.
set -euo pipefail

REPO_URL="${SAFECLOAK_REPO_URL:-https://git.owaspblt.org/BLT.git}"
REPO_FOLDER="blt-safecloak"
OS_NAME="$(uname -s)"
ARCH_NAME="$(uname -m)"
BIN_DIR="${SAFECLOAK_BIN_DIR:-$HOME/.local/bin}"
BIN_PATH="$BIN_DIR/safecloak"

info() { printf '\033[1;31m[safecloak]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[safecloak] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

mkdir -p "$BIN_DIR"

build_jobs() {
    if command -v nproc >/dev/null 2>&1; then
        nproc
    elif command -v sysctl >/dev/null 2>&1; then
        sysctl -n hw.logicalcpu
    else
        printf '2\n'
    fi
}

platform_label() {
    case "$OS_NAME:$ARCH_NAME" in
        Linux:x86_64|Linux:amd64) printf 'Linux x86_64\n' ;;
        Darwin:arm64|Darwin:aarch64) printf 'macOS arm64\n' ;;
        Darwin:x86_64) printf 'macOS x86_64\n' ;;
        *) printf '%s %s\n' "$OS_NAME" "$ARCH_NAME" ;;
    esac
}

install_macos_app() {
    local app="$1"
    local app_dir="${SAFECLOAK_APP_DIR:-$HOME/Applications}"
    local dest="$app_dir/SafeCloak.app"
    [ -d "$app" ] || fail "Missing SafeCloak.app in the build."
    [ -x "$app/Contents/MacOS/SafeCloak" ] ||
        fail "SafeCloak.app is missing its executable."

    mkdir -p "$app_dir"
    rm -rf "$dest"
    if command -v ditto >/dev/null 2>&1; then
        ditto "$app" "$dest"
    else
        cp -R "$app" "$dest"
    fi
    ln -sf "$dest/Contents/MacOS/SafeCloak" "$BIN_PATH"
    info "Installed app bundle: $dest"
}

require_tool() {
    local tool="$1"
    local hint="$2"
    command -v "$tool" >/dev/null 2>&1 || fail "'$tool' is required to build from source. $hint"
}

cmake_configure_args() {
    printf '%s\0' -DCMAKE_BUILD_TYPE=Release -DSAFECLOAK_BUILD_TESTS=OFF
    if [ "$OS_NAME" = "Darwin" ]; then
        command -v brew >/dev/null 2>&1 ||
            fail "Homebrew is required for a macOS source build. Install dependencies with: brew install cmake qt openssl@3"

        local qt_prefix openssl_prefix
        qt_prefix="$(brew --prefix qt 2>/dev/null || true)"
        openssl_prefix="$(brew --prefix openssl@3 2>/dev/null || true)"
        [ -n "$qt_prefix" ] ||
            fail "Qt 6 is required. Install dependencies with: brew install cmake qt openssl@3"
        [ -n "$openssl_prefix" ] ||
            fail "OpenSSL 3 is required. Install dependencies with: brew install cmake qt openssl@3"
        printf '%s\0' "-DCMAKE_PREFIX_PATH=$qt_prefix" "-DOPENSSL_ROOT_DIR=$openssl_prefix"
    fi
}

install_built_client() {
    local build_dir="$1"
    if [ "$OS_NAME" = "Darwin" ] && [ -d "$build_dir/SafeCloak.app" ]; then
        install_macos_app "$build_dir/SafeCloak.app"
    elif [ -x "$build_dir/safecloak" ]; then
        cp "$build_dir/safecloak" "$BIN_PATH"
    else
        fail "Build finished, but no SafeCloak executable was found."
    fi
}

# Set CLIENT_DIR to the client sources (the folder with CMakeLists.txt).
CLIENT_DIR=""
CLONE_DIR=""
cleanup() { [ -z "$CLONE_DIR" ] || rm -rf "$CLONE_DIR"; [ -z "${BUILD_DIR:-}" ] || rm -rf "$BUILD_DIR"; }
trap cleanup EXIT

client_source() {
    local dir="${SAFECLOAK_SOURCE_DIR:-}"
    if [ -n "$dir" ]; then
        for candidate in "$dir" "$dir/client" "$dir/$REPO_FOLDER/client"; do
            if [ -f "$candidate/CMakeLists.txt" ]; then
                CLIENT_DIR="$candidate"
                return 0
            fi
        done
        fail "SAFECLOAK_SOURCE_DIR=$dir has no SafeCloak client sources (client/CMakeLists.txt)."
    fi

    CLONE_DIR="$(mktemp -d)"
    info "Fetching $REPO_FOLDER/client from $REPO_URL..."
    if git clone --quiet --depth 1 --filter=blob:none --sparse "$REPO_URL" "$CLONE_DIR/src" &&
        git -C "$CLONE_DIR/src" sparse-checkout set "$REPO_FOLDER/client"; then
        :
    else
        # Older git without sparse-checkout or partial clone: a shallow full clone.
        rm -rf "$CLONE_DIR/src"
        git clone --quiet --depth 1 "$REPO_URL" "$CLONE_DIR/src" ||
            fail "Could not clone $REPO_URL."
    fi
    CLIENT_DIR="$CLONE_DIR/src/$REPO_FOLDER/client"
    [ -f "$CLIENT_DIR/CMakeLists.txt" ] || fail "The clone has no $REPO_FOLDER/client/CMakeLists.txt."
}

build_from_source() {
    info "Building SafeCloak from source..."
    case "$OS_NAME" in
        Linux)
            require_tool git "On Debian/Ubuntu: sudo apt install build-essential cmake git qt6-base-dev libssl-dev libxkbcommon-dev libxkbcommon-x11-dev openssl"
            require_tool cmake "On Debian/Ubuntu: sudo apt install cmake"
            require_tool g++ "On Debian/Ubuntu: sudo apt install build-essential"
            require_tool make "On Debian/Ubuntu: sudo apt install build-essential"
            require_tool openssl "On Debian/Ubuntu: sudo apt install openssl"
            ;;
        Darwin)
            require_tool git "Install Apple's command line tools with: xcode-select --install"
            require_tool cmake "Install dependencies with: brew install cmake qt openssl@3"
            require_tool clang++ "Install Apple's command line tools with: xcode-select --install"
            require_tool make "Install Apple's command line tools with: xcode-select --install"
            require_tool openssl "Install dependencies with: brew install cmake qt openssl@3"
            ;;
        *)
            fail "This installer supports Linux and macOS. Detected: $(platform_label)"
            ;;
    esac

    client_source

    local args=()
    while IFS= read -r -d '' arg; do
        args+=("$arg")
    done < <(cmake_configure_args)

    BUILD_DIR="$(mktemp -d)"
    cmake -S "$CLIENT_DIR" -B "$BUILD_DIR" "${args[@]}" ||
        fail "CMake configure failed. Make sure Qt 6 and OpenSSL development headers are installed."
    cmake --build "$BUILD_DIR" --parallel "$(build_jobs)"
    install_built_client "$BUILD_DIR"
}

build_from_source

info "Installed launcher: $BIN_PATH"
case ":$PATH:" in
    *":$BIN_DIR:"*) info "Run it with: safecloak" ;;
    *) info "Note: $BIN_DIR is not on your PATH. Run it with: $BIN_PATH" ;;
esac
