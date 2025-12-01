import os.path
import json
import logging
import contextlib
import pickle
from typing import Callable
from dataclasses import asdict
from datetime import datetime

import pytest
from mock import patch, MagicMock

from pkdiagram.pyqt import QUndoStack
from pkdiagram.personal import PersonalAppController
from pkdiagram.server_types import Diagram
from btcopilot.schema import (
    DiagramData,
    PDP,
    Person,
    Event,
    EventKind,
    PairBond,
    asdict as schema_asdict,
)


_log = logging.getLogger(__name__)


# QML-related fixtures and tests are skipped - require full QML infrastructure
# @pytest.fixture
# def controller(qmlEngine):
#     controller = PersonalAppController()
#     with contextlib.ExitStack() as stack:
#         stack.enter_context(patch.object(controller.personal, "_refreshDiscussion"))
#         controller.init(qmlEngine)
#         yield controller


# @pytest.fixture
# def view(qtbot, test_session, qmlEngine, controller: PersonalAppController):
#     FPATH = os.path.join(
#         os.path.dirname(__file__),
#         "..",
#         "..",
#         "pkdiagram",
#         "resources",
#         "qml",
#         "Personal",
#         "LearnView.qml",
#     )
#     _view = QQuickWidget(qmlEngine, None)
#     _view.setSource(QUrl.fromLocalFile(FPATH))
#     _view.setFormat(util.SURFACE_FORMAT)
#     _view.setResizeMode(QQuickWidget.SizeRootObjectToView)
#     _view.resize(600, 800)
#     _view.show()
#     qtbot.addWidget(_view)
#     qtbot.waitActive(_view)
#     yield _view
#     _view.hide()
#     _view.setSource(QUrl(""))


# @pytest.mark.skip(reason="Requires QML infrastructure")
# def test_init_with_pdp(view: QQuickWidget, controller: PersonalAppController):
#     pdpList = view.rootObject().property("pdpList")
#     assert pdpList.property("numDelegates") == 0
#     controller.personalApp.setPDP(
#         {
#             "people": [{"id": -1, "name": "Alice"}, {"id": -2, "name": "Bob"}],
#             "events": [
#                 {"id": -3, "description": "Event 1"},
#                 {"id": -4, "description": "Event 2"},
#             ],
#         }
#     )
#     assert util.waitForCondition(lambda: pdpList.property("numDelegates") == 4) == True


@pytest.fixture
def session():
    s = MagicMock()
    s.user = MagicMock()
    s.user.free_diagram_id = 1
    s.changed = MagicMock()
    s.changed.connect = MagicMock()
    return s


def _create_save_func(personalApp: PersonalAppController) -> Callable:
    def save(server, applyChange, stillValidAfterRefresh, useJson=False):
        diagramData = personalApp.diagram.getDiagramData()
        diagramData = applyChange(diagramData)
        personalApp.diagram.setDiagramData(diagramData)
        return True

    return save


@pytest.fixture
def personalApp(qApp, session):
    undoStack = QUndoStack()
    personalApp = PersonalAppController(undoStack=undoStack)
    personalApp.session = session

    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Alice"),
                Person(id=-2, name="Bob"),
            ],
            events=[
                Event(id=-3, kind=EventKind.Shift, person=-1, description="Event 1"),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )
    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.now(),
        data=pickle.dumps(schema_asdict(diagramData)),
    )
    personalApp._diagram = diagram

    yield personalApp


def test_accept_person(personalApp):
    with (
        patch.object(personalApp.diagram, "save", _create_save_func(personalApp)),
        patch.object(personalApp, "_addCommittedItemsToScene"),
    ):
        result = personalApp.acceptPDPItem(-1, undo=False)

    assert result is True

    final_data = personalApp.diagram.getDiagramData()

    assert len(final_data.pdp.people) == 1
    assert final_data.pdp.people[0].name == "Bob"

    assert len(final_data.people) == 1
    assert final_data.people[0]["name"] == "Alice"
    assert final_data.people[0]["id"] > 0


