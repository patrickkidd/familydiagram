"""
Inspect the MVP_Merge_Fix diagram and print its current state.

Run after each journey to verify the pass criterion:

    uv run --env-file ../.env python familydiagram/doc/plans/2026-05-01--mvp-merge-fix/fixtures/verify.py

Prints:
  - DB row id, version, blob size
  - All persons (id + name + cutoff)
  - All events (id + kind + person/child link)
  - lastItemId

Compare what's printed against the journey's pass criterion.
"""
import base64
import pickle
import subprocess

import PyQt5.sip  # noqa: F401  side-effect: registers QtCore unpickle types

DIAGRAM_NAME = "MVP_Merge_Fix"
USER_EMAIL = "patrick@alaskafamilysystems.com"


def psql(sql: str) -> str:
    return subprocess.check_output(
        [
            "docker", "exec", "fd-postgres",
            "psql", "-U", "familydiagram", "-d", "familydiagram",
            "-tAc", sql,
        ]
    ).decode().strip()


def main() -> None:
    user_id = psql(f"SELECT id FROM users WHERE username='{USER_EMAIL}'")
    row_id = psql(
        f"SELECT id FROM diagrams WHERE name='{DIAGRAM_NAME}' AND user_id={user_id}"
    )
    if not row_id:
        print(f"diagram '{DIAGRAM_NAME}' not found — run reset_baseline.py first")
        return

    blob_b64 = psql(f"SELECT encode(data, 'base64') FROM diagrams WHERE id={row_id}")
    version = psql(f"SELECT version FROM diagrams WHERE id={row_id}")
    bytes_size = psql(f"SELECT octet_length(data) FROM diagrams WHERE id={row_id}")

    data = pickle.loads(base64.b64decode(blob_b64))

    print(f"diagram '{DIAGRAM_NAME}' id={row_id} version={version} bytes={bytes_size}")
    print(f"lastItemId: {data.get('lastItemId')}")
    print()
    print("People:")
    for p in data.get("people", []):
        print(
            f"  id={p.get('id')} name={p.get('name')!r} "
            f"gender={p.get('gender')!r} cutoff={p.get('cutoff')}"
        )
    print()
    print("Events:")
    for e in data.get("events", []):
        person_link = (
            f"child={e.get('child')}"
            if e.get("child")
            else f"person={e.get('person')}"
        )
        print(f"  id={e.get('id')} kind={e.get('kind')!r} {person_link}")
    print()
    pdp = data.get("pdp") or {}
    print("PDP (pending, not yet committed):")
    for p in pdp.get("people", []):
        print(f"  pdp.person id={p.get('id')} name={p.get('name')!r}")
    for e in pdp.get("events", []):
        print(f"  pdp.event id={e.get('id')} kind={e.get('kind')!r}")


if __name__ == "__main__":
    main()
