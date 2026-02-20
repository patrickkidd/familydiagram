from datetime import datetime
import pickle

import pytest

from pkdiagram.server_types import Diagram
from btcopilot.schema import (
    DiagramData,
    PDP,
    Person,
    Event,
    EventKind,
    PairBond,
    asdict,
)


@pytest.fixture
def diagram_with_json():
    """Diagram using JSON (Personal app style)"""
    initial_data = DiagramData(
        people=[],
        events=[],
        pair_bonds=[],
        pdp=PDP(
            people=[Person(id=-1, name="Test Person")],
            events=[Event(id=-2, kind=EventKind.Shift, person=-1)],
            pair_bonds=[],
        ),
        lastItemId=100,
    )
    return Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_data)),
        version=1,
    )


def test_getDiagramData_with_json():
    initial_data = DiagramData(
        pdp=PDP(people=[Person(id=-1, name="Alice")]),
        lastItemId=50,
    )
    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_data)),
    )

    result = diagram.getDiagramData()

    assert isinstance(result, DiagramData)
    assert result.lastItemId == 50
    assert len(result.pdp.people) == 1
    assert result.pdp.people[0].name == "Alice"
    assert result.pdp.people[0].id == -1


def test_getDiagramData_with_empty_pdp():
    initial_data = DiagramData(lastItemId=10)
    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_data)),
    )

    result = diagram.getDiagramData()

    assert isinstance(result, DiagramData)
    assert len(result.pdp.people) == 0
    assert len(result.pdp.events) == 0
    assert len(result.pdp.pair_bonds) == 0


def test_setDiagramData_with_json():
    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps({}),
    )

    new_data = DiagramData(
        pdp=PDP(
            people=[Person(id=-1, name="Bob")],
            events=[Event(id=-2, kind=EventKind.Birth, person=-1)],
        ),
        lastItemId=75,
    )

    diagram.setDiagramData(new_data)

    assert isinstance(diagram.data, bytes)
    unpickled = pickle.loads(diagram.data)
    assert unpickled["lastItemId"] == 75
    assert len(unpickled["pdp"]["people"]) == 1
    assert unpickled["pdp"]["people"][0]["name"] == "Bob"


def test_getDiagramData_preserves_all_fields():
    initial_data = DiagramData(
        people=[{"id": 1, "name": "Alice"}],
        emotions=[{"id": 10, "kind": "conflict"}],
        layers=[{"id": 20, "name": "default"}],
        hideNames=True,
        scaleFactor=1.5,
        pdp=PDP(people=[Person(id=-1, name="Bob")]),
        lastItemId=50,
    )
    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_data)),
    )

    result = diagram.getDiagramData()

    assert result.people == [{"id": 1, "name": "Alice"}]
    assert result.emotions == [{"id": 10, "kind": "conflict"}]
    assert result.layers == [{"id": 20, "name": "default"}]
    assert result.hideNames is True
    assert result.scaleFactor == 1.5
    assert result.lastItemId == 50
    assert len(result.pdp.people) == 1


def test_getDiagramData_ignores_unknown_fields():
    blob = {"people": [], "lastItemId": 5, "unknownField": "junk"}
    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(blob),
    )

    result = diagram.getDiagramData()

    assert result.lastItemId == 5
    assert not hasattr(result, "unknownField")


def test_getDiagramData_setDiagramData_roundtrip():
    initial_data = DiagramData(
        pdp=PDP(
            people=[Person(id=-1, name="Charlie", last_name="Brown")],
            events=[Event(id=-2, kind=EventKind.Married, person=-1, spouse=-3)],
            pair_bonds=[PairBond(id=-4, person_a=-1, person_b=-3)],
        ),
        lastItemId=200,
    )

    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_data)),
    )

    retrieved = diagram.getDiagramData()
    diagram.setDiagramData(retrieved)
    final = diagram.getDiagramData()

    assert final.lastItemId == 200
    assert len(final.pdp.people) == 1
    assert final.pdp.people[0].name == "Charlie"
    assert final.pdp.people[0].last_name == "Brown"
    assert len(final.pdp.events) == 1
    assert final.pdp.events[0].spouse == -3
    assert len(final.pdp.pair_bonds) == 1
    assert final.pdp.pair_bonds[0].person_a == -1


