# MVP Merge Fix — Implementation Report (Phases 1-3)

**Date:** 2026-05-01
**Status:** Implementation complete; ready for harness validation.

---

## What changed

**Two correctness fixes shipped together as one PR:**

1. **Snapshot-diff merge** (`apply_local_changes`) replaces "union by id, local wins". Each app captures the server's blob at diagram open as `_openSnapshot`. On save, the merge takes the server's copy of any item the user didn't actually edit (preserving concurrent edits) and the local copy of any item the user did edit.

2. **Server-side id-block allocation** prevents `lastItemId` collisions. Pro's Scene gets a `ServerBlockAllocator` injected on server-diagram open; it pulls ids from a server-reserved range (default block size 100). Local `.fd` files unchanged. Personal unchanged.

**Plus latent fixes:**

3. PUT `/v1/diagrams/{id}` 200 response now includes the canonical post-write blob so the client's snapshot reflects what the server actually stored.
4. `_create_inferred_*` idempotency verified (no code change needed; tests added as regression guard).

---

## Test results (unit + integration)

| Suite | Tests | Result |
|-------|-------|--------|
| btcopilot full suite | 137 | PASS |
| familydiagram (id_allocator + serverfilemanagermodel) | 27 | PASS |
| **New tests added** | **31** across 5 files | **PASS** |

End-to-end Python integration tests in `test_mvp_merge_integration.py` mirror the JOURNEYS scenarios at the HTTP-stack level (route handler + Diagram model + apply_local_changes + reserve_ids endpoint).

---

## Files

**Source:**
- `btcopilot/btcopilot/schema.py` — added `apply_local_changes`, deprecated `merge_scene_collection`
- `btcopilot/btcopilot/pro/models/diagram.py` — added `reserve_id_block`
- `btcopilot/btcopilot/pro/routes.py` — added `POST /v1/diagrams/{id}/reserve_ids`; PUT 200 returns canonical blob
- `familydiagram/pkdiagram/serverblockallocator.py` — new
- `familydiagram/pkdiagram/scene/scene.py` — added `setIdAllocator`; `nextId` delegates
- `familydiagram/pkdiagram/server_types.py` — `Diagram.save` 200 path uses server's canonical blob
- `familydiagram/pkdiagram/models/serverfilemanagermodel.py` — Pro `applyChange` uses `apply_local_changes` with `_openSnapshot`
- `familydiagram/pkdiagram/personal/personalappcontroller.py` — Personal `applyChange` same
- `familydiagram/pkdiagram/mainwindow/mainwindow.py` — binds allocator on server-diagram open

**Plan & journeys:**
- `familydiagram/doc/plans/2026-05-01--mvp-merge-fix/README.md`
- `familydiagram/doc/plans/2026-05-01--mvp-merge-fix/JOURNEYS.md` (machine-readable, deprecated by JOURNEYS_HUMAN.md)
- `familydiagram/doc/plans/2026-05-01--mvp-merge-fix/JOURNEYS_HUMAN.md` (human-readable, this is the one Patrick runs)
- `familydiagram/doc/plans/2026-05-01--mvp-merge-fix/logs/`

**Doc relocation:**
- `theapp/doc/TEST_JOURNEYS.md` → `familydiagram/doc/TEST_JOURNEYS.md`
- `theapp/CLAUDE.md` reverted; equivalent content added to `familydiagram/CLAUDE.md`

**New tests:**
- `btcopilot/btcopilot/tests/schema/test_apply_local_changes.py` (12)
- `btcopilot/btcopilot/tests/schema/test_inferred_idempotent.py` (2)
- `btcopilot/btcopilot/tests/pro/test_reserve_ids.py` (10)
- `btcopilot/btcopilot/tests/pro/test_mvp_merge_integration.py` (4)
- `familydiagram/pkdiagram/tests/scene/test_id_allocator.py` (5)

---

## Operational consequences

| Concern | After this PR |
|---------|---------------|
| Pro left open while Personal edits, Pro then saves → loses Personal's edits | **FIXED** at item level. |
| Personal open while Pro edits, Personal auto-saves → loses Pro's edits | **FIXED** at item level. |
| Either side's deletes resurrected by the other's stale snapshot | **FIXED.** |
| Both sides allocate same `lastItemId` → collision | **FIXED** for Pro. |
| Same field of same item edited on both sides | Item-level last-write-wins. **Documented as accepted MVP behavior** (J-6); deferred to v3. |
| Server-side post-processing reverted by client's stale snapshot | **FIXED.** |
| Local `.fd` open in Pro | Unchanged. No allocator binding, no server traffic for ids. |

---

## Risks tracked

- **`apply_local_changes` byte comparison cost.** Pickle-dumps every item per save. Cheap for typical diagrams (<200 items). Investigation underway: if Qt types support reliable Python `==`, dict-equality is faster and simpler.
- **Allocator on first save of a brand-new diagram.** The `POST /diagrams` create path is NOT yet wired with an allocator binding. First few items on a brand-new server diagram get local-allocated ids. Either fix in this PR or defer to a follow-up.
- **In-flight UI cleanup** (conflict-dialog removal) was committed by Patrick before this work. The dirty-tracking merge is now load-bearing because there's no fallback dialog.

---

## Pending

1. Patrick reviews plan + human-readable journeys.
2. Patrick builds Pro: `cd familydiagram && uv run --env-file ../.env make`.
3. Patrick runs human-readable journeys on real hardware.
4. Phase 4 (autonomous harness) — see Phase 4 log.
