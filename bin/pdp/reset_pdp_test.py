#!/usr/bin/env python3
"""Reset a diagram and load comprehensive PDP test data.

Creates a multi-generational family diagram with:
- Existing committed data (positive IDs) including people to be deleted
- PDP pending items (negative IDs) with family relationships
- Delete entries for removing existing diagram items
"""

import os
import sys
import pickle

# bin/pdp -> bin -> familydiagram -> theapp
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
from btcopilot.personal.models import Discussion
from btcopilot.schema import (
    DiagramData,
    PDP,
    Person,
    Event,
    EventKind,
    PairBond,
    asdict,
)


def reset_diagram(diagram_id: int):
    app = create_app()

    with app.app_context():
        diagram = db.session.get(Diagram, diagram_id)
        if not diagram:
            print(f"Diagram {diagram_id} not found")
            sys.exit(1)

        # Delete all discussions and their statements/speakers for this diagram
        from btcopilot.personal.models import Statement, Speaker

        discussions = Discussion.query.filter_by(diagram_id=diagram_id).all()
        for d in discussions:
            Statement.query.filter_by(discussion_id=d.id).delete()
            Speaker.query.filter_by(discussion_id=d.id).delete()
            db.session.delete(d)
        print(f"Deleted {len(discussions)} discussions")

        # --- Existing committed diagram data (positive IDs) ---
        # Grandparents generation - some will be marked for deletion
        grandpa_joe = asdict(Person(id=1, name="Grandpa Joe"))
        grandma_mary = asdict(Person(id=2, name="Grandma Mary"))
        grandparents_bond = asdict(PairBond(id=3, person_a=1, person_b=2))

        # Uncle to be deleted
        uncle_frank = asdict(Person(id=4, name="Uncle Frank", parents=3))
        uncle_birth = asdict(
            Event(
                id=5,
                kind=EventKind.Birth,
                person=1,
                spouse=2,
                child=4,
                description="Frank born",
                dateTime="1955-02-10",
            )
        )

        # Event to be deleted (outdated info)
        outdated_event = asdict(
            Event(
                id=6,
                kind=EventKind.Shift,
                person=1,
                description="Outdated event to delete",
                dateTime="1990-01-01",
            )
        )

        existing_people = [grandpa_joe, grandma_mary, uncle_frank]
        existing_events = [uncle_birth, outdated_event]
        existing_pair_bonds = [grandparents_bond]

        # --- PDP pending items (negative IDs) ---
        # Parents generation (children of grandparents)
        pdp = PDP(
            people=[
                # Dad is child of grandparents
                Person(id=-1, name="Dad (Tom)", parents=3),
                # Mom (married into family)
                Person(id=-2, name="Mom (Susan)"),
                # Children of Tom & Susan
                Person(id=-3, name="Alice", parents=-10),
                Person(id=-4, name="Bob", parents=-10),
                # Alice's spouse
                Person(id=-5, name="Dave"),
                # Alice & Dave's child (grandchild)
                Person(id=-6, name="Emma", parents=-11),
            ],
            events=[
                # Dad's birth
                Event(
                    id=-20,
                    kind=EventKind.Birth,
                    person=1,
                    spouse=2,
                    child=-1,
                    description="Tom born to Joe & Mary",
                    dateTime="1960-05-20",
                ),
                # Parents' marriage
                Event(
                    id=-21,
                    kind=EventKind.Married,
                    person=-1,
                    spouse=-2,
                    description="Tom & Susan wedding",
                    dateTime="1985-06-15",
                ),
                # Alice's birth
                Event(
                    id=-22,
                    kind=EventKind.Birth,
                    person=-1,
                    spouse=-2,
                    child=-3,
                    description="Alice born",
                    dateTime="1988-03-12",
                ),
                # Bob's birth
                Event(
                    id=-23,
                    kind=EventKind.Birth,
                    person=-1,
                    spouse=-2,
                    child=-4,
                    description="Bob born",
                    dateTime="1991-09-05",
                ),
                # Alice & Dave marriage
                Event(
                    id=-24,
                    kind=EventKind.Married,
                    person=-3,
                    spouse=-5,
                    description="Alice & Dave wedding",
                    dateTime="2012-08-18",
                ),
                # Emma's birth (grandchild)
                Event(
                    id=-25,
                    kind=EventKind.Birth,
                    person=-3,
                    spouse=-5,
                    child=-6,
                    description="Emma born",
                    dateTime="2015-11-30",
                ),
                # Life events
                Event(
                    id=-26,
                    kind=EventKind.Shift,
                    person=-1,
                    description="Tom job loss",
                    dateTime="2008-09-15",
                ),
                Event(
                    id=-27,
                    kind=EventKind.Shift,
                    person=-3,
                    description="Alice promotion",
                    dateTime="2020-03-01",
                ),
            ],
            pair_bonds=[
                # Tom & Susan (parents)
                PairBond(id=-10, person_a=-1, person_b=-2),
                # Alice & Dave
                PairBond(id=-11, person_a=-3, person_b=-5),
            ],
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
        print(f"  People ({len(diagram_data.people)}):")
        for p in diagram_data.people:
            parents_str = f", parents={p.get('parents')}" if p.get("parents") else ""
            print(f"    id={p['id']}, name={p['name']}{parents_str}")
        print(f"  Events ({len(diagram_data.events)}):")
        for e in diagram_data.events:
            print(
                f"    id={e['id']}, kind={e['kind']}, date={e.get('dateTime')}, desc={e.get('description')}"
            )
        print(f"  PairBonds ({len(diagram_data.pair_bonds)}):")
        for pb in diagram_data.pair_bonds:
            print(
                f"    id={pb['id']}, person_a={pb['person_a']}, person_b={pb['person_b']}"
            )
        print()
        print("=== PDP Pending Items (negative IDs) ===")
        print(f"  People ({len(pdp.people)}):")
        for p in pdp.people:
            parents_str = f", parents={p.parents}" if p.parents else ""
            print(f"    id={p.id}, name={p.name}{parents_str}")
        print(f"  Events ({len(pdp.events)}):")
        for e in pdp.events:
            print(
                f"    id={e.id}, kind={e.kind.value}, date={e.dateTime}, desc={e.description}"
            )
        print(f"  PairBonds ({len(pdp.pair_bonds)}):")
        for pb in pdp.pair_bonds:
            print(f"    id={pb.id}, person_a={pb.person_a}, person_b={pb.person_b}")
        print()
        print("=== Test Scenarios ===")
        print(
            "  - Uncle Frank (id=4): Existing person that can be referenced by PDP items"
        )
        print("  - Outdated event (id=6): Existing event demonstrating committed data")
        print("  - PDP items can be rejected via DiagramData.reject_pdp_item()")
        print(
            "  - Multi-generational family: Grandparents -> Parents -> Children -> Grandchild"
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <diagram_id>")
        sys.exit(1)

    diagram_id = int(sys.argv[1])
    reset_diagram(diagram_id)
