import os.path
import logging
import json
import logging
import time
import base64
from typing import Union, Callable

import pydantic

from pkdiagram.pyqt import (
    pyqtSignal,
    QApplication,
    QObject,
    QNetworkRequest,
    QNetworkReply,
    QUrl,
)
from pkdiagram import util, version, pepper
from pkdiagram.server_types import Server, HTTPError


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

        logger = logging.getLogger(__name__)
        handler = BugsnagHandler()
        # send only ERROR-level logs and above
        handler.setLevel(logging.ERROR)
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


## Mixpanel


import pickle
from uuid import uuid4

QNAM = util.QNAM


class MixpanelItem(pydantic.BaseModel):
    def __init__(self, **data):
        super().__init__(**data)
        self.properties["$insert_id"] = str(uuid4())


class MixpanelEvent(MixpanelItem):
    """
    A queued Mixpanel event, either in memory or on disk.
    """

    eventName: str
    username: str
    properties: dict
    time: int


class MixpanelProfile(MixpanelItem):
    """
    A queued Mixpanel user profile update, either in memory or on disk.
    """

    username: str
    first_name: str
    last_name: str
    email: str
    properties: dict


class Analytics(QObject):
    """
    TODO: Rename to MixpanelManager

    Manage an offline-capable queue of analytics events.
    """

    RETRY_TIMER_MS = 7000
    MIXPANEL_BATCH_MAX = 2000

    completedOneRequest = pyqtSignal(QNetworkReply)

    def __init__(
        self, mixpanel_project_id=None, mixpanel_project_token=None, parent=None
    ):
        super().__init__(parent)
        if mixpanel_project_token is None:
            raise ValueError("mixpanel_project_token is required")
        self._mixpanel_project_id = mixpanel_project_id
        self._mixpanel_project_token = mixpanel_project_token
        # Queue up events with timestamps stored and in order they are sent
        self._eventQueue = []
        # Cache the last profile data since only the most recent ones apply
        self._profilesCache = {}
        self._currentRequest = None
        self._numEventsSent = 0
        self._timer = None

    def filePath(self) -> str:
        return os.path.join(util.appDataDir(), "analytics.pickle")

    def init(self):
        if os.path.isfile(self.filePath()):
            with open(self.filePath(), "rb") as f:
                self._eventQueue, self._profilesCache = pickle.load(f)
        self._timer = self.startTimer(self.RETRY_TIMER_MS)
        self.tick()

    def _writeToDisk(self):
        log.debug(
            f"Writing {len(self._eventQueue)} MixpanelEvent's and {len(self._profilesCache)} MixpanelProfile's"  #  {self.filePath()}"
        )
        with open(self.filePath(), "wb") as f:
            pickle.dump((self._eventQueue, self._profilesCache), f)

    def timerEvent(self, e):
        self._writeToDisk()
        self.tick()

    def deinit(self):
        if self._timer is None:
            return
        self.killTimer(self._timer)
        self._timer = None
        if self._currentRequest:
            util.wait(self.completedOneRequest)
        self._writeToDisk()

    def numProfilesQueued(self) -> int:
        return len(self._profilesCache.keys())

    def numEventsQueued(self) -> int:
        return len(self._eventQueue)

    def numEventsSent(self) -> int:
        return self._numEventsSent

    def currentRequest(self) -> QNetworkRequest:
        return self._currentRequest

    def importUrl(self) -> str:
        return f"https://api.mixpanel.com/import?strict=1&project_id={self._mixpanel_project_id}"

    def profilesUrl(self) -> str:
        return f"https://api.mixpanel.com/engage#profile-batch-update"

    def sendJSONRequest(self, url, data, verb, success: Callable):
        self._currentRequest = QNetworkRequest(QUrl(url))
        self._currentRequest.setRawHeader(b"Content-Type", b"application/json")
        self._currentRequest.setRawHeader(b"Accept", b"application/json")
        self._currentRequest.setRawHeader(
            b"Authorization",
            b"Basic "
            + base64.b64encode(f"{self._mixpanel_project_token}:".encode("utf-8")),
        )
        self._currentReply = QNAM.instance().sendCustomRequest(
            self._currentRequest, verb, json.dumps(data).encode("utf-8")
        )

        def onFinished():
            reply = self._currentReply
            self._currentReply.finished.disconnect(onFinished)
            try:
                Server.checkHTTPReply(self._currentReply, statuses=[200])
            except HTTPError as e:
                log.debug(f"Mixpanel error: {self._currentReply.errorString()}")
            else:
                success()
            self.completedOneRequest.emit(self._currentReply)
            self._currentRequest = None
            self._currentReply = None
            # skip if no internet connection
            if (
                reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) != 0
                and reply.error() != QNetworkReply.HostNotFoundError
            ):
                self.tick()

        self._currentReply.finished.connect(onFinished)

    def _postNextEvents(self):
        chunk = self._eventQueue[: self.MIXPANEL_BATCH_MAX]
        data = [
            {
                "event": x.eventName,
                "properties": dict(distinct_id=x.username, time=x.time, **x.properties),
            }
            for x in chunk
        ]

        def onSuccess():
            # log.debug(f"Sent {len(self._currentRequest._chunk)} events to Mixpanel")
            self._numEventsSent += len(self._currentRequest._chunk)
            for event in self._currentRequest._chunk:
                self._eventQueue.remove(event)
            # in case there is a dangling reference somewhere
            self._currentRequest._chunk = None
            self._writeToDisk()

        log.debug(f"Attempting to send {len(chunk)} events to Mixpanel...")
        self.sendJSONRequest(self.importUrl(), data, b"POST", onSuccess)
        # so they can be popped from the queue afterward
        self._currentRequest._chunk = chunk

    def _postProfiles(self):
        data = [
            {
                "$token": self._mixpanel_project_token,
                "$distinct_id": username,
                "$set": {
                    "$first_name": x.first_name,
                    "$last_name": x.last_name,
                    "$email": x.email,
                    "roles": x.properties.get("roles", []),
                    "license": x.properties.get("licenses", []),
                },
            }
            for username, x in self._profilesCache.items()
        ]

        def onSuccess():
            log.debug(
                f"Successfully sent {len(self._profilesCache.keys())} profiles to Mixpanel"
            )
            self._profilesCache = {}
            self._writeToDisk()

        log.debug(
            f"Attempting to send {len(self._profilesCache.keys())} profiles to Mixpanel..."
        )
        self.sendJSONRequest(self.profilesUrl(), data, b"POST", onSuccess)

    def tick(self):
        """
        Idempotent check and send. Only one request at a time. Prioritize
        profiles.
        """
        if self._currentRequest:
            return
        elif self._profilesCache:
            self._postProfiles()
        elif self._eventQueue:
            self._postNextEvents()

    def send(self, item: Union[MixpanelEvent, MixpanelProfile], defer=False):
        if isinstance(item, MixpanelEvent):
            self._eventQueue.append(item)
        elif isinstance(item, MixpanelProfile):
            self._profilesCache[item.username] = item
        else:
            raise ValueError(f"Invalid analytics item type: {type(item)}")
        if not defer:
            self.tick()


_analytics = None


def analytics() -> Analytics:
    """
    TODO: Refactor out.
    """
    global _analytics

    return _analytics


def init_analytics(app: QApplication):
    global _analytics

    if not pepper.MIXPANEL_PROJECT_ID:
        log.warning(
            "pepper.MIXPANEL_PROJECT_ID is not set, skipping analytics initialization"
        )
        return

    if not pepper.MIXPANEL_PROJECT_TOKEN:
        log.warning(
            "pepper.MIXPANEL_PROJECT_TOKEN is not set, skipping analytics initialization"
        )
        return

    if util.IS_TEST:
        log.debug("Skipping Mixpanel initialization for automated tests")
        return

    _analytics = Analytics(
        mixpanel_project_id=pepper.MIXPANEL_PROJECT_ID,
        mixpanel_project_token=pepper.MIXPANEL_PROJECT_TOKEN,
    )


## App


def init_app(app: QApplication):
    init_bugsnag(app)
    init_analytics(app)
