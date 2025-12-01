#!/usr/bin/env python3
import os
import sys
import pickle

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "btcopilot"
    ),
)

os.environ.setdefault("FLASK_CONFIG", "development")

from btcopilot.app import create_app
from btcopilot.extensions import db
from btcopilot.pro.models import Diagram
from btcopilot.personal.models import Discussion, Statement, Speaker
from btcopilot.schema import (
    DiagramData,
    PDP,
    Person,
    Event,
    EventKind,
    PairBond,
    RelationshipKind,
    VariableShift,
    asdict,
)


def reset_diagram(diagram_id: int):
    app = create_app()

    with app.app_context():
        diagram = db.session.get(Diagram, diagram_id)
        if not diagram:
            print(f"Diagram {diagram_id} not found")
            sys.exit(1)

        discussions = Discussion.query.filter_by(diagram_id=diagram_id).all()
        for discussion in discussions:
            Statement.query.filter_by(discussion_id=discussion.id).delete()
            Speaker.query.filter_by(discussion_id=discussion.id).delete()
            db.session.delete(discussion)
        print(f"Deleted {len(discussions)} discussions")

        existing_people = [
            asdict(Person(id=1, name="Grandpa Joe")),
            asdict(Person(id=2, name="Grandma Mary")),
        ]
        existing_pair_bonds = [
            asdict(PairBond(id=3, person_a=1, person_b=2)),
        ]
        existing_events = []

        pdp_people = [
            Person(id=-1, name="Dad (Tom)", parents=3),
            Person(id=-2, name="Mom (Susan)"),
            Person(id=-3, name="Alice", parents=-10),
            Person(id=-4, name="Bob", parents=-10),
            Person(id=-5, name="Charlie (adopted)", parents=-10),
            Person(id=-6, name="Ex (Linda)"),
        ]

        pdp_pair_bonds = [
            PairBond(id=-10, person_a=-1, person_b=-2),
            PairBond(id=-11, person_a=-1, person_b=-6),
        ]

        pdp_events = [
            Event(
                id=-20,
                kind=EventKind.Birth,
                person=1,
                spouse=2,
                child=-1,
                description="Tom born",
                dateTime="1960-05-20",
            ),
            Event(
                id=-21,
                kind=EventKind.Adopted,
                person=-1,
                spouse=-2,
                child=-5,
                description="Charlie adopted",
                dateTime="2005-03-15",
            ),
            Event(
                id=-28,
                kind=EventKind.Birth,
                person=-1,
                spouse=-2,
                child=-3,
                description="Alice born",
                dateTime="1990-01-15",
            ),
            Event(
                id=-29,
                kind=EventKind.Birth,
                person=-1,
                spouse=-2,
                child=-4,
                description="Bob born",
                dateTime="1992-06-20",
            ),
            Event(
                id=-22,
                kind=EventKind.Bonded,
                person=-1,
                spouse=-6,
                description="Tom & Linda bonded",
                dateTime="1982-01-01",
            ),
            Event(
                id=-23,
                kind=EventKind.Married,
                person=-1,
                spouse=-2,
                description="Tom & Susan wedding",
                dateTime="1985-06-15",
            ),
            Event(
                id=-24,
                kind=EventKind.Separated,
                person=-1,
                spouse=-6,
                description="Tom & Linda separated",
                dateTime="1984-06-01",
            ),
            Event(
                id=-25,
                kind=EventKind.Divorced,
                person=-1,
                spouse=-6,
                description="Tom & Linda divorced",
                dateTime="1984-12-01",
            ),
            Event(
                id=-26,
                kind=EventKind.Moved,
                person=-1,
                spouse=-2,
                description="Family moved to new city",
                dateTime="1990-08-01",
            ),
            Event(
                id=-27,
                kind=EventKind.Death,
                person=1,
                description="Grandpa Joe passed",
                dateTime="2020-01-15",
            ),
            Event(
                id=-30,
                kind=EventKind.Shift,
                person=-1,
                description="Tom health issue",
                dateTime="2015-03-01",
                symptom=VariableShift.Up,
            ),
            Event(
                id=-31,
                kind=EventKind.Shift,
                person=-2,
                description="Susan worry about kids",
                dateTime="2018-09-01",
                anxiety=VariableShift.Up,
            ),
            Event(
                id=-32,
                kind=EventKind.Shift,
                person=-3,
                description="Alice got promotion",
                dateTime="2020-06-01",
                functioning=VariableShift.Up,
            ),
            Event(
                id=-40,
                kind=EventKind.Shift,
                person=-1,
                description="Tom conflict with Susan",
                dateTime="2019-01-15",
                relationship=RelationshipKind.Conflict,
                relationshipTargets=[-2],
            ),
            Event(
                id=-41,
                kind=EventKind.Shift,
                person=-3,
                description="Alice distancing from Bob",
                dateTime="2021-05-01",
                relationship=RelationshipKind.Distance,
                relationshipTargets=[-4],
            ),
            Event(
                id=-42,
                kind=EventKind.Shift,
                person=-4,
                description="Bob cutoff from family",
                dateTime="2022-01-01",
                relationship=RelationshipKind.Cutoff,
                relationshipTargets=[-1, -2],
            ),
            Event(
                id=-43,
                kind=EventKind.Shift,
                person=-2,
                description="Susan projecting onto Alice",
                dateTime="2017-03-01",
                relationship=RelationshipKind.Projection,
                relationshipTargets=[-3],
            ),
            Event(
                id=-44,
                kind=EventKind.Shift,
                person=-3,
                description="Alice inside triangle",
                dateTime="2019-06-01",
                relationship=RelationshipKind.Inside,
                relationshipTargets=[-1],
                relationshipTriangles=[-2],
            ),
            Event(
                id=-45,
                kind=EventKind.Shift,
                person=-4,
                description="Bob outside triangle",
                dateTime="2019-07-01",
                relationship=RelationshipKind.Outside,
                relationshipTargets=[-1],
                relationshipTriangles=[-2, -3],
            ),
            Event(
                id=-50,
                kind=EventKind.Shift,
                person=-1,
                description="Tom complex stress response",
                dateTime="2023-01-01",
                symptom=VariableShift.Up,
                anxiety=VariableShift.Up,
                functioning=VariableShift.Down,
                relationship=RelationshipKind.Overfunctioning,
                relationshipTargets=[-2],
            ),
        ]

        pdp = PDP(
            people=pdp_people,
            events=pdp_events,
            pair_bonds=pdp_pair_bonds,
        )

        diagram_data = DiagramData(
            people=existing_people,
            events=existing_events,
            pair_bonds=existing_pair_bonds,
            pdp=pdp,
            lastItemId=10,
        )

        diagram.data = pickle.dumps(asdict(diagram_data))
        diagram.version += 1
        db.session.commit()

        print(f"Reset diagram {diagram_id}")
        print(f"Diagram version: {diagram.version}")
        print()
        print("=== Existing Diagram Data (positive IDs) ===")
        print(f"  People: {[p['name'] for p in diagram_data.people]}")
        print(f"  PairBonds: {len(diagram_data.pair_bonds)}")
        print()
        print("=== PDP Pending Items (negative IDs) ===")
        print(f"  People ({len(pdp.people)}):")
        for p in pdp.people:
            parents_str = f" [parents={p.parents}]" if p.parents else ""
            print(f"    {p.id}: {p.name}{parents_str}")
        print(f"  PairBonds ({len(pdp.pair_bonds)}):")
        for pb in pdp.pair_bonds:
            print(f"    {pb.id}: person_a={pb.person_a}, person_b={pb.person_b}")
        print(f"  Events ({len(pdp.events)}):")
        for event in pdp.events:
            extras = []
            if event.symptom:
                extras.append(f"symptom={event.symptom.value}")
            if event.anxiety:
                extras.append(f"anxiety={event.anxiety.value}")
            if event.functioning:
                extras.append(f"functioning={event.functioning.value}")
            if event.relationship:
                extras.append(f"rel={event.relationship.value}")
            if event.relationshipTargets:
                extras.append(f"targets={event.relationshipTargets}")
            if event.relationshipTriangles:
                extras.append(f"triangles={event.relationshipTriangles}")
            extras_str = f" [{', '.join(extras)}]" if extras else ""
            print(
                f"    {event.id}: {event.kind.value} - {event.description}{extras_str}"
            )
        print()
        print("=== Test Scenarios ===")
        print("  Cascade: Reject Tom (-1) -> cascades to his events and children")
        print("  Cascade: Reject pair bond (-10) -> cascades to Alice/Bob/Charlie")
        print("  EventKinds: Birth (3), Adopted (1), Bonded, Married, Separated,")
        print("              Divorced, Moved, Death, Shift")
        print("  SARF: symptom, anxiety, functioning (all VariableShift values)")
        print("  Relationships: Conflict, Distance, Cutoff, Projection,")
        print("                 Inside/Outside triangles, Overfunctioning")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <diagram_id>")
        sys.exit(1)

    diagram_id = int(sys.argv[1])
    reset_diagram(diagram_id)
