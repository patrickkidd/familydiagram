"""
Tests for Diagram.save() with personal app endpoint (/personal/diagrams).

Uses flask_qnam fixture to test Qt <-> Flask HTTP communication.

NOTE: Optimistic locking conflict handling is tested in backend tests
(btcopilot/tests/personal/test_diagrams.py::test_diagrams_optimistic_locking_conflict).
Testing it here with flask_qnam has issues with 409 response body preservation.
"""

import pickle
from datetime import datetime

import pytest

from btcopilot.pro.models import Diagram as DBDiagram, User
from btcopilot.schema import (
    DiagramData,
    PDP,
    Person,
    Event,
    EventKind,
    PairBond,
    VariableShift,
    RelationshipKind,
    asdict,
)
from btcopilot.extensions import db
from pkdiagram.server_types import Diagram as FEDiagram, User as FEUser, Server
from pkdiagram.scene import Scene


def test_diagram_save_json_format(test_user, flask_app):
    """Test that diagram.save() works with JSON format (personal app endpoint)."""

    # Create backend diagram with PDP data
    initial_data = DiagramData(pdp=PDP(people=[Person(id=-1, name="TestPerson")]))

    with flask_app.app_context():
        db_diagram = DBDiagram(
            user_id=test_user.id,
            data=pickle.dumps(asdict(initial_data)),
        )
        db.session.add(db_diagram)
        db.session.commit()
        diagram_id = db_diagram.id
        initial_version = db_diagram.version

    # Create User proxy for frontend (has secret encoded)
    fe_user = FEUser(
        id=test_user.id,
        username=test_user.username,
        first_name="Test",
        last_name="User",
        roles=[test_user.roles],
        secret=test_user.secret.encode("utf-8"),  # Frontend expects bytes
    )

    # Create frontend diagram instance
    fe_diagram = FEDiagram(
        id=diagram_id,
        user_id=test_user.id,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_data)),
        version=initial_version,
    )

    # Create server instance with user
    server = Server(user=fe_user)

    # Test successful save
    def applyChange(diagramData: DiagramData):
        diagramData.lastItemId = 999
        return diagramData

    def stillValidAfterRefresh(diagramData: DiagramData):
        return True

    success = fe_diagram.save(server, applyChange, stillValidAfterRefresh, useJson=True)

    assert success is True
    assert fe_diagram.version == initial_version + 1
    assert fe_diagram.getDiagramData().lastItemId == 999

    server.deinit()


def test_commit_pdp_items_and_scene_read(qApp):
    """
    Integration test:
    - create PDP entries (negative ids)
    - commit them with DiagramData.commit_pdp_items
    - create a Scene and call Scene.read with the DiagramData contents
    - assert committed people/events exist in the Scene
    """

    # create DiagramData and populate PDP with two people and a married event
    diagramData = DiagramData.create_with_defaults()

    # PDP people/events use negative IDs
    p1 = Person(id=-1, name="Alice")
    p2 = Person(id=-2, name="Bob")
    ev = Event(
        id=-3,
        kind=EventKind.Married,
        person=-1,
        spouse=-2,
        dateTime="2000-01-01T00:00:00",
    )

    diagramData.pdp.people.extend([p1, p2])
    diagramData.pdp.events.append(ev)

    # commit all PDP items (expects negative ids)
    id_map = diagramData.commit_pdp_items([-1, -2, -3])
    assert -1 in id_map and -2 in id_map and -3 in id_map

    # Build data dict and read into Scene
    data = asdict(diagramData)
    scene = Scene()
    scene.read(data)

    # Ensure committed people exist in the scene
    committed_ids = set(id_map.values())
    found_people = [p for p in scene.people() if p.id in committed_ids]
    assert (
        len(found_people) >= 2
    ), f"Expected at least 2 committed people, got {len(found_people)}"

    # Ensure the married event exists and links the committed people
    married_events = [e for e in scene.events() if e.kind() == EventKind.Married]
    assert married_events, "No married events found in scene after read"
    married_event = married_events[-1]
    person_obj = married_event.person()
    spouse_obj = married_event.spouse()
    assert person_obj is not None and spouse_obj is not None
    assert person_obj.id in committed_ids and spouse_obj.id in committed_ids


def _commit_and_load_scene(diagramData: DiagramData, item_ids: list[int]):
    """Helper: Commit PDP items and load into Scene."""
    id_mapping = diagramData.commit_pdp_items(item_ids)
    scene = Scene()
    scene_data = asdict(diagramData)
    error = scene.read(scene_data)
    assert error is None, f"Scene.read failed: {error}"
    return scene, id_mapping


