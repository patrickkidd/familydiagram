#!/bin/bash -v

set -e

# export KEYCHAIN=~/Library/Keychains/login.keychain
export KEYCHAIN=build.keychain


base64 -d /tmp/pks-developerprofile/FD.developerprofile.enc > FD.developerprofile
unzip FD.developerprofile

echo "Creating keychain..."
security create-keychain -p actions $KEYCHAIN

echo "Defaulting keychain..."
security default-keychain -s $KEYCHAIN

echo "Unlocking keychain..."
security unlock-keychain -p actions $KEYCHAIN


echo "Importing the private keys..."
security import developer/identities/4FD361BAAB621575F79AE0CE6669240293415415.p12 -k $KEYCHAIN -P ${PKS_PASSWORD} -T /usr/bin/codesign -T /usr/bin/security
security import developer/identities/6EFF94EFF56E06B554BB8820FC85D2AA4D42AE2A.p12  -k $KEYCHAIN -P ${PKS_PASSWORD} -T /usr/bin/codesign -T /usr/bin/security

echo "Setting $KEYCHAIN as default for security checks..."
security list-keychains -s ~/Library/Keychains/login.keychain

echo "List Identities..."
security find-identity -v -p codesigning $KEYCHAIN


# security set-keychain-settings $KEYCHAIN
echo "Allowing codesign to access the keychain without prompts..."
security unlock-keychain -p actions $KEYCHAIN
security set-key-partition-list -S apple-tool:,apple: -s -k actions $KEYCHAIN
echo "Done 1"

##


echo "Installing Developer Profiles..."
mkdir -p ~/Library/MobileDevice/Provisioning\ Profiles/
cp developer/profiles/*.provisionprofile ~/Library/MobileDevice/Provisioning\ Profiles/

# # security import developer_id.p12 -A -t cert -f pkcs12 -P "" -k $KEYCHAIN
# security -v  import developer/profiles/38054c77-a471-49ac-80bd-dd79de777df1.provisionprofile  -k $KEYCHAIN -T /usr/bin/codesign
# security -v  import developer/profiles/71182a4a-8944-4462-b795-4657ec2b1097.provisionprofile   -k $KEYCHAIN -T /usr/bin/codesign
# security -v  import developer/profiles/cd1e72cc-1763-4f58-b46a-3f2714cbdd0f.provisionprofile  -k $KEYCHAIN -T /usr/bin/codesign

##

echo "Listing certificate..."
security list-keychain -d user -s $KEYCHAIN

echo "Done 4"