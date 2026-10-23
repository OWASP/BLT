#!/bin/bash

# Flutter Activity Tracker - Demo Script
# This script demonstrates the Flutter tracker capabilities

echo "=================================="
echo "Flutter Activity Tracker Demo"
echo "=================================="
echo ""

# Check if we're on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "❌ This app requires Linux"
    exit 1
fi

# Check for X11
if [ -z "$DISPLAY" ]; then
    echo "❌ X11 display not found. Are you running in a graphical session?"
    exit 1
fi

# Check for Flutter
if ! command -v flutter &> /dev/null; then
    echo "❌ Flutter not found. Please install Flutter first:"
    echo "   https://flutter.dev/docs/get-started/install/linux"
    exit 1
fi

echo "✅ Linux detected"
echo "✅ X11 display: $DISPLAY"
echo "✅ Flutter found: $(flutter --version | head -n1)"
echo ""

# Check for required libraries
echo "Checking system dependencies..."
MISSING_DEPS=()

if ! ldconfig -p | grep -q libX11.so; then
    MISSING_DEPS+=("libx11-dev")
fi

if ! ldconfig -p | grep -q libXi.so; then
    MISSING_DEPS+=("libxi-dev")
fi

if ! ldconfig -p | grep -q libXtst.so; then
    MISSING_DEPS+=("libxtst-dev")
fi

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo "❌ Missing dependencies: ${MISSING_DEPS[*]}"
    echo ""
    echo "Install with:"
    echo "  sudo apt-get install ${MISSING_DEPS[*]}"
    exit 1
fi

echo "✅ All system dependencies found"
echo ""

# Navigate to flutter_tracker directory
cd "$(dirname "$0")"

# Build native library
echo "Building native library..."
cd linux
if [ ! -f build.sh ]; then
    echo "❌ build.sh not found"
    exit 1
fi

chmod +x build.sh
./build.sh

if [ ! -f libactivity_tracker.so ]; then
    echo "❌ Failed to build libactivity_tracker.so"
    exit 1
fi

echo "✅ Native library built"
cd ..

# Get Flutter dependencies
echo ""
echo "Installing Flutter dependencies..."
flutter pub get

if [ $? -ne 0 ]; then
    echo "❌ Failed to get Flutter dependencies"
    exit 1
fi

echo "✅ Dependencies installed"
echo ""

# Show what will be tracked
echo "=================================="
echo "🔒 Privacy Notice"
echo "=================================="
echo ""
echo "This app will track:"
echo "  ✅ Number of keys pressed (count only)"
echo "  ✅ Mouse movement distance (total pixels)"
echo ""
echo "This app will NOT track:"
echo "  ❌ Actual keystrokes or text"
echo "  ❌ Mouse cursor positions"
echo "  ❌ Window titles or applications"
echo ""
echo "All data stays on your machine unless you"
echo "configure API integration."
echo ""
echo "=================================="
echo ""

# Ask for confirmation
read -p "Start the Activity Tracker? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Demo cancelled"
    exit 0
fi

# Launch the app
echo ""
echo "🚀 Launching Activity Tracker..."
echo ""
echo "The app will show:"
echo "  • Real-time keyboard and mouse counters"
echo "  • Live scrolling chart (updates every second)"
echo "  • Daily summary statistics"
echo ""
echo "Press Ctrl+C to stop"
echo ""

flutter run -d linux

echo ""
echo "Demo completed. Thank you!"