def test_commit_person_with_parents(qApp):
    """Person.parents field should create ChildOf relationship in Scene."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Father"),
                Person(id=-2, name="Mother"),
                Person(id=-3, name="Child", parents=-4),
            ],
            events=[],
            pair_bonds=[
                PairBond(id=-4, person_a=-1, person_b=-2),
            ],
        ),
        lastItemId=0,
    )

    scene, id_mapping = _commit_and_load_scene(diagramData, [-1, -2, -3, -4])

    # Verify all people committed
    assert len(scene.people()) == 3

    # Verify marriage exists
    marriages = scene.marriages()
    assert len(marriages) == 1
    marriage = marriages[0]

    # Find the child
    child = next(p for p in scene.people() if p.name() == "Child")
    assert child is not None

    # Verify child's parent relationship
    assert child.childOf is not None, "Child should have childOf set"
    assert child.childOf.parents() == marriage, "Child's parents should be the marriage"


# =============================================================================
# Category 1: Person Field Mapping
# =============================================================================


def test_commit_person_basic(qApp):
    """Minimal person with just id/name commits and loads correctly."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[Person(id=-1, name="Alice")],
            events=[],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, id_mapping = _commit_and_load_scene(diagramData, [-1])

    assert len(scene.people()) == 1
    person = scene.people()[0]
    assert person.name() == "Alice"
    assert person.id == id_mapping[-1]


def test_commit_person_with_last_name(qApp):
    """Person.last_name maps correctly to Scene."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[Person(id=-1, name="Alice", last_name="Smith")],
            events=[],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1])

    person = scene.people()[0]
    assert person.name() == "Alice"
    assert person.lastName() == "Smith"


def test_commit_multiple_children_same_parents(qApp):
    """Multiple children referencing same PairBond load correctly."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Parent A"),
                Person(id=-2, name="Parent B"),
                Person(id=-3, name="Child 1", parents=-5),
                Person(id=-4, name="Child 2", parents=-5),
            ],
            events=[],
            pair_bonds=[
                PairBond(id=-5, person_a=-1, person_b=-2),
            ],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2, -3, -4, -5])

    marriage = scene.marriages()[0]
    child1 = next(p for p in scene.people() if p.name() == "Child 1")
    child2 = next(p for p in scene.people() if p.name() == "Child 2")

    assert child1.childOf is not None
    assert child2.childOf is not None
    assert child1.childOf.parents() == marriage
    assert child2.childOf.parents() == marriage


# =============================================================================
# Category 2: Event Field Mapping
# =============================================================================


def test_commit_event_datetime_conversion(qApp):
    """String dateTime converts to QDateTime in Scene."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[Person(id=-1, name="Alice")],
            events=[
                Event(
                    id=-2,
                    kind=EventKind.Shift,
                    person=-1,
                    dateTime="1985-06-15",
                    description="Test event",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2])

    events = list(scene.events())
    assert len(events) == 1
    event = events[0]
    assert event.dateTime() is not None
    assert not event.dateTime().isNull()
    assert event.dateTime().date().year() == 1985
    assert event.dateTime().date().month() == 6
    assert event.dateTime().date().day() == 15


def test_commit_event_with_child_field(qApp):
    """Event.child field is remapped and resolved correctly."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Father"),
                Person(id=-2, name="Mother"),
                Person(id=-3, name="Child"),
            ],
            events=[
                Event(
                    id=-4,
                    kind=EventKind.Birth,
                    person=-1,
                    spouse=-2,
                    child=-3,
                    dateTime="2010-01-01",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, id_mapping = _commit_and_load_scene(diagramData, [-1, -2, -3, -4])

    birth_events = [e for e in scene.events() if e.kind() == EventKind.Birth]
    assert len(birth_events) == 1
    birth_event = birth_events[0]

    assert birth_event.child() is not None
    assert birth_event.child().name() == "Child"
    assert birth_event.child().id == id_mapping[-3]


def test_commit_shift_event_with_variables(qApp):
    """Shift event with symptom/anxiety/functioning loads correctly."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[Person(id=-1, name="Alice")],
            events=[
                Event(
                    id=-2,
                    kind=EventKind.Shift,
                    person=-1,
                    symptom=VariableShift.Up,
                    anxiety=VariableShift.Down,
                    functioning=VariableShift.Same,
                    dateTime="2020-01-01",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2])

    event = list(scene.events())[0]
    assert event.symptom() == VariableShift.Up
    assert event.anxiety() == VariableShift.Down
    assert event.functioning() == VariableShift.Same


def test_commit_shift_event_with_relationship(qApp):
    """Shift event with relationship and targets loads correctly."""
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
                    relationship=RelationshipKind.Conflict,
                    relationshipTargets=[-2],
                    dateTime="2020-01-01",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, id_mapping = _commit_and_load_scene(diagramData, [-1, -2, -3])

    event = list(scene.events())[0]
    assert event.relationship() == RelationshipKind.Conflict
    targets = event.relationshipTargets()
    assert len(targets) == 1
    assert targets[0].name() == "Bob"


def test_commit_shift_event_with_triangles(qApp):
    """Shift event with relationshipTriangles loads correctly."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Alice"),
                Person(id=-2, name="Bob"),
                Person(id=-3, name="Charlie"),
            ],
            events=[
                Event(
                    id=-4,
                    kind=EventKind.Shift,
                    person=-1,
                    relationship=RelationshipKind.Inside,
                    relationshipTargets=[-2],
                    relationshipTriangles=[-3],
                    dateTime="2020-01-01",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2, -3, -4])

    event = list(scene.events())[0]
    triangles = event.relationshipTriangles()
    assert len(triangles) == 1
    assert triangles[0].name() == "Charlie"


