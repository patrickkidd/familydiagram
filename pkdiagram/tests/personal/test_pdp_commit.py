import pytest

from btcopilot.schema import (
    DiagramData,
    PDP,
    Person,
    Event,
    EventKind,
    PairBond,
    RelationshipKind,
    VariableShift,
)


def test_accept_pair_bond_event_includes_pair_bond():
    diagram_data = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Tom"),
                Person(id=-2, name="Susan"),
            ],
            pair_bonds=[
                PairBond(id=-10, person_a=-1, person_b=-2),
            ],
            events=[
                Event(id=-20, kind=EventKind.Married, person=-1, spouse=-2),
            ],
        )
    )

    diagram_data.commit_pdp_items([-20])

    assert len(diagram_data.pdp.people) == 0
    assert len(diagram_data.pdp.pair_bonds) == 0
    assert len(diagram_data.pdp.events) == 0
    assert len(diagram_data.people) == 2
    assert len(diagram_data.pair_bonds) == 1
    assert len(diagram_data.events) == 1


def test_accept_child_event_includes_parents_pair_bond():
    diagram_data = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Dad"),
                Person(id=-2, name="Mom"),
                Person(id=-3, name="Child", parents=-10),
            ],
            pair_bonds=[
                PairBond(id=-10, person_a=-1, person_b=-2),
            ],
            events=[
                Event(id=-20, kind=EventKind.Birth, person=-1, spouse=-2, child=-3),
            ],
        )
    )

    diagram_data.commit_pdp_items([-20])

    assert len(diagram_data.people) == 3
    assert len(diagram_data.pair_bonds) == 1
    assert len(diagram_data.events) == 1
    child = next(p for p in diagram_data.people if p["name"] == "Child")
    assert child["parents"] == diagram_data.pair_bonds[0]["id"]


def test_accept_event_with_existing_diagram_person():
    diagram_data = DiagramData(
        people=[{"id": 1, "name": "Tom"}],
        pdp=PDP(
            people=[Person(id=-2, name="Susan")],
            pair_bonds=[PairBond(id=-10, person_a=1, person_b=-2)],
            events=[
                Event(id=-23, kind=EventKind.Married, person=1, spouse=-2),
            ],
        ),
        lastItemId=1,
    )

    diagram_data.commit_pdp_items([-23])

    assert len(diagram_data.people) == 2
    assert len(diagram_data.pair_bonds) == 1
    assert len(diagram_data.events) == 1


def test_accept_shift_event_with_sarf_variables():
    diagram_data = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Tom"),
                Person(id=-2, name="Susan"),
            ],
            events=[
                Event(
                    id=-30,
                    kind=EventKind.Shift,
                    person=-1,
                    symptom=VariableShift.Up,
                    anxiety=VariableShift.Down,
                    functioning=VariableShift.Up,
                    relationship=RelationshipKind.Conflict,
                    relationshipTargets=[-2],
                ),
            ],
        )
    )

    diagram_data.commit_pdp_items([-30])

    assert len(diagram_data.people) == 2
    event = diagram_data.events[0]
    assert event["symptom"] == VariableShift.Up.value
    assert event["anxiety"] == VariableShift.Down.value
    assert event["functioning"] == VariableShift.Up.value
    assert event["relationship"] == RelationshipKind.Conflict.value
    assert event["relationshipTargets"][0] > 0


def test_accept_shift_event_with_triangle():
    diagram_data = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Tom"),
                Person(id=-2, name="Susan"),
                Person(id=-3, name="Alice"),
            ],
            events=[
                Event(
                    id=-44,
                    kind=EventKind.Shift,
                    person=-3,
                    relationship=RelationshipKind.Inside,
                    relationshipTargets=[-1],
                    relationshipTriangles=[-2],
                ),
            ],
        )
    )

    diagram_data.commit_pdp_items([-44])

    assert len(diagram_data.people) == 3
    event = diagram_data.events[0]
    assert event["relationship"] == RelationshipKind.Inside.value
    assert len(event["relationshipTargets"]) == 1
    assert len(event["relationshipTriangles"]) == 1


def test_accept_multiple_events_sequentially():
    diagram_data = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Tom"),
                Person(id=-2, name="Susan"),
                Person(id=-3, name="Linda"),
            ],
            pair_bonds=[
                PairBond(id=-10, person_a=-1, person_b=-2),
                PairBond(id=-11, person_a=-1, person_b=-3),
            ],
            events=[
                Event(id=-22, kind=EventKind.Married, person=-1, spouse=-2),
                Event(id=-23, kind=EventKind.Bonded, person=-1, spouse=-3),
            ],
        )
    )

    diagram_data.commit_pdp_items([-22])
    assert len(diagram_data.pair_bonds) == 1
    assert len(diagram_data.people) == 2

    diagram_data.commit_pdp_items([-23])
    assert len(diagram_data.pair_bonds) == 2
    assert len(diagram_data.people) == 3
    assert len(diagram_data.events) == 2


def test_reject_person_cascades_to_events_and_pair_bonds():
    diagram_data = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Tom"),
                Person(id=-2, name="Susan"),
            ],
            pair_bonds=[
                PairBond(id=-10, person_a=-1, person_b=-2),
            ],
            events=[
                Event(id=-30, kind=EventKind.Shift, person=-1),
                Event(id=-23, kind=EventKind.Married, person=-1, spouse=-2),
            ],
        )
    )

    diagram_data.reject_pdp_item(-1)

    assert len(diagram_data.pdp.people) == 1
    assert diagram_data.pdp.people[0].name == "Susan"
    assert len(diagram_data.pdp.pair_bonds) == 0
    assert len(diagram_data.pdp.events) == 0


def test_reject_pair_bond_cascades_to_children():
    diagram_data = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Tom"),
                Person(id=-2, name="Susan"),
                Person(id=-3, name="Alice", parents=-10),
                Person(id=-4, name="Bob", parents=-10),
            ],
            pair_bonds=[
                PairBond(id=-10, person_a=-1, person_b=-2),
            ],
        )
    )

    diagram_data.reject_pdp_item(-10)

    assert len(diagram_data.pdp.pair_bonds) == 0
    remaining_names = {p.name for p in diagram_data.pdp.people}
    assert remaining_names == {"Tom", "Susan"}


def test_id_remapping_preserves_references():
    diagram_data = DiagramData(
        pdp=PDP(
            people=[
                Person(id=-1, name="Tom"),
                Person(id=-2, name="Susan"),
                Person(id=-3, name="Alice", parents=-10),
            ],
            pair_bonds=[
                PairBond(id=-10, person_a=-1, person_b=-2),
            ],
            events=[
                Event(id=-28, kind=EventKind.Birth, person=-1, spouse=-2, child=-3),
            ],
        ),
        lastItemId=100,
    )

    diagram_data.commit_pdp_items([-28])

    for person in diagram_data.people:
        assert person["id"] > 0
        if person.get("parents"):
            assert person["parents"] > 0

    for pb in diagram_data.pair_bonds:
        assert pb["id"] > 0
        assert pb["person_a"] > 0
        assert pb["person_b"] > 0

    for event in diagram_data.events:
        assert event["id"] > 0
        if event.get("person"):
            assert event["person"] > 0
        if event.get("spouse"):
            assert event["spouse"] > 0
        if event.get("child"):
            assert event["child"] > 0
