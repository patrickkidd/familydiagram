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


def _main_impl():
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
            "--personal",
            dest="personal",
            action="store_true",
            help="Run the personal mobile UI",
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
    parser.add_option(
        "--test-error-logging",
        dest="test_error_logging",
        action="store_true",
        help="Force an exception to test error logging to startup_errors.txt",
        default=False,
    )
    options, args = parser.parse_args(sys.argv)

    if util.IS_IOS:
        options.personal = True

    # Handle console allocation for Windows
    if sys.platform == "win32" and (options.windows_console or options.version):
        # Allocates a console and redirects stdout/stderr for Windows.
        from _pkdiagram import CUtil

        _log.info("Opening windows debug console...")

        CUtil.dev_showDebugConsole()

        # Reopen stdout/stderr in the new console
        sys.stdout = open("CONOUT$", "w")
        sys.stderr = open("CONOUT$", "w")

        # Only add the "Press Enter to close" for --windows-console, not for --version
        if options.windows_console:
            import atexit

            atexit.register(lambda: input("\nPress Enter to close..."))

    if options.test_error_logging:
        raise RuntimeError("Test error logging to startup_errors.txt")

    if options.version:

        # import os.path, importlib

        from . import version

        print(version.VERSION)

        # Exit after printing version to avoid starting the GUI
        sys.exit(0)

    elif ENABLE_THERAPIST and options.personal:
        from pkdiagram.personal import PersonalAppController

        util.init_logging()

        app = Application(
            sys.argv, Application.Type.Mobile, prefsName=options.prefsName
        )
        controller = PersonalAppController(app)

        import sys
        from PyQt5.QtQml import QQmlApplicationEngine

        engine = QQmlApplicationEngine()
        engine.addImportPath("resources:")
        controller.init(engine)

        engine.load("resources:qml/PersonalApplication.qml")
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


def main():

    import os
    from datetime import datetime
    import traceback
    import sys

    try:
        _main_impl()
    except Exception as e:

        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        error_log_path = os.path.join(desktop_dir, "startup_errors.txt")

        from . import version

        with open(error_log_path, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n=== {timestamp} ===\n")
            f.write(f"Family Diagram: {version.VERSION}\n")
            f.write(f"Platform: {sys.platform}\n")
            f.write(f"Executable: {sys.executable}\n")
            f.write(f"Critical startup error: {str(e)}\n")
            f.write("Traceback:\n")
            f.write(traceback.format_exc())
            f.write("\n")
            f.flush()

        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"Family Diagram failed to start.\n\nError: {str(e)}\n\nCheck the log file at:\n{error_log_path}",
                    "Family Diagram Startup Error",
                    0x10,  # MB_ICONERROR
                )
            except:
                pass

        # Re-raise for normal Python error handling
        raise


if __name__ == "__main__":
    main()
