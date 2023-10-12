#!/bin/bash


# https://forums.developer.apple.com/thread/107976
# https://stackoverflow.com/questions/45748140/xcode-9-distribution-build-fails-because-format-of-exportoptions-plist-has-chang
# https://developer.apple.com/documentation/xcode/notarizing_macos_software_before_distribution/customizing_the_notarization_workflow?preferredLanguage=occ
# https://nativeconnect.app/blog/mac-app-notarization-from-the-command-line/

xcodebuild \
    -project build/osx/Family\ Diagram.xcodeproj \
    -scheme "Family Diagram" \
    -configuration Release \
    -archivePath build/osx/Release/Family\ Diagram.xcarchive \
    archive
xcodebuild \
    -exportArchive \
    -archivePath build/osx/Release/Family\ Diagram.xcarchive \
    -exportOptionsPlist build/osx/ExportOptions.plist


## Wait until the app has been notarized by apple.
## An email should also arrive when it is notarized.
SUBMISSION_UUID=`ls build/osx/Release/Family\ Diagram.xcarchive/Submissions/`
REQUEST_INFO_PLIST="build/osx/Release/NotarizeRequestInfo.plist"

while :
do
    /usr/bin/xcrun altool --notarization-info $SUBMISSION_UUID -u $AC_USERNAME -p $AC_FD_PASSWORD --output-format xml > $REQUEST_INFO_PLIST
    STATUS=`/usr/libexec/PlistBuddy -c "Print :notarization-info:Status" $REQUEST_INFO_PLIST`
    echo $STATUS
    if [ "$STATUS" != "in progress" ]; then
      break
    fi
    echo "Will check notarization status again in just a bit..."
    sleep 20
done

# Copy the app bundle from the archive now that it is notarized
rm -rf build/osx/Release/Family\ Diagram.app
xcodebuild \
    -exportNotarizedApp \
    -archivePath build/osx/Release/Family\ Diagram.xcarchive \
    -exportPath build/osx/Release

# APP_PATH="build/osx/Release/Family\ Diagram.xcarchive/Submissions/$SUBMISSION_UUID/Family\ Diagram.app"
xcrun stapler staple build/osx/Release/Family\ Diagram.app
# ditto -c -k --keepParent build/osx/Release/Family\ Diagram.app build/osx/Release/Family\ Diagram.zip
