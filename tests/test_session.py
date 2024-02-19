import pytest, mock

from sqlalchemy import inspect

import vedana
from pkdiagram import util, version, Session, Diagram
from fdserver import util as fdserver_util


@pytest.fixture
def create_session(request):

    def _create_session(db_session=True):
        ret = Session()
        if db_session:
            test_session = request.getfixturevalue("test_session")
            ret.init(test_session.account_editor_dict(), syncWithServer=False)
        return ret

    return _create_session


def test_init(test_session, create_session):
    session = create_session()
    assert session.isLoggedIn() == True
    assert len(test_session.account_editor_dict()["users"]) == len(session.users)
    assert session.activeFeatures() == [vedana.LICENSE_FREE]


def test_init_no_server(create_session, server_down):
    with server_down():
        session = create_session(db_session=False)
    assert session.isLoggedIn() == False
    assert len(session.users) == 0
    assert session.activeFeatures() == []


def test_login_with_username_password(test_user):
    session = Session()
    changed = util.Condition(session.changed)
    session.init()
    changed.wait()
    changed.reset()
    session.login(username=test_user.username, password=test_user._plaintext_password)
    assert changed.wait() == True
    assert session.isLoggedIn() == True


def test_login_expired_session(test_session):
    sessionData = test_session.account_editor_dict()
    sessionData["session"]["token"] = "something-expired"

    session = Session()
    session.init(sessionData=sessionData)
    assert session.isLoggedIn() == False


def test_logout(test_session):
    session = Session()
    changed = util.Condition(session.changed)
    failed = util.Condition(session.logoutFailed)
    finished = util.Condition(session.logoutFinished)
    session.init(test_session.account_editor_dict(), syncWithServer=False)
    session.logout()
    assert changed.callCount > 0
    assert failed.callCount == 0
    assert finished.wait() == True


def test_logout_failed(test_session):
    session = Session()
    failed = util.Condition(session.logoutFailed)
    finished = util.Condition(session.logoutFinished)
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
            session, "activeFeatures", return_value=[vedana.LICENSE_ALPHA]
        ):
            assert session.hasFeature(vedana.LICENSE_ALPHA) == True
            assert session.hasFeature(vedana.LICENSE_PROFESSIONAL) == True
            assert session.hasFeature(vedana.LICENSE_FREE) == False
            assert session.hasFeature(vedana.LICENSE_CLIENT) == False

        with mock.patch.object(
            session, "activeFeatures", return_value=[vedana.LICENSE_PROFESSIONAL]
        ):
            assert session.hasFeature(vedana.LICENSE_ALPHA) == False
            assert session.hasFeature(vedana.LICENSE_PROFESSIONAL) == False
            assert session.hasFeature(vedana.LICENSE_FREE) == False
            assert session.hasFeature(vedana.LICENSE_CLIENT) == False


def test_hasFeature_beta(create_session):
    session = create_session(db_session=False)

    with mock.patch.object(version, "IS_BETA", True):
        with mock.patch.object(
            session, "activeFeatures", return_value=[vedana.LICENSE_BETA]
        ):
            assert session.hasFeature(vedana.LICENSE_BETA) == True
            assert session.hasFeature(vedana.LICENSE_PROFESSIONAL) == True
            assert session.hasFeature(vedana.LICENSE_FREE) == False
            assert session.hasFeature(vedana.LICENSE_CLIENT) == False

        with mock.patch.object(
            session, "activeFeatures", return_value=[vedana.LICENSE_PROFESSIONAL]
        ):
            assert session.hasFeature(vedana.LICENSE_BETA) == False
            assert session.hasFeature(vedana.LICENSE_PROFESSIONAL) == False
            assert session.hasFeature(vedana.LICENSE_FREE) == False
            assert session.hasFeature(vedana.LICENSE_CLIENT) == False


def test_hasFeature_professional():
    session = Session()

    with mock.patch.object(version, "IS_ALPHA", False):
        with mock.patch.object(version, "IS_BETA", False):
            with mock.patch.object(
                session, "activeFeatures", return_value=[vedana.LICENSE_PROFESSIONAL]
            ):
                assert session.hasFeature(vedana.LICENSE_BETA) == False
                assert session.hasFeature(vedana.LICENSE_PROFESSIONAL) == True
                assert session.hasFeature(vedana.LICENSE_FREE) == False
                assert session.hasFeature(vedana.LICENSE_CLIENT) == False


def test_hasFeature_client():
    session = Session()

    with mock.patch.object(version, "IS_ALPHA", False):
        with mock.patch.object(version, "IS_BETA", False):
            with mock.patch.object(
                session,
                "activeFeatures",
                return_value=[vedana.LICENSE_FREE, vedana.LICENSE_CLIENT],
            ):
                assert session.hasFeature(vedana.LICENSE_BETA) == False
                assert session.hasFeature(vedana.LICENSE_PROFESSIONAL) == False
                assert session.hasFeature(vedana.LICENSE_FREE) == True
                assert session.hasFeature(vedana.LICENSE_CLIENT) == True


def test_version_deactivated(test_session):
    with mock.patch.object(
        fdserver_util,
        "DEACTIVATED_VERSIONS",
        list(fdserver_util.DEACTIVATED_VERSIONS) + [version.VERSION],
    ):
        session = Session()
        session.init(sessionData=test_session.account_editor_dict())
        assert session.isVersionDeactivated() == True


def test_version_not_deactivated():
    session = Session()
    session.init()
    assert session.isVersionDeactivated() == False
