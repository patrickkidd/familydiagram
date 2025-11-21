"""
Third-party extensions.
"""

import os.path
import sys
import logging
import logging
import traceback

from pkdiagram.pyqt import QApplication
from pkdiagram import util


log = logging.getLogger(__name__)


class SessionTrackingHandler(logging.Handler):
    """
    A logging handler that sends log records to _activeSession.track().

    Configured via FD_TRACK_LOG_LEVEL environment variable to filter which
    log levels are sent to tracking. Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    Default is WARNING (only WARNING, ERROR, and CRITICAL are tracked).
    """

    def __init__(self, min_level=logging.WARNING):
        super().__init__(level=min_level)
        self._min_level = min_level

    def emit(self, record):
        global _activeSession

        try:
            if not _activeSession:
                return

            # Format the log message
            msg = self.format(record) if self.formatter else record.getMessage()

            # Include file and line number in extras for Datadog
            extras = {
                # "logger_name": record.name,
                # "pathname": record.pathname,
                # "filename": record.filename,
                # "lineno": record.lineno,
                # "funcName": record.funcName,
            }

            # Track the log message with extras
            _activeSession.log(msg, level=record.levelno, extras=extras)
        except Exception:
            # Silently ignore errors in the handler to avoid breaking logging
            self.handleError(record)


_excepthooks = []


def _excepthook(etype, value, tb):
    global _excepthooks

    for hook in _excepthooks:
        hook(etype, value, tb)


def _logging_excepthook(etype, value, tb):
    lines = traceback.format_exception(etype, value, tb)
    log.error("\n".join(lines))


_activeSession = None


def setActiveSession(session):
    global _activeSession

    _activeSession = session


def init_app(app: QApplication):
    if sys.excepthook != sys.__excepthook__:
        # already a custom excepthook, so keep it
        _excepthooks.append(sys.excepthook)
    # Installing an excepthook prevents a call to abort on exception from PyQt
    sys.excepthook = _excepthook

    _excepthooks.append(_logging_excepthook)
