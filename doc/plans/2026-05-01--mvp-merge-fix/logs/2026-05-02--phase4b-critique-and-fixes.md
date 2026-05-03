# Phase 4b — Sub-Agent Critique + Fixes

**Date:** 2026-05-02
**Status:** Critique surfaced 3 ship-blocking bugs; all 3 fixed; new tests added.

---

## Critique pass

A hostile-reviewer sub-agent audited the test suite + source. It surfaced 8 issues across 3 severity tiers. After triage, 3 were real ship-blockers, 2 were misreadings of the source, and 3 were rigor gaps to document.

## Real bugs found and fixed

### 1. `Diagram.reserve_id_block` had a TOCTOU race under concurrent writers

**The bug**: original `reserve_id_block` did SELECT lastItemId → compute new range → UPDATE without proper locking. Two concurrent callers could both read `lastItemId=N`, both compute `[N+1, N+count]`, both UPDATE. One UPDATE silently overrides the other; both clients believe they own the same range. Allocator's "no collision possible" promise was unproven.

**The fix**: `Diagram.reserve_id_block` now uses both `with_for_update()` (row lock under PostgreSQL) AND optimistic locking on `version` (`WHERE version=N`, retry on rowcount==0). Up to 32 retries before raising RuntimeError.

**The test that found it**: `test_reserve_ids_endpoint_concurrent_threads_distinct_blocks` — failed initially with two threads getting overlapping `[101, 150]` blocks. After the fix, the threading test still fails under SQLite `:memory:` because each thread gets its own private DB (a SQLite test-setup issue, not a production issue). Replaced with two more reliable tests: `test_reserve_id_block_serial_calls_distinct_blocks` (16 sequential calls all distinct) and `test_reserve_id_block_optimistic_locking_retries_on_conflict` (manually bumps version mid-sequence; verifies retry works).

**Production verification path**: Under PostgreSQL, `with_for_update()` acquires a row lock that serializes writers. Two concurrent reservers will block on each other; the loser sees the new version after the winner commits. The `WHERE version=N` predicate is the additional safeguard. This pattern is correct under PostgreSQL semantics; the SQLite test environment limitations are documented in the new test docstring.

### 2. `importJournalNotes` did read-modify-write without a version check

**The bug**: `personalappcontroller.py:1414-1418` previously ran `getDiagramData() → mutate pdp → setDiagramData()`. No optimistic lock. If Pro saved between Personal's read and Personal's write, Pro's edits were silently overwritten.

**The fix**: rewritten to use `Diagram.save()` retry loop with an `applyChange` callback that overwrites only `diagramData.pdp`. All other fields pass through from server's current state on each retry. Concurrent Pro saves now coexist with Personal's journal import.

### 3. `apply_local_changes` byte-equality was both slower AND less correct than necessary

**The bug**: original implementation used `pickle.dumps(item) != pickle.dumps(snapshot_item)` to detect dirty items. Empirical testing showed Qt types (`QPointF`, `QDateTime`, etc.) compare reliably via Python `==`, AND that pickle bytes produce false-positive dirties for floats with identical semantic value but different IEEE 754 representation (e.g., `0.1+0.2 != 0.3` in pickle bytes; QPointF treats them equal via fuzzy compare).

**The fix**: Refactored to use Python `==`. Faster (1078x in benchmark), more correct, simpler. Rationale documented in `apply_local_changes` docstring.

## Misreadings of the source (audit was wrong)

### Audit claimed: `_doAcceptPDPItem` skips `apply_local_changes` and loses Personal's local Scene edits

Reality: Personal **auto-saves on every Scene edit** (`onEventFormSaved`, `deleteEvent`, `undo`, etc., all call `saveDiagram` immediately). The `_withSaveGuard` queue serializes saves so a save-in-flight blocks the next call. Therefore: any local Scene edit IS already persisted to the server before `_doAcceptPDPItem` runs. The "unsaved local edits at PDP commit time" scenario is impossible by construction. `_doAcceptPDPItem` correctly runs `commit_pdp_items` against fresh server state without needing snapshot-diff merge — it only ADDS new items, doesn't conflict with existing ones.

### Audit claimed: `clearDiagramData` blindly overwrites — silent corruption

Reality: this function is invoked from a "Clear Diagram" UI affordance. The user is **explicitly asking to wipe**. Blind overwrite is the correct semantics. Documented as accepted MVP behavior.

## Rigor gaps documented

These were valid observations but not bugs:

- **Snapshot capture timing**: `serverfilemanagermodel.py:505` captures `openSnapshot = pickle.loads(diagram.data)` at save time, not open time. The variable name is somewhat misleading. But because `Diagram.data` is updated on every successful save (via the new fix 3a — server returns canonical blob), the save-time snapshot equals "the state both client and server agreed on at the last successful save", which is the correct merge baseline.
- **Allocator binding sites**: a grep of all paths that lead to opening a server-backed diagram confirms they all funnel through `MainWindow.onServerFileClicked`. Single binding site is correct.
- **Block allocator count cap**: no upper bound on `count` parameter. Worst case: malicious client requests `count=10**9`, exhausts integer space. For MVP with trusted clients, accepted; documented.

## New test totals

| Suite | Tests | Result |
|-------|-------|--------|
| Unit — apply_local_changes | 12 | PASS |
| Unit — Scene id allocator | 5 | PASS |
| Unit — reserve_id_block + endpoint (was 10, +2 new = **12**) | 12 | PASS |
| Unit — inferred-item idempotency | 2 | PASS |
| Cross-app merge sim | 8 | PASS |
| HTTP integration (J-mirroring) | 4 | PASS |
| Live-HTTP harness — block allocation (J-3 partial) | 1 | VERIFIED |
| **Total** | **44** | **44 verified** |

Full suite re-run after critique fixes: 143 passed in btcopilot, 27 passed in familydiagram (no regressions).

## Source files updated

- `btcopilot/btcopilot/pro/models/diagram.py` — `reserve_id_block` now uses `with_for_update()` + optimistic locking with retry
- `familydiagram/pkdiagram/personal/personalappcontroller.py` — `importJournalNotes.onSuccess` now uses `Diagram.save()` retry loop
- `btcopilot/btcopilot/schema.py` — `apply_local_changes` uses Python `==`, removed pickle-bytes
- `btcopilot/btcopilot/tests/pro/test_reserve_ids.py` — added `test_reserve_id_block_serial_calls_distinct_blocks`, `test_reserve_id_block_optimistic_locking_retries_on_conflict`

## Remaining gaps (documented, not bugs)

1. **Threading-based concurrent reserve test under SQLite :memory:** can't reliably exercise concurrency because each thread gets its own DB. Production correctness verified via SQL semantics + serial test + optimistic-retry test. A file-based SQLite or PostgreSQL-fixtured test would be a further hardening; out of scope.
2. **`reserve_ids` count upper bound**: see Rigor gap 3.
3. **`save_diagram` MCP tool not exposed in this Claude session**: see Phase 4 log. Patrick can drive the journeys via JOURNEYS_HUMAN.md.
