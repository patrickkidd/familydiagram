import os.path
import logging
import json
import logging
import base64
import pickle
import enum
from uuid import uuid4
from typing import Union, Callable
from dataclasses import dataclass

from pkdiagram.pyqt import (
    pyqtSignal,
    QObject,
    QNetworkRequest,
    QNetworkReply,
    QUrl,
)
from pkdiagram import util, version
from pkdiagram.qnam import QNAM


log = logging.getLogger(__name__)


@dataclass
class MixpanelItem:

    properties: dict

    def __post_init__(self):
        self.properties["$insert_id"] = str(uuid4())


@dataclass
class MixpanelEvent(MixpanelItem):
    """
    A queued Mixpanel event, either in memory or on disk.
    """

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.time, float):
            self.time = int(self.time)

    eventName: str
    time: int
    username: str = None


class DatadogLogLevel(enum.Enum):
    Info = "info"
    Error = "error"


@dataclass
class DatadogLog:
    timestamp: int
    message: str
    host: str = "<desktop>"
    service: str = "gui"
    level: str = "info"
    username: str = None
    tags: list[str] = None


@dataclass
class MixpanelProfile(MixpanelItem):
    """
    A queued Mixpanel user profile update, either in memory or on disk.
    """

    username: str
    first_name: str
    last_name: str
    email: str


