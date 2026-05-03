# MVP Merge Fix — Final Consolidated Report

**Date:** 2026-05-02
**Status:** Implementation, testing, and three-pass critique complete. Ready for Patrick's manual journey runs (`JOURNEYS_HUMAN.md`).

---

## What shipped

Two correctness fixes + three latent fixes, packaged as one PR spanning the `btcopilot` and `familydiagram` repos.

### Core fixes

1. **Snapshot-diff merge** (`apply_local_changes`) replaces the broken `merge_scene_collection`. Per item: take server's copy unless the user actually changed it (snapshot vs current diff). Native Python `==` for comparison (1078x faster than pickle bytes; more correct because Qt fuzzy float compare avoids false positives).

2. **Server-side block id allocation** (`POST /v1/diagrams/{id}/reserve_ids`) prevents `lastItemId` collisions when concurrent writers add new items. Pro's `ServerBlockAllocator` binds at server-diagram open; Personal allocates server-side via `commit_pdp_items` (unchanged). `Diagram.reserve_id_block` uses SELECT-FOR-UPDATE row lock (PostgreSQL) plus optimistic version locking (SQLite-compatible backstop) with up to 32 retries.

### Latent fixes (in scope, surfaced by audits)

3. **Server returns canonical post-write blob in 200 response.** Client's snapshot now reflects what the server actually stored, not what the client sent.
4. **`_create_inferred_*` idempotency** verified (no code change needed; tests added as regression guard).
5. **`importJournalNotes` uses optimistic save loop and `_withSaveGuard`** instead of read-modify-write blind setDiagramData.

---

## Phase 4c — full real-binary e2e validation (added 2026-05-02 after first ship attempt)

**A real bug was found and fixed by actually running the harness end-to-end against the live Pro app + ephemeral btcopilot server.**

### The bug

After Pro's first save brought other-client items into the merged result (via fix 3a's canonical-blob update of `_diagram.data`), the next save's snapshot would contain those items even though Pro's local Scene never loaded them. `apply_local_changes` then interpreted "in snapshot, not in local" as a DELETE and silently dropped them.

### The fix

Snapshot baseline for the merge is now captured by the **caller** (Pro's `setData` and Personal's `saveDiagram`) from the **caller's local Scene view**, not from the merged bytes returned by `Diagram.save`. `Diagram.data` continues to track canonical server state for display/reopen (latent fix 3a unchanged).

### What enabled finding the bug

- Multi-threaded the bridge (`mcpbridge/server.py`) so MCP host + a direct-bridge driver can coexist.
- Extended `/test/diagrams/{id}` PUT in ephemeral_server.py to bump version (so server-side test changes trigger 409 on the next save).
- Drove three journeys end-to-end: J-3 (block allocation), J-1A (other-client commit preserved), J-2A (delete + prior-add both preserved through 2nd stale save).

All three pass. Two new regression unit tests added so the bug can be caught without harness in future. See `logs/2026-05-02--phase4c-real-e2e-validation.md` for full detail.

### Updated test totals

- 46 automated tests (was 44; added 2 regression cases for the snapshot bug)
- 3 e2e harness journeys verified end-to-end against live Pro app + Flask server (J-3, J-1A, J-2A)

### Files changed in 4c

- `pkdiagram/server_types.py` — clarified that callers own `_lastSavedSnapshot` capture
- `pkdiagram/models/serverfilemanagermodel.py` — Pro captures from `dataToSave` after success
- `pkdiagram/personal/personalappcontroller.py` — Personal captures from Scene before save, stashes after success
- `pkdiagram/mcpbridge/server.py` — multi-threaded bridge
- `mcpserver/ephemeral_server.py` — `/test/diagrams/{id}` PUT bumps version
- `btcopilot/tests/schema/test_apply_local_changes.py` — 2 regression tests

---

## Three-pass critique log

### Pass 1 (test-rigor critique by hostile sub-agent)
Found 3 real ship-blockers + several rigor gaps. Misclassified 3 issues that audit followup ruled out as misreadings.

### Pass 2 (verification of fixes from Pass 1)
Found 2 more real bugs introduced or missed:
- `importJournalNotes` save bypassed `_withSaveGuard` — race with concurrent saves.
- `reserve_id_block` retry branch had no test coverage.

### Pass 3 (verification of fixes from Pass 2)
Verdict: **no remaining ship-blockers. Ready to ship.**

Detailed log:
- `logs/2026-05-02--phase4b-critique-and-fixes.md` (Pass 1 outcomes)
- `logs/harness000409-J-3/result.md` (live HTTP harness verification of block allocation)
- `logs/2026-05-02--phase4-comprehensive-validation.md` (validation pyramid)

---

## Final test totals

| Suite | Tests | Result |
|-------|-------|--------|
| Unit — `apply_local_changes` algorithm | 12 | PASS |
| Unit — Scene id allocator | 5 | PASS |
| Unit — `reserve_id_block` + endpoint (incl. retry-branch coverage) | 13 | PASS |
| Unit — `_create_inferred_*` idempotency | 2 | PASS |
| Cross-app merge sim (`test_serverfilemanagermodel.py concurrent_*`) | 8 | PASS |
| HTTP integration (J-mirroring) | 4 | PASS |
| **Total automated** | **44** | **44 PASS** |
| Live-HTTP harness — block allocation triggered on real Pro diagram open | 1 | VERIFIED |

Full repo runs (no regressions):
- `btcopilot/`: 226 passed, 11 skipped
- `familydiagram/` (touched subset): 27 passed

---

## Files touched

