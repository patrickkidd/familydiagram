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
from pkdiagram.app import (
    Analytics,
    DatadogLog,
    DatadogLogStatus,
    MixpanelEvent,
    MixpanelProfile,
)
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

    x = Analytics(mixpanel_project_token="some-token", datadog_api_key="som-dd-key")

    yield x

    x.deinit()


def test_init(analytics):
    analytics.init()
    assert analytics.numLogsQueued() == 0
    assert analytics.numEventsQueued() == 0
    assert analytics.numProfilesQueued() == 0
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


def test_http_error_does_not_repeat(analytics):
    completedOneRequest = util.Condition(analytics.completedOneRequest)
    analytics.init()
    event = MixpanelEvent(
        eventName="test_event", username="user_1", time=123, properties={}
    )
    with mockRequest(401):
        analytics.send(event)
    assert completedOneRequest.wait() == True
    assert analytics.numEventsQueued() == 0
    assert analytics.currentRequest() is None


def test_datadog_send_logs_api(test_user, analytics):
    completedOneRequest = util.Condition(analytics.completedOneRequest)
    analytics.init()
    assert analytics.numEventsQueued() == 0
    assert analytics.currentRequest() is None

    log = DatadogLog(
        message="some log content",
        user=test_user,
        time=123,
        status=DatadogLogStatus.Info,
    )

    with mock.patch("time.time", return_value=123):
        with mockRequest(200) as sendCustomRequest:
            with mock.patch("os.uname", return_value="os_uname"):
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
            "date": time_2_iso8601(123),
            "host": "",
            "log_txt": "",
            "service": "desktop",
            "status": "info",
            "user": {
                "id": test_user.id,
                "username": test_user.username,
                "name": test_user.first_name + " " + test_user.last_name,
            },
            "device": "os_uname",
            "version": version.VERSION,
        }
    ]


def test_mixpanel_send_events_api(analytics):
    completedOneRequest = util.Condition(analytics.completedOneRequest)
    analytics.init()
    assert analytics.numEventsQueued() == 0
    assert analytics.currentRequest() is None

    event = MixpanelEvent(
        eventName="test_event", username="user_1", time=123, properties={}
    )

    with mock.patch("time.time", return_value=123):
        with mockRequest(200) as sendCustomRequest:
            analytics.send(event)
    assert analytics.numEventsQueued() == 1
    assert analytics.currentRequest() is not None
    assert completedOneRequest.wait() == True
    assert analytics.numEventsQueued() == 0
    assert sendCustomRequest.call_count == 1
    assert sendCustomRequest.call_args[0][2] == (
        '[{"event": "test_event", "properties": {"distinct_id": "user_1", "time": 123, "$insert_id": "'
        + event.properties["$insert_id"]
        + '"}}]'
    ).encode("utf-8")


def test_send_two_events_to_mixpanel(analytics):
    completedOneRequest = util.Condition(analytics.completedOneRequest)
    analytics.init()
    event_1 = MixpanelEvent(
        eventName="test_event", username="user_1", time=123, properties={}
    )
    event_2 = MixpanelEvent(
        eventName="test_event", username="user_1", time=123, properties={}
    )
    with mock.patch("time.time", return_value=123):
        with mockRequest(200) as sendCustomRequest:
            analytics.send(
                event_1,
                defer=True,
            )
            analytics.send(
                event_2,
                defer=True,
            )
            analytics.tick()
    assert completedOneRequest.wait() == True
    assert sendCustomRequest.call_count == 1
    assert sendCustomRequest.call_args[0][2] == (
        '[{"event": "test_event", "properties": {"distinct_id": "user_1", "time": 123, "$insert_id": "'
        + event_1.properties["$insert_id"]
        + '"}}, {"event": "test_event", "properties": {"distinct_id": "user_1", "time": 123, "$insert_id": "'
        + event_2.properties["$insert_id"]
        + '"}}]'
    ).encode("utf-8")
    assert analytics.numEventsQueued() == 0
    assert analytics.numEventsSent() == 2


def test_queue_on_init_with_data(analytics):

    LOGS = [
        DatadogLog(
            message="some log content",
            user=User(
                id=456, username="user_1", first_name="Hey", last_name="You", roles=[]
            ),
            time=123,
            status=DatadogLogStatus.Info,
        )
        for i in range(10)
    ]
    EVENTS = [
        MixpanelEvent(
            eventName="test_event",
            properties={},
            username="user_1",
            time=123 + i,
        )
        for i in range(10)
    ]
    PROFILES = {
        "user_1": MixpanelProfile(
            username="user_1",
            email="you@me.com",
            first_name="Hey",
            last_name="You",
            properties={},
        ),
        "user_2": MixpanelProfile(
            username="user_2",
            email="you@me.com",
            first_name="Hey",
            last_name="You",
            properties={},
        ),
    }

    with open(analytics.filePath(), "wb") as f:
        pickle.dump((LOGS, EVENTS, PROFILES), f)
    with mockRequest(0):
        analytics.init()
    assert analytics.numLogsQueued() == len(LOGS)
    assert analytics.numEventsQueued() == len(EVENTS)
    assert analytics.numProfilesQueued() == len(PROFILES.keys())


def test_cache_file_is_corrupted(analytics):
    with open(analytics.filePath(), "wb") as f:
        pickle.dump("bad-analytics-cache", f)
    analytics.init()
    assert analytics.numEventsQueued() == 0
    assert analytics.numProfilesQueued() == 0


