#!/bin/bash.sh


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


export FD_BUILD_DIR=build/osx/Release
export FD_BUILD_KEYCHAIN_NAME=build.keychain-db
export FD_BUILD_PROVISIONING_PROFILE_FPATH=${FD_BUILD_DIR}/FD.provisionprofile
export FD_BUILD_CERTIFICATE_FPATH=${FD_BUILD_DIR}/FD_certificate.crt
export FD_BUILD_PRIVATE_KEY_FPATH=${FD_BUILD_DIR}/FD_certificate.pem
export FD_BUILD_AC_AUTH_KEY_FPATH="./private_keys/AuthKey_${FD_BUILD_AC_AUTH_KEY_ID}.p8"
export FD_APP_PATH=build/osx/Release/Family\ Diagram.app