class Analytics(QObject):
    """
    TODO: Rename to MixpanelManager

    Manage an offline-capable queue of analytics events.
    """

    RETRY_TIMER_MS = 7000
    MIXPANEL_BATCH_MAX = 2000
    DATADOG_BATCH_MAX = 1000

    completedOneRequest = pyqtSignal(QNetworkReply)

    def __init__(
        self,
        mixpanel_project_id=None,
        mixpanel_project_token=None,
        datadog_api_key: str = None,
        parent=None,
    ):
        super().__init__(parent)
        if mixpanel_project_token is None:
            raise ValueError("mixpanel_project_token is required")
        self._mixpanel_project_id = mixpanel_project_id
        self._mixpanel_project_token = mixpanel_project_token
        self._datadog_api_key = datadog_api_key
        self._enabled = True
        # Queue up events with timestamps stored and in order they are sent
        self._logQueue = []
        # Queue up events with timestamps stored and in order they are sent
        self._eventQueue = []
        # Cache the last profile data since only the most recent ones apply
        self._profilesCache = {}
        self._currentRequest = None
        self._numLogsSent = 0
        self._numEventsSent = 0
        self._timer = None

    def filePath(self) -> str:
        return os.path.join(util.appDataDir(), "analytics.pickle")

    def init(self):
        if os.path.isfile(self.filePath()):
            with open(self.filePath(), "rb") as f:
                try:
                    self._eventQueue, self._profilesCache = pickle.load(f)
                except Exception as e:
                    log.exception("Cached analytics data is corrupt")
                    self._eventQueue, self._profilesCache = [], {}
        self._timer = self.startTimer(self.RETRY_TIMER_MS)
        self.tick()

    def _writeToDisk(self):
        log.debug(
            f"Writing {len(self._eventQueue)} DatadogLog's and {len(self._eventQueue)} MixpanelEvent's and {len(self._profilesCache)} MixpanelProfile's"  #  {self.filePath()}"
        )
        with open(self.filePath(), "wb") as f:
            pickle.dump((self._eventQueue, self._profilesCache), f)

    def deinit(self):
        if self._timer is None:
            return
        self.killTimer(self._timer)
        self._timer = None
        if self._currentRequest:
            util.wait(self.completedOneRequest)
        self._writeToDisk()

    def timerEvent(self, e):
        self._writeToDisk()
        self.tick()

    def setEnabled(self, on: bool):
        self._enabled = on

    def numLogsQueued(self) -> int:
        return len(self._logQueue)

    def numProfilesQueued(self) -> int:
        return len(self._profilesCache.keys())

    def numEventsQueued(self) -> int:
        return len(self._eventQueue)

    def numEventsSent(self) -> int:
        return self._numEventsSent

    def numLogsSent(self) -> int:
        return self._numLogsSent

    def currentRequest(self) -> QNetworkRequest:
        return self._currentRequest

    def importUrl(self) -> str:
        return f"https://api.mixpanel.com/import?strict=1&project_id={self._mixpanel_project_id}"

    def profilesUrl(self) -> str:
        return f"https://api.mixpanel.com/engage#profile-batch-update"

    def logsUrl(self) -> str:
        return f"https://http-intake.logs.datadoghq.com/api/v2/logs"

    def sendJSONRequest(
        self, url, data, verb, success: Callable, finished: Callable, headers: dict
    ) -> QNetworkReply:
        self._currentRequest = QNetworkRequest(QUrl(url))
        for k, v in headers.items():
            self._currentRequest.setRawHeader(k, v)
        self._currentReply = QNAM.instance().sendCustomRequest(
            self._currentRequest, verb, json.dumps(data).encode("utf-8")
        )

        def onFinished():
            reply = self._currentReply
            self._currentRequest = None
            self._currentReply = None
            reply.finished.disconnect(onFinished)

            status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            if status_code != 0 and reply.error() == QNetworkReply.NoError:
                success(reply)
                finished(reply)
                self.tick()
            elif (
                status_code != status_code
                or reply.error() == QNetworkReply.HostNotFoundError
            ):
                log.debug(
                    f"Analytics request {url} failed with HTTP code: {status_code}"
                )
                finished(reply)
            else:
                log.debug(f"Analytics request {url} failed: no internet connection")
            self.completedOneRequest.emit(reply)

        self._currentReply.finished.connect(onFinished)
        return self._currentReply

    def _postNextLogs(self):

        def _consume(chunk):
            for event in chunk:
                self._logQueue.remove(event)
            self._writeToDisk()

        chunk = self._logQueue[: self.DATADOG_BATCH_MAX]
        try:
            data = [
                {
                    "message": x.message,
                    "timestamp": x.timestamp,
                    "host": x.host,
                    "service": x.service,
                    "level": x.level,
                    "username": x.username,
                }
                for x in chunk
            ]
        except Exception as e:
            log.exception("Error reading cached analytics event data")
            _consume(chunk)
            return

        def onSuccess(reply):
            log.debug(f"Sent {len(reply._chunk)} logs to Mixpanel")
            self._numLogsSent += len(reply._chunk)

        def onFinished(reply, *args):
            _consume(reply._chunk)

        log.debug(f"Attempting to send {len(chunk)} logs to Mixpanel...")
        reply = self.sendJSONRequest(
            self.logsUrl(),
            data,
            b"POST",
            onSuccess,
            onFinished,
            {
                b"Content-Type": b"application/json",
            },
        )
        # so they can be popped from the queue afterward
        reply._chunk = chunk

    def _postNextEvents(self):

        def _consume(chunk):
            for event in chunk:
                self._eventQueue.remove(event)
            self._writeToDisk()

        chunk = self._eventQueue[: self.MIXPANEL_BATCH_MAX]
        try:
            data = [
                {
                    "event": x.eventName,
                    "properties": dict(
                        distinct_id=x.username, time=x.time, **x.properties
                    ),
                }
                for x in chunk
            ]
        except Exception as e:
            log.exception("Error reading cached analytics event data")
            _consume(chunk)
            return

        def onSuccess(reply):
            log.debug(f"Sent {len(reply._chunk)} events to Mixpanel")
            self._numEventsSent += len(reply._chunk)

        def onFinished(reply, *args):
            _consume(reply._chunk)

        log.debug(f"Attempting to send {len(chunk)} events to Mixpanel...")
        reply = self.sendJSONRequest(
            self.importUrl(),
            data,
            b"POST",
            onSuccess,
            onFinished,
            {
                b"Content-Type": b"application/json",
                b"Accept": b"application/json",
                b"Authorization": b"Basic "
                + base64.b64encode(f"{self._mixpanel_project_token}:".encode("utf-8")),
            },
        )
        # so they can be popped from the queue afterward
        reply._chunk = chunk

    def _postProfiles(self):
        def _consume():
            self._profilesCache = {}
            self._writeToDisk()

        try:
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
                        "version": version.VERSION,
                    },
                }
                for username, x in self._profilesCache.items()
            ]
        except Exception as e:
            log.exception("Error reading cached analytics profile data")
            self._profilesCache = {}
            return

        def onSuccess(reply):
            log.debug(
                f"Successfully sent {len(self._profilesCache.keys())} profiles to Mixpanel"
            )

        def onFinished(reply):
            _consume()
            self._profilesCache = {}
            self._writeToDisk()

        log.debug(
            f"Attempting to send {len(self._profilesCache.keys())} profiles to Mixpanel..."
        )
        self.sendJSONRequest(
            self.profilesUrl(),
            data,
            b"POST",
            onSuccess,
            onFinished,
            {
                b"Content-Type": b"application/json",
                b"Accept": b"application/json",
                b"Authorization": b"Basic "
                + base64.b64encode(f"{self._mixpanel_project_token}:".encode("utf-8")),
            },
        )

    def tick(self):
        """
        Idempotent check and send. Only one request at a time. Prioritize
        profiles.
        """
        if self._currentRequest:
            return
        elif self._logQueue:
            self._postNextLogs()
        elif self._profilesCache:
            self._postProfiles()
        elif self._eventQueue:
            self._postNextEvents()

    def send(
        self, item: Union[MixpanelEvent, MixpanelProfile, DatadogLog], defer=False
    ):
        if not self._enabled:
            return
        if isinstance(item, DatadogLog):
            self._logQueue.append(item)
        elif isinstance(item, MixpanelEvent):
            self._eventQueue.append(item)
        elif isinstance(item, MixpanelProfile):
            self._profilesCache[item.username] = item
        else:
            raise ValueError(f"Invalid analytics item type: {type(item)}")
        if not defer:
            self.tick()
