"""
Seed for Journey-6 (Item 6: field coverage).

Resets T04-03 (id=1975) to known baseline:
  - hideNames=True, hideToolBars=True, hideVariablesOnDiagram=True (all flags that Item 6 tests)
  - 2 people, 0 events (original state)

Run: python familydiagram/doc/plans/2026-04-17--data-integrity/fixtures/seed_journey_6.py
"""
import base64
import pickle
import subprocess

import PyQt5.sip  # noqa: F401

DIAGRAM_ID = 1975


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

    data["hideNames"] = True
    data["hideToolBars"] = True
    data["hideVariablesOnDiagram"] = True

    blob = pickle.dumps(data)
    psql_write(
        f"UPDATE diagrams SET data='\\x{blob.hex()}'::bytea, version=version+1 WHERE id={DIAGRAM_ID};\n"
    )

    new_version = psql_read(f"SELECT version FROM diagrams WHERE id={DIAGRAM_ID}")
    print(f"Seeded T04-03: hideNames=True, hideToolBars=True, hideVariablesOnDiagram=True, DB version now {new_version}")


if __name__ == "__main__":
    main()
