_PKDIAGRAM = $$PWD/../../pkdiagram/_pkdiagram

# HEADERS += $$_PKDIAGRAM/_pkdiagram.h


PK_ENTITLEMENTS.name = CODE_SIGN_ENTITLEMENTS
PK_ENTITLEMENTS.value = Family Diagram.entitlements
QMAKE_MAC_XCODE_SETTINGS += PK_ENTITLEMENTS

QMAKE_INFO_PLIST = Info.plist
ICON = PKDiagram-Filled.icns

CONFIG += precompiled_header
PRECOMPILED_HEADER = pkdiagram_pch.h
PRECOMPILED_SOURCE = pkdiagram_pch.cpp
HEADERS += pkdiagram_pch.h


beta {
	QMAKE_CFLAGS += -DPK_BETA_BUILD=1
	QMAKE_CXXFLAGS += -DPK_BETA_BUILD=1
}

alpha {
	QMAKE_CFLAGS += -DPK_ALPHA_BUILD=1
	QMAKE_CXXFLAGS += -DPK_ALPHA_BUILD=1
}

macx {

    include(../osx/osx.pri)

}

ios {

    include(../ios/ios.pri)

}


win32 {

    include(../win32/win32.pri)
}

