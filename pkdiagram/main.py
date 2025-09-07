import sys, os.path, logging
from optparse import OptionParser

from pkdiagram.pyqt import (
    Qt,
    QUrl,
    QSettings,
    QWidget,
    QVBoxLayout,
    QOpenGLWidget,
    QSurfaceFormat,
    QEventLoop,
)
from pkdiagram import util, extensions
from pkdiagram.mainwindow import MainWindow
from pkdiagram.app import Application, AppController


_log = logging.getLogger(__name__)

import sysconfig


# Python-3.8+ patch sysconfig._init_non_posix() to support _imp.extension_suffixes() == [] for pyqtdeploy
def _init_non_posix_pyqtdeploy(vars):
    """Initialize the module as appropriate for NT"""
    # set basic install directories
    import _imp

    vars["LIBDEST"] = sysconfig.get_path("stdlib")
    vars["BINLIBDEST"] = sysconfig.get_path("platstdlib")
    vars["INCLUDEPY"] = sysconfig.get_path("include")
    vars["EXT_SUFFIX"] = None
    vars["EXE"] = ".exe"
    vars["VERSION"] = sysconfig._PY_VERSION_SHORT_NO_DOT
    vars["BINDIR"] = os.path.dirname(sysconfig._safe_realpath(sys.executable))
    vars["TZPATH"] = ""


if sys.version_info[1] > 7:
    sysconfig._init_non_posix = _init_non_posix_pyqtdeploy

# _log.info(_imp.extension_suffixes())

# _log.info(sysconfig.get_path('purelib'))


def main():
    import sys  # no idea

    ENABLE_THERAPIST = util.IS_DEV or util.IS_IOS

    parser = OptionParser()
    parser.add_option(
        "-v",
        "--version",
        dest="version",
        action="store_true",
        help="Print the version",
        default=False,
    )
    if ENABLE_THERAPIST:
        parser.add_option(
            "-t",
            "--therapist",
            dest="therapist",
            action="store_true",
            help="Run the therapist UI",
        )
    if sys.platform == "win32":
        parser.add_option(
            "-c",
            "--windows-console",
            dest="windows_console",
            action="store_true",
            help="Show the windows app console for troubleshooting",
            default=False,
        )
    parser.add_option(
        "-p",
        "--prefs-name",
        dest="prefsName",
        help="The preferences scope to use when testing",
    )
    options, args = parser.parse_args(sys.argv)

    if util.IS_IOS:
        options.therapist = True

    if sys.platform == "win32" and options.windows_console:
        # Allocates a console and redirects stdout/stderr for Windows.
        from _pkdiagram import CUtil

        _log.info("Opening windows debug console...")

        CUtil.dev_showDebugConsole()

        import sys

        # Reopen stdout/stderr in the new console
        sys.stdout = open("CONOUT$", "w")
        sys.stderr = open("CONOUT$", "w")

        import atexit

        atexit.register(lambda: input("\nPress Enter to close..."))

    if options.version:

        # import os.path, importlib

        from . import version

        print(version.VERSION)

    elif ENABLE_THERAPIST and options.therapist:
        from pkdiagram.therapist import TherapistAppController

        util.init_logging()

        app = Application(
            sys.argv, Application.Type.Mobile, prefsName=options.prefsName
        )
        controller = TherapistAppController(app)

        import sys
        from PyQt5.QtQml import QQmlApplicationEngine

        engine = QQmlApplicationEngine()
        engine.addImportPath("resources:")
        controller.init(engine)

        engine.load("resources:qml/TherapistApplication.qml")
        extensions.setActiveSession(session=controller.session)

        ret = app.exec_()

        controller.deinit()
        app.sendPostedEvents()
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents)
        sys.exit(ret)

    else:
        util.init_logging()

        app = Application(
            sys.argv, Application.Type.Desktop, prefsName=options.prefsName
        )
        controller = AppController(app, prefsName=options.prefsName)
        controller.init()

        mainWindow = MainWindow(
            appConfig=controller.appConfig, session=controller.session
        )
        mainWindow.init()

        extensions.setActiveSession(session=controller.session)
        controller.exec(mainWindow)

        mainWindow.deinit()
        controller.deinit()
        app.deinit()


if __name__ == "__main__":
    main()
