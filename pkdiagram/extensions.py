"""
Third-party extensions.
"""

import os.path
import logging
import logging

from pkdiagram.pyqt import QApplication
from pkdiagram import util, version, pepper


log = logging.getLogger(__name__)


## Bugsnag


class AccumulativeLogHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._records = []

    def emit(self, record):
        self._records.append(record)

    def read(self):
        return "\n".join([self.format(record) for record in self._records])


def init_bugsnag(app: QApplication):

    if pepper.BUGSNAG_API_KEY and not util.IS_DEV and not util.IS_TEST:

        import ssl  # fix SSL cert errors from bugsnag

        ssl._create_default_https_context = ssl._create_unverified_context

        import bugsnag
        from bugsnag.handlers import BugsnagHandler

        root_folder_path = os.path.realpath(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
        )

        bugsnag.configure(
            api_key=pepper.BUGSNAG_API_KEY,
            project_root=root_folder_path,
            app_version=version.VERSION,
        )

        logger = logging.getLogger()
        handler = BugsnagHandler()
        # send only ERROR-level logs and above
        handler.setLevel(logging.WARNING)
        logger.addHandler(handler)

        accumulativeHandler = AccumulativeLogHandler()
        accumulativeHandler.addFilter(util.logging_allFilter)
        accumulativeHandler.setFormatter(logging.Formatter(util.LOG_FORMAT))
        logger.addHandler(handler)

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

        def bugsnag_before_notify(event):
            if isinstance(event.exception, KeyboardInterrupt):
                return False
            # Not sure what to do without a mainwindow without breaking encapsulation
            mainwindow = findTheMainWindow()
            if not mainwindow:
                return
            for handler in logging.getLogger().handlers:
                handler.flush()
            user = mainwindow.session.user
            event.user = {
                "id": user.username,
                "name": f"{user.first_name} {user.last_name}",
                "email": user.username,
            }
            event.add_tab(
                "account",
                {
                    "licenses": [
                        license.policy.name
                        for license in user.licenses
                        if license.active
                    ]
                },
            )
            event.add_tab("device", {"os.uname": os.uname()})
            for handler in logging.getLogger().handlers:
                if isinstance(handler, util.AccumulativeLogHandler):
                    event.add_tab("log.txt", handler.read())

        bugsnag.before_notify(bugsnag_before_notify)


def init_app(app: QApplication):
    init_bugsnag(app)
