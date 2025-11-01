import sys
import traceback
import datetime

import pytest, mock
from sqlalchemy import inspect

import btcopilot
from pkdiagram import version
from pkdiagram.condition import Condition
from pkdiagram.server_types import Diagram
from pkdiagram.app import Session, DatadogLogStatus


from btcopilot import pro

from .test_analytics import analytics


pytestmark = [
    pytest.mark.component("Session"),
    pytest.mark.depends_on("Scene"),
]


@pytest.fixture
def create_session(request, analytics):

    def _create_session(db_session=True):
        ret = Session(analytics)
        if db_session:
            test_session = request.getfixturevalue("test_session")
            ret.init(test_session.account_editor_dict(), syncWithServer=False)
        return ret

    yield _create_session


@pytest.fixture(autouse=True)
def Analytics_send():
    with mock.patch("time.time", return_value=123):
        with mock.patch("pkdiagram.app.Analytics.send") as send:
            yield send


def test_init(test_session, create_session, Analytics_send):
    session = create_session()
    assert session.isLoggedIn() == True
    assert len(test_session.account_editor_dict()["users"]) == len(session.users)
    assert session.activeFeatures() == [btcopilot.LICENSE_FREE]
    assert Analytics_send.call_count == 1
    assert (
        Analytics_send.call_args_list[0][0][0].user.username
        == "patrickkidd+unittest@gmail.com"
    )


def test_init_with_activation(test_session, test_activation, create_session):
    session = create_session()
    assert session.isLoggedIn() == True
    assert session.user.licenses[0].id == test_activation.license_id


def test_init_no_server(create_session, server_down, Analytics_send):
    with server_down():
        session = create_session(db_session=False)
    assert session.isLoggedIn() == False
    assert len(session.users) == 0
    assert session.activeFeatures() == []
    assert Analytics_send.call_count == 0


def test_error_no_user(create_session, Analytics_send):
    session = create_session(db_session=False)

    try:
        raise ValueError("This is a simulated error for testing")
    except ValueError as e:
        # Capture the exception and its traceback
        etype, value, tb = sys.exc_info()

    session.error(etype, value, tb)
    assert Analytics_send.call_count == 1
    assert Analytics_send.call_args[0][0].user == None
    assert Analytics_send.call_args[0][0].time == 123
    assert Analytics_send.call_args[0][0].status == DatadogLogStatus.Error
    assert Analytics_send.call_args[0][0].message == "".join(
        traceback.format_exception(etype, value, tb)
    )


def test_error_with_user(test_user, create_session, Analytics_send):
    session = create_session(db_session=True)

    try:
        raise ValueError("This is a simulated error for testing")
    except ValueError as e:
        # Capture the exception and its traceback
        etype, value, tb = sys.exc_info()

    session.error(etype, value, tb)
    assert Analytics_send.call_count == 2
    assert Analytics_send.call_args[0][0].user.username == test_user.username
    assert Analytics_send.call_args[0][0].time == 123
    assert Analytics_send.call_args[0][0].status == DatadogLogStatus.Error
    assert Analytics_send.call_args[0][0].message == "".join(
        traceback.format_exception(etype, value, tb)
    )


def test_login_with_username_password(test_user, analytics):
    session = Session(analytics)
    changed = Condition(session.changed)
    session.init()
    changed.wait()
    changed.reset()
    session.login(username=test_user.username, password=test_user._plaintext_password)
    assert changed.wait() == True
    assert session.isLoggedIn() == True


@pytest.mark.use_bcrypt
def test_login_incorrect_password(test_user, analytics):
    session = Session(analytics)
    changed = Condition(session.changed)
    session.init()
    changed.wait()
    changed.reset()
    session.login(username=test_user.username, password="some-wrong pw")
    assert session.isLoggedIn() == False


def test_login_expired_session(test_session, analytics):
    sessionData = test_session.account_editor_dict()
    sessionData["session"]["token"] = "something-expired"

    session = Session(analytics)
    session.init(sessionData=sessionData)
    assert session.isLoggedIn() == False


def test_logout(test_session, analytics):
    session = Session(analytics)
    changed = Condition(session.changed)
    failed = Condition(session.logoutFailed)
    finished = Condition(session.logoutFinished)
    session.init(test_session.account_editor_dict(), syncWithServer=False)
    session.logout()
    assert changed.callCount > 0
    assert failed.callCount == 0
    assert finished.wait() == True


