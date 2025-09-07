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


_excepthooks = []


def _excepthook(etype, value, tb):
    global _excepthooks

    for hook in _excepthooks:
        hook(etype, value, tb)


def _logging_excepthook(etype, value, tb):
    lines = traceback.format_exception(etype, value, tb)
    log.error("\n".join(lines))


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


_activeSession = None


def setActiveSession(session):
    global _activeSession

    _activeSession = session


def datadog_excepthook(etype, value, tb):
    global _activeSession

    if issubclass(etype, KeyboardInterrupt):
        sys.__excepthook__(etype, value, tb)
        return

    if not _activeSession:
        return

    _activeSession.error(etype, value, tb)


def init_datadog(app: QApplication):
    global _excepthooks

    _excepthooks.append(datadog_excepthook)


def init_app(app: QApplication):
    if sys.excepthook != sys.__excepthook__:
        # already a custom excepthook, so keep it
        _excepthooks.append(sys.excepthook)
    # Installing an excepthook prevents a call to abort on exception from PyQt
    sys.excepthook = _excepthook
    init_logging()
    # if not util.IS_DEV:
    init_datadog(app)
