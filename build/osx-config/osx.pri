alpha|beta|release {

    # Bugsnag
    bugsnag.files = Vendor/Bugsnag.framework
    bugsnag.path = Contents/Frameworks
    QMAKE_BUNDLE_DATA += bugsnag
    QMAKE_CXXFLAGS += -F$$PWD -DPK_USE_BUGSNAG=1
    LIBS += -L$$PWD -framework Bugsnag

    # Sparkle
    sparkle.files = Vendor/Sparkle.framework
    sparkle.path = Contents/Frameworks
    QMAKE_BUNDLE_DATA += sparkle
    QMAKE_CXXFLAGS += -F$$PWD -DPK_USE_SPARKLE=1
    LIBS += -L$$PWD -framework Sparkle

    # AppCenter
    LIBS += -FVendor -framework AppCenter -framework AppCenterAnalytics -framework AppCenterCrashes
    QMAKE_CFLAGS += -fmodules -fcxx-modules -DPK_USE_APPCENTER=1
    QMAKE_CXXFLAGS += -Werror -fmodules -fcxx-modules -Wno-module-import-in-extern-c -DPK_USE_APPCENTER=1

    QMAKE_LFLAGS += -rpath @executable_path/../Frameworks -F$$PWD
}

## Bundle Resources
QMAKE_INFO_PLIST = Info.plist
ICON = PKDiagram-Filled.icns
app_icon.files = PKDiagram-Filled.icns
app_icon.path = Contents/Resources
QMAKE_BUNDLE_DATA += app_icon
doc_icon.files = PKDiagram-Document.icns
doc_icon.path = Contents/Resources
QMAKE_BUNDLE_DATA += doc_icon

# User Manual
# usermanual.files = ../../doc/User-Manual
# usermanual.path = Contents/Resources
# QMAKE_BUNDLE_DATA += usermanual

# openssl
# INCLUDEPATH += /usr/local/Cellar/openssl@1.1/1.1.1g/include
# LIBS += -L/usr/local/Cellar/openssl@1.1/1.1.1g/lib

LIBS += -framework AppKit
# QMAKE_MAC_SDK = macosx10.12
# QMAKE_MACOSX_DEPLOYMENT_TARGET = 10.12
# QMAKE_DEVELOPMENT_TEAM = 8KJB799CU7
QMAKE_TARGET_BUNDLE_PREFIX = com.vedanamedia
QMAKE_BUNDLE = familydiagrammac

