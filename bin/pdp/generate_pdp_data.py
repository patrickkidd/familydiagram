#!/usr/bin/env python3
"""Generate PDP test data for manual testing of accept/reject functionality."""

import sys
import json
from pathlib import Path

# bin/pdp -> bin -> familydiagram -> theapp
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "btcopilot"))

from btcopilot.schema import (
    DiagramData,
    PDP,
    Person,
    Event,
    EventKind,
    PairBond,
    asdict,
)


def scenario_simple():
    """Single person with birth event"""
    return PDP(
        people=[Person(id=-1, name="Alice", last_name="Smith")],
        events=[Event(id=-2, kind=EventKind.Birth, person=-1, dateTime="1990-05-15")],
    )


def scenario_couple():
    """Married couple with pair bond"""
    return PDP(
        people=[
            Person(id=-1, name="Bob", last_name="Jones"),
            Person(id=-2, name="Carol", last_name="Jones"),
        ],
        events=[
            Event(id=-3, kind=EventKind.Birth, person=-1, dateTime="1985-03-20"),
            Event(id=-4, kind=EventKind.Birth, person=-2, dateTime="1987-08-12"),
            Event(
                id=-5,
                kind=EventKind.Married,
                person=-1,
                spouse=-2,
                dateTime="2010-06-15",
            ),
        ],
        pair_bonds=[PairBond(id=-6, person_a=-1, person_b=-2)],
    )


def scenario_family():
    """Parents with children - demonstrates transitive closure"""
    return PDP(
        people=[
            Person(id=-1, name="David", last_name="Brown"),
            Person(id=-2, name="Emma", last_name="Brown"),
            Person(id=-3, name="Frank", last_name="Brown", parents=-7),
            Person(id=-4, name="Grace", last_name="Brown", parents=-7),
        ],
        events=[
            Event(id=-5, kind=EventKind.Birth, person=-1, dateTime="1980-01-10"),
            Event(id=-6, kind=EventKind.Birth, person=-2, dateTime="1982-04-22"),
            Event(
                id=-8,
                kind=EventKind.Married,
                person=-1,
                spouse=-2,
                dateTime="2005-07-30",
            ),
            Event(id=-9, kind=EventKind.Birth, person=-3, dateTime="2010-09-12"),
            Event(id=-10, kind=EventKind.Birth, person=-4, dateTime="2012-11-05"),
        ],
        pair_bonds=[PairBond(id=-7, person_a=-1, person_b=-2)],
    )


def scenario_complex():
    """Multiple families with various relationships"""
    return PDP(
        people=[
            Person(id=-1, name="Henry", last_name="White"),
            Person(id=-2, name="Iris", last_name="White"),
            Person(id=-3, name="Jack", last_name="White", parents=-10),
            Person(id=-4, name="Kate", last_name="Green"),
            Person(id=-5, name="Liam", last_name="White", parents=-11),
        ],
        events=[
            Event(id=-6, kind=EventKind.Birth, person=-1, dateTime="1975-02-14"),
            Event(id=-7, kind=EventKind.Birth, person=-2, dateTime="1977-06-18"),
            Event(
                id=-8,
                kind=EventKind.Married,
                person=-1,
                spouse=-2,
                dateTime="2000-05-20",
            ),
            Event(id=-9, kind=EventKind.Birth, person=-3, dateTime="2005-03-15"),
            Event(id=-12, kind=EventKind.Birth, person=-4, dateTime="1978-09-25"),
            Event(
                id=-13,
                kind=EventKind.Married,
                person=-3,
                spouse=-4,
                dateTime="2028-08-10",
            ),
            Event(id=-14, kind=EventKind.Birth, person=-5, dateTime="2030-12-01"),
        ],
        pair_bonds=[
            PairBond(id=-10, person_a=-1, person_b=-2),
            PairBond(id=-11, person_a=-3, person_b=-4),
        ],
    )


