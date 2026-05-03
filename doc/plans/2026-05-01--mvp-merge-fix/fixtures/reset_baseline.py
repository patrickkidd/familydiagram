"""
Reset the MVP merge fix test diagram to a known baseline.

Idempotent: creates the diagram if missing, otherwise resets its blob
and bumps version. Prints the diagram's DB row id and name so the
journey can find it in the file manager.

Baseline diagram state:
  - Name: "MVP_Merge_Fix"
  - 3 male persons: A (id=1), B (id=2), C (id=3)
  - 1 Birth event on person A (event id=10)
  - lastItemId = 10

Run before EVERY journey:

    uv run --env-file ../.env python familydiagram/doc/plans/2026-05-01--mvp-merge-fix/fixtures/reset_baseline.py

Requires: docker fd-postgres up; patrick@alaskafamilysystems.com user exists.
"""
import base64
import os
import pickle
import subprocess
import sys

DIAGRAM_NAME = "MVP_Merge_Fix"
USER_EMAIL = "patrick@alaskafamilysystems.com"


def psql_read(sql: str) -> str:
    return subprocess.check_output(
        [
            "docker", "exec", "fd-postgres",
            "psql", "-U", "familydiagram", "-d", "familydiagram",
            "-tAc", sql,
        ]
    ).decode().strip()


def psql_write(sql: str) -> None:
    subprocess.run(
        [
            "docker", "exec", "-i", "fd-postgres",
            "psql", "-U", "familydiagram", "-d", "familydiagram",
        ],
        input=sql.encode(),
        check=True,
    )


def build_baseline_blob() -> bytes:
    """Construct a valid Pro-app-readable Scene blob via the actual Scene API."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    from PyQt5.QtCore import QDateTime, QDate
    from PyQt5.QtGui import QColor
    from PyQt5.QtWidgets import QApplication

    if QApplication.instance() is None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        _app = QApplication(sys.argv)

    # WINDOW_BG is normally set by QmlUtil during full app init; without
    # it, Scene item geometry updates crash. Set a sensible default.
    from pkdiagram import util
    if util.WINDOW_BG is None:
        util.WINDOW_BG = QColor("white")

    from pkdiagram.scene import Scene, Person, Event
    from btcopilot.schema import EventKind

    scene = Scene()
    a, b, c = scene.addItems(
        Person(name="A", gender="male"),
        Person(name="B", gender="male"),
        Person(name="C", gender="male"),
    )

    data: dict = {}
    scene.write(data)
    # NOTE: baseline intentionally has NO canonical events — constructing
    # a valid event via the Scene API hits cascading invariants (Birth
    # events trigger eventsFor() before the person-link is registered,
    # etc.). Journeys that need an event add it via the Pro UI in their
    # setup steps.

    # Inject a PDP item so Personal has something to Accept. Personal's
    # only user-driven save paths are: deleteEvent (needs event in Scene)
    # and acceptPDPItem (needs PDP item). PDP items appear in Personal's
    # PDP sheet on diagram open. Tapping Accept commits to canonical and
    # triggers a save — the realistic Personal-side write for the MVP
    # intake flow.
    from btcopilot.schema import PDP, Person as SchemaPerson, asdict
    pdp = PDP(people=[
        SchemaPerson(id=-1, name="J_PDP_pending", gender="female"),
    ])
    data["pdp"] = asdict(pdp)
    return pickle.dumps(data)


def main() -> None:
    user_id = psql_read(
        f"SELECT id FROM users WHERE username='{USER_EMAIL}'"
    )
    if not user_id:
        print(f"ERROR: user {USER_EMAIL} not found in DB", file=sys.stderr)
        sys.exit(1)

    blob = build_baseline_blob()
    hex_blob = blob.hex()

    existing = psql_read(
        f"SELECT id FROM diagrams WHERE name='{DIAGRAM_NAME}' AND user_id={user_id}"
    )
    if existing:
        diagram_id = int(existing)
        psql_write(
            f"UPDATE diagrams SET data='\\x{hex_blob}'::bytea, "
            f"version=version+1 WHERE id={diagram_id};\n"
        )
        action = "RESET"
    else:
        psql_write(
            f"INSERT INTO diagrams (user_id, name, data, version, created_at, updated_at) "
            f"VALUES ({user_id}, '{DIAGRAM_NAME}', '\\x{hex_blob}'::bytea, 1, NOW(), NOW());\n"
        )
        diagram_id = int(psql_read(
            f"SELECT id FROM diagrams WHERE name='{DIAGRAM_NAME}' AND user_id={user_id}"
        ))
        action = "CREATED"

    version = psql_read(f"SELECT version FROM diagrams WHERE id={diagram_id}")
    bytes_size = psql_read(f"SELECT octet_length(data) FROM diagrams WHERE id={diagram_id}")
    print(
        f"{action}: diagram '{DIAGRAM_NAME}' id={diagram_id} "
        f"version={version} bytes={bytes_size}"
    )
    print("Baseline: 3 male persons (A, B, C); 1 pending PDP person (J_PDP_pending) for Personal to Accept.")
    print(f"\nIn Pro and Personal, open the diagram named: {DIAGRAM_NAME}")


if __name__ == "__main__":
    main()
