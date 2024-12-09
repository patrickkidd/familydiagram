include(win32-config.prf)

LIBS += -lcrypt32
# fatal error C1189: #error:  The C++ Standard Library forbids macroizing keywords. Enable warning C4005 to find the forbidden macro.
# DEFINES += _XKEYCHECK_H

RC_ICONS = PKDiagram-Filled.ico

RESOURCES += windows.qrc

QMAKE_CXXFLAGS += -DPK_USE_SPARKLE=1

INCLUDEPATH += $$[QT_INSTALL_PREFIX]/include/QtCore/5.15.16 $$[QT_INSTALL_PREFIX]/include/QtGui/5.15.16

# this is only here because sometimes you need to debug C++ and there is no debug qt to link to
release {
    QMAKE_CXXFLAGS += /Zi /Od /Zm1000
    # QMAKE_CXXFLAGS += /Zc:wchar_t- # convert QString to LPCWSTR
    QMAKE_LFLAGS += /DEBUG /OPT:NOREF

    #QMAKE_CXXFLAGS_RELEASE += -MT
    #QMAKE_CFLAGS_RELEASE += -MT

    #QMAKE_CXXFLAGS_RELEASE -= -MD
    #QMAKE_CFLAGS_RELEASE -= -MD
}