# =============================================================================
# Category 3: PairBond Events
# =============================================================================


def test_commit_bonded_event(qApp):
    """EventKind.Bonded with person+spouse loads correctly."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Alice"),
                Person(id=-2, name="Bob"),
            ],
            events=[
                Event(
                    id=-3,
                    kind=EventKind.Bonded,
                    person=-1,
                    spouse=-2,
                    dateTime="2015-01-01",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2, -3])

    bonded_events = [e for e in scene.events() if e.kind() == EventKind.Bonded]
    assert len(bonded_events) == 1
    assert bonded_events[0].person().name() == "Alice"
    assert bonded_events[0].spouse().name() == "Bob"


def test_commit_married_event(qApp):
    """EventKind.Married loads correctly."""
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
                    dateTime="2010-06-15",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2, -3])

    married_events = [e for e in scene.events() if e.kind() == EventKind.Married]
    assert len(married_events) == 1
    event = married_events[0]
    assert event.person().name() == "Alice"
    assert event.spouse().name() == "Bob"


def test_commit_birth_event(qApp):
    """EventKind.Birth with person+spouse+child loads correctly."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Father"),
                Person(id=-2, name="Mother"),
                Person(id=-3, name="Baby"),
            ],
            events=[
                Event(
                    id=-4,
                    kind=EventKind.Birth,
                    person=-1,
                    spouse=-2,
                    child=-3,
                    dateTime="2020-03-15",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2, -3, -4])

    birth_events = [e for e in scene.events() if e.kind() == EventKind.Birth]
    assert len(birth_events) == 1
    event = birth_events[0]
    assert event.person().name() == "Father"
    assert event.spouse().name() == "Mother"
    assert event.child().name() == "Baby"


def test_commit_separated_event(qApp):
    """EventKind.Separated loads correctly."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Alice"),
                Person(id=-2, name="Bob"),
            ],
            events=[
                Event(
                    id=-3,
                    kind=EventKind.Separated,
                    person=-1,
                    spouse=-2,
                    dateTime="2022-01-01",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2, -3])

    separated_events = [e for e in scene.events() if e.kind() == EventKind.Separated]
    assert len(separated_events) == 1


def test_commit_divorced_event(qApp):
    """EventKind.Divorced loads correctly."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Alice"),
                Person(id=-2, name="Bob"),
            ],
            events=[
                Event(
                    id=-3,
                    kind=EventKind.Divorced,
                    person=-1,
                    spouse=-2,
                    dateTime="2023-01-01",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2, -3])

    divorced_events = [e for e in scene.events() if e.kind() == EventKind.Divorced]
    assert len(divorced_events) == 1


# =============================================================================
# Category 4: PairBond/Marriage Mapping
# =============================================================================