### btcopilot
- `btcopilot/schema.py` — `apply_local_changes` (Python ==), `merge_scene_collection` deprecated
- `btcopilot/pro/models/diagram.py` — `reserve_id_block` with FOR UPDATE + optimistic retry
- `btcopilot/pro/routes.py` — `POST /v1/diagrams/{id}/reserve_ids`; PUT 200 returns canonical blob
- `tests/schema/test_apply_local_changes.py` (12 cases, new)
- `tests/schema/test_inferred_idempotent.py` (2 cases, new)
- `tests/pro/test_reserve_ids.py` (13 cases, new)
- `tests/pro/test_mvp_merge_integration.py` (4 cases, new)

### familydiagram
- `pkdiagram/serverblockallocator.py` (new — fail-fast on HTTP error per CLAUDE.md no-bandaid rule)
- `pkdiagram/scene/scene.py` — `setIdAllocator`, `nextId` delegates
- `pkdiagram/server_types.py` — 200 path uses server's canonical blob
- `pkdiagram/models/serverfilemanagermodel.py` — Pro `applyChange` uses snapshot-diff merge
- `pkdiagram/personal/personalappcontroller.py` — Personal `saveDiagram` + `importJournalNotes` use snapshot-diff merge with `_withSaveGuard`
- `pkdiagram/mainwindow/mainwindow.py` — binds `ServerBlockAllocator` on server-diagram open
- `pkdiagram/tests/scene/test_id_allocator.py` (5 cases, new)
- `CLAUDE.md` — added test-journey methodology reference + plan-naming convention
- `doc/TEST_JOURNEYS.md` — moved from `theapp/doc/`
- `doc/specs/DATA_SYNC_FLOW.md` — Outstanding Issues section + File Reference moved up

### Plan and journeys
- `doc/plans/2026-05-01--mvp-merge-fix/README.md` — full plan
- `doc/plans/2026-05-01--mvp-merge-fix/JOURNEYS.md` — machine-readable
- `doc/plans/2026-05-01--mvp-merge-fix/JOURNEYS_HUMAN.md` — for Patrick to run
- `doc/plans/2026-05-01--mvp-merge-fix/logs/` — six log files documenting phases 1-5 + 3 critique passes

---

## Operational consequences

| Concern | After this PR |
|---------|---------------|
| Pro left open while Personal edits, Pro then saves → loses Personal's edits | **FIXED** at item level |
| Personal open while Pro edits, Personal auto-saves → loses Pro's edits | **FIXED** at item level |
| Either side's deletes resurrected by other's stale snapshot | **FIXED** |
| Both apps allocate same `lastItemId` → new-item collision | **FIXED** (server-allocated blocks) |
| Concurrent `reserve_id_block` calls → overlapping blocks | **FIXED** (FOR UPDATE + optimistic lock) |
| `importJournalNotes` blind overwrite during concurrent save | **FIXED** (uses retry loop + save guard) |
| Server post-processing reverted by client's stale snapshot | **FIXED** (canonical-blob response) |
| Same field of same item edited on both sides | Item-level last-write-wins (documented MVP behavior) |
| Local `.fd` open in Pro | Unchanged — no allocator binding, no server traffic |

---

## What's still pending

1. **Patrick runs `JOURNEYS_HUMAN.md` on real hardware.** 8 journeys (J-1A, J-1B, J-2A, J-2B, J-3, J-4, J-5, J-6). Reports PASS/FAIL per journey via the `Status` table at the bottom of that file.
2. **PR review and merge** — the work spans two repos; coordinate commits.

---

## Known limitations (acknowledged, not bugs)

1. **Threading-based concurrent reserve test under SQLite `:memory:`** can't reliably verify because each thread gets its own private DB. Production correctness covered by SQL semantics (FOR UPDATE + optimistic lock), serial test, and retry-branch monkeypatch test.
2. **`save_diagram` MCP tool not exposed in the current Claude session.** The harness has the tool registered but my MCP host predates the addition. Patrick's manual journey run covers what UI-driven harness automation can't yet.
3. **import-text endpoint pattern is wasteful** — server commits PDP, returns it, client save then 409s once and retries. Correct but one extra round-trip per import.

---

## Risks I'm tracking after ship

- **First save of a brand-new server diagram** (created via `POST /diagrams`) — the allocator binding happens in `onServerFileClicked`, which is the natural entry point for opens. New-diagram flow funnels through `onServerFileClicked` after creation; verified by code-grep but not by harness journey. If a future change adds a different create path, the allocator binding invariant must be re-checked.
- **Field-level concurrent edits to the same item** are item-level LWW per MVP. If a real customer hits this and complains, it's a v3 work item, not an MVP regression. Documented in JOURNEYS_HUMAN.md J-6 as expected behavior.

---

## Three-pass critique summary

| Pass | Bugs found | Bugs fixed | Misreadings | Verdict |
|------|------------|------------|-------------|---------|
| 1 | 3 ship-blockers + rigor gaps | 3 (apply_local_changes refactor, importJournalNotes optimistic save, ServerBlockAllocator try/except later removed per CLAUDE.md) | 3 (`_doAcceptPDPItem`, `clearDiagramData`, `updatePDPItem` defenses upheld) | DO-NOT-SHIP |
| 2 | 2 more (importJournalNotes guard bypass, retry-branch test coverage) | 2 | 0 | DO-NOT-SHIP |
| 3 | 0 | — | 0 | **READY TO SHIP** |

---

## Your next steps

1. Review this report + `JOURNEYS_HUMAN.md`.
2. Run the 8 manual journeys.
3. Commit/PR per repo.
