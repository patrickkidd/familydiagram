#!/bin/bash

# Create a transient build keychain and import provisioning profile,
# certificate, and private key into it.
# 
# All run from bin/build.sh in the normal case.

set -e
set -x  # Enable command echoing with expanded environment variables

if [ "${FD_BUILD_DIR}" = "" ]; then
    echo "PKS Pulling in build_env.sh"
    . ./bin/build_env.sh
fi

# Must be in environment, not set in build_env.sh
if [ "$FD_BUILD_APPLE_ID" == "" ]; then
    echo "FD_BUILD_APPLE_ID must be set"
    exit 1
fi

# Must be in environment, not set in build_env.sh
if [ "$FD_BUILD_APPLE_ID_PASSWORD" == "" ]; then
    echo "FD_BUILD_APPLE_ID_PASSWORD must be set"
    exit 1
fi


# Must be in environment, not set in build_env.sh
if [ "$FD_BUILD_CERTIFICATE_PASSWORD" == "" ]; then
    echo "FD_BUILD_CERTIFICATE_PASSWORD must be set"
    exit 1
fi


echo "PKS Using transient keychain name: ${FD_BUILD_KEYCHAIN_NAME}"

mkdir -p $FD_BUILD_DIR

echo "PKS Writing provisioning profile to ${FD_BUILD_PROVISIONING_PROFILE_FPATH}"
echo "${FD_BUILD_PROVISIONING_PROFILE_BASE64}" | base64 --decode > "${FD_BUILD_PROVISIONING_PROFILE_FPATH}"

echo "PKS Writing certificate to ${FD_BUILD_CERTIFICATE_FPATH}"
echo "${FD_BUILD_CERTIFICATE_BASE64}" | base64 --decode > "${FD_BUILD_CERTIFICATE_FPATH}"

echo "PKS Writing private key to ${FD_BUILD_PRIVATE_KEY_FPATH}"
echo "${FD_BUILD_PRIVATE_KEY_BASE64}" | base64 --decode > "${FD_BUILD_PRIVATE_KEY_FPATH}"

echo "PKS Writing AppCenter to ${FD_BUILD_AC_AUTH_KEY_FPATH}"
echo "${FD_BUILD_AC_AUTH_KEY_BASE64}" | base64 --decode > "${FD_BUILD_AC_AUTH_KEY_FPATH}"

echo "PKS Creating keychain"
security create-keychain -p "$FD_BUILD_CERTIFICATE_PASSWORD" $FD_BUILD_KEYCHAIN_NAME

echo "PKS Setting build keychain default"
security default-keychain -s $FD_BUILD_KEYCHAIN_NAME

echo "PKS Unlocking keychain"
security unlock-keychain -p $FD_BUILD_CERTIFICATE_PASSWORD $FD_BUILD_KEYCHAIN_NAME

echo "PKS Extending keychain timeout"
security set-keychain-settings -lut 1200 $FD_BUILD_KEYCHAIN_NAME

echo "PKS Adding keychain to search list"
security list-keychains -s $FD_BUILD_KEYCHAIN_NAME

echo "PKS Importing private key"
security import $FD_BUILD_PRIVATE_KEY_FPATH -t priv -P "${FD_BUILD_CERTIFICATE_PASSWORD}" -A -T /usr/bin/codesign -k $FD_BUILD_KEYCHAIN_NAME 

echo "PKS Importing signing certificate"
security import $FD_BUILD_CERTIFICATE_FPATH -P "${FD_BUILD_CERTIFICATE_PASSWORD}" -k $FD_BUILD_KEYCHAIN_NAME 

echo "PKS Storing password in the keychain"
xcrun altool --store-password-in-keychain-item "${FD_BUILD_APPLE_ID}" -u "${FD_BUILD_APPLE_ID}" -p "${FD_BUILD_APPLE_ID_PASSWORD}"

echo "PKS Setting keychain partitions list"
security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k $FD_BUILD_CERTIFICATE_PASSWORD $FD_BUILD_KEYCHAIN_NAME

echo "PKS Adding provisioning profile to local machine"
mkdir -p ~/Library/MobileDevice/Provisioning\ Profiles
security cms -D -i $FD_BUILD_PROVISIONING_PROFILE_FPATH > $FD_BUILD_DIR/FD.provisionprofile.plist
FD_BUILD_PROVISIONING_PROFILE=$(/usr/libexec/PlistBuddy -c "Print :Name" $FD_BUILD_DIR/FD.provisionprofile.plist)

echo "PKS Found provisioning profile name ${FD_BUILD_PROVISIONING_PROFILE}"
FD_BUILD_PROVISIONING_PROFILE_SPECIFIER=$(/usr/libexec/PlistBuddy -c "Print :UUID" $FD_BUILD_DIR/FD.provisionprofile.plist)

echo "PKS Found provisioning profile specifier ${FD_BUILD_PROVISIONING_PROFILE_SPECIFIER}"
mv $FD_BUILD_PROVISIONING_PROFILE_FPATH ~/Library/MobileDevice/Provisioning\ Profiles/${FD_BUILD_PROVISIONING_PROFILE_SPECIFIER}.provisionprofile

echo "PKS Listing identities in the keychain"
security find-identity -p codesigning -v $FD_BUILD_KEYCHAIN_NAME

# echo "PKS Listing certificates in the keychain"
# security find-certificate -c "Developer ID Application: Patrick Stinson (8KJB799CU7)" -a -p $FD_BUILD_KEYCHAIN_NAME

echo "PKS Listing keychains"
security list-keychains

echo "PKS dump-keychain"
security dump-keychain
