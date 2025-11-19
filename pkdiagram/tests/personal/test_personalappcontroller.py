import contextlib

import pytest
from mock import patch

from pkdiagram.app import Session
from pkdiagram.personal import PersonalAppController, Discussion, Statement
from pkdiagram import util

from btcopilot.extensions import db
from btcopilot.schema import DiagramData, PDP, Person, asdict


pytestmark = [
    pytest.mark.component("Personal"),
    pytest.mark.depends_on("Session"),
]


@pytest.fixture
def discussion(test_user):
    from btcopilot.personal.models import Discussion

    discussion = Discussion(user_id=test_user.id, diagram_id=test_user.free_diagram_id)
    db.session.add(discussion)
    return discussion


@pytest.fixture
def controller(test_session):
    session = Session()
    session.init(sessionData=test_session.account_editor_dict(), syncWithServer=False)
    _controller = PersonalAppController(session)

    yield _controller


def test_refreshDiagram(
    flask_app, test_user, discussion, controller: PersonalAppController
):
    discussionsChanged = util.Condition(controller.discussionsChanged)
    controller._refreshDiagram()
    assert discussionsChanged.wait() == True
    assert set(x.id for x in controller.discussions) == {discussion.id}


def test_refreshPDP(test_user, controller: PersonalAppController):
    pdpChanged = util.Condition(controller.pdpChanged)
    diagram = test_user.free_diagram
    diagram.set_diagram_data(DiagramData(pdp=PDP(people=[Person(name="Test Person")])))
    db.session.add(diagram)
    db.session.commit()
    controller.refreshPDP()
    assert pdpChanged.wait() == True
    assert controller.pdp == asdict(test_user.free_diagram.get_diagram_data().pdp)


@pytest.mark.parametrize("success", [True, False])
def test_sendStatement(
    server_error, test_user, discussion, controller: PersonalAppController, success
):

    from btcopilot.controller.chat import Response, PDP

    RESPONSE = Response(statement="some response", pdp=PDP())

    requestSent = util.Condition(controller.requestSent)
    responseReceived = util.Condition(controller.responseReceived)
    serverError = util.Condition(controller.serverError)
    serverDown = util.Condition(controller.serverDown)

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch("btcopilot.controller.routes.discussions.ask", return_value=RESPONSE)
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
        controller.sendStatement("test message")
    assert requestSent.callCount == 1
    if success:
        assert responseReceived.wait() == True
        assert responseReceived.callArgs[0][0] == RESPONSE.statement
        assert serverError.callCount == 0
    else:
        assert serverError.wait() == True
        assert responseReceived.callCount == 0
    assert serverDown.callCount == 0
