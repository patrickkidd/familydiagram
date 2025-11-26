#!/usr/bin/env python3
"""Reset a diagram and load comprehensive PDP test data."""

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

        # Create fresh diagram data with comprehensive PDP
        pdp = PDP(
            people=[
                Person(id=-1, name="Alice"),
                Person(id=-2, name="Bob"),
                Person(id=-3, name="Charlie", parents=-10),
                Person(id=-4, name="Diana"),
            ],
            events=[
                Event(
                    id=-5,
                    kind=EventKind.Birth,
                    person=-1,
                    description="Alice born",
                    dateTime="1980-03-15",
                ),
                Event(
                    id=-6,
                    kind=EventKind.Birth,
                    person=-2,
                    description="Bob born",
                    dateTime="1978-07-22",
                ),
                Event(
                    id=-7,
                    kind=EventKind.Married,
                    person=-1,
                    spouse=-2,
                    description="Wedding",
                    dateTime="2005-06-10",
                ),
                Event(
                    id=-8,
                    kind=EventKind.Birth,
                    person=-3,
                    description="Charlie born",
                    dateTime="2008-11-03",
                ),
                Event(
                    id=-9,
                    kind=EventKind.Shift,
                    person=-1,
                    description="Alice stress event",
                    dateTime="2020-04-01",
                ),
            ],
            pair_bonds=[
                PairBond(id=-10, person_a=-1, person_b=-2),
            ],
        )

        diagram_data = DiagramData(
            people=[],
            events=[],
            pair_bonds=[],
            pdp=pdp,
            lastItemId=0,
        )

        diagram.data = pickle.dumps(asdict(diagram_data))
        diagram.version += 1
        db.session.commit()

        print(f"Reset diagram {diagram_id}")
        print(f"Diagram version: {diagram.version}")
        print(f"  People: {len(diagram_data.people)}")
        print(f"  Events: {len(diagram_data.events)}")
        print(f"  PairBonds: {len(diagram_data.pair_bonds)}")
        print(f"  PDP People: {len(pdp.people)}")
        for p in pdp.people:
            print(f"    id={p.id}, name={p.name}, parents={p.parents}")
        print(f"  PDP Events: {len(pdp.events)}")
        for e in pdp.events:
            print(
                f"    id={e.id}, kind={e.kind.value}, date={e.dateTime}, desc={e.description}"
            )
        print(f"  PDP PairBonds: {len(pdp.pair_bonds)}")
        for pb in pdp.pair_bonds:
            print(f"    id={pb.id}, person_a={pb.person_a}, person_b={pb.person_b}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <diagram_id>")
        sys.exit(1)

    diagram_id = int(sys.argv[1])
    reset_diagram(diagram_id)