def test_commit_pdp_items_removes_from_pdp(diagram_with_json):
    diagram_data = diagram_with_json.getDiagramData()

    assert len(diagram_data.pdp.people) == 1
    assert len(diagram_data.pdp.events) == 1

    id_mapping = diagram_data.commit_pdp_items([-1])

    assert len(diagram_data.pdp.people) == 0
    assert len(diagram_data.pdp.events) == 1
    assert -1 in id_mapping
    assert id_mapping[-1] > 0


def test_commit_pdp_items_adds_to_main_diagram():
    initial_data = DiagramData(
        pdp=PDP(
            people=[Person(id=-1, name="Test Person")],
            events=[Event(id=-2, kind=EventKind.Shift, person=-1)],
        ),
        lastItemId=100,
    )
    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_data)),
    )

    diagram_data = diagram.getDiagramData()

    assert len(diagram_data.people) == 0
    assert len(diagram_data.events) == 0

    id_mapping = diagram_data.commit_pdp_items([-1, -2])

    assert len(diagram_data.people) == 1
    assert len(diagram_data.events) == 1

    committed_person = diagram_data.people[0]
    assert committed_person["id"] == id_mapping[-1]
    assert committed_person["id"] > 0
    assert committed_person["name"] == "Test Person"

    committed_event = diagram_data.events[0]
    assert committed_event["id"] == id_mapping[-2]
    assert committed_event["id"] > 0
    assert committed_event["person"] == id_mapping[-1]


def test_commit_pdp_items_with_transitive_closure():
    initial_data = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Parent A"),
                Person(id=-2, name="Parent B"),
                Person(id=-3, name="Child", parents=-4),
            ],
            pair_bonds=[PairBond(id=-4, person_a=-1, person_b=-2)],
        ),
        lastItemId=50,
    )

    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_data)),
    )

    diagram_data = diagram.getDiagramData()
    id_mapping = diagram_data.commit_pdp_items([-3])

    assert len(diagram_data.pdp.people) == 0
    assert len(diagram_data.pdp.pair_bonds) == 0

    assert len(diagram_data.people) == 3
    assert len(diagram_data.pair_bonds) == 1

    child = next(p for p in diagram_data.people if p["name"] == "Child")
    assert child["parents"] > 0
    assert child["parents"] == id_mapping[-4]


def test_commit_pdp_items_preserves_lastItemId():
    initial_data = DiagramData(
        pdp=PDP(people=[Person(id=-1, name="Test")]),
        lastItemId=100,
    )

    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_data)),
    )

    diagram_data = diagram.getDiagramData()
    id_mapping = diagram_data.commit_pdp_items([-1])

    assert diagram_data.lastItemId == id_mapping[-1]
    assert diagram_data.lastItemId > 100


def test_commit_pdp_items_raises_on_positive_id():
    initial_data = DiagramData(
        pdp=PDP(people=[Person(id=-1, name="Test")]),
    )

    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_data)),
    )

    diagram_data = diagram.getDiagramData()

    with pytest.raises(ValueError, match="must be negative"):
        diagram_data.commit_pdp_items([1])


def test_commit_pdp_items_raises_on_missing_item():
    initial_data = DiagramData(
        pdp=PDP(people=[Person(id=-1, name="Test")]),
    )

    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_data)),
    )

    diagram_data = diagram.getDiagramData()

    with pytest.raises(ValueError, match="not found in PDP"):
        diagram_data.commit_pdp_items([-999])


def test_setDiagramData_after_commit_persists():
    initial_data = DiagramData(
        pdp=PDP(people=[Person(id=-1, name="Test")]),
        lastItemId=50,
    )

    diagram = Diagram(
        id=1,
        user_id=1,
        access_rights=[],
        created_at=datetime.utcnow(),
        data=pickle.dumps(asdict(initial_data)),
    )

    diagram_data = diagram.getDiagramData()
    diagram_data.commit_pdp_items([-1])
    diagram.setDiagramData(diagram_data)

    final = diagram.getDiagramData()

    assert len(final.pdp.people) == 0
    assert len(final.people) == 1
    assert final.people[0]["name"] == "Test"