def test_commit_pairbond_basic(qApp):
    """PairBond maps to Marriage with person_a/person_b."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Alice"),
                Person(id=-2, name="Bob"),
            ],
            events=[],
            pair_bonds=[
                PairBond(id=-3, person_a=-1, person_b=-2),
            ],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2, -3])

    marriages = scene.marriages()
    assert len(marriages) == 1
    marriage = marriages[0]
    people_in_marriage = {marriage.personA().name(), marriage.personB().name()}
    assert people_in_marriage == {"Alice", "Bob"}


def test_commit_pairbond_both_pdp(qApp):
    """PairBond with both persons as negative IDs commits transitively."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Alice"),
                Person(id=-2, name="Bob"),
            ],
            events=[],
            pair_bonds=[
                PairBond(id=-3, person_a=-1, person_b=-2),
            ],
        ),
        lastItemId=0,
    )

    # Only commit the PairBond - should transitively commit both persons
    scene, id_mapping = _commit_and_load_scene(diagramData, [-3])

    assert -1 in id_mapping
    assert -2 in id_mapping
    assert len(scene.people()) == 2
    assert len(scene.marriages()) == 1


# =============================================================================
# Category 5: Transitive Closure & ID Remapping
# =============================================================================


def test_commit_transitive_event_persons(qApp):
    """Committing event transitively commits person and spouse."""
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
                    dateTime="2020-01-01",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    # Only commit the event - should transitively commit both persons
    scene, id_mapping = _commit_and_load_scene(diagramData, [-3])

    assert -1 in id_mapping
    assert -2 in id_mapping
    assert len(scene.people()) == 2


def test_commit_transitive_person_parents(qApp):
    """Committing person with parents transitively commits PairBond."""
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

    # Only commit the child - should transitively commit parents and PairBond
    scene, id_mapping = _commit_and_load_scene(diagramData, [-3])

    assert -1 in id_mapping
    assert -2 in id_mapping
    assert -4 in id_mapping
    assert len(scene.people()) == 3
    assert len(scene.marriages()) == 1


def test_commit_transitive_birth_chain(qApp):
    """Birth event commits parents, child, and referenced PairBond."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Father"),
                Person(id=-2, name="Mother"),
                Person(id=-3, name="Baby", parents=-5),
            ],
            events=[
                Event(
                    id=-4,
                    kind=EventKind.Birth,
                    person=-1,
                    spouse=-2,
                    child=-3,
                    dateTime="2020-01-01",
                ),
            ],
            pair_bonds=[
                PairBond(id=-5, person_a=-1, person_b=-2),
            ],
        ),
        lastItemId=0,
    )

    # Only commit the birth event - should transitively commit all
    scene, id_mapping = _commit_and_load_scene(diagramData, [-4])

    assert -1 in id_mapping  # Father
    assert -2 in id_mapping  # Mother
    assert -3 in id_mapping  # Baby
    assert -5 in id_mapping  # PairBond
    assert len(scene.people()) == 3
    assert len(scene.marriages()) == 1


def test_commit_relationship_targets_remapped(qApp):
    """Event.relationshipTargets IDs are remapped correctly."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Alice"),
                Person(id=-2, name="Bob"),
                Person(id=-3, name="Charlie"),
            ],
            events=[
                Event(
                    id=-4,
                    kind=EventKind.Shift,
                    person=-1,
                    relationship=RelationshipKind.Conflict,
                    relationshipTargets=[-2, -3],
                    dateTime="2020-01-01",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, id_mapping = _commit_and_load_scene(diagramData, [-1, -2, -3, -4])

    event = list(scene.events())[0]
    targets = event.relationshipTargets()
    target_names = {t.name() for t in targets}
    assert target_names == {"Bob", "Charlie"}


# =============================================================================
# Category 6: Scene Integration Verification
# =============================================================================


def test_scene_eventsFor_after_commit(qApp):
    """scene.eventsFor(person) works after PDP commit."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[Person(id=-1, name="Alice")],
            events=[
                Event(
                    id=-2,
                    kind=EventKind.Shift,
                    person=-1,
                    dateTime="2020-01-01",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2])

    person = scene.people()[0]
    events = scene.eventsFor(person)
    assert len(events) == 1


def test_scene_marriageFor_after_commit(qApp):
    """scene.marriageFor(a, b) returns Marriage after PDP commit."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Alice"),
                Person(id=-2, name="Bob"),
            ],
            events=[],
            pair_bonds=[
                PairBond(id=-3, person_a=-1, person_b=-2),
            ],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2, -3])

    alice = next(p for p in scene.people() if p.name() == "Alice")
    bob = next(p for p in scene.people() if p.name() == "Bob")
    marriage = scene.marriageFor(alice, bob)
    assert marriage is not None


