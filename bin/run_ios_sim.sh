#/bin/sh

# https://nshipster.com/simctl/

UUID=`xcrun simctl list | grep "iPhone Xʀ" | grep -E -o -i "([0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12})"`
BOOTED=`xcrun simctl list | grep $UUID`
if [ -z $BOOTEDx ]; then
    xcrun simctl boot $UUID
fi

open /Applications/Xcode.app/Contents/Developer/Applications/Simulator.app
clear
xcrun simctl launch --console-pty $UUID com.vedanamedia.familydiagram
