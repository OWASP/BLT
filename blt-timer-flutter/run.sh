#!/bin/bash

echo "Building Activity Tracker Flutter App..."

# Build the native library first
echo "Building native tracker library..."
cd linux
chmod +x build.sh
./build.sh
cd ..

# Get Flutter dependencies
echo "Getting Flutter dependencies..."
flutter pub get

# Run the app
echo "Starting the app..."
flutter run -d linux
