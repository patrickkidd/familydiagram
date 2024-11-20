import os, os.path, sys, traceback, logging

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
    QNetworkAccessManager,
    QNetworkReply,
)
from pkdiagram import util, version, extensions
from pkdiagram.app.qmlutil import QmlUtil

CUtil = util.CUtil


log = logging.getLogger(__name__)


class Application(QApplication):

    def __init__(self, *args, prefsName=None, **kwargs):

        import logging  # Won't pull in from module scope

        # TODO: Should not be global
        util._prefs = self.makeSettings(prefsName=prefsName)

        # prefsPath = QFileInfo(util.prefs().fileName()).filePath()
        util.prefs().setAutoSave(True)
        util.prefs().setValue("lastVersion", version.VERSION)

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

        ## Python exception handling

        def no_abort(etype, value, tb):
            """
            The one and only excepthook.
            Installing an excepthook prevent a call to abort on exception from PyQt
            """
            lines = traceback.format_exception(etype, value, tb)
            for line in lines:
                log.error(line[:-1])

            if "pytest" in sys.modules:
                sys.modules["pytest"].fail(str(value), pytrace=False)

            # bugsnag
            if "bugsnag" in sys.modules:
                sys.modules["bugsnag"].legacy.default_client.notify_exc_info(
                    etype, value, tb
                )

        extensions.init_app(self)

        # After extensions
        self._excepthook_was = sys.excepthook
        if not "pytest" in sys.modules:
            sys.excepthook = no_abort

        QApplication.setAttribute(
            Qt.AA_EnableHighDpiScaling, True
        )  # before app creation
        # cargs = list(args[0])
        # if IS_TEST:
        #     cargs += ('-platform', 'offscreen')
        # args[0].append(
        #     "-qmljsdebugger=port:1234,block",
        # )
        super().__init__(*args, **kwargs)

        self._qnam = QNetworkAccessManager(self)

        # TODO: Should not be global
        self._qmlUtil = QmlUtil(self)

        self.appFilter = util.AppFilter(
            self
        )  # Move global app filtering to C++ for speed
        self.installEventFilter(self.appFilter)

        CUtil.startup()  # after QApplication() for QFileSystemWatcher
        util.IS_UI_DARK_MODE = CUtil.instance().isUIDarkMode()

        if util.IS_DEV and util.prefs().value(
            "iCloudWasOn", defaultValue=False, type=bool
        ):
            lastiCloudPath = util.prefs().value("lastiCloudPath", defaultValue=None)
            if lastiCloudPath is not None:
                # Debug("Forcing docRoot for [dev]:", lastiCloudPath)
                CUtil.instance().forceDocsPath(lastiCloudPath)
        else:
            localDocsPath = util.prefs().value("localDocsPath", type=str)
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
                lastiCloudPath = util.prefs().value("lastiCloudPath", defaultValue=None)
                if iCloudRoot != lastiCloudPath:
                    util.prefs().setValue("lastiCloudPath", iCloudRoot)

        iCloudDevPostInit()
        CUtil.instance().deinit()
        CUtil.shutdown()

        if not "pytest" in sys.modules:
            sys.excepthook = self._excepthook_was
        self._excepthook_was = None

    # def onPaletteChanged(self):
    #     self.here(CUtil.isUIDarkMode())

    @staticmethod
    def makeSettings(prefsName=None) -> QSettings:
        if prefsName is not None:
            pass
        elif util.IS_WINDOWS:
            prefsName = "familydiagram"
        elif util.IS_IOS:
            prefsName = "familydiagram"
        elif util.IS_APPLE:
            prefsName = "familydiagrammac"

        return util.Settings("vedanamedia", prefsName)

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

    def qnam(self) -> QNetworkAccessManager:
        return self._qnam
