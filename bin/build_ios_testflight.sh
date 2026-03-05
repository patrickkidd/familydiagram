#!/bin/bash

# Export an iOS archive and upload to TestFlight via App Store Connect API.
#
# Prerequisites:
#   - Run `bin/build.sh ios-release` first to create the archive
#   - Set environment variables (see bin/build_env.sh and doc/IOS_BUILD_GUIDE.md)
#
# Usage:
#   bin/build_ios_testflight.sh
#   FD_IOS_BUILD_DIR=path/to/dir bin/build_ios_testflight.sh

set -e

BIN="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT=$(cd "$BIN/.."; pwd)

FD_IOS_BUILD_DIR="${FD_IOS_BUILD_DIR:-$ROOT/build/ios/Release}"
ARCHIVE_PATH="$FD_IOS_BUILD_DIR/Family Diagram.xcarchive"
EXPORT_PATH="$FD_IOS_BUILD_DIR/Export"
EXPORT_OPTIONS_PLIST="$ROOT/build/ios-config/ExportOptions-AppStore.plist"

# Validate archive exists
if [ ! -d "$ARCHIVE_PATH" ]; then
    echo "PKS ERROR: No archive found at $ARCHIVE_PATH"
    echo "PKS Run 'bin/build.sh ios-release' first."
    exit 1
fi

# Validate export options plist exists
if [ ! -f "$EXPORT_OPTIONS_PLIST" ]; then
    echo "PKS ERROR: ExportOptions-AppStore.plist not found at $EXPORT_OPTIONS_PLIST"
    echo "PKS Creating default ExportOptions plist..."
    cat > "$EXPORT_OPTIONS_PLIST" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>method</key>
    <string>app-store-connect</string>
    <key>teamID</key>
    <string>8KJB799CU7</string>
    <key>destination</key>
    <string>upload</string>
    <key>signingStyle</key>
    <string>manual</string>
    <key>provisioningProfiles</key>
    <dict>
        <key>com.vedanamedia.familydiagram</key>
        <string>Family Diagram App Store</string>
    </dict>
    <key>uploadBitcode</key>
    <false/>
    <key>uploadSymbols</key>
    <true/>
</dict>
</plist>
PLIST
    echo "PKS Created $EXPORT_OPTIONS_PLIST - review and update provisioning profile name before uploading."
fi

# Step 1: Export the archive
echo "PKS Exporting archive for App Store..."
rm -rf "$EXPORT_PATH"

xcodebuild \
    -exportArchive \
    -archivePath "$ARCHIVE_PATH" \
    -exportOptionsPlist "$EXPORT_OPTIONS_PLIST" \
    -exportPath "$EXPORT_PATH"

echo "PKS Export complete at $EXPORT_PATH"

# Step 2: Upload to TestFlight
IPA_PATH="$EXPORT_PATH/Family Diagram.ipa"

if [ ! -f "$IPA_PATH" ]; then
    echo "PKS ERROR: No IPA found at $IPA_PATH"
    echo "PKS Check export output above for errors."
    exit 1
fi

echo "PKS Uploading to TestFlight..."

# Prefer API key auth (non-interactive)
if [ -n "$FD_BUILD_AC_AUTH_KEY_ID" ] && [ -n "$FD_BUILD_AC_AUTH_KEY_ISSUER" ]; then

    # Ensure the API key file exists
    FD_BUILD_AC_AUTH_KEY_FPATH="${FD_IOS_BUILD_DIR}/AuthKey_${FD_BUILD_AC_AUTH_KEY_ID}.p8"
    if [ ! -f "$FD_BUILD_AC_AUTH_KEY_FPATH" ] && [ -n "$FD_BUILD_AC_AUTH_KEY_BASE64" ]; then
        echo "$FD_BUILD_AC_AUTH_KEY_BASE64" | base64 --decode > "$FD_BUILD_AC_AUTH_KEY_FPATH"
    fi

    if [ -f "$FD_BUILD_AC_AUTH_KEY_FPATH" ]; then
        xcrun notarytool --version > /dev/null 2>&1 || true

        # Use xcodebuild for upload (preferred modern approach)
        xcodebuild -exportArchive \
            -archivePath "$ARCHIVE_PATH" \
            -exportOptionsPlist "$EXPORT_OPTIONS_PLIST" \
            -exportPath "$EXPORT_PATH" \
            -allowProvisioningUpdates \
            -authenticationKeyPath "$FD_BUILD_AC_AUTH_KEY_FPATH" \
            -authenticationKeyID "$FD_BUILD_AC_AUTH_KEY_ID" \
            -authenticationKeyIssuerID "$FD_BUILD_AC_AUTH_KEY_ISSUER" \
            2>/dev/null || \
        # Fallback to xcrun altool
        xcrun altool --upload-app \
            --type ios \
            --file "$IPA_PATH" \
            --apiKey "$FD_BUILD_AC_AUTH_KEY_ID" \
            --apiIssuer "$FD_BUILD_AC_AUTH_KEY_ISSUER" \
            --show-progress
    else
        echo "PKS ERROR: API key file not found and FD_BUILD_AC_AUTH_KEY_BASE64 not set."
        echo "PKS Set App Store Connect API credentials to upload automatically."
        echo "PKS IPA is available at: $IPA_PATH"
        echo "PKS You can upload manually via Transporter.app or:"
        echo "PKS   xcrun altool --upload-app --type ios --file \"$IPA_PATH\" --apiKey KEY_ID --apiIssuer ISSUER_ID"
        exit 1
    fi
else
    echo "PKS WARNING: App Store Connect API credentials not set."
    echo "PKS IPA is available at: $IPA_PATH"
    echo "PKS Upload manually via Transporter.app or set FD_BUILD_AC_AUTH_KEY_ID and FD_BUILD_AC_AUTH_KEY_ISSUER."
    exit 0
fi

echo "PKS TestFlight upload complete!"
echo "PKS The build should appear in App Store Connect within a few minutes."
echo "PKS TestFlight review may take up to 24 hours for the first build."