def scenario_cascade_test():
    """Data designed to test cascade deletion - rejecting person should remove events"""
    return PDP(
        people=[
            Person(id=-1, name="Mike", last_name="Test"),
            Person(id=-2, name="Nancy", last_name="Test"),
        ],
        events=[
            Event(id=-3, kind=EventKind.Birth, person=-1, dateTime="1990-01-01"),
            Event(id=-4, kind=EventKind.Shift, person=-1),
            Event(id=-5, kind=EventKind.Death, person=-1, dateTime="2050-12-31"),
            Event(id=-6, kind=EventKind.Birth, person=-2, dateTime="1992-02-02"),
        ],
        pair_bonds=[],
    )


SCENARIOS = {
    "simple": scenario_simple,
    "couple": scenario_couple,
    "family": scenario_family,
    "complex": scenario_complex,
    "cascade": scenario_cascade_test,
}


def print_scenario_info(name, pdp):
    """Print human-readable scenario information"""
    print(f"\n{'='*60}")
    print(f"Scenario: {name}")
    print("=" * 60)
    print(f"People: {len(pdp.people)}")
    for p in pdp.people:
        parents_info = f" (parents: {p.parents})" if p.parents else ""
        print(f"  {p.id}: {p.name} {p.last_name or ''}{parents_info}")

    print(f"\nEvents: {len(pdp.events)}")
    for e in pdp.events:
        person_info = f"person={e.person}" if e.person else ""
        spouse_info = f", spouse={e.spouse}" if e.spouse else ""
        date_info = f", date={e.dateTime}" if e.dateTime else ""
        print(f"  {e.id}: {e.kind.value} ({person_info}{spouse_info}{date_info})")

    print(f"\nPair Bonds: {len(pdp.pair_bonds)}")
    for pb in pdp.pair_bonds:
        print(f"  {pb.id}: {pb.person_a} <-> {pb.person_b}")


def generate_diagram_data(scenario_name):
    """Generate complete DiagramData with PDP scenario"""
    if scenario_name not in SCENARIOS:
        print(f"Unknown scenario: {scenario_name}")
        print(f"Available scenarios: {', '.join(SCENARIOS.keys())}")
        sys.exit(1)

    pdp = SCENARIOS[scenario_name]()

    diagram_data = DiagramData(
        people=[],
        events=[],
        pair_bonds=[],
        pdp=pdp,
        lastItemId=100,
    )

    return diagram_data


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate PDP test data for manual testing"
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        choices=list(SCENARIOS.keys()) + ["all"],
        default="all",
        help="Scenario to generate (default: all)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of human-readable format",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Write JSON to file instead of stdout",
    )

    args = parser.parse_args()

    if args.scenario == "all":
        if args.json:
            print("Cannot output JSON for all scenarios. Choose one scenario.")
            sys.exit(1)

        for name in SCENARIOS.keys():
            pdp = SCENARIOS[name]()
            print_scenario_info(name, pdp)

        print(f"\n{'='*60}")
        print("Usage examples:")
        print("=" * 60)
        print("Generate JSON for a scenario:")
        print(f"  python {sys.argv[0]} family --json")
        print("\nSave to file:")
        print(f"  python {sys.argv[0]} family --json -o test_data.json")
        print("\nLoad in Python REPL:")
        print("  from btcopilot.schema import from_dict, DiagramData")
        print("  import json")
        print("  with open('test_data.json') as f:")
        print("      data = from_dict(DiagramData, json.load(f))")
    else:
        diagram_data = generate_diagram_data(args.scenario)

        if args.json:
            output = json.dumps(asdict(diagram_data), indent=2)

            if args.output:
                Path(args.output).write_text(output)
                print(f"Wrote {args.scenario} scenario to {args.output}")
            else:
                print(output)
        else:
            print_scenario_info(args.scenario, diagram_data.pdp)


if __name__ == "__main__":
    main()