def test_cache_events_is_corrupted(analytics):
    with open(analytics.filePath(), "wb") as f:
        pickle.dump((["bad-event-data"], {}), f)
    with mockRequest(0):
        analytics.init()
    assert analytics.numEventsQueued() == 0
    assert analytics.numProfilesQueued() == 0


def test_cache_profiles_is_corrupted(analytics):
    with open(analytics.filePath(), "wb") as f:
        pickle.dump(([], {"bad-profile-key": "bad-profile-data"}), f)
    with mockRequest(0):
        analytics.init()
    assert analytics.numEventsQueued() == 0
    assert analytics.numProfilesQueued() == 0


def test_offline_come_back_online_and_send(analytics):
    completedOneRequest = util.Condition(analytics.completedOneRequest)
    analytics.init()
    assert analytics.numEventsQueued() == 0
    assert analytics.currentRequest() is None

    with mockRequest(0):
        analytics.send(
            MixpanelEvent(
                eventName="test_event", username="user_1", time=123, properties={}
            )
        )
        analytics.send(
            MixpanelEvent(
                eventName="test_event", username="user_1", time=123, properties={}
            )
        )
    assert completedOneRequest.wait() == True
    assert analytics.numEventsQueued() == 2
    assert analytics.numEventsSent() == 0
    assert analytics.currentRequest() is None

    # # complete request
    # completedOneRequest.reset()
    # with mockRequest(200):
    #     analytics.tick()
    # assert completedOneRequest.wait() == True
    # assert analytics.numEventsQueued() == 2
    # assert analytics.currentRequest() is None

    # Simulate coming back online
    completedOneRequest.reset()
    with mockRequest(200):
        analytics.timerEvent(None)
    assert completedOneRequest.wait() == True
    assert analytics.numEventsQueued() == 0
    assert analytics.numEventsSent() == 2


def test_offline_deinit_init_and_send(analytics):
    completedOneRequest = util.Condition(analytics.completedOneRequest)
    analytics.init()
    with mockRequest(0):
        analytics.send(
            MixpanelEvent(
                eventName="test_event", username="user_1", time=123, properties={}
            )
        )
        analytics.send(
            MixpanelEvent(
                eventName="test_event", username="user_1", time=123, properties={}
            )
        )
    assert analytics.numEventsQueued() == 2
    assert analytics.currentRequest() is not None

    assert completedOneRequest.wait() == True
    assert analytics.numEventsSent() == 0
    assert analytics.numEventsQueued() == 2

    analytics.deinit()
    analytics = Analytics(mixpanel_project_token="678")
    completedOneRequest = util.Condition(analytics.completedOneRequest)
    with mockRequest(200):
        analytics.init()
    assert analytics.numEventsQueued() == 2
    assert analytics.currentRequest() is not None
    assert completedOneRequest.wait() == True
    assert analytics.numEventsSent() == 2
    assert analytics.numEventsQueued() == 0


# test colaesce profile updates


def test_coalesce_profiles(analytics):
    analytics.init()
    analytics.send(
        MixpanelProfile(
            username="user_1",
            email="you@me.com",
            first_name="Hey",
            last_name="You",
            properties={},
        ),
        defer=True,
    )
    assert analytics.numProfilesQueued() == 1

    analytics.send(
        MixpanelProfile(
            username="user_2",
            email="you_2@me.com",
            first_name="Hey",
            last_name="You2",
            properties={},
        ),
        defer=True,
    )
    assert analytics.numProfilesQueued() == 2

    analytics.send(
        MixpanelProfile(
            username="user_1",
            email="you_2@me.com",
            first_name="Hey",
            last_name="You2",
            properties={},
        ),
        defer=True,
    )
    assert analytics.numProfilesQueued() == 2


def test_send_profiles_before_events(analytics):

    completedOneRequest = util.Condition(analytics.completedOneRequest)
    analytics.init()
    analytics.send(
        MixpanelEvent(
            eventName="logged_in", username="user_1", time=123, properties={}
        ),
        defer=True,
    )
    analytics.send(
        MixpanelEvent(
            eventName="logged_in", username="user_2", time=123, properties={}
        ),
        defer=True,
    )
    analytics.send(
        MixpanelProfile(
            username="user_1",
            email="you@me.com",
            first_name="Hey",
            last_name="You",
            properties={},
        ),
        defer=True,
    )
    analytics.send(
        MixpanelProfile(
            username="user_2",
            email="you_2@me.com",
            first_name="Hey",
            last_name="You2",
            properties={},
        ),
        defer=True,
    )
    assert analytics.numProfilesQueued() == 2

    urls = []
    orig_sendJSONRequest = analytics.sendJSONRequest

    def _sendJSONRequest(url, data, verb, success, finished, headers):
        urls.append(url)
        return orig_sendJSONRequest(url, data, verb, success, finished, headers)

    with mock.patch(
        "pkdiagram.app.Analytics.sendJSONRequest", side_effect=_sendJSONRequest
    ) as sendJSONRequest:
        with mockRequest(200):
            analytics.tick()
            assert completedOneRequest.wait() == True
    assert analytics.numEventsQueued() == 0
    assert analytics.numProfilesQueued() == 0
    assert urls == [
        analytics.profilesUrl(),
        analytics.importUrl(),
    ]
