#!/usr/bin/env bash
# Build and run SafeCloak Chat locally.
#
#   ./run.sh          build (incremental) and launch the app
#   ./run.sh clean    clear the build cache (removes build/)
#   ./run.sh rebuild  clear the cache, then build and launch
#   ./run.sh test     build and run the headless backend tests
set -euo pipefail
cd "$(dirname "$0")"

build() {
    cmake -B build -DCMAKE_BUILD_TYPE=Release
    cmake --build build -j"$(nproc)"
}

case "${1:-run}" in
    clean)
        rm -rf build
        echo "Build cache cleared."
        ;;
    rebuild)
        rm -rf build
        build
        exec ./build/safecloak
        ;;
    test)
        build
        QT_QPA_PLATFORM=offscreen exec ./build/safecloak-tests
        ;;
    run)
        build
        exec ./build/safecloak
        ;;
    *)
        echo "Usage: $0 [run|clean|rebuild|test]" >&2
        exit 2
        ;;
esac
