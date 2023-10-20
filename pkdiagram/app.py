try:
    import pdytools # only exists for app bundle
except:
    IS_BUNDLE = False
else:
    IS_BUNDLE = True


def init():

    import sys, os.path, logging
    from pathlib import Path
    from . import appdirs

    def allFilter(record: logging.LogRecord):
        """ Add filenames for non-Qt records. """
        if not hasattr(record, 'pk_fileloc'):
            record.pk_fileloc = f"{record.filename}:{record.lineno}"
        return True

    LOG_FORMAT = '%(asctime)s %(pk_fileloc)-26s %(message)s'

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.addFilter(allFilter)
    consoleHandler.setFormatter(logging.Formatter(LOG_FORMAT))

    appDataDir = appdirs.user_data_dir('Family Diagram', appauthor='')
    if not os.path.isdir(appDataDir):
        Path(appDataDir).mkdir()
    fileName = 'log.txt' if IS_BUNDLE else 'log_dev.txt'
    filePath = os.path.join(appDataDir, fileName)
    if not os.path.isfile(filePath):
        Path(filePath).touch()
    fileHandler = logging.FileHandler(filePath, mode='a+')
    fileHandler.addFilter(allFilter)
    fileHandler.setFormatter(logging.Formatter(LOG_FORMAT))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[consoleHandler, fileHandler],
    )


def main(attach=False, prefsName=None):

    import sys, os.path, logging
    from . import util, MainWindow, Application, AppController

    log = logging.getLogger(__name__)


    import sysconfig

    # Python-3.8+ patch sysconfig._init_non_posix() to support _imp.extension_suffixes() == [] for pyqtdeploy
    def _init_non_posix_pyqtdeploy(vars):
        """Initialize the module as appropriate for NT"""
        # set basic install directories
        import _imp
        vars['LIBDEST'] = sysconfig.get_path('stdlib')
        vars['BINLIBDEST'] = sysconfig.get_path('platstdlib')
        vars['INCLUDEPY'] = sysconfig.get_path('include')
        vars['EXT_SUFFIX'] = None
        vars['EXE'] = '.exe'
        vars['VERSION'] = sysconfig._PY_VERSION_SHORT_NO_DOT
        vars['BINDIR'] = os.path.dirname(sysconfig._safe_realpath(sys.executable))
        vars['TZPATH'] = ''
    if sys.version_info[1] > 7:
        sysconfig._init_non_posix = _init_non_posix_pyqtdeploy

    # log.info(_imp.extension_suffixes())

    # log.info(sysconfig.get_path('purelib'))



    if attach:
        util.wait_for_attach()

    app = Application(sys.argv)
    if prefsName:
        prefs = util.Settings('vedanamedia', prefsName)
    else:
        prefs = util.prefs()
    controller = AppController(app, prefs, prefsName=prefsName)
    controller.init()
    
    mainWindow = MainWindow(
        appConfig=controller.appConfig,
        session=controller.session,
        prefs=prefs
    )
    mainWindow.init()

    controller.exec(mainWindow)
        
    mainWindow.deinit()
    controller.deinit()
    app.deinit()


# def main(*args, **kwargs):
#     import _pkdiagram
