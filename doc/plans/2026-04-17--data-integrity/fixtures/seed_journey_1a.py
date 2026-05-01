"""
Seed script for Journey-1A (Item 1: concurrent merge).

Resets diagram id=1976 (T04-04-kitchen-sink-both-apps) to a known baseline:
  - hideNames = False
  - no J1A_* people (removes prior-run leftovers)
  - DB version incremented so both apps see a clean slate

Run with: uv run python familydiagram/doc/plans/2026-04-17--data-integrity/fixtures/seed_journey_1a.py
Requires: PyQt5 on PYTHONPATH (standard familydiagram dev env), docker fd-postgres up.
"""
import base64
import pickle
import subprocess

import PyQt5.sip  # noqa: F401 — required to unpickle Qt objects

DIAGRAM_ID = 1976


def psql_read(sql: str) -> str:
    return subprocess.check_output(
        ["docker", "exec", "fd-postgres", "psql", "-U", "familydiagram", "-d", "familydiagram", "-tAc", sql]
    ).decode().strip()


def psql_write(sql: str) -> None:
    subprocess.run(
        ["docker", "exec", "-i", "fd-postgres", "psql", "-U", "familydiagram", "-d", "familydiagram"],
        input=sql.encode(),
        check=True,
    )


def main() -> None:
    raw = psql_read(f"SELECT encode(data,'base64') FROM diagrams WHERE id={DIAGRAM_ID}")
    data: dict = pickle.loads(base64.b64decode(raw))

    before = len(data.get("people", []))
    data["people"] = [p for p in data.get("people", []) if not str(p.get("name", "")).startswith("J1A")]
    data["hideNames"] = False
    after = len(data["people"])

    blob = pickle.dumps(data)
    hex_blob = blob.hex()

    psql_write(
        f"UPDATE diagrams SET data='\\x{hex_blob}'::bytea, version=version+1 WHERE id={DIAGRAM_ID};\n"
    )

    new_version = psql_read(f"SELECT version FROM diagrams WHERE id={DIAGRAM_ID}")
    events = len(data.get("events", []))
    print(f"Seeded: {before} → {after} people, {events} events, hideNames=False, DB version now {new_version}")


if __name__ == "__main__":
    main()