#!/bin/bash

set -e # exit on first error

TARGET=$1

if [[ "$TARGET" = "" ]]; then
    TARGET=osx
fi

BIN="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT=`cd "$BIN/.."; pwd`

export FAMILYDIAGRAM_BUILD=1
export PYTHONPATH=`pwd`/lib/site-packages

if [ "$FD_BUILD_PEPPER" == "" ]; then
    echo "FD_BUILD_PEPPER must be set"
    exit 1
fi

if [ "$FD_BUILD_BUGSNAG_API_KEY" == "" ]; then
    echo "FD_BUILD_BUGSNAG_API_KEY must be set"
    exit 1
fi


function make_all {
    if [[ ! -f Makefile ]]; then 
        qmake && make
    fi
}

function export_and_notarize {

    python3 bin/fixup_xcodeproj_workspace.py

    # https://forums.developer.apple.com/thread/107976
    # https://stackoverflow.com/questions/45748140/xcode-9-distribution-build-fails-because-format-of-exportoptions-plist-has-chang
    # https://developer.apple.com/documentation/xcode/notarizing_macos_software_before_distribution/customizing_the_notarization_workflow?preferredLanguage=occ
    # https://nativeconnect.app/blog/mac-app-notarization-from-the-command-line/

    echo "Building Family Diagram app..."

    xcodebuild \
        -project build/osx/Family\ Diagram.xcodeproj \
        -target "Qt Preprocess" \
        -configuration Release \
        -xcconfig build/osx/Family-Diagram-Release.xcconfig 
        # -UseModernBuildSystem=YES

    echo "Archiving Family Diagram app build..."

    xcodebuild \
        -project build/osx/Family\ Diagram.xcodeproj \
        -scheme "Family Diagram" \
        -configuration Release \
        -xcconfig build/osx/Family-Diagram-Release.xcconfig \
        -archivePath build/osx/Release/Family\ Diagram.xcarchive \
        archive
        # -UseModernBuildSystem=YES \

    echo "Exporting Family Diagram archive, creating notarization plist..."

    xcodebuild \
        -exportArchive \
        -archivePath build/osx/Release/Family\ Diagram.xcarchive \
        -exportOptionsPlist build/osx/ExportOptions.plist

    ## Wait until the app has been notarized by apple.
    ## An email should also arrive when it is notarized.
    SUBMISSION_UUID=`ls build/osx/Release/Family\ Diagram.xcarchive/Submissions/`
    REQUEST_INFO_PLIST="build/osx/Release/NotarizeRequestInfo.plist"

    echo "Notarizing Family Diagram export..."

    /usr/bin/xcrun altool --notarization-info $SUBMISSION_UUID -u $AC_USERNAME -p $AC_FD_PASSWORD --output-format xml > $REQUEST_INFO_PLIST  || true
    # while :
    # do
    #     /usr/bin/xcrun altool --notarization-info $SUBMISSION_UUID -u $AC_USERNAME -p $AC_FD_PASSWORD --output-format xml > $REQUEST_INFO_PLIST
    #     STATUS=`/usr/libexec/PlistBuddy -c "Print :notarization-info:Status" $REQUEST_INFO_PLIST`
    #     echo $STATUS
    #     if [ "$STATUS" != "in progress" ]; then
    #         break
    #     fi
    #     echo "Will check notarization status again in just a bit..."
    #     sleep 20
    # done

    sleep 20 # sometimes still wasn't done notarizing yet.
    echo "Copying Family Diagram app bundle to folder to staple it..."

    # Copy the app bundle from the archive now that it is notarized
    rm -rf build/osx/Release/Family\ Diagram.app
    xcodebuild \
        -exportNotarizedApp \
        -archivePath build/osx/Release/Family\ Diagram.xcarchive \
        -exportPath build/osx/Release

    echo "Stapling Family Diagram app bundle..."

    # APP_PATH="build/osx/Release/Family\ Diagram.xcarchive/Submissions/$SUBMISSION_UUID/Family\ Diagram.app"
    xcrun stapler staple build/osx/Release/Family\ Diagram.app
    # ditto -c -k --keepParent build/osx/Release/Family\ Diagram.app build/osx/Release/Family\ Diagram.zip    
}


