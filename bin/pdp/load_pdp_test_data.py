#!/usr/bin/env python3
"""Load PDP test data into a diagram for manual testing in the app."""

import sys
from pathlib import Path

# bin/pdp -> bin -> familydiagram -> theapp
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "btcopilot"))
sys.path.insert(0, str(Path(__file__).parent))

from generate_pdp_data import SCENARIOS, generate_diagram_data
from btcopilot.schema import asdict
import pickle


def load_into_diagram(scenario_name, username="patrickkidd+unittest@gmail.com"):
    """Load PDP scenario into user's free diagram"""
    import os
    from btcopilot.app import create_app
    from btcopilot.extensions import db
    from btcopilot.pro.models import User, Diagram

    os.environ.setdefault("FLASK_CONFIG", "development")

    app = create_app()

    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"User not found: {username}")
            print("Create user first by running:")
            print(
                "  uv run pytest btcopilot/btcopilot/tests/training/routes/test_login.py -v"
            )
            sys.exit(1)

        diagram = Diagram.query.get(user.free_diagram_id)
        if not diagram:
            print(f"Free diagram not found for user {username}")
            sys.exit(1)

        diagram_data = generate_diagram_data(scenario_name)

        print(f"Loading scenario '{scenario_name}' into diagram {diagram.id}...")
        print(f"  People in PDP: {len(diagram_data.pdp.people)}")
        print(f"  Events in PDP: {len(diagram_data.pdp.events)}")
        print(f"  Pair Bonds in PDP: {len(diagram_data.pdp.pair_bonds)}")

        diagram.data = pickle.dumps(asdict(diagram_data))
        diagram.version += 1

        db.session.commit()

        print(f"\n✓ Successfully loaded scenario into diagram {diagram.id}")
        print(f"  User: {user.username}")
        print(f"  Diagram version: {diagram.version}")
        print("\nNow start the app to test:")
        print("  uv run familydiagram/main.py")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Load PDP test data into a diagram for manual testing"
    )
    parser.add_argument(
        "scenario",
        choices=list(SCENARIOS.keys()),
        help="Scenario to load into diagram",
    )
    parser.add_argument(
        "--user",
        "-u",
        default="patrickkidd+unittest@gmail.com",
        help="User username (default: patrickkidd+unittest@gmail.com)",
    )

    args = parser.parse_args()

    load_into_diagram(args.scenario, args.user)


if __name__ == "__main__":
    main()