def test_accept_event(personalApp):
    with (
        patch.object(personalApp.diagram, "save", _create_save_func(personalApp)),
        patch.object(personalApp, "_addCommittedItemsToScene"),
    ):
        result = personalApp.acceptPDPItem(-3, undo=False)

    assert result is True

    final_data = personalApp.diagram.getDiagramData()

    assert len(final_data.pdp.events) == 0
    assert len(final_data.pdp.people) == 1
    assert final_data.pdp.people[0].name == "Bob"

    assert len(final_data.events) == 1
    assert final_data.events[0]["description"] == "Event 1"
    assert final_data.events[0]["id"] > 0

    assert len(final_data.people) == 1
    assert final_data.people[0]["name"] == "Alice"


def test_reject_person(personalApp):
    with patch.object(personalApp.diagram, "save", _create_save_func(personalApp)):
        result = personalApp.rejectPDPItem(-1, undo=False)

    assert result is True

    final_data = personalApp.diagram.getDiagramData()

    assert len(final_data.pdp.people) == 1
    assert final_data.pdp.people[0].name == "Bob"
    assert len(final_data.pdp.events) == 0

    assert len(final_data.people) == 0
    assert len(final_data.events) == 0


def test_reject_event(personalApp):
    with patch.object(personalApp.diagram, "save", _create_save_func(personalApp)):
        result = personalApp.rejectPDPItem(-3, undo=False)

    assert result is True

    final_data = personalApp.diagram.getDiagramData()

    assert len(final_data.pdp.events) == 0

    assert len(final_data.pdp.people) == 2

    assert len(final_data.people) == 0
    assert len(final_data.events) == 0


def test_accept_with_pair_bond(qApp, session):
    undoStack = QUndoStack()

    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Parent A"),
                Person(id=-2, name="Parent B"),
                Person(id=-3, name="Child", parents=-4),
            ],
            events=[],
            pair_bonds=[
                PairBond(id=-4, person_a=-1, person_b=-2),
            ],
        ),
        lastItemId=0,
    )
    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.now(),
        data=pickle.dumps(schema_asdict(diagramData)),
    )
    personalApp = PersonalAppController(undoStack=undoStack)
    personalApp.session = session
    personalApp._diagram = diagram

    with (
        patch.object(personalApp.diagram, "save", _create_save_func(personalApp)),
        patch.object(personalApp, "_addCommittedItemsToScene"),
    ):
        result = personalApp.acceptPDPItem(-3, undo=False)

    assert result is True

    final_data = personalApp.diagram.getDiagramData()

    assert len(final_data.pdp.people) == 0
    assert len(final_data.pdp.pair_bonds) == 0

    assert len(final_data.people) == 3
    assert len(final_data.pair_bonds) == 1

    child = next(p for p in final_data.people if p["name"] == "Child")
    assert child["parents"] > 0

    pair_bond = final_data.pair_bonds[0]
    assert pair_bond["person_a"] > 0
    assert pair_bond["person_b"] > 0


def test_accept_event_after_person_already_committed(qApp, session):
    """Accept person first, then accept event referencing that person.

    This tests the scenario where an event references a person via negative ID,
    but that person has already been committed (now has positive ID).
    """
    undoStack = QUndoStack()

    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Alice"),
                Person(id=-2, name="Bob"),
            ],
            events=[
                Event(
                    id=-3,
                    kind=EventKind.Married,
                    person=-1,
                    spouse=-2,
                    description="Wedding",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=100,
    )
    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.now(),
        data=pickle.dumps(schema_asdict(diagramData)),
    )
    personalApp = PersonalAppController(undoStack=undoStack)
    personalApp.session = session
    personalApp._diagram = diagram

    # First accept Bob (-2)
    with (
        patch.object(personalApp.diagram, "save", _create_save_func(personalApp)),
        patch.object(personalApp, "_addCommittedItemsToScene"),
    ):
        result = personalApp.acceptPDPItem(-2, undo=False)
    assert result is True

    mid_data = personalApp.diagram.getDiagramData()
    assert len(mid_data.pdp.people) == 1
    assert mid_data.pdp.people[0].name == "Alice"
    assert len(mid_data.people) == 1
    assert mid_data.people[0]["name"] == "Bob"
    bob_committed_id = mid_data.people[0]["id"]
    assert bob_committed_id > 0

    # Now accept the wedding event (-3) which references spouse=-2
    # This should work even though Bob is no longer in PDP
    with (
        patch.object(personalApp.diagram, "save", _create_save_func(personalApp)),
        patch.object(personalApp, "_addCommittedItemsToScene"),
    ):
        result = personalApp.acceptPDPItem(-3, undo=False)
    assert result is True

    final_data = personalApp.diagram.getDiagramData()

    # Event and Alice should be committed
    assert len(final_data.pdp.events) == 0
    assert len(final_data.pdp.people) == 0

    assert len(final_data.events) == 1
    assert final_data.events[0]["description"] == "Wedding"

    # Both people should be in diagram
    assert len(final_data.people) == 2

    # The event's spouse reference should be updated to Bob's committed ID
    event = final_data.events[0]
    assert event["person"] > 0
    assert event["spouse"] == bob_committed_id


