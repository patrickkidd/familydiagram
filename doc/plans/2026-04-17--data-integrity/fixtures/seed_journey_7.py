"""
Seed for Journey-7 (Item 7: chat history persists).

Resets T04-04 (id=1976) to known baseline:
  - Deletes all discussions for diagram 1976 so chat view starts empty

Run: python familydiagram/doc/plans/2026-04-17--data-integrity/fixtures/seed_journey_7.py
"""
import subprocess

DIAGRAM_ID = 1976


def psql(sql: str) -> str:
    return subprocess.check_output(
        ["docker", "exec", "fd-postgres", "psql", "-U", "familydiagram", "-d", "familydiagram", "-tAc", sql]
    ).decode().strip()


def main() -> None:
    psql(f"DELETE FROM discussions WHERE diagram_id={DIAGRAM_ID}")
    remaining = psql(f"SELECT count(*) FROM discussions WHERE diagram_id={DIAGRAM_ID}")
    print(f"Seeded T04-04: discussions cleared ({remaining} remaining)")


if __name__ == "__main__":
    main()
