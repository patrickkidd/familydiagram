import os, os.path, sys, traceback, logging, enum

from _pkdiagram import AppFilter
from pkdiagram.pyqt import (
    Qt,
    QApplication,
    QIcon,
    QPixmap,
    QFileInfo,
    qInstallMessageHandler,
    QStandardPaths,
    QFontDatabase,
    QSettings,
    QUrl,
)
from pkdiagram import util, version, extensions
from pkdiagram.app import QmlUtil

CUtil = util.CUtil


log = logging.getLogger(__name__)


class Application(QApplication):

    class Type(enum.StrEnum):
        Desktop = "desktop"
        Mobile = "mobile"
        Test = "test"

    def __init__(self, argv: list[str], appType: Type, prefsName=None, **kwargs):
        def qtMessageHandler(msgType, context, msg):
            GREP_V = [
                "QMacCGContext:: Unsupported paint engine type",
                "TouchPointPressed without previous release event",
                "CreateFontFaceFromHDC",
                "Tried to flush backingstore without painting to it first",
                "This plugin does not support createPlatformOpenGLContext!",
                "This plugin does not support propagateSizeHints()",
                "failed to acquire GL context to resolve capabilities, using defaults..",
                "Could not find virtual screen for QCocoaScreen",
                "This plugin does not support raise()",
                "Qt Quick Layouts: Detected recursive rearrange. Aborting after two iterations.",
                "QOpenGLFramebufferObject: Framebuffer incomplete attachment.",
                "QOpenGLFramebufferObject: Framebuffer incomplete, missing attachment.",
                "Binding loop detected for property",
                "QObject::connect: No such signal QQuickPalette::destroyed(QObject *)",
                "QObject::connect: No such signal QQuickIcon::destroyed(QObject *)",
                "QObject::connect: No such signal QQuickFontValueType::destroyed(QObject *)",
                "QObject::connect: No such signal QQmlEasingValueType::destroyed(QObject *)",
            ]
            for line in GREP_V:
                if line in msg:
                    return

            logging.getLogger().info(
                msg,
                extra={
                    "pk_fileloc": f"{QFileInfo(context.file).fileName()}:{context.line}",
                },
            )

        qInstallMessageHandler(qtMessageHandler)

        extensions.init_app(self)

        QApplication.setAttribute(
            Qt.AA_EnableHighDpiScaling, True
        )  # before app creation
        # cargs = list(args[0])
        # if IS_TEST:
        #     cargs += ('-platform', 'offscreen')
        # args[0].append(
        #     "-qmljsdebugger=port:1234,block",
        # )
        super().__init__(argv, **kwargs)

        self.setQuitOnLastWindowClosed(True)

        self._appType = appType
        self._prefsName = prefsName
        self._prefs = None
        self.pendingUrlOpen = None
        # prefsPath = QFileInfo(self.prefs().fileName()).filePath()
        self.prefs().setValue("lastVersion", version.VERSION)

        # TODO: Should not be global
        self._qmlUtil = QmlUtil(self)

        # Move global app filtering to C++ for speed
        self.appFilter = AppFilter(self)
        self.appFilter.urlOpened.connect(self.onUrlOpened)
        self.installEventFilter(self.appFilter)

        # Register Windows URL scheme on startup
        if util.IS_WINDOWS:
            util.registerURLScheme()

        CUtil.startup()  # after QApplication() for QFileSystemWatcher
        util.IS_UI_DARK_MODE = CUtil.instance().isUIDarkMode()

        if util.IS_DEV and self.prefs().value(
            "iCloudWasOn", defaultValue=False, type=bool
        ):
            lastiCloudPath = self.prefs().value("lastiCloudPath", defaultValue=None)
            if lastiCloudPath is not None:
                # Debug("Forcing docRoot for [dev]:", lastiCloudPath)
                CUtil.instance().forceDocsPath(lastiCloudPath)
        else:
            localDocsPath = self.prefs().value("localDocsPath", type=str)
            CUtil.instance().forceDocsPath(localDocsPath)

        # def _onQmlWarning(warnings):
        #     for warning in warnings:
        #         log.warning(warning.toString())

        # self.paletteChanged.connect(self.onPaletteChanged)

        # self.osOpenedFile = None
        ret1 = QFontDatabase.addApplicationFont(
            util.QRC + "fonts/SF-Pro-Text-Regular.otf"
        )
        ret2 = QFontDatabase.addApplicationFont(util.QRC + "fonts/SF-Pro-Text-Bold.otf")
        ret3 = QFontDatabase.addApplicationFont(
            util.QRC + "fonts/SF-Pro-Display-Bold.otf"
        )
        ret4 = QFontDatabase.addApplicationFont(
            util.QRC + "fonts/Helvetica65Medium_22443.ttf"
        )
        ret5 = QFontDatabase.addApplicationFont(
            util.QRC + "fonts/HelveticaNeueBold.otf"
        )
        # appFont = QFont('Segoe UI', 11) # , QApplication.font().pixelSize())
        # QApplication.setFont(appFont)

        # self.setQuitOnLastWindowClosed(True)
        self.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        if util.IS_DEV:
            self.setWindowIcon(QIcon(QPixmap(util.QRC + "PKDiagram.png")))
        self.focusWindowChanged.connect(self.onFocusWindowChanged)
        self.firstFocusWindow = None

        # Copy resource files

        files = [
            # 'misc/User-Manual'
        ]
        if util.IS_WINDOWS:
            files += [
                "misc/WinSparkle.dll",
            ]
        appDataDir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        os.makedirs(appDataDir, exist_ok=True)
        for fileName in files:
            inFilePath = util.QRC + fileName
            outFilePath = os.path.join(appDataDir, fileName)
            util.copyFileOrDir(inFilePath, outFilePath)

        # C++ Init

        CUtil.instance().init()  # blocking now, at end of __init__()
        self._qmlUtil.initColors()  # After CUtil.init()

    def deinit(self):
        def iCloudDevPostInit():
            iCloudRoot = CUtil.instance().iCloudDocsPath()
            if iCloudRoot:
                lastiCloudPath = self.prefs().value("lastiCloudPath", defaultValue=None)
                if iCloudRoot != lastiCloudPath:
                    self.prefs().setValue("lastiCloudPath", iCloudRoot)

        iCloudDevPostInit()
        CUtil.instance().deinit()
        CUtil.shutdown()

    def prefs(self):
        if not self._prefs:
            if self._prefsName is None:
                if util.IS_IOS or util.IS_WINDOWS:
                    self._prefsName = "familydiagram"
                elif util.IS_MAC:
                    self._prefsName = "familydiagrammac"
            self._prefs = QSettings("vedanamedia", self._prefsName)
        return self._prefs

    # def onPaletteChanged(self):
    #     self.here(CUtil.isUIDarkMode())

    def onUrlOpened(self, url: QUrl):
        """
        Catches it on launche before the AppController is setup.
        """
        self.pendingUrlOpen = url

    def onFocusWindowChanged(self, w):
        if self.firstFocusWindow is None and w:
            self.firstFocusWindow = w
            # self.here('TODO: Test not refreshing palette on first window')
            # self.paletteChanged.emit(self.activeWindow().palette())

    # def event(self, e):
    #     """ Port to C++ for speed? There aren't many events coming through here actually..."""
    #     if e.type() == QEvent.FileOpen:
    #         if util.suffix(e.file()) != util.EXTENSION:
    #             return False
    #         # open it up later to avoid a crash
    #         self.osOpenedFile = e.file()
    #         commands.trackApp('Open file from Dock')
    #         return True
    #     return super().event(e)

    def qmlUtil(self):
        return self._qmlUtil

    def appType(self) -> Type:
        return self._appType