def test_accept_event_with_spouse_both_in_pdp(qApp, session):
    """Accept event where both person and spouse are still in PDP."""
    undoStack = QUndoStack()

    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Alice"),
                Person(id=-2, name="Bob"),
            ],
            events=[
                Event(
                    id=-3,
                    kind=EventKind.Married,
                    person=-1,
                    spouse=-2,
                    description="Wedding",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=100,
    )
    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.now(),
        data=pickle.dumps(schema_asdict(diagramData)),
    )
    personalApp = PersonalAppController(undoStack=undoStack)
    personalApp.session = session
    personalApp._diagram = diagram

    # Accept wedding event - should transitively commit both Alice and Bob
    with (
        patch.object(personalApp.diagram, "save", _create_save_func(personalApp)),
        patch.object(personalApp, "_addCommittedItemsToScene"),
    ):
        result = personalApp.acceptPDPItem(-3, undo=False)
    assert result is True

    final_data = personalApp.diagram.getDiagramData()

    # All items should be committed
    assert len(final_data.pdp.people) == 0
    assert len(final_data.pdp.events) == 0

    assert len(final_data.people) == 2
    assert len(final_data.events) == 1

    # Event references should be positive IDs
    event = final_data.events[0]
    assert event["person"] > 0
    assert event["spouse"] > 0


def test_committed_pdp_events_load_in_scene():
    """Events committed from PDP with string dateTimes should load correctly in Scene.

    This tests the bug where PDP events stored dateTime as strings (e.g. "1980-03-15")
    which couldn't be converted to QDateTime by Item.read(), causing events to be
    pruned by Scene.prune() because they appeared to have no dateTime.
    """
    from pkdiagram.scene import Scene

    # Create diagram data with PDP containing events with string dateTimes
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Alice"),
                Person(id=-2, name="Bob"),
            ],
            events=[
                Event(
                    id=-3,
                    kind=EventKind.Shift,
                    person=-1,
                    dateTime="1980-03-15",
                    description="Alice stress event",
                ),
                Event(
                    id=-4,
                    kind=EventKind.Married,
                    person=-1,
                    spouse=-2,
                    dateTime="2005-06-10",
                    description="Wedding",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    # Commit the PDP events - this should convert string dateTimes to QDateTime
    diagramData.commit_pdp_items([-3, -4])

    # Convert to dict format that Scene.read expects
    scene_data = schema_asdict(diagramData)

    # Load into scene
    scene = Scene()
    error = scene.read(scene_data)
    assert error is None, f"Scene.read failed: {error}"

    # Verify people were loaded
    people = scene.people()
    assert len(people) == 2

    # Verify events were loaded (not pruned due to missing dateTime)
    events = list(scene.events())
    assert (
        len(events) == 2
    ), f"Expected 2 events but got {len(events)} - events may have been pruned"

    # Verify dateTimes were properly converted from strings
    shift_event = next(e for e in events if e.kind() == EventKind.Shift)
    assert shift_event.dateTime() is not None
    assert not shift_event.dateTime().isNull()
    assert shift_event.dateTime().date().year() == 1980
    assert shift_event.dateTime().date().month() == 3
    assert shift_event.dateTime().date().day() == 15

    wedding_event = next(e for e in events if e.kind() == EventKind.Married)
    assert wedding_event.dateTime() is not None
    assert not wedding_event.dateTime().isNull()
    assert wedding_event.dateTime().date().year() == 2005
