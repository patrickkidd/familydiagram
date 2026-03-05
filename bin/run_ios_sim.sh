#!/bin/bash

# Launch Family Diagram Personal app in iPhone simulator
# https://nshipster.com/simctl/
#
# Usage:
#   bin/run_ios_sim.sh                  # Default: iPhone 14
#   bin/run_ios_sim.sh "iPhone 15 Pro"  # Custom device name

set -e

DEVICE_NAME="${1:-iPhone 14}"
BUNDLE_ID="com.vedanamedia.familydiagram"

echo "PKS Looking for simulator: $DEVICE_NAME"

# Find the device UUID
UUID=$(xcrun simctl list devices available | grep "$DEVICE_NAME" | grep -E -o -i "([0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12})" | head -1)

if [ -z "$UUID" ]; then
    echo "PKS ERROR: No simulator found matching '$DEVICE_NAME'"
    echo "PKS Available simulators:"
    xcrun simctl list devices available | grep -i "iphone"
    echo ""
    echo "PKS To create one:"
    echo "  xcrun simctl create \"iPhone 14\" com.apple.CoreSimulator.SimDeviceType.iPhone-14"
    exit 1
fi

echo "PKS Found simulator UUID: $UUID"

# Boot if not already booted
BOOTED=$(xcrun simctl list devices | grep "$UUID" | grep "Booted" || true)
if [ -z "$BOOTED" ]; then
    echo "PKS Booting simulator..."
    xcrun simctl boot "$UUID"
fi

# Open Simulator.app
open /Applications/Xcode.app/Contents/Developer/Applications/Simulator.app

# Install the app if build exists
APP_PATH="build/ios/Release-iphonesimulator/Family Diagram.app"
if [ -d "$APP_PATH" ]; then
    echo "PKS Installing app to simulator..."
    xcrun simctl install "$UUID" "$APP_PATH"
else
    echo "PKS WARNING: No simulator build found at $APP_PATH"
    echo "PKS Run 'bin/build.sh ios-sim' first to build for simulator"
fi

echo "PKS Launching app..."
clear
xcrun simctl launch --console-pty "$UUID" "$BUNDLE_ID"