def test_logout_failed(test_session, analytics):
    session = Session(analytics)
    failed = Condition(session.logoutFailed)
    finished = Condition(session.logoutFinished)
    session.init(test_session.account_editor_dict(), syncWithServer=False)
    db_session = inspect(test_session).session
    db_session.delete(test_session)  # makes it fail
    db_session.commit()
    session.logout()
    assert failed.wait() == True
    assert failed.callCount == 1
    assert finished.wait() == True


def test_Diagram_get(test_user, create_session):
    session = create_session()
    diagram = Diagram.get(test_user.free_diagram_id, session)
    assert diagram is not None


def test_hasFeature_alpha(create_session):
    session = create_session(db_session=False)

    with mock.patch.object(version, "IS_ALPHA", True):
        with mock.patch.object(
            session, "activeFeatures", return_value=[btcopilot.LICENSE_ALPHA]
        ):
            assert session.hasFeature(btcopilot.LICENSE_ALPHA) == True
            assert session.hasFeature(btcopilot.LICENSE_PROFESSIONAL) == True
            assert session.hasFeature(btcopilot.LICENSE_FREE) == False
            assert session.hasFeature(btcopilot.LICENSE_CLIENT) == False

        with mock.patch.object(
            session, "activeFeatures", return_value=[btcopilot.LICENSE_PROFESSIONAL]
        ):
            assert session.hasFeature(btcopilot.LICENSE_ALPHA) == False
            assert session.hasFeature(btcopilot.LICENSE_PROFESSIONAL) == False
            assert session.hasFeature(btcopilot.LICENSE_FREE) == False
            assert session.hasFeature(btcopilot.LICENSE_CLIENT) == False


def test_hasFeature_beta(create_session):
    session = create_session(db_session=False)

    with mock.patch.object(version, "IS_BETA", True):
        with mock.patch.object(
            session, "activeFeatures", return_value=[btcopilot.LICENSE_BETA]
        ):
            assert session.hasFeature(btcopilot.LICENSE_BETA) == True
            assert session.hasFeature(btcopilot.LICENSE_PROFESSIONAL) == True
            assert session.hasFeature(btcopilot.LICENSE_FREE) == False
            assert session.hasFeature(btcopilot.LICENSE_CLIENT) == False

        with mock.patch.object(
            session, "activeFeatures", return_value=[btcopilot.LICENSE_PROFESSIONAL]
        ):
            assert session.hasFeature(btcopilot.LICENSE_BETA) == False
            assert session.hasFeature(btcopilot.LICENSE_PROFESSIONAL) == False
            assert session.hasFeature(btcopilot.LICENSE_FREE) == False
            assert session.hasFeature(btcopilot.LICENSE_CLIENT) == False


def test_hasFeature_professional(analytics):
    session = Session(analytics)

    with mock.patch.object(version, "IS_ALPHA", False):
        with mock.patch.object(version, "IS_BETA", False):
            with mock.patch.object(
                session, "activeFeatures", return_value=[btcopilot.LICENSE_PROFESSIONAL]
            ):
                assert session.hasFeature(btcopilot.LICENSE_BETA) == False
                assert session.hasFeature(btcopilot.LICENSE_PROFESSIONAL) == True
                assert session.hasFeature(btcopilot.LICENSE_FREE) == False
                assert session.hasFeature(btcopilot.LICENSE_CLIENT) == False


def test_hasFeature_client(analytics):
    session = Session(analytics)

    with mock.patch.object(version, "IS_ALPHA", False):
        with mock.patch.object(version, "IS_BETA", False):
            with mock.patch.object(
                session,
                "activeFeatures",
                return_value=[btcopilot.LICENSE_FREE, btcopilot.LICENSE_CLIENT],
            ):
                assert session.hasFeature(btcopilot.LICENSE_BETA) == False
                assert session.hasFeature(btcopilot.LICENSE_PROFESSIONAL) == False
                assert session.hasFeature(btcopilot.LICENSE_FREE) == True
                assert session.hasFeature(btcopilot.LICENSE_CLIENT) == True


def test_version_deactivated(test_session, analytics):
    with mock.patch.object(
        pro,
        "DEACTIVATED_VERSIONS",
        list(pro.DEACTIVATED_VERSIONS) + [version.VERSION],
    ):
        session = Session(analytics)
        session.init(sessionData=test_session.account_editor_dict())
        assert session.isVersionDeactivated() == True


def test_version_not_deactivated():
    session = Session()
    session.init()
    assert session.isVersionDeactivated() == False


def test_deinit(analytics):
    session = Session(analytics)
    session.init()
    session.deinit()
