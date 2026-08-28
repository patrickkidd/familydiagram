"""FD-336 / S2: the extraction pipeline writes through the one saver.

Accept used to rewrite the stored blob over a private JSON endpoint while the
open Scene stayed as it was, and undo put the blob back without touching the
Scene — a split brain that only resolved on reopen. These tests drive a real
accept against a real server row with a real Scene attached, so the Scene, the
row and the undo stack have to agree at every step.

Criteria: C7 (one save path), D5 (one accept = one undo step on Pro's stack),
D9 (lastItemId clamp), D11 (accepted people are placed, not stacked at origin).
"""

import datetime
import inspect
import pickle

import pytest

from btcopilot.extensions import db
from btcopilot.pro.models import Diagram as StoredDiagram
from btcopilot.schema import PDP, Person as SchemaPerson, asdict as schema_asdict

from pkdiagram.personal.pdpcontroller import PDPController
from pkdiagram.pyqt import QLineF, QPointF
from pkdiagram.scene import Person, Scene
from pkdiagram.server_types import Diagram
from pkdiagram.serverblockallocator import ServerBlockAllocator

from pkdiagram.tests.models.test_serverfilemanagermodel import create_model


pytestmark = [pytest.mark.component("Personal")]


STAGED = schema_asdict(
    PDP(
        people=[
            SchemaPerson(id=-1, name="Ana"),
            SchemaPerson(id=-2, name="Ben"),
        ]
    )
)


def _row(diagram_id) -> dict:
    db.session.expire_all()
    return pickle.loads(StoredDiagram.query.get(diagram_id).data)


def _row_names(diagram_id) -> set:
    return {p.get("name") for p in _row(diagram_id).get("people", [])}


def _staged_names(diagram_id) -> list:
    return [p["name"] for p in _row(diagram_id)["pdp"]["people"]]


def _scene_names(scene: Scene) -> set:
    return {p.name() for p in scene.people()}


# Below this a person symbol reads as sitting on top of its neighbour rather
# than beside it.
MIN_SEPARATION = 40


def _crowding(person: Person, others: list) -> list:
    """The people `person` landed on top of, named so a failure says who."""
    return [
        other.name()
        for other in others
        if QLineF(person.pos(), other.pos()).length() < MIN_SEPARATION
    ]


def _pipeline(create_model):
    """A Pro case open on a real row that already carries an extraction."""
    model = create_model()
    diagram_id = model.index(0, 0).data(model.IDRole)

    stored = StoredDiagram.query.get(diagram_id)
    data = pickle.loads(stored.data) if stored.data else {}
    data["pdp"] = STAGED
    stored.update_with_version_check(None, new_data=pickle.dumps(data))
    stored.updated_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=1)
    db.session.commit()
    model.syncDiagramFromServer(diagram_id)

    scene = Scene()
    controller = PDPController(model.session, model.saver)
    controller.setDiagram(model.findDiagram(diagram_id))
    controller.setScene(scene)
    return model, diagram_id, controller, scene


def test_accept_lands_on_the_row_and_in_the_scene(create_model):
    """C7/D5: one accept persists the whole Scene through the saver and adds
    the person to the open Scene, and leaves exactly one undoable step.

    D4 says the document is clean afterwards — in Pro that is literally
    `scene.stack().isClean()`, which is what draws the `*` in the title bar —
    so a successful accept must mark the stack clean even though it pushed a
    command onto it."""
    model, diagram_id, controller, scene = _pipeline(create_model)

    assert controller.acceptPDPItem(-1) == True
    assert "Ana" in _row_names(diagram_id)
    assert "Ana" in _scene_names(scene)
    assert scene.stack().canUndo() == True
    assert scene.stack().isClean() == True


def test_undo_removes_the_person_and_restores_the_card(create_model):
    """D5: undo is one step for the whole accept. The person leaves the Scene
    and the row together and the staged card comes back, so the coach and the
    diagram cannot disagree about whether the person exists.

    The undo persists through the same saver, so it leaves the document clean
    for the same reason the accept does — otherwise undoing a change strands
    Pro showing unsaved work that is already on the server. Two accepts before
    the undo, because undoing a lone accept returns the stack to index 0, where
    Qt reports clean whether or not anything marked it so."""
    model, diagram_id, controller, scene = _pipeline(create_model)
    assert controller.acceptPDPItem(-1) == True
    assert controller.acceptPDPItem(-2) == True

    scene.stack().undo()
    assert "Ben" not in _scene_names(scene)
    assert "Ben" not in _row_names(diagram_id)
    assert _staged_names(diagram_id) == ["Ben"]
    assert "Ana" in _scene_names(scene)
    assert scene.stack().canRedo() == True
    assert scene.stack().isClean() == True


def test_reject_is_not_undoable(create_model):
    """D5: only an accept changes the diagram, so only an accept earns a step
    on Pro's undo stack. A reject that pushed one would let Cmd-Z resurrect a
    card the user deliberately dismissed."""
    model, diagram_id, controller, scene = _pipeline(create_model)

    assert controller.rejectPDPItem(-1) == True
    assert _staged_names(diagram_id) == ["Ben"]
    assert scene.stack().count() == 0


def test_accepted_people_are_placed_not_stacked(create_model):
    """D11: 1924 opens with everyone on top of each other at the origin. Each
    accepted person must clear every person already on the diagram, and it must
    hold across separate accepts — a cascade that only spaces out people
    committed in the same batch still hides the one-at-a-time case, which is
    how the review sheet is actually used."""
    model, diagram_id, controller, scene = _pipeline(create_model)
    root = Person(name="Root")
    scene.addItem(root)
    root.setItemPosNow(QPointF(200, 200))

    assert controller.acceptPDPItem(-1) == True
    ana = scene.query1(name="Ana")
    assert _crowding(ana, [root]) == []

    assert controller.acceptPDPItem(-2) == True
    assert _crowding(scene.query1(name="Ben"), [root, ana]) == []


def test_reserved_id_block_survives_the_save(create_model):
    """D9: reserving a block advances the row's lastItemId but not the client's
    cached copy, so a save that trusted the Scene's counter would hand the same
    ids out twice to the next writer."""
    model, diagram_id, controller, scene = _pipeline(create_model)
    allocator = ServerBlockAllocator(
        model.findDiagram(diagram_id), model.session.server(), blockSize=100
    )
    scene.setIdAllocator(allocator)
    scene.addItem(Person(name="Local"))
    blockEnd = allocator._end

    assert controller.acceptPDPItem(-1) == True
    assert _row(diagram_id)["lastItemId"] >= blockEnd
    assert scene.query1(name="Ana").id > blockEnd


def test_pipeline_has_no_second_save_endpoint():
    """C7: the JSON diagram endpoint was the pipeline's private write path and
    the reason the row and the Scene could diverge. Retiring the flag is what
    makes "exactly one save path" checkable rather than aspirational."""
    assert "useJson" not in inspect.signature(Diagram.save).parameters
