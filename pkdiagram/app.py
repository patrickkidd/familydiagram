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


import sys
import os

import importlib.util


def import_module_from_file(relative_fpath: str):
    this_path = os.path.dirname(os.path.abspath(__file__))
    relative_fpath = os.path.join(this_path, relative_fpath.replace("/", os.sep))
    basename = os.path.splitext(os.path.basename(relative_fpath))[0]
    spec = importlib.util.spec_from_file_location(basename, relative_fpath)
    if spec is None:
        raise ImportError(f"Cannot find module at {relative_fpath}")
    mod = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise ImportError(f"Cannot load module at {relative_fpath}")
    spec.loader.exec_module(mod)
    return mod


def main(*args, **kwargs):
    import sys

    sys.path.append(
        "/Users/patrick/dev/familydiagram/.venv/lib/python3.10/site-packages"
    )
    import pip

    # from pdytools import qrcimporter

    # from pip._vendor.distlib.resources import register_finder

    # register_finder(pip._vendor.distlib, qrcimporter)

    from pkdiagram import site

    sys.modules["site"] = site

    pip.main(["install", "flask"])
