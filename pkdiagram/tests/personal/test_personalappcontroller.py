import contextlib
import pickle
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from pkdiagram.personal import PersonalAppController
from pkdiagram.personal.models import (
    Discussion,
    Statement,
    Speaker,
    SpeakerType,
)
from pkdiagram import util
from pkdiagram.server_types import Diagram

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


def test_refreshDiagram(
    flask_app, test_user, discussion, personalApp: PersonalAppController
):
    # _refreshDiagram is already called by fixture via session.init -> onSessionChanged
    # Just verify the result
    assert set(x.id for x in personalApp.discussions) == {discussion.id}


@pytest.mark.parametrize("success", [True, False])
def test_sendStatement(
    server_error, test_user, discussion, personalApp: PersonalAppController, success
):

    from btcopilot.personal.chat import Response

    RESPONSE = Response(statement="some response")

    requestSent = util.Condition(personalApp.requestSent)
    responseReceived = util.Condition(personalApp.responseReceived)
    serverError = util.Condition(personalApp.serverError)
    serverDown = util.Condition(personalApp.serverDown)

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch("btcopilot.personal.routes.discussions.ask", return_value=RESPONSE)
        )
        stack.enter_context(
            patch.object(
                personalApp,
                "_currentDiscussion",
                Discussion(
                    id=discussion.id,
                    user_id=test_user.id,
                    diagram_id=test_user.free_diagram_id,
                    statements=[
                        Statement(
                            id=1,
                            text="blah",
                            speaker=Speaker(
                                id=1, person_id=1, name="Test", type=SpeakerType.Subject
                            ),
                        )
                    ],
                ),
            )
        )
        if not success:
            stack.enter_context(server_error())
        personalApp.sendStatement("test message")
    assert requestSent.callCount == 1
    if success:
        assert responseReceived.wait()
        assert responseReceived.callArgs[0][0] == RESPONSE.statement
        assert serverError.callCount == 0
    else:
        assert serverError.wait()
        assert responseReceived.callCount == 0
    assert serverDown.callCount == 0


def test_acceptPDPItem_undo(test_user, personalApp: PersonalAppController):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    with patch.object(personalApp, "_doAcceptPDPItem") as accept:
        personalApp.acceptPDPItem(-1)
        assert accept.call_count == 1
        assert personalApp._undoStack.count() == 1
        assert personalApp._undoStack.canUndo()

        personalApp._undoStack.undo()
        expected = asdict(initial_diagram_data.pdp)
        expected["committedPeople"] = []
        assert personalApp.pdp == expected
        assert not personalApp._undoStack.canUndo()
        assert personalApp._undoStack.canRedo()

        personalApp._undoStack.redo()
        assert accept.call_count == 2
        assert not personalApp._undoStack.canRedo()


def test_rejectPDPItem_undo(test_user, personalApp: PersonalAppController):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    with patch.object(personalApp, "_doRejectPDPItem") as reject:
        personalApp.rejectPDPItem(-1)
        assert reject.call_count == 1
        assert personalApp._undoStack.count() == 1
        assert personalApp._undoStack.canUndo()

        personalApp._undoStack.undo()
        expected = asdict(initial_diagram_data.pdp)
        expected["committedPeople"] = []
        assert personalApp.pdp == expected
        assert not personalApp._undoStack.canUndo()
        assert personalApp._undoStack.canRedo()

        personalApp._undoStack.redo()
        assert reject.call_count == 2
        assert not personalApp._undoStack.canRedo()


def test_undo_stack_multiple_operations(test_user, personalApp: PersonalAppController):
    diagram_data1 = DiagramData(pdp=PDP(people=[Person(id=-1, name="Person1")]))
    diagram_data2 = DiagramData(
        pdp=PDP(people=[Person(id=-1, name="Person1"), Person(id=-2, name="Person2")])
    )

    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(diagram_data1)),
    )

    with (
        patch.object(personalApp, "_doAcceptPDPItem"),
        patch.object(personalApp, "_doRejectPDPItem"),
    ):
        personalApp.acceptPDPItem(-1)
        personalApp._diagram.setDiagramData(diagram_data2)
        personalApp.rejectPDPItem(-2)

        assert personalApp._undoStack.count() == 2

        personalApp._undoStack.undo()
        expected2 = asdict(diagram_data2.pdp)
        expected2["committedPeople"] = []
        assert personalApp.pdp == expected2

        personalApp._undoStack.undo()
        expected1 = asdict(diagram_data1.pdp)
        expected1["committedPeople"] = []
        assert personalApp.pdp == expected1


