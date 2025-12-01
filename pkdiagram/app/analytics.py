import sys
import os.path
import logging
import json
import logging
import pickle
import enum
import datetime
import platform
from typing import Callable
from dataclasses import dataclass

from pkdiagram.pyqt import (
    pyqtSignal,
    QObject,
    QApplication,
    QNetworkRequest,
    QNetworkReply,
    QUrl,
)
from pkdiagram import util, version
from pkdiagram.qnam import QNAM
from pkdiagram.server_types import User


log = logging.getLogger(__name__)


class DatadogLogStatus(enum.Enum):
    Critical = "critical"
    Error = "error"
    Warning = "warning"
    Info = "info"
    Debug = "debug"

    @staticmethod
    def from_python_level(level: int):
        if level >= logging.CRITICAL:
            return DatadogLogStatus.Critical
        elif level >= logging.ERROR:
            return DatadogLogStatus.Error
        elif level >= logging.WARNING:
            return DatadogLogStatus.Warning
        elif level >= logging.INFO:
            return DatadogLogStatus.Info
        else:
            return DatadogLogStatus.Debug


class DatadogFDType(enum.Enum):
    Action = "action"
    Log = "log"


@dataclass
class DatadogLog:
    time: float
    message: str
    status: DatadogLogStatus = DatadogLogStatus.Info
    user: User = None
    session_id: str = None
    fdtype: DatadogFDType = DatadogFDType.Log
    extras: dict = None


def time_2_iso8601(x: float) -> str:
    return (
        datetime.datetime.fromtimestamp(x, tz=datetime.timezone.utc).isoformat() + "Z"
    )


class Analytics(QObject):
    """
    Manage an offline-capable queue of analytics events.
    """

    RETRY_TIMER_MS = 12000
    DATADOG_BATCH_MAX = 1000

    completedOneRequest = pyqtSignal(QNetworkReply)

    def __init__(
        self,
        datadog_api_key: str = None,
        parent=None,
    ):
        super().__init__(parent)
        if datadog_api_key is None:
            raise ValueError("datadog_api_key is required")
        self._datadog_api_key = datadog_api_key
        self._enabled = True
        # Queue up events with timestamps stored and in order they are sent
        self._logQueue = []
        self._numLogsSent = 0
        self._currentRequest = None
        self._timer = None
        self._service = QApplication.instance().appType()

    def filePath(self) -> str:
        return os.path.join(util.appDataDir(), "analytics.pickle")

    def init(self):
        if os.path.isfile(self.filePath()):
            with open(self.filePath(), "rb") as f:
                try:
                    self._logQueue = pickle.load(f)
                except Exception as e:
                    log.exception("Cached analytics data is corrupt, recovering")
                    self._logQueue = []
                if self._logQueue and not isinstance(self._logQueue[0], DatadogLog):
                    log.error("Cached analytics data is corrupt")
                    self._logQueue = []
        self._timer = self.startTimer(self.RETRY_TIMER_MS)
        self.tick()

    def _writeToDisk(self):
        log.debug(f"Writing {len(self._logQueue)} DatadogLog items")
        with open(self.filePath(), "wb") as f:
            pickle.dump(self._logQueue, f)

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

    def numLogsSent(self) -> int:
        return self._numLogsSent

    def currentRequest(self) -> QNetworkRequest:
        return self._currentRequest

    def logsUrl(self) -> str:
        return f"https://http-intake.logs.datadoghq.com/api/v2/logs"

    def sendJSONRequest(
        self,
        url,
        data,
        verb,
        success: Callable,
        finished: Callable,
        headers: dict,
        statuses=[200],
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
            if reply.error() == QNetworkReply.NoError and status_code in statuses:
                success(reply)
                finished(reply)
                self.tick()
            elif reply.error() == QNetworkReply.NoError and status_code != 0:
                log.info(
                    f"Analytics request {url} failed with HTTP code: {status_code} (not in {statuses})"
                )
                finished(reply)
            else:
                log.info(
                    f"Analytics request {url} failed: could not connect to host (Qt error: {reply.error()}, status_code: {status_code})"
                )
            self.completedOneRequest.emit(reply)

        self._currentReply.finished.connect(onFinished)
        return self._currentReply

    def _postNextLogs(self):

        def _consume(chunk):
            for event in chunk:
                self._logQueue.remove(event)
            self._writeToDisk()

        if util.IS_TEST:
            TAGS = "env:test"
        elif util.IS_DEV:
            TAGS = "env:staging"
        else:
            TAGS = "env:production"

        chunk = self._logQueue[: self.DATADOG_BATCH_MAX]
        uname = platform.uname()
        try:
            data = [
                {
                    "ddsource": "python",
                    "ddtags": TAGS,
                    "host": "",
                    "service": self._service,
                    #
                    "date": time_2_iso8601(x.time),
                    "message": x.message,
                    "status": x.status.value,
                    "fdtype": x.fdtype.value,
                    "user": (
                        {
                            "id": x.user.id,
                            "name": f"{x.user.first_name} {x.user.last_name}",
                            "username": x.user.username,
                            "free_diagram_id": x.user.free_diagram_id,
                            "licenses": (
                                [y.policy.code for y in x.user.licenses]
                                if x.user.licenses
                                else []
                            ),
                        }
                        if x.user
                        else None
                    ),
                    "session_id": x.session_id,
                    "uname": {
                        "system": uname.system,
                        "node": uname.node,
                        "release": uname.release,
                        "version": uname.version,
                        "machine": uname.machine,
                    },
                    "platform": sys.platform,
                    "version": version.VERSION,
                    **(x.extras if x.extras else {}),  # Include extras if provided
                }
                for x in chunk
            ]
        except Exception as e:
            log.exception("Error reading cached analytics event data")
            _consume(chunk)
            return

        def onSuccess(reply):
            self._numLogsSent += len(reply._chunk)

        def onFinished(reply, *args):
            _consume(reply._chunk)

        reply = self.sendJSONRequest(
            self.logsUrl(),
            data,
            b"POST",
            onSuccess,
            onFinished,
            {
                b"Content-Type": b"application/json",
                b"DD-API-KEY": self._datadog_api_key.encode("utf-8"),
            },
            statuses=[202],
        )
        # so they can be popped from the queue afterward
        reply._chunk = chunk

    def tick(self):
        """
        Idempotent check and send. Only one request at a time. Prioritize
        profiles.
        """
        if self._currentRequest:
            return
        if self._logQueue:
            self._postNextLogs()

    def send(self, item: DatadogLog, defer=False):
        if util.IS_TEST:
            return
        if not self._enabled:
            return
        log.debug(f"Analytics.send: util.IS_BUNDLE: {util.IS_BUNDLE}, item: {item}")
        self._logQueue.append(item)
        if not defer:
            self.tick()
