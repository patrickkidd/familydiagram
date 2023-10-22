#!/bin/bash

set -e

. ./bin/build_env.sh

rm -rf ./private_keys/
mkdir -p ./private_keys/
mkdir -p $FD_BUILD_DIR

echo "PKS Decoding provisioning profile to ${FD_BUILD_PROVISIONING_PROFILE_FPATH}"
echo "${FD_BUILD_PROVISIONING_PROFILE_BASE64}" | base64 --decode > "${FD_BUILD_PROVISIONING_PROFILE_FPATH}"

echo "PKS Decoding certificate"
echo "${FD_BUILD_CERTIFICATE_BASE64}" | base64 --decode > "${FD_BUILD_CERTIFICATE_FPATH}"

echo "PKS Decoding private key to ${FD_BUILD_PRIVATE_KEY_FPATH}"
echo "${FD_BUILD_PRIVATE_KEY_BASE64}" | base64 --decode > "${FD_BUILD_PRIVATE_KEY_FPATH}"

echo "PKS Decoding App Store Connect auth key"
echo "${FD_BUILD_AC_AUTH_KEY_BASE64}" | base64 --decode > "${FD_BUILD_AC_AUTH_KEY_FPATH}"

echo "PKS Cleaning up previous keychains"
security delete-keychain $FD_BUILD_KEYCHAIN_NAME || true

echo "PKS Creating isolated build keychain"
security create-keychain -p my_password $FD_BUILD_KEYCHAIN_NAME

echo "PKS Setting build keychain default"
security default-keychain -s $FD_BUILD_KEYCHAIN_NAME

echo "PKS Unlocking keychain"
security unlock-keychain -p my_password $FD_BUILD_KEYCHAIN_NAME

# echo "PKS Extending keychain timeout"
# security set-keychain-settings -lut 1200

echo "PKS Importing private key"
security import $FD_BUILD_PRIVATE_KEY_FPATH -t priv -P "${FD_BUILD_CERTIFICATE_PASSWORD}" -A -T /usr/bin/codesign -k $FD_BUILD_KEYCHAIN_NAME 

echo "PKS Importing signing certificate"
security import $FD_BUILD_CERTIFICATE_FPATH -P "${FD_BUILD_CERTIFICATE_PASSWORD}" -k $FD_BUILD_KEYCHAIN_NAME 

echo "PKS Storing password in the keychain"
xcrun altool --store-password-in-keychain-item "${FD_BUILD_APPLE_ID}" -u "${FD_BUILD_APPLE_ID}" -p "${FD_BUILD_APPLE_ID_PASSWORD}"

echo "PKS Setting keychain partitions list"
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k my_password $FD_BUILD_KEYCHAIN_NAME

echo "PKS Adding provisioning profile to local machine"
mkdir -p ~/Library/MobileDevice/Provisioning\ Profiles
security cms -D -i $FD_BUILD_PROVISIONING_PROFILE_FPATH > $FD_BUILD_DIR/FD.provisionprofile.plist
FD_BUILD_PROVISIONING_PROFILE=$(/usr/libexec/PlistBuddy -c "Print :Name" $FD_BUILD_DIR/FD.provisionprofile.plist)
FD_BUILD_PROVISIONING_PROFILE_SPECIFIER=$(/usr/libexec/PlistBuddy -c "Print :UUID" $FD_BUILD_DIR/FD.provisionprofile.plist)
mv $FD_BUILD_PROVISIONING_PROFILE_FPATH ~/Library/MobileDevice/Provisioning\ Profiles/${FD_BUILD_PROVISIONING_PROFILE_SPECIFIER}.provisionprofile
