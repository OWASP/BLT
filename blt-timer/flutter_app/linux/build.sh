#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Building native activity tracker library (clicks + scroll)..."
gcc -shared -fPIC -o libactivity_tracker.so "$SCRIPT_DIR/activity_tracker.c" \
    -lX11 -lXi -lXtst -lm
echo "Built libactivity_tracker.so at $SCRIPT_DIR/libactivity_tracker.so"
