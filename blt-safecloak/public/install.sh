#!/usr/bin/env bash
# SafeCloak installer - encrypted LAN chat desktop client (Qt 6).
#
#   curl -fsSL https://<this-site>/install.sh | bash
#
# Tries the latest matching GitLab CI artifact first. If no artifact exists for
# this platform, or it cannot be installed, it builds from source instead.
# Installs the CLI launcher to ~/.local/bin/safecloak unless SAFECLOAK_BIN_DIR
# is set. On macOS, the app bundle is installed to ~/Applications/SafeCloak.app
# unless SAFECLOAK_APP_DIR is set.
set -euo pipefail

REPO_URL="https://gitlab.com/owasp-blt/blt-safecloak"
ARTIFACT_BASE="$REPO_URL/-/jobs/artifacts/main/raw"
OS_NAME="$(uname -s)"
ARCH_NAME="$(uname -m)"
BIN_DIR="${SAFECLOAK_BIN_DIR:-$HOME/.local/bin}"
BIN_PATH="$BIN_DIR/safecloak"

info() { printf '\033[1;31m[safecloak]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[safecloak] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

command -v curl >/dev/null 2>&1 || fail "curl is required."
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

prebuilt_url() {
    case "$OS_NAME:$ARCH_NAME" in
        Linux:x86_64|Linux:amd64)
            printf '%s/client/build/safecloak?job=build-client\n' "$ARTIFACT_BASE"
            ;;
        Darwin:arm64|Darwin:aarch64)
            printf '%s/client/dist/safecloak-macos-arm64.zip?job=build-client-macos-arm64\n' "$ARTIFACT_BASE"
            ;;
        *)
            return 1
            ;;
    esac
}

install_macos_app() {
    local app="$1"
    local app_dir="${SAFECLOAK_APP_DIR:-$HOME/Applications}"
    local dest="$app_dir/SafeCloak.app"
    [ -d "$app" ] || fail "Missing SafeCloak.app in downloaded artifact."
    [ -x "$app/Contents/MacOS/SafeCloak" ] ||
        fail "Downloaded SafeCloak.app is missing its executable."

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

try_prebuilt_linux() {
    local url="$1"
    local tmp
    tmp="$(mktemp)"

    if ! curl -fsSL -o "$tmp" "$url"; then
        rm -f "$tmp"
        info "No prebuilt Linux binary available."
        return 1
    fi

    chmod +x "$tmp"
    if command -v ldd >/dev/null 2>&1 && ldd "$tmp" 2>/dev/null | grep -q "not found"; then
        rm -f "$tmp"
        info "Prebuilt binary needs libraries this system does not have" \
             "(install the Qt 6 runtime, e.g. 'sudo apt install libqt6widgets6 libqt6network6')."
        return 1
    fi

    mv "$tmp" "$BIN_PATH"
}

try_prebuilt_macos() {
    local url="$1"
    command -v unzip >/dev/null 2>&1 || {
        info "unzip is required to install the prebuilt macOS app."
        return 1
    }

    local tmp extract app
    tmp="$(mktemp)"
    extract="$(mktemp -d)"

    if ! curl -fsSL -o "$tmp" "$url"; then
        rm -rf "$tmp" "$extract"
        info "No prebuilt macOS app available."
        return 1
    fi

    if ! unzip -q "$tmp" -d "$extract"; then
        rm -rf "$tmp" "$extract"
        info "Downloaded macOS artifact could not be unpacked."
        return 1
    fi

    app="$extract/SafeCloak.app"
    if [ ! -d "$app" ]; then
        app="$(find "$extract" -maxdepth 3 -type d -name 'SafeCloak.app' | head -n 1)"
    fi
    if [ -z "$app" ] || [ ! -d "$app" ]; then
        rm -rf "$tmp" "$extract"
        info "Downloaded macOS artifact did not contain SafeCloak.app."
        return 1
    fi
    install_macos_app "$app"
    rm -rf "$tmp" "$extract"
}

try_prebuilt() {
    local url
    if ! url="$(prebuilt_url)"; then
        info "No prebuilt artifact is configured for $(platform_label)."
        return 1
    fi

    info "Downloading the latest prebuilt $(platform_label) build from GitLab CI..."
    case "$OS_NAME" in
        Linux) try_prebuilt_linux "$url" ;;
        Darwin) try_prebuilt_macos "$url" ;;
        *) return 1 ;;
    esac
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

build_from_source() {
    info "Building from source instead..."
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

    local src
    src="$(mktemp -d)"
    trap 'rm -rf "$src"' EXIT
    git clone --quiet --depth 1 "$REPO_URL.git" "$src"

    local args=()
    while IFS= read -r -d '' arg; do
        args+=("$arg")
    done < <(cmake_configure_args)

    cmake -S "$src/client" -B "$src/client/build" "${args[@]}" ||
        fail "CMake configure failed. Make sure Qt 6 and OpenSSL development headers are installed."
    cmake --build "$src/client/build" --parallel "$(build_jobs)"
    install_built_client "$src/client/build"
}

try_prebuilt || build_from_source

info "Installed launcher: $BIN_PATH"
case ":$PATH:" in
    *":$BIN_DIR:"*) info "Run it with: safecloak" ;;
    *) info "Note: $BIN_DIR is not on your PATH. Run it with: $BIN_PATH" ;;
esac
