import sys
import pickle
import contextlib
import logging
import json
import datetime

import pytest
import mock

from pkdiagram.pyqt import (
    QByteArray,
    QNetworkReply,
    QNetworkRequest,
    QTimer,
)
from pkdiagram import util, version
from pkdiagram.qnam import QNAM
from pkdiagram.app import Analytics, DatadogLog, DatadogLogStatus
from pkdiagram.server_types import User
from pkdiagram.app.analytics import time_2_iso8601


_log = logging.getLogger(__name__)


class NetworkReply(QNetworkReply):
    def abort(self):
        pass

    def writeData(self, data):
        if not hasattr(self, "_data"):
            self._data = b""
        self._data = self._data + data
        return len(data)

    def readAll(self):
        if hasattr(self, "_data"):
            return QByteArray(self._data)
        else:
            return QByteArray(b"")


@contextlib.contextmanager
def mockRequest(status_code: int):

    def _simulateFinished(reply):
        reply.finished.emit()

    def _sendCustomRequest(request, verb, data=b""):
        reply = NetworkReply()
        reply.setAttribute(QNetworkRequest.HttpStatusCodeAttribute, status_code)
        reply.writeData(b'{"bleb": true}')
        QTimer.singleShot(0, lambda: _simulateFinished(reply))
        return reply

    with mock.patch.object(
        QNAM.instance(), "sendCustomRequest", side_effect=_sendCustomRequest
    ) as sendCustomRequest:
        yield sendCustomRequest


@pytest.fixture(autouse=True)
def _init():
    with mock.patch("pkdiagram.app.Analytics.killTimer"):
        yield


@pytest.fixture
def analytics():
    """
    Just to ensure that timers are killed.
    """

    x = Analytics(datadog_api_key="som-dd-key")

    yield x

    x.deinit()


@pytest.fixture
def user():
    return User(id=123, username="user_1", first_name="Hey", last_name="You", roles=[])


def test_init(analytics):
    analytics.init()
    assert analytics.numLogsQueued() == 0
    assert analytics.currentRequest() is None


def test_send_request(analytics):

    URL = "https://google.com"
    DATA = {"event": "test_event"}

    completedOneRequest = util.Condition(analytics.completedOneRequest)
    analytics.init()
    onSuccess = mock.Mock()
    onFinished = mock.Mock()
    with mockRequest(200) as sendCustomRequest:
        analytics.sendJSONRequest(
            URL,
            DATA,
            verb=b"POST",
            success=onSuccess,
            finished=onFinished,
            headers={b"Custom-Header": b"Custom-Value"},
        )
    assert analytics.currentRequest() is not None

    assert completedOneRequest.wait() == True
    assert analytics.currentRequest() is None
    assert sendCustomRequest.call_count == 1
    assert sendCustomRequest.call_args[0][0].url().toString() == URL
    assert (
        sendCustomRequest.call_args[0][0].rawHeader(b"Custom-Header") == b"Custom-Value"
    )
    assert sendCustomRequest.call_args[0][1] == b"POST"
    assert sendCustomRequest.call_args[0][2] == b'{"event": "test_event"}'


def test_http_error_does_not_repeat(analytics, user):
    completedOneRequest = util.Condition(analytics.completedOneRequest)
    analytics.init()
    with mockRequest(401):
        analytics.send(
            DatadogLog(
                message="test_event", user=user, time=123, status=DatadogLogStatus.Info
            )
        )
    assert completedOneRequest.wait() == True
    assert analytics.numLogsQueued() == 0
    assert analytics.currentRequest() is None


def test_datadog_send_logs_api(analytics, user):
    completedOneRequest = util.Condition(analytics.completedOneRequest)
    analytics.init()
    assert analytics.numLogsQueued() == 0
    assert analytics.currentRequest() is None

    log = DatadogLog(
        message="some log content", user=user, time=123, status=DatadogLogStatus.Info
    )

    with mock.patch("time.time", return_value=123):
        with mockRequest(200) as sendCustomRequest:
            with mock.patch("os.uname", return_value="os_uname"):
                with mock.patch.object(sys, "platform", "platform-123"):
                    analytics.send(log)
    assert analytics.numLogsQueued() == 1
    assert analytics.currentRequest() is not None
    assert completedOneRequest.wait() == True
    assert analytics.numLogsQueued() == 0
    assert sendCustomRequest.call_count == 1
    assert json.loads(sendCustomRequest.call_args[0][2].decode()) == [
        {
            "ddsource": "python",
            "ddtags": "env:test",
            "message": "some log content",
            "platform": "platform-123",
            "date": time_2_iso8601(123),
            "host": "",
            "service": "desktop",
            "status": "info",
            "session_id": None,
            "user": {
                "id": user.id,
                "username": user.username,
                "name": user.first_name + " " + user.last_name,
                "free_diagram_id": None,
                "licenses": [],
            },
            "device": "os_uname",
            "version": version.VERSION,
            "fdtype": "log",
        }
    ]


