"""
Third-party extensions.
"""

import sys
import logging
import logging
import traceback

from pkdiagram.pyqt import QApplication
from pkdiagram import util


log = logging.getLogger(__name__)


class AccumulativeLogHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._records = []

    def emit(self, record):
        self._records.append(record)

    def read(self):
        return "\n".join([self.format(record) for record in self._records])


def findTheMainWindow():
    app = QApplication.instance()
    if not app:
        return
    windows = app.topLevelWidgets()
    if len(windows) == 1:
        window = windows[0]
    else:
        window = app.activeWindow()
    if window and hasattr(window, "session"):
        return window


def init_logging():

    logger = logging.getLogger()

    # Store the whole log.txt for this session in memory so as to post it with
    # each error log
    accumulativeHandler = AccumulativeLogHandler()
    accumulativeHandler.addFilter(util.logging_allFilter)
    accumulativeHandler.setFormatter(logging.Formatter(util.LOG_FORMAT))
    logger.addHandler(accumulativeHandler)


def datadog_excepthook(etype, value, tb):
    """
    Installing an excepthook prevents a call to abort on exception from PyQt
    """

    if issubclass(etype, KeyboardInterrupt):
        sys.__excepthook__(etype, value, tb)
        return

    lines = traceback.format_exception(etype, value, tb)
    for line in lines:
        log.error(line[:-1])

    mainwindow = findTheMainWindow()
    if not mainwindow:
        return

    mainwindow.session.error(etype, value, tb)


def init_datadog(app: QApplication):
    sys.excepthook = datadog_excepthook


def init_app(app: QApplication):
    init_logging()
    if not util.IS_DEV:
        init_datadog(app)
