
security delete-keychain `pwd`/build/osx/Release/build.keychain-db
security list-keychains -s login.keychain-db
security default-keychain -s login.keychain-db
