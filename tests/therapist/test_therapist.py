import contextlib

import pytest
from mock import patch

from pkdiagram.app import Session
from pkdiagram.therapist import Therapist
from pkdiagram.therapist.therapist import Response
from pkdiagram import util

from fdserver.extensions import db
from fdserver.models import User
from fdserver.therapist.models import Discussion, Statement, Speaker, SpeakerType
from fdserver.therapist.database import Database, PDP, Person


pytestmark = [
    pytest.mark.component("Therapist"),
    pytest.mark.depends_on("Session"),
]


@pytest.fixture
def discussion(test_user):
    discussion = Discussion(user_id=test_user.id)
    db.session.add(discussion)
    return discussion


@pytest.fixture
def therapist(test_session):
    session = Session()
    session.init(sessionData=test_session.account_editor_dict(), syncWithServer=False)
    _therapist = Therapist(session)

    yield _therapist


from fdserver.tests.therapist.conftest import discussion


def test_refreshDiagram(flask_app, test_user, discussion, therapist: Therapist):
    discussionsChanged = util.Condition(therapist.discussionsChanged)
    with flask_app.app_context():
        therapist._refreshDiagram()
    assert discussionsChanged.wait() == True
    assert set(x.id for x in therapist.discussions) == {discussion.id}


def test_refreshPDP(test_user, therapist: Therapist):
    pdpChanged = util.Condition(therapist.pdpChanged)
    diagram = test_user.free_diagram
    diagram.set_database(Database(pdp=PDP(people=[Person(name="Test Person")])))
    db.session.add(diagram)
    db.session.commit()
    therapist.refreshPDP()
    assert pdpChanged.wait() == True
    assert therapist.pdp == test_user.free_diagram.get_database().pdp.model_dump()


@pytest.mark.parametrize("success", [True, False])
def test_sendStatement(
    server_error, test_user, discussion, therapist: Therapist, success
):

    from fdserver.therapist.chat import Response, PDP

    RESPONSE = Response(statement="some response", pdp=PDP())

    requestSent = util.Condition(therapist.requestSent)
    responseReceived = util.Condition(therapist.responseReceived)
    serverError = util.Condition(therapist.serverError)
    serverDown = util.Condition(therapist.serverDown)

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch("fdserver.therapist.routes.discussions.ask", return_value=RESPONSE)
        )
        stack.enter_context(
            patch.object(
                therapist,
                "_currentDiscussion",
                Discussion(
                    id=discussion.id,
                    user_id=test_user.id,
                    statements=[Statement(text="blah")],
                ),
            )
        )
        if not success:
            stack.enter_context(server_error())
        therapist.sendStatement("test message")
    assert requestSent.callCount == 1
    if success:
        assert responseReceived.wait() == True
        assert responseReceived.callArgs[0][0] == RESPONSE.statement
        assert serverError.callCount == 0
    else:
        assert serverError.wait() == True
        assert responseReceived.callCount == 0
    assert serverDown.callCount == 0