if [[ $TARGET = osx* ]]; then

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
    }

    # function appcenter_release {
    #     # Alpha API token
    #     # d8f179f78f320adf762560c3f96c97ad0f4ca8bc
    # }

    # SYSROOT=`cd "$ROOT/sysroot/sysroot-macos-64"; pwd`
    SYSROOT=$ROOT/sysroot/sysroot-macos-64
    if [ "$(which qmake)" == "" ]; then
        QMAKE=$SYSROOT/Qt/bin/qmake
    else
        QMAKE=$(which qmake)
    fi
    PYTHON_VERSION=`python3 -c "import platform; print(platform.python_version())"`
    FAMILYDIAGRAM_VERSION=`python3 main.py --version`

    echo "PEPPER = b\"$FD_BUILD_PEPPER\"" > pkdiagram/pepper.py
    echo "BUGSNAG_API_KEY = \"$FD_BUILD_BUGSNAG_API_KEY\"" >> pkdiagram/pepper.py

    echo "qmake && make"
    make_all

    echo "Updating app version in plist"
	python3 bin/update_plist_version.py
    if [ ! -f pkdiagram/build_uuid.py ] || [ pkdiagram/version.py -nt bin/update_build_uuid.py ]; then
        python3 bin/update_build_uuid.py
    fi
    echo "Running pyqtdeploy-build"
	pyqtdeploy-build --verbose  --resources 12 --target macos-64 --build-dir build/osx familydiagram.pdt
    echo "Updating build uuid"
    python3 bin/update_build_uuid.py
	rsync -avzq build/common-config/* build/osx
	rsync -avzq build/osx-config/* build/osx
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
            -xcconfig build/osx/Family-Diagram-Release.xcconfig 
            # -UseModernBuildSystem=YES

        xcodebuild \
            -project build/osx/Family\ Diagram.xcodeproj \
            -scheme "Family Diagram" \
            -configuration Release \
            -xcconfig build/osx/Family-Diagram-Release.xcconfig \
            -UseModernBuildSystem=YES \
            build
    
    elif [[ $TARGET == "osx-alpha" ]]; then

        cd build/osx && $QMAKE -spec macx-xcode CONFIG+=no_autoqmake CONFIG-=debug CONFIG+=release CONFIG+=alpha && cd ../..
        # bin/filter_xcodeproj.rb osx "Family Diagram" "$SYSROOT/src/Python-$PYTHON_VERSION/Modules/_ctypes/libffi_osx/x86/darwin64.S" 2> /dev/null
        # xcodebuild -project build/osx/Family\ Diagram.xcodeproj -scheme "Family Diagram" -configuration Release -UseModernBuildSystem=YES build
        export_and_notarize
        osx_dmg

        # curl -X POST "https://api.appcenter.ms/v0.1/apps/pstinson/Family-Diagram-1/uploads/releases" -H  "accept: application/json" -H  "X-API-Token: d8f179f78f320adf762560c3f96c97ad0f4ca8bc" -H  "Content-Type: application/json" -d "{  \"build_version\": \"$FAMILYDIAGRAM_VERSION\",  \"build_number\": \"$FAMILYDIAGRAM_VERSION\"}"

    elif [[ $TARGET == "osx-beta" ]]; then

        cd build/osx && $QMAKE -spec macx-xcode CONFIG+=no_autoqmake CONFIG-=debug CONFIG+=release CONFIG+=beta && cd ../..
        # bin/filter_xcodeproj.rb osx "Family Diagram" "$SYSROOT/src/Python-$PYTHON_VERSION/Modules/_ctypes/libffi_osx/x86/darwin64.S" 2> /dev/null
        export_and_notarize
        osx_dmg


    elif [[ $TARGET == "osx-release" ]]; then

        cd build/osx && $QMAKE -spec macx-xcode CONFIG+=no_autoqmake CONFIG-=debug CONFIG+=release && cd ../..
        # bin/filter_xcodeproj.rb osx "Family Diagram" "$SYSROOT/src/Python-$PYTHON_VERSION/Modules/_ctypes/libffi_osx/x86/darwin64.S" # 2> /dev/null
        export_and_notarize
        osx_dmg

        # zip -r -X build/osx/Release/Family\ Diagram-$FAMILYDIAGRAM_VERSION.dSYM.zip build/osx/Release/Family\ Diagram.dSYM
        # bugsnag-dsym-upload --api-key YOUR_UUID_API_KEY build/osx/Release/Family\ Diagram-$FAMILYDIAGRAM_VERSION.dSYM.zip

    elif [[ $TARGET == "osx-debug" ]]; then

        cd build/osx && $QMAKE -spec macx-xcode CONFIG+=no_autoqmake CONFIG+=debug CONFIG-=release && cd ../..
        # bin/filter_xcodeproj.rb osx "Family Diagram" "$SYSROOT/src/Python-$PYTHON_VERSION/Modules/_ctypes/libffi_osx/x86/darwin64.S" 2> /dev/null
        xcodebuild -project build/osx/Family\ Diagram.xcodeproj -scheme "Family Diagram" -configuration Debug -UseModernBuildSystem=YES build

    fi

elif [[ $TARGET = ios* ]]; then

    SYSROOT=`cd "$ROOT/sysroot-ios-64"; pwd`
    QMAKE=~/dev/Qt/5.15.1/ios/bin/qmake

    make_all

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
