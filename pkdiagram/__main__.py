try:
    import pdytools  # only exists for app bundle
except:
    IS_BUNDLE = False
else:
    IS_BUNDLE = True


def main(attach=False, prefsName=None):

    import sys, os.path, logging
    from optparse import OptionParser

    from . import util, MainWindow, Application, AppController

    log = logging.getLogger(__name__)

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

    # log.info(_imp.extension_suffixes())

    # log.info(sysconfig.get_path('purelib'))

    parser = OptionParser()
    parser.add_option(
        "-v",
        "--version",
        dest="version",
        action="store_true",
        help="Print the version",
        default=False,
    )
    options, args = parser.parse_args(sys.argv)
    if options.version:

        # import os.path, importlib

        from . import version

        print(version.VERSION)

        # PKDIAGRAM = os.path.realpath(os.path.dirname(__file__))
        # spec = importlib.util.spec_from_file_location(
        #     "version", os.path.join(PKDIAGRAM, "version.py")
        # )
        # version = importlib.util.module_from_spec(spec)
        # spec.loader.exec_module(version)
        # print(version.VERSION)
        return

    if attach:
        util.wait_for_attach()

    app = Application(sys.argv)
    if prefsName:
        prefs = util.Settings("vedanamedia", prefsName)
    else:
        prefs = util.prefs()
    controller = AppController(app, prefs, prefsName=prefsName)
    controller.init()

    mainWindow = MainWindow(
        appConfig=controller.appConfig, session=controller.session, prefs=prefs
    )
    mainWindow.init()

    controller.exec(mainWindow)

    mainWindow.deinit()
    controller.deinit()
    app.deinit()


# def main(*args, **kwargs):
#     import _pkdiagram


main
