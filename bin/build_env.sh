#!/bin/bash -e

# Validate all the private environment variables required for the build. These
# vars are the confidential end of the build configuration that should be added
# to any dev shell or CD pipeline as secrets.


if [ "$FD_BUILD_PEPPER" == "" ]; then
    echo "FD_BUILD_PEPPER must be set"
    exit 1
fi

if [ "$FD_BUILD_BUGSNAG_API_KEY" == "" ]; then
    echo "FD_BUILD_BUGSNAG_API_KEY must be set"
    exit 1
fi

if [ "$FD_BUILD_PROVISIONING_PROFILE_BASE64" == "" ]; then
    echo "FD_BUILD_PROVISIONING_PROFILE_BASE64 must be set"
    exit 1
fi

if [ "$FD_BUILD_CERTIFICATE_BASE64" == "" ]; then
    echo "FD_BUILD_CERTIFICATE_BASE64 must be set"
    exit 1
fi

if [ "$FD_BUILD_PRIVATE_KEY_BASE64" == "" ]; then
    echo "FD_BUILD_PRIVATE_KEY_BASE64 must be set"
    exit 1
fi

if [ "$FD_BUILD_AC_AUTH_KEY_ID" == "" ]; then
    echo "FD_BUILD_AC_AUTH_KEY_ID must be set"
    exit 1
fi


if [ "$FD_BUILD_AC_AUTH_KEY_BASE64" == "" ]; then
    echo "FD_BUILD_AC_AUTH_KEY_BASE64 must be set"
    exit 1
fi


if [ "$FD_BUILD_AC_AUTH_KEY_ISSUER" == "" ]; then
    echo "FD_BUILD_AC_AUTH_KEY_ISSUER must be set"
    exit 1
fi


export FD_BUILD_DIR=`pwd`/build/osx/Release
export FD_BUILD_KEYCHAIN_NAME=${FD_BUILD_DIR}/build.keychain-db
export FD_BUILD_PROVISIONING_PROFILE_FPATH=${FD_BUILD_DIR}/FD.provisionprofile
export FD_BUILD_CERTIFICATE_FPATH=${FD_BUILD_DIR}/FD_certificate.crt
export FD_BUILD_PRIVATE_KEY_FPATH=${FD_BUILD_DIR}/FD_certificate.pem
export FD_BUILD_AC_AUTH_KEY_FPATH="./private_keys/AuthKey_${FD_BUILD_AC_AUTH_KEY_ID}.p8"
export FD_APP_PATH=`pwd`/build/osx/Release/Family\ Diagram.app
