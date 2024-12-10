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

    # Common Vendor
    LIBS += -FVendor
    QMAKE_CFLAGS += -fmodules -fcxx-modules
    QMAKE_CXXFLAGS += -Werror -fmodules -fcxx-modules -Wno-module-import-in-extern-c
    QMAKE_LFLAGS += -rpath @executable_path/../Frameworks -F$$PWD
}

DEFINES += NEEDS_PY_IDENTIFIER

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

# Set these to get the default values in the xcode project.
# This might be a good idea instead of xcconfig files anyway
# Since the build is only ever debug or release, never both

CONFIG(release, debug|release) {

    GCC_GENERATE_DEBUGGING_SYMBOLS.name = GCC_GENERATE_DEBUGGING_SYMBOLS
    GCC_GENERATE_DEBUGGING_SYMBOLS.value = Yes
    QMAKE_MAC_XCODE_SETTINGS += GCC_GENERATE_DEBUGGING_SYMBOLS

    GCC_DEBUGGING_SYMBOLS.name = GCC_DEBUGGING_SYMBOLS
    GCC_DEBUGGING_SYMBOLS.value = full
    QMAKE_MAC_XCODE_SETTINGS += GCC_DEBUGGING_SYMBOLS

    DWARF_DSYM_FILE_NAME.name = DWARF_DSYM_FILE_NAME
    DWARF_DSYM_FILE_NAME.value = $(TARGET_NAME).dSYM
    QMAKE_MAC_XCODE_SETTINGS += DWARF_DSYM_FILE_NAME

    DWARF_DSYM_FOLDER_PATH.name = DWARF_DSYM_FOLDER_PATH
    DWARF_DSYM_FOLDER_PATH.value = $(CONFIGURATION_BUILD_DIR)
    QMAKE_MAC_XCODE_SETTINGS += DWARF_DSYM_FOLDER_PATH

    STRIP_INSTALLED_PRODUCT.name = STRIP_INSTALLED_PRODUCT
    STRIP_INSTALLED_PRODUCT.value = No
    QMAKE_MAC_XCODE_SETTINGS += STRIP_INSTALLED_PRODUCT

    DEPLOYMENT_POSTPROCESSING.name = DEPLOYMENT_POSTPROCESSING
    DEPLOYMENT_POSTPROCESSING.value = Yes
    QMAKE_MAC_XCODE_SETTINGS += DEPLOYMENT_POSTPROCESSING

    DISABLE_MANUAL_TARGET_ORDER_BUILD_WARNING.name = DISABLE_MANUAL_TARGET_ORDER_BUILD_WARNING
    DISABLE_MANUAL_TARGET_ORDER_BUILD_WARNING.value = Yes
    QMAKE_MAC_XCODE_SETTINGS += DISABLE_MANUAL_TARGET_ORDER_BUILD_WARNING

    ENABLE_HARDENED_RUNTIME.name = ENABLE_HARDENED_RUNTIME
    ENABLE_HARDENED_RUNTIME.value = YES
    QMAKE_MAC_XCODE_SETTINGS += ENABLE_HARDENED_RUNTIME

    CODE_SIGN_STYLE.name = CODE_SIGN_STYLE
    CODE_SIGN_STYLE.value = Manual
    QMAKE_MAC_XCODE_SETTINGS += CODE_SIGN_STYLE

    CODE_SIGN_IDENTITY.name = CODE_SIGN_IDENTITY
    CODE_SIGN_IDENTITY.value = "Developer ID Application: Patrick Stinson (8KJB799CU7)"
    QMAKE_MAC_XCODE_SETTINGS += CODE_SIGN_IDENTITY

    PROVISIONING_PROFILE_SPECIFIER.name = PROVISIONING_PROFILE_SPECIFIER
    PROVISIONING_PROFILE_SPECIFIER.value = cd1e72cc-1763-4f58-b46a-3f2714cbdd0f
    QMAKE_MAC_XCODE_SETTINGS += PROVISIONING_PROFILE_SPECIFIER

    DEVELOPMENT_TEAM.name = DEVELOPMENT_TEAM
    DEVELOPMENT_TEAM.value = 8KJB799CU7
    QMAKE_MAC_XCODE_SETTINGS += DEVELOPMENT_TEAM

    CODE_SIGN_FLAGS.name = CODE_SIGN_FLAGS
    CODE_SIGN_FLAGS.value = --options=runtime
    QMAKE_MAC_XCODE_SETTINGS += CODE_SIGN_FLAGS

} else {

    QMAKE_MAC_XCODE_SETTINGS += CODE_SIGN_STYLE
    QMAKE_MAC_XCODE_SETTING_CODE_SIGN_STYLE = Manual

    QMAKE_MAC_XCODE_SETTINGS += CODE_SIGN_IDENTITY
    QMAKE_MAC_XCODE_SETTING_CODE_SIGN_IDENTITY = Patrick Stinson

    QMAKE_MAC_XCODE_SETTINGS += PROVISIONING_PROFILE
    QMAKE_MAC_XCODE_SETTING_PROVISIONING_PROFILE = ad2c99d5-4c7d-4b6d-807e-91bafa49c92d
}