def test_scene_person_parents_resolved(qApp):
    """person.parents() returns Marriage after PDP commit with parents field."""
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

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2, -3, -4])

    child = next(p for p in scene.people() if p.name() == "Child")
    assert child.parents() is not None
    assert child.parents() == scene.marriages()[0]


def test_scene_event_child_resolved(qApp):
    """birth_event.child() returns Person after PDP commit."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Father"),
                Person(id=-2, name="Mother"),
                Person(id=-3, name="Baby"),
            ],
            events=[
                Event(
                    id=-4,
                    kind=EventKind.Birth,
                    person=-1,
                    spouse=-2,
                    child=-3,
                    dateTime="2020-01-01",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2, -3, -4])

    birth_event = [e for e in scene.events() if e.kind() == EventKind.Birth][0]
    assert birth_event.child() is not None
    assert birth_event.child().name() == "Baby"


# =============================================================================
# Category 7: Edge Cases & Error Handling
# =============================================================================


def test_commit_person_without_parents(qApp):
    """Person without parents field loads correctly."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[Person(id=-1, name="Orphan")],
            events=[],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1])

    person = scene.people()[0]
    assert person.childOf is None


def test_commit_event_without_datetime(qApp):
    """Event with dateTime=None is pruned by Scene (expected behavior)."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[Person(id=-1, name="Alice")],
            events=[
                Event(
                    id=-2,
                    kind=EventKind.Shift,
                    person=-1,
                    dateTime=None,
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2])

    # Events without dateTime are intentionally pruned by Scene
    events = list(scene.events())
    assert len(events) == 0


def test_commit_event_with_enddatetime(qApp):
    """Event with both dateTime and endDateTime loads correctly."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[Person(id=-1, name="Alice")],
            events=[
                Event(
                    id=-2,
                    kind=EventKind.Shift,
                    person=-1,
                    dateTime="2020-01-01",
                    endDateTime="2020-12-31",
                ),
            ],
            pair_bonds=[],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2])

    event = list(scene.events())[0]
    assert event.endDateTime() is not None
    assert event.endDateTime().date().year() == 2020
    assert event.endDateTime().date().month() == 12


# =============================================================================
# Category 8: Multi-Generation Family Structure
# =============================================================================


def test_commit_three_generation_family(qApp):
    """Three-generation family structure loads correctly."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Grandpa"),
                Person(id=-2, name="Grandma"),
                Person(id=-3, name="Father", parents=-7),
                Person(id=-4, name="Mother"),
                Person(id=-5, name="Child", parents=-8),
                Person(id=-6, name="Sibling", parents=-8),
            ],
            events=[],
            pair_bonds=[
                PairBond(id=-7, person_a=-1, person_b=-2),  # Grandparents
                PairBond(id=-8, person_a=-3, person_b=-4),  # Parents
            ],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2, -3, -4, -5, -6, -7, -8])

    assert len(scene.people()) == 6
    assert len(scene.marriages()) == 2

    father = next(p for p in scene.people() if p.name() == "Father")
    child = next(p for p in scene.people() if p.name() == "Child")
    sibling = next(p for p in scene.people() if p.name() == "Sibling")

    # Father's parents are grandparents
    assert father.childOf is not None
    grandparents_marriage = father.childOf.parents()
    assert {
        grandparents_marriage.personA().name(),
        grandparents_marriage.personB().name(),
    } == {
        "Grandpa",
        "Grandma",
    }

    # Child and sibling have same parents
    assert child.childOf is not None
    assert sibling.childOf is not None
    assert child.childOf.parents() == sibling.childOf.parents()


def test_commit_sibling_group(qApp):
    """Multiple siblings from same parents all resolve correctly."""
    diagramData = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Parent A"),
                Person(id=-2, name="Parent B"),
                Person(id=-3, name="Child 1", parents=-6),
                Person(id=-4, name="Child 2", parents=-6),
                Person(id=-5, name="Child 3", parents=-6),
            ],
            events=[],
            pair_bonds=[
                PairBond(id=-6, person_a=-1, person_b=-2),
            ],
        ),
        lastItemId=0,
    )

    scene, _ = _commit_and_load_scene(diagramData, [-1, -2, -3, -4, -5, -6])

    marriage = scene.marriages()[0]
    children = [p for p in scene.people() if p.childOf is not None]
    assert len(children) == 3

    for child in children:
        assert child.childOf.parents() == marriage
