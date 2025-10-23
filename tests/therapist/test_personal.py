import contextlib

import pytest
from mock import patch

from pkdiagram.app import Session
from pkdiagram.personal import Personal
from pkdiagram import util

from btcopilot.extensions import db
from btcopilot.personal.models import Discussion, Statement
from btcopilot.schema import Database, PDP, Person


pytestmark = [
    pytest.mark.component("Personal"),
    pytest.mark.depends_on("Session"),
]


@pytest.fixture
def discussion(test_user):
    discussion = Discussion(user_id=test_user.id, diagram_id=test_user.free_diagram_id)
    db.session.add(discussion)
    return discussion


@pytest.fixture
def personal(test_session):
    session = Session()
    session.init(sessionData=test_session.account_editor_dict(), syncWithServer=False)
    _personal = Personal(session)

    yield _personal


def test_refreshDiagram(flask_app, test_user, discussion, personal: Personal):
    discussionsChanged = util.Condition(personal.discussionsChanged)
    personal._refreshDiagram()
    assert discussionsChanged.wait() == True
    assert set(x.id for x in personal.discussions) == {discussion.id}


def test_refreshPDP(test_user, personal: Personal):
    pdpChanged = util.Condition(personal.pdpChanged)
    diagram = test_user.free_diagram
    diagram.set_dataclass(Database(pdp=PDP(people=[Person(name="Test Person")])))
    db.session.add(diagram)
    db.session.commit()
    personal.refreshPDP()
    assert pdpChanged.wait() == True
    assert personal.pdp == test_user.free_diagram.get_database().pdp.model_dump()


@pytest.mark.parametrize("success", [True, False])
def test_sendStatement(
    server_error, test_user, discussion, personal: Personal, success
):

    from btcopilot.personal.chat import Response, PDP

    RESPONSE = Response(statement="some response", pdp=PDP())

    requestSent = util.Condition(personal.requestSent)
    responseReceived = util.Condition(personal.responseReceived)
    serverError = util.Condition(personal.serverError)
    serverDown = util.Condition(personal.serverDown)

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch("btcopilot.personal.routes.discussions.ask", return_value=RESPONSE)
        )
        stack.enter_context(
            patch.object(
                personal,
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
        personal.sendStatement("test message")
    assert requestSent.callCount == 1
    if success:
        assert responseReceived.wait() == True
        assert responseReceived.callArgs[0][0] == RESPONSE.statement
        assert serverError.callCount == 0
    else:
        assert serverError.wait() == True
        assert responseReceived.callCount == 0
    assert serverDown.callCount == 0
