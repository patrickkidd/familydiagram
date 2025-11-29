import contextlib
import pickle
from datetime import datetime

import pytest
from mock import patch
from pkdiagram.pyqt import QApplication

from pkdiagram.app import Session
from pkdiagram.personal import PersonalAppController
from pkdiagram.personal.models import Discussion, Statement
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
    _controller = PersonalAppController(QApplication.instance())
    _controller.session.init(
        sessionData=test_session.account_editor_dict(), syncWithServer=False
    )

    yield _controller


def test_refreshDiagram(
    flask_app, test_user, discussion, controller: PersonalAppController
):
    discussionsChanged = util.Condition(controller.discussionsChanged)
    controller._refreshDiagram()
    assert discussionsChanged.wait() == True
    assert set(x.id for x in controller.discussions) == {discussion.id}


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
        assert responseReceived.wait()
        assert responseReceived.callArgs[0][0] == RESPONSE.statement
        assert serverError.callCount == 0
    else:
        assert serverError.wait()
        assert responseReceived.callCount == 0
    assert serverDown.callCount == 0


def test_acceptPDPItem_undo(test_user, personal: Personal):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personal._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    with patch.object(personal, "_doAcceptPDPItem") as mock_accept:
        personal.acceptPDPItem(-1)
        assert mock_accept.call_count == 1
        assert personal._undoStack.count() == 1
        assert personal._undoStack.canUndo()

        personal._undoStack.undo()
        assert personal.pdp == asdict(initial_diagram_data.pdp)
        assert not personal._undoStack.canUndo()
        assert personal._undoStack.canRedo()

        personal._undoStack.redo()
        assert mock_accept.call_count == 2
        assert not personal._undoStack.canRedo()


def test_rejectPDPItem_undo(test_user, personal: Personal):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personal._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    with patch.object(personal, "_doRejectPDPItem") as mock_reject:
        personal.rejectPDPItem(-1)
        assert mock_reject.call_count == 1
        assert personal._undoStack.count() == 1
        assert personal._undoStack.canUndo()

        personal._undoStack.undo()
        assert personal.pdp == asdict(initial_diagram_data.pdp)
        assert not personal._undoStack.canUndo()
        assert personal._undoStack.canRedo()

        personal._undoStack.redo()
        assert mock_reject.call_count == 2
        assert not personal._undoStack.canRedo()


def test_undo_stack_multiple_operations(test_user, personal: Personal):
    diagram_data1 = DiagramData(pdp=PDP(people=[Person(id=-1, name="Person1")]))
    diagram_data2 = DiagramData(
        pdp=PDP(people=[Person(id=-1, name="Person1"), Person(id=-2, name="Person2")])
    )

    personal._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(diagram_data1)),
    )

    with (
        patch.object(personal, "_doAcceptPDPItem"),
        patch.object(personal, "_doRejectPDPItem"),
    ):
        personal.acceptPDPItem(-1)
        personal._diagram.setDiagramData(diagram_data2)
        personal.rejectPDPItem(-2)

        assert personal._undoStack.count() == 2

        personal._undoStack.undo()
        assert personal.pdp == asdict(diagram_data2.pdp)

        personal._undoStack.undo()
        assert personal.pdp == asdict(diagram_data1.pdp)


def test_acceptPDPItem_failure_doesnt_push_to_stack(test_user, personal: Personal):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personal._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    stack_count_before = personal._undoStack.count()

    with patch.object(personal, "_doAcceptPDPItem", return_value=False):
        result = personal.acceptPDPItem(-1)

    assert result is False
    assert personal._undoStack.count() == stack_count_before


def test_acceptPDPItem_failure_doesnt_emit_signal(test_user, personal: Personal):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personal._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    signal_emitted = False

    def onItemAdded(item):
        nonlocal signal_emitted
        signal_emitted = True

    personal.pdpItemAdded.connect(onItemAdded)

    with patch.object(personal, "_doAcceptPDPItem", return_value=False):
        personal.acceptPDPItem(-1)

    assert signal_emitted is False


def test_rejectPDPItem_failure_doesnt_push_to_stack(test_user, personal: Personal):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personal._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    stack_count_before = personal._undoStack.count()

    with patch.object(personal, "_doRejectPDPItem", return_value=False):
        result = personal.rejectPDPItem(-1)

    assert result is False
    assert personal._undoStack.count() == stack_count_before


def test_rejectPDPItem_failure_doesnt_emit_signal(test_user, personal: Personal):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personal._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    signal_emitted = False

    def onItemRemoved(item):
        nonlocal signal_emitted
        signal_emitted = True

    personal.pdpItemRemoved.connect(onItemRemoved)

    with patch.object(personal, "_doRejectPDPItem", return_value=False):
        personal.rejectPDPItem(-1)

    assert signal_emitted is False


def test_diagram_save_shows_error_on_unexpected_status(test_user):
    from pkdiagram.pyqt import QMessageBox
    from pkdiagram.server_types import HTTPError
    from unittest.mock import MagicMock

    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    mock_server = MagicMock()
    mock_server.blockingRequest.side_effect = HTTPError(
        "Unexpected server error", status_code=500
    )

    with patch.object(QMessageBox, "critical") as mock_critical:

        def applyChange(diagramData: DiagramData):
            return diagramData

        def stillValidAfterRefresh(diagramData: DiagramData):
            return True

        success = diagram.save(
            mock_server, applyChange, stillValidAfterRefresh, useJson=True
        )

        assert success is False
        assert mock_critical.call_count == 1
        args = mock_critical.call_args[0]
        assert "500" in args[2]
