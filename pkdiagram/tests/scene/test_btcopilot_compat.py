import pickle

import pytest

from btcopilot.schema import (
    DiagramData,
    PDP,
    PDPDeltas,
    Person as BtcopilotPerson,
    Event as BtcopilotEvent,
    EventKind as BtcopilotEventKind,
    VariableShift,
)
from btcopilot.pdp import apply_deltas
from pkdiagram.scene import Scene, Person, Event, Marriage
from pkdiagram import util
from btcopilot.schema import EventKind

pytestmark = [
    pytest.mark.component("BtcopilotCompat"),
]


def test_fd_can_load_diagram_after_btcopilot_writes_pdp(scene):
    """
    Verify that FD can still load a diagram file after btcopilot has written PDP data to it.
    FD's Qt Person/Event objects should be preserved, and btcopilot's PDP should be accessible.
    """
    # Create FD Scene with Qt objects
    p1, p2 = scene.addItems(Person(name="Alice"), Person(name="Bob"))
    m = scene.addItem(Marriage(p1, p2))
    child = scene.addItem(Person(name="Charlie"))
    child.setParents(m)
    scene.addItem(
        Event(
            EventKind.Shift,
            p1,
            dateTime=util.Date(2020, 1, 1),
            description="Alice felt anxious",
        )
    )

    # Write FD Scene to pickle (simulating save to file)
    data = {}
    scene.write(data)
    pickled = pickle.dumps(data)

    # Simulate btcopilot loading and adding PDP
    loaded_data = pickle.loads(pickled)
    diagram_data = DiagramData(pdp=PDP(), lastItemId=loaded_data.get("lastItemId", 0))
    pdp_deltas = PDPDeltas(
        people=[BtcopilotPerson(id=-1, name="Mother")],
        events=[
            BtcopilotEvent(
                id=-2,
                kind=BtcopilotEventKind.Shift,
                person=p1.id,  # Reference existing FD person
                anxiety=VariableShift.Up,
                description="Anxiety spike",
            )
        ],
    )
    diagram_data.pdp = apply_deltas(diagram_data.pdp, pdp_deltas)
    # save back to pickle
    loaded_data["pdp"] = diagram_data.pdp
    loaded_data["lastItemId"] = diagram_data.lastItemId
    updated_pickled = pickle.dumps(loaded_data)

    # Verify FD can load the updated pickle
    reloaded_data = pickle.loads(updated_pickled)
    new_scene = Scene()
    new_scene.read(reloaded_data)
    assert len(new_scene.people()) == 3
    people_names = {p.name() for p in new_scene.people()}
    assert people_names == {"Alice", "Bob", "Charlie"}

    assert len(new_scene.marriages()) == 1
    assert len(new_scene.events()) == 1

    assert "pdp" in reloaded_data
    pdp = reloaded_data["pdp"]
    assert len(pdp.people) == 1
    assert pdp.people[0].name == "Mother"
    assert len(pdp.events) == 1
    assert pdp.events[0].person == p1.id


def test_btcopilot_preserves_fd_qt_objects_in_pickle(scene):
    """
    Verify btcopilot's get/set_diagram_data doesn't corrupt FD's Qt Person/Event objects.
    """
    # Create FD Scene with complex Qt objects
    p1 = scene.addItem(Person(name="Person1"))
    p1.setDiagramNotes("Important notes about Person1")
    p1.setGender(util.PERSON_KIND_FEMALE)
    p1.setPrimary(True)

    # Write to pickle
    data = {}
    scene.write(data)
    pickled = pickle.dumps(data)

    # Simulate btcopilot operations (load, add PDP, save)
    loaded_data = pickle.loads(pickled)

    # Verify FD's Person objects are serialized as dicts (not btcopilot dataclasses)
    assert "people" in loaded_data
    fd_people = loaded_data["people"]
    assert len(fd_people) > 0

    # FD serializes Person as dict with all properties
    fd_person = fd_people[0]
    assert isinstance(fd_person, dict)
    assert "name" in fd_person
    assert "diagramNotes" in fd_person
    assert not isinstance(fd_person, BtcopilotPerson)  # Not btcopilot dataclass

    # Add PDP via btcopilot
    diagram_data = DiagramData(pdp=PDP(), lastItemId=loaded_data.get("lastItemId", 0))
    pdp_deltas = PDPDeltas(
        people=[BtcopilotPerson(id=-1, name="PDP Person")],
    )
    diagram_data.pdp = apply_deltas(diagram_data.pdp, pdp_deltas)

    # Simulate btcopilot's set_diagram_data (only updates PDP, not people/events)
    loaded_data["pdp"] = diagram_data.pdp
    loaded_data["lastItemId"] = diagram_data.lastItemId

    # Save back to pickle
    updated_pickled = pickle.dumps(loaded_data)

    # Load again and verify FD Qt objects are still intact
    reloaded_data = pickle.loads(updated_pickled)
    new_scene = Scene()
    new_scene.read(reloaded_data)

    # Verify FD Person properties are preserved
    people = new_scene.people()
    assert len(people) == 1
    person = people[0]
    assert person.name() == "Person1"
    assert person.diagramNotes() == "Important notes about Person1"
    assert person.gender() == util.PERSON_KIND_FEMALE
    assert person.primary() is True

    # Verify PDP is accessible
    assert "pdp" in reloaded_data
    pdp = reloaded_data["pdp"]
    assert len(pdp.people) == 1
    assert pdp.people[0].name == "PDP Person"


def test_empty_pdp_doesnt_break_fd_loading(scene):
    """Verify an empty PDP doesn't cause issues when FD loads the diagram."""
    # Create minimal FD Scene
    p1 = scene.addItem(Person(name="Test"))

    # Write to pickle
    data = {}
    scene.write(data)

    # Add empty PDP
    data["pdp"] = PDP()
    data["lastItemId"] = 1

    pickled = pickle.dumps(data)

    # Verify FD can load it
    reloaded_data = pickle.loads(pickled)
    new_scene = Scene()
    new_scene.read(reloaded_data)

    assert len(new_scene.people()) == 1
    assert new_scene.people()[0].name() == "Test"