def test_send_two_logs(analytics, user):
    completedOneRequest = util.Condition(analytics.completedOneRequest)
    analytics.init()
    log_1 = DatadogLog(
        message="test_event 1", user=user, time=123, status=DatadogLogStatus.Info
    )
    log_2 = DatadogLog(
        message="test_event 2", user=user, time=123, status=DatadogLogStatus.Info
    )
    with mock.patch("time.time", return_value=123):
        with mockRequest(202) as sendCustomRequest:
            analytics.send(log_1, defer=True)
            analytics.send(log_2, defer=True)
            analytics.tick()
    assert completedOneRequest.wait() == True
    assert sendCustomRequest.call_count == 1
    assert json.loads(sendCustomRequest.call_args[0][2])
    assert analytics.numLogsQueued() == 0
    assert analytics.numLogsSent() == 2


def test_queue_on_init_with_data(analytics, user):

    LOGS = [
        DatadogLog(
            message="some log content",
            user=user,
            time=123,
            status=DatadogLogStatus.Info,
        )
        for i in range(10)
    ]

    with open(analytics.filePath(), "wb") as f:
        pickle.dump(LOGS, f)
    with mockRequest(0):
        analytics.init()
    assert analytics.numLogsQueued() == len(LOGS)


def test_cache_file_is_corrupted(analytics):
    with open(analytics.filePath(), "wb") as f:
        pickle.dump("bad-analytics-cache", f)
    analytics.init()
    assert analytics.numLogsQueued() == 0


def test_offline_come_back_online_and_send(analytics, user):
    completedOneRequest = util.Condition(analytics.completedOneRequest)
    analytics.init()
    assert analytics.numLogsQueued() == 0
    assert analytics.currentRequest() is None

    with mockRequest(0):
        analytics.send(
            DatadogLog(
                message="test_event 1",
                user=user,
                status=DatadogLogStatus.Info,
                time=123,
            )
        )
        analytics.send(
            DatadogLog(
                message="test_event 2",
                user=user,
                status=DatadogLogStatus.Info,
                time=123,
            )
        )
    assert completedOneRequest.wait() == True
    assert analytics.numLogsQueued() == 2
    assert analytics.numLogsSent() == 0
    assert analytics.currentRequest() is None

    # # complete request
    # completedOneRequest.reset()
    # with mockRequest(200):
    #     analytics.tick()
    # assert completedOneRequest.wait() == True
    # assert analytics.numLogsQueued() == 2
    # assert analytics.currentRequest() is None

    # Simulate coming back online
    completedOneRequest.reset()
    with mockRequest(202):
        analytics.timerEvent(None)
    assert completedOneRequest.wait() == True
    assert analytics.numLogsQueued() == 0
    assert analytics.numLogsSent() == 2


def test_offline_deinit_init_and_send(analytics, user):
    completedOneRequest = util.Condition(analytics.completedOneRequest)
    analytics.init()
    with mockRequest(0):
        analytics.send(
            DatadogLog(
                message="test_event 1",
                user=user,
                status=DatadogLogStatus.Info,
                time=123,
            )
        )
        analytics.send(
            DatadogLog(
                message="test_event 2",
                user=user,
                status=DatadogLogStatus.Info,
                time=123,
            )
        )
    assert analytics.numLogsQueued() == 2
    assert analytics.currentRequest() is not None

    assert completedOneRequest.wait() == True
    assert analytics.numLogsSent() == 0
    assert analytics.numLogsQueued() == 2

    analytics.deinit()
    analytics = Analytics(datadog_api_key="678")
    completedOneRequest = util.Condition(analytics.completedOneRequest)
    with mockRequest(202):
        analytics.init()
    assert analytics.numLogsQueued() == 2
    assert analytics.currentRequest() is not None
    assert completedOneRequest.wait() == True
    assert analytics.numLogsSent() == 2
    assert analytics.numLogsQueued() == 0
