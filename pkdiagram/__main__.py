try:
    import pdytools  # only exists for app bundle
except:
    IS_BUNDLE = False
else:
    IS_BUNDLE = True


def main():

    import sysconfig
    import sys, os.path, logging
    from optparse import OptionParser

    log = logging.getLogger(__name__)

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

    parser = OptionParser()
    parser.add_option(
        "-v",
        "--version",
        dest="version",
        action="store_true",
        help="Print the version",
        default=False,
    )
    parser.add_option(
        "-n",
        "--prefs-name",
        dest="prefs_name",
        help="What alias to load preferences from, useful for debugging multiple instances.",
    )
    options, args = parser.parse_args(sys.argv)
    if options.version:

        from pkdiagram import version

        print(version.VERSION)
        return
    else:
        from pkdiagram import util, Application, AppController, MainWindow

        app = Application(sys.argv, prefsName=options.prefs_name)
        controller = AppController(app, util.prefs(), prefsName=options.prefs_name)
        controller.init()

        mainWindow = MainWindow(
            appConfig=controller.appConfig,
            session=controller.session,
            prefs=util.prefs(),
        )
        mainWindow.init()

        controller.exec(mainWindow)

        mainWindow.deinit()
        controller.deinit()
        app.deinit()


main()