def test_acceptPDPItem_failure_doesnt_push_to_stack(
    test_user, personalApp: PersonalAppController
):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    count_before = personalApp._undoStack.count()

    with patch.object(personalApp, "_doAcceptPDPItem", return_value=False):
        result = personalApp.acceptPDPItem(-1)

    assert result is False
    assert personalApp._undoStack.count() == count_before


def test_rejectPDPItem_failure_doesnt_push_to_stack(
    test_user, personalApp: PersonalAppController
):
    initial_diagram_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="Test")]))
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    count_before = personalApp._undoStack.count()

    with patch.object(personalApp, "_doRejectPDPItem", return_value=False):
        result = personalApp.rejectPDPItem(-1)

    assert result is False
    assert personalApp._undoStack.count() == count_before


def test_diagram_save_shows_error_on_unexpected_status(test_user):
    from pkdiagram.pyqt import QMessageBox
    from pkdiagram.server_types import HTTPError

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


def test_importJournalNotes_emits_summary_dict_with_correct_keys(
    test_user, personalApp: PersonalAppController
):
    from btcopilot.schema import DiagramData, PDP, PDPDeltas, Event, EventKind
    from unittest.mock import AsyncMock
    from pkdiagram.pyqt import QMessageBox

    initial_diagram_data = DiagramData(pdp=PDP())
    personalApp._diagram = Diagram(
        id=test_user.free_diagram_id,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    mock_pdp = PDP(
        people=[Person(id=-1, name="TestPerson"), Person(id=-2, name="Mom")],
        events=[Event(id=-3, kind=EventKind.Shift, description="called")],
    )
    mock_deltas = PDPDeltas(
        people=[Person(id=-1, name="TestPerson"), Person(id=-2, name="Mom")],
        events=[Event(id=-3, kind=EventKind.Shift, description="called")],
        pair_bonds=[],
    )

    with (
        patch(
            "btcopilot.pdp.import_text",
            AsyncMock(return_value=(mock_pdp, mock_deltas)),
        ),
        patch.object(QMessageBox, "information") as info_mock,
    ):
        completed = util.Condition(personalApp.journalImportCompleted)
        personalApp.importJournalNotes("Some journal text")
        assert completed.wait()

    summary = completed.callArgs[0][0]
    assert "people" in summary, f"'people' key missing from summary: {summary}"
    assert "events" in summary, f"'events' key missing from summary: {summary}"
    assert "pairBonds" in summary, f"'pairBonds' key missing from summary: {summary}"
    assert summary["people"] == 2
    assert summary["events"] == 1
    assert summary["pairBonds"] == 0


def test_importJournalNotes_no_diagram(test_user, personalApp: PersonalAppController):
    from pkdiagram.pyqt import QMessageBox

    personalApp._diagram = None

    failed = util.Condition(personalApp.journalImportFailed)

    with patch.object(QMessageBox, "critical"):
        personalApp.importJournalNotes("Some journal text")
        assert failed.wait()

    assert "No diagram loaded" in failed.callArgs[0][0]


def test_acceptAllPDPItems_adds_to_scene(test_user, personalApp: PersonalAppController):
    from btcopilot.schema import Event, EventKind

    initial_diagram_data = DiagramData(
        pdp=PDP(
            people=[Person(id=-1, name="TestPerson")],
            events=[Event(id=-2, kind=EventKind.Shift, person=-1, description="test")],
        )
    )
    personalApp._diagram = Diagram(
        id=1,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_diagram_data)),
    )

    with patch.object(personalApp, "_addCommittedItemsToScene") as add_mock:
        with patch.object(personalApp._diagram, "save", return_value=True):
            personalApp.acceptAllPDPItems()
            assert add_mock.call_count == 1
            args = add_mock.call_args[0][0]
            assert "people" in args
            assert "events" in args
            assert "pair_bonds" in args
