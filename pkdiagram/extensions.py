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


_excepthooks = []


def _excepthook(etype, value, tb):
    global _excepthooks

    for hook in _excepthooks:
        hook(etype, value, tb)


def _logging_excepthook(etype, value, tb):
    lines = traceback.format_exception(etype, value, tb)
    for line in lines:
        log.error(line[:-1])


def init_logging():
    global _excepthooks

    _excepthooks.append(_logging_excepthook)

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

    mainwindow = findTheMainWindow()
    if not mainwindow:
        return

    mainwindow.session.error(etype, value, tb)


def init_datadog(app: QApplication):
    global _excepthooks

    _excepthooks.append(datadog_excepthook)


def init_app(app: QApplication):
    sys.excepthook = _excepthook
    init_logging()
    if not util.IS_DEV:
        init_datadog(app)
