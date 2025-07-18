import pytest
from mock import patch

from pkdiagram.app import Session
from pkdiagram.therapist import Therapist
from pkdiagram.therapist.therapist import Response
from pkdiagram import util

from fdserver.extensions import db
from fdserver.models import User, Discussion, Statement
from fdserver.therapist.database import Database, PDP, Person


pytestmark = [
    pytest.mark.component("Therapist"),
    pytest.mark.depends_on("Session"),
]


@pytest.fixture
def chat_thread(test_user):
    chat_thread = Discussion(user_id=test_user.id)
    db.session.add(chat_thread)


@pytest.fixture
def therapist(test_session):
    session = Session()
    session.init(sessionData=test_session.account_editor_dict(), syncWithServer=False)
    _therapist = Therapist(session)

    yield _therapist


def test_refreshThreads(test_user, therapist: Therapist):
    threadsChanged = util.Condition(therapist.threadsChanged)
    threads = [
        Discussion(user_id=test_user.id, messages=[Statement(text="blah")]),
        Discussion(user_id=test_user.id, messages=[Statement(text="blah")]),
    ]
    db.session.add_all(threads)
    db.session.commit()
    therapist.refreshThreads()
    assert threadsChanged.wait() == True
    assert set(x.id for x in therapist.threads) == set(x.id for x in threads)


def test_refreshPDP(test_user, therapist: Therapist):
    pdpChanged = util.Condition(therapist.pdpChanged)
    test_user.database = Database(
        pdp=PDP(people=[Person(name="Test Person")])
    ).model_dump()
    db.session.commit()
    therapist.refreshPDP()
    assert pdpChanged.wait() == True
    assert therapist.pdp == test_user.database["pdp"]


def test_sendMessage(chat_thread, therapist: Therapist):

    RESPONSE = Response(
        message="some response",
        added_data_points=[],
        removed_data_points=[],
        guidance=[],
    )

    requestSent = util.Condition(therapist.requestSent)
    responseReceived = util.Condition(therapist.responseReceived)
    serverError = util.Condition(therapist.serverError)
    serverDown = util.Condition(therapist.serverDown)

    with patch("fdserver.therapist.ask", return_value=RESPONSE):
        therapist.sendMessage("test message")
    assert requestSent.callCount == 1
    assert responseReceived.wait() == True
    assert responseReceived.callArgs[0][0] == RESPONSE.message
    assert serverError.callCount == 0
    assert serverDown.callCount == 0


def test_server_error(chat_thread, server_error, therapist: Therapist):
    requestSent = util.Condition(therapist.requestSent)
    responseReceived = util.Condition(therapist.responseReceived)
    serverError = util.Condition(therapist.serverError)
    serverDown = util.Condition(therapist.serverDown)

    with server_error():
        with patch("fdserver.therapist.ask"):
            therapist.sendMessage("test message")
    assert requestSent.callCount == 1
    assert serverError.wait() == True
    assert responseReceived.callCount == 0
    assert serverDown.callCount == 0
