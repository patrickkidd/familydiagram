#!/bin/bash

set -e


TARGET=$1

if [[ "$TARGET" = "" ]]; then
    TARGET=osx
fi

BIN="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT=`cd "$BIN/.."; pwd`

export PYTHONPATH=`pwd`/lib/site-packages



if [[ $TARGET = osx* ]]; then

    function build_archive {

        # https://forums.developer.apple.com/thread/107976
        # https://stackoverflow.com/questions/45748140/xcode-9-distribution-build-fails-because-format-of-exportoptions-plist-has-chang
        # https://developer.apple.com/documentation/xcode/notarizing_macos_software_before_distribution/customizing_the_notarization_workflow?preferredLanguage=occ
        # https://nativeconnect.app/blog/mac-app-notarization-from-the-command-line/

        echo "PKS Fixing up xcodeproject"
        python3 bin/fixup_xcodeproj_workspace.py

        echo "PKS Running \"Qt Preprocess\" target..."

        xcodebuild \
            -project build/osx/Family\ Diagram.xcodeproj \
            -target "Qt Preprocess" \
            -configuration Release \
            # -xcconfig build/osx/Family-Diagram-Release.xcconfig 
            # -UseModernBuildSystem=YES

        echo "PKS Building app archive..."

        xcodebuild \
            -project build/osx/Family\ Diagram.xcodeproj \
            -scheme "Family Diagram" \
            -configuration Release \
            -archivePath ${FD_BUILD_DIR}/Family\ Diagram.xcarchive \
            archive
            # -xcconfig build/osx/Family-Diagram-Release.xcconfig \
            # -UseModernBuildSystem=YES \

        echo "PKS Exporting app from archive..."

        xcodebuild \
            -verbose \
            -exportArchive \
            -archivePath ${FD_BUILD_DIR}/Family\ Diagram.xcarchive \
            -exportOptionsPlist build/osx/ExportOptions.plist \
            -exportPath $FD_BUILD_DIR/Export

        echo "PKS Copying exported app to Release folder"

        rm build/osx/Release/Family\ Diagram.app
        cp -R $FD_BUILD_DIR/Export/Family\ Diagram.app build/osx/Release

    }

    function notarize {

        echo "PKS Zipping up archive"

        ditto -c -k --keepParent \
            "$FD_BUILD_DIR/Family Diagram.app" \
            "$FD_BUILD_DIR/Family Diagram.zip"

        echo "PKS Uploading for notarization..."

        xcrun notarytool submit \
            --key "${FD_BUILD_AC_AUTH_KEY_FPATH}" \
            --key-id "${FD_BUILD_AC_AUTH_KEY_ID}" \
            --issuer "${FD_BUILD_AC_AUTH_KEY_ISSUER}" \
            --timeout 2h \
            --wait --progress \
            --output-format plist \
            "$FD_BUILD_DIR/Family Diagram.zip" \
            > ${FD_BUILD_DIR}/NotaryResults.plist || true

        REQUEST_STATUS=$(/usr/libexec/PlistBuddy -c "Print :status" build/osx/Release/NotaryResults.plist)

        if [ "$REQUEST_STATUS" != "Accepted" ]; then
            REQUEST_UUID=$(/usr/libexec/PlistBuddy -c "Print :id" ${FD_BUILD_DIR}/NotaryResults.plist)
            echo "PKS *** Notarizing failed, fetching developer log for Request ID: ${REQUEST_UUID}..."
            xcrun notarytool log $REQUEST_UUID \
                --key "${FD_BUILD_AC_AUTH_KEY_FPATH}" \
                --key-id "${FD_BUILD_AC_AUTH_KEY_ID}" \
                --issuer "${FD_BUILD_AC_AUTH_KEY_ISSUER}" 
            exit
        fi

        echo "PKS Stapling Family Diagram app bundle..."
        # APP_PATH="build/osx/Release/Family\ Diagram.xcarchive/Submissions/$SUBMISSION_UUID/Family\ Diagram.app"
        xcrun stapler staple "${FD_BUILD_DIR}/Family Diagram.app"

    }


    function osx_dmg {
        # sips --setProperty dpiWidth 144 --setProperty dpiHeight 144 build/osx-config/DMG-Background.jpg
        # install with `brew install create-dbg`
        # or https://github.com/andreyvit/create-dmg
        cd build/osx && create-dmg \
            --volname "Family Diagram" \
            --volicon "PKDiagram-Filled.icns" \
            --background "DMG-Background.png" \
            --window-pos 200 200 \
            --window-size 800 600 \
            --icon-size 128 \
            --icon "Family Diagram.app" 200 350 \
            --hide-extension "Family Diagram.app" \
            --app-drop-link 600 350 \
            --no-internet-enable \
            "Release/Family Diagram.dmg" \
            "Release/"
        cd ../..
    }

    # export CI=1 # prevent xcode from prompting anything?

    # rm -rf build/osx # emphemeral

    SYSROOT=$ROOT/sysroot/sysroot-macos-64
    # if [ "$(which qmake)" == "" ]; then
    #     QMAKE=$SYSROOT/Qt/bin/qmake
    # else
    #     QMAKE=$(which qmake)
    # fi
    QMAKE=$SYSROOT/Qt/bin/qmake
    # PYTHON_VERSION=`python3 -c "import platform; print(platform.python_version())"`
    FAMILYDIAGRAM_VERSION=`python3 -m pkdiagram --version`
    if echo "$FAMILYDIAGRAM_VERSION" | grep -q "a"; then
        echo "PKS Alpha version detected"
        QT_EXTRA_CONFIG="CONFIG+=alpha"
    elif echo "$FAMILYDIAGRAM_VERSION" | grep -q "b"; then
        echo "PKS Beta version detected"
        QT_EXTRA_CONFIG="CONFIG+=beta"
    else
        echo "PKS Full release version detected"
    fi
    echo "PEPPER = b\"$FD_BUILD_PEPPER\"" > pkdiagram/pepper.py
    echo "BUGSNAG_API_KEY = \"$FD_BUILD_BUGSNAG_API_KEY\"" >> pkdiagram/pepper.py

    echo "PKS Updating app pepper and version"
    if [ ! -f pkdiagram/build_uuid.py ] || \
        [ pkdiagram/version.py -nt bin/update_build_info.py ] || \
        [ pkdiagram/version.py -nt build/osx-config/Info.plist.py ] || \
        [ pkdiagram/version.py -nt build/osx-config/Info.plist.py ]; then
        python3 bin/update_build_info.py
    else
        echo "PKS version and pepper are up to date"
    fi

    echo "PKS Generating _pkdiagram sources"
    (
        set -e
        cd _pkdiagram
        sip-build --no-compile
        moc -o build/_pkdiagram/moc_unsafearea.cpp unsafearea.h
        moc -o build/_pkdiagram/moc__pkdiagram.cpp _pkdiagram.h
    )

    echo "PKS Running pyqtdeploy-build (wipes out build/osx folder)"
	pyqtdeploy-build --verbose  --resources 12 --target macos-64 --build-dir build/osx familydiagram.pdt

	rsync -avzq build/common-config/* build/osx
	rsync -avzq build/osx-config/* build/osx

    . ./bin/setup_provisioning_profile.sh

	# rsync -avzq resources/* build/osx/resources/resources

    if [[ $TARGET == "osx" ]]; then

        cd build/osx && $QMAKE -spec macx-xcode CONFIG+=no_autoqmake CONFIG+=debug CONFIG-=release && cd ../..
        echo "Updating xcode project to new build system"
        python3 bin/fixup_xcodeproj_workspace.py
        # bin/filter_xcodeproj.rb osx "Family Diagram" "$SYSROOT/src/Python-$PYTHON_VERSION/Modules/_ctypes/libffi_osx/x86/darwin64.S" # 2> /dev/null
        # echo "Opening build/osx/Family\ Diagram.xcodeproj..."
        # open build/osx/Family\ Diagram.xcodeproj

        xcodebuild \
            -project build/osx/Family\ Diagram.xcodeproj \
            -target "Qt Preprocess" \
            -configuration Release \
            -UseModernBuildSystem=YES \
            -xcconfig build/osx/Family-Diagram-Release.xcconfig 

        xcodebuild \
            -project build/osx/Family\ Diagram.xcodeproj \
            -scheme "Family Diagram" \
            -configuration Release \
            -xcconfig build/osx/Family-Diagram-Release.xcconfig \
            -UseModernBuildSystem=YES \
            build

        ./build/osx/Release/Family\ Diagram.app/Contents/MacOS/Family\ Diagram --version


    elif [[ $TARGET == "osx-release" ]]; then

        cd build/osx && $QMAKE -spec macx-xcode CONFIG+=no_autoqmake CONFIG-=debug CONFIG+=release $QT_EXTRA_CONFIG && cd ../..
        # bin/filter_xcodeproj.rb osx "Family Diagram" "$SYSROOT/src/Python-$PYTHON_VERSION/Modules/_ctypes/libffi_osx/x86/darwin64.S" # 2> /dev/null
        build_archive
        ./build/osx/Release/Family\ Diagram.app/Contents/MacOS/Family\ Diagram --version
        notarize
        osx_dmg

        # zip -r -X build/osx/Release/Family\ Diagram-$FAMILYDIAGRAM_VERSION.dSYM.zip build/osx/Release/Family\ Diagram.dSYM
        # bugsnag-dsym-upload --api-key YOUR_UUID_API_KEY build/osx/Release/Family\ Diagram-$FAMILYDIAGRAM_VERSION.dSYM.zip

    elif [[ $TARGET == "osx-debug" ]]; then

        cd build/osx && $QMAKE -spec macx-xcode CONFIG+=no_autoqmake CONFIG+=debug CONFIG-=release && cd ../..
        # bin/filter_xcodeproj.rb osx "Family Diagram" "$SYSROOT/src/Python-$PYTHON_VERSION/Modules/_ctypes/libffi_osx/x86/darwin64.S" 2> /dev/null
        xcodebuild -project build/osx/Family\ Diagram.xcodeproj -scheme "Family Diagram" -configuration Debug -UseModernBuildSystem=YES build

    fi

    . ./bin/teardown_provisioning_profile.sh

elif [[ $TARGET = ios* ]]; then

    SYSROOT=`cd "$ROOT/sysroot-ios-64"; pwd`
    QMAKE=~/dev/Qt/5.15.1/ios/bin/qmake

    if [[ ! -f Makefile ]]; then 
        qmake && make
    fi

	python bin/update_plist_version.py

	pyqtdeploy-build --verbose --resources 4 --target ios-64 --build-dir build/ios familydiagram.pdt
	sed -e 's/printsupport//' build/ios/Family\ Diagram.pro > build/ios/Family\ Diagram.pro.2
	mv build/ios/Family\ Diagram.pro.2 build/ios/Family\ Diagram.pro
	sed -e 's/LIBS += -lQtPrintSupport//' build/ios/Family\ Diagram.pro > build/ios/Family\ Diagram.pro.2
	mv build/ios/Family\ Diagram.pro.2 build/ios/Family\ Diagram.pro
	sed -e 's/extern "C" PyObject *PyInit_QtPrintSupport(void);//' build/ios/pyqtdeploy_main.cpp  > build/ios/pyqtdeploy_main.cpp.2
	mv build/ios/pyqtdeploy_main.cpp.2 build/ios/pyqtdeploy_main.cpp
	sed -e 's/    {"PyQt5.QtPrintSupport", PyInit_QtPrintSupport},//' build/ios/pyqtdeploy_main.cpp  > build/ios/pyqtdeploy_main.cpp.2
	mv build/ios/pyqtdeploy_main.cpp.2 build/ios/pyqtdeploy_main.cpp

	rsync -avzq build/common-config/* build/ios
	rsync -avzq build/ios-config/* build/ios
	cd build/ios && $QMAKE CONFIG+=no_autoqmake

    if [[ $TARGET == "ios" ]]; then

    	open Family\ Diagram.xcodeproj
    
    elif [[ $TARGET == "osx-build" ]]; then

    	# xcrun xcodebuild -scheme "Family Diagram" -configuration Release -project build/ios/Family\ Diagram.xcodeproj -destination 'platform=iOS Simulator,name=iPhone Xʀ,OS=12.2' build
    	xcrun xcodebuild -scheme "Family Diagram" -configuration Release -project build/ios/Family\ Diagram.xcodeproj -destination 'platform=iOS Simulator,name=iPhone Xʀ,OS=12.2' build

    elif [[ $TARGET == "osx-deploy" ]]; then

    	# xcrun xcodebuild -scheme "Family Diagram" -configuration Release -project build/ios/Family\ Diagram.xcodeproj -destination 'platform=iOS Simulator,name=iPhone Xʀ,OS=12.2' build
    	xcrun xcodebuild -scheme "Family Diagram" -configuration Release -project build/ios/Family\ Diagram.xcodeproj -destination "platform=iPadOS,name=Patrick Stinson's iPad" build

    fi

elif [[ $TARGET == "clean" ]]; then

	rm -rf build/osx/*
	rm -rf build/ios
    rm -rf build/win32
	rm -rf `find . -name xcuserdata`
	rm -rf `find . -name __pycache__`
	rm -rf `find . -name .qmake.stash`

fi
