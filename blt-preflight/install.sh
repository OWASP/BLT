#!/usr/bin/env bash
# install.sh - Installer for BLT-Preflight that sets up the 'pf' command.
#
# Usage:
#   ./install.sh            # install for the current user (default)
#   ./install.sh --system   # install system-wide (requires sudo)
#   ./install.sh --uninstall
#
# After running this script the 'pf' command becomes available in your shell.

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIP_FLAGS="--editable"

print_usage() {
    echo "Usage: $0 [--system] [--uninstall]"
    echo ""
    echo "Options:"
    echo "  --system      Install system-wide (requires sudo)"
    echo "  --uninstall   Remove the installed 'pf' command"
    echo "  -h, --help    Show this help message"
}

install_pf() {
    local pip_args=("install" "${PIP_FLAGS}" "${REPO_DIR}")

    if [ "$SYSTEM_INSTALL" = "true" ]; then
        echo "Installing BLT-Preflight system-wide…"
        sudo pip3 "${pip_args[@]}"
    else
        echo "Installing BLT-Preflight for current user…"
        pip3 "${pip_args[@]}" --user
        # Ensure the user bin directory is on PATH
        USER_BIN="$(python3 -m site --user-base)/bin"
        if [[ ":$PATH:" != *":${USER_BIN}:"* ]]; then
            echo ""
            echo "NOTE: Add the following line to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
            echo "  export PATH=\"${USER_BIN}:\$PATH\""
            echo ""
        fi
    fi

    echo ""
    echo "✅ Installation complete.  Run 'pf --help' to get started."
    echo ""
    echo "Quick-start:"
    echo "  pf                   # check staged files (pre-commit style)"
    echo "  pf check             # same as above"
    echo "  pf advise --help     # generate a full advisory report"
    echo "  pf dashboard         # show the maintainer dashboard"
}

uninstall_pf() {
    echo "Uninstalling BLT-Preflight…"
    if [ "$SYSTEM_INSTALL" = "true" ]; then
        sudo pip3 uninstall -y blt-preflight
    else
        pip3 uninstall -y blt-preflight
    fi
    echo "✅ Uninstalled."
}

# ── argument parsing ──────────────────────────────────────────────────────────
SYSTEM_INSTALL="false"
ACTION="install"

for arg in "$@"; do
    case "$arg" in
        --system)    SYSTEM_INSTALL="true" ;;
        --uninstall) ACTION="uninstall" ;;
        -h|--help)   print_usage; exit 0 ;;
        *)           echo "Unknown option: $arg"; print_usage; exit 1 ;;
    esac
done

# ── pre-flight checks ─────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required but not found in PATH." >&2
    exit 1
fi

if ! command -v pip3 &>/dev/null; then
    echo "Error: pip3 is required but not found in PATH." >&2
    exit 1
fi

# ── run ───────────────────────────────────────────────────────────────────────
if [ "$ACTION" = "install" ]; then
    install_pf
else
    uninstall_pf
fi
