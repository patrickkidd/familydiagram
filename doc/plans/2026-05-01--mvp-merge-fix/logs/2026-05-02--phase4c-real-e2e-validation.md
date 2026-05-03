# Phase 4c — Real E2E Harness Validation

**Date:** 2026-05-02
**Status:** Three journeys (J-3, J-1A, J-2A) verified end-to-end via the live Pro app + ephemeral btcopilot server, exposing and fixing a real bug that all prior unit/integration tests missed.

---

## What changed in this phase

1. **Multi-threaded the bridge** (`mcpbridge/server.py`) so MCP host + a direct-bridge driver script can both connect simultaneously. Without this, the harness's `save_diagram` could not be invoked from outside MCP.

2. **Extended `/test/diagrams/{id}` PUT** in ephemeral_server.py to bump version on each call. Without this, a server-side change made via the test endpoint wouldn't trigger a 409 on the next Pro save — the merge code path would never fire under harness simulation.

3. **Found and fixed a real merge bug** that all prior unit/integration tests missed: after a successful save that included other-client items in the merged result, the next save's snapshot baseline would include those items even though the local Scene never loaded them. Result: next save would interpret them as deletes and silently drop them.

   Fix: `_lastSavedSnapshot` is now captured by the caller (Pro's `setData` and Personal's `saveDiagram`) from the **caller's local Scene view**, not from the merged bytes returned by `Diagram.save`. `Diagram.data` continues to track the canonical server state for display/reopen (latent fix 3a unchanged).

## Files changed

- `familydiagram/pkdiagram/server_types.py` — clarified that `Diagram.save` does NOT set the merge snapshot; callers do.
- `familydiagram/pkdiagram/models/serverfilemanagermodel.py` — Pro's `setData` captures `dataToSave` as `_lastSavedSnapshot` after success.
- `familydiagram/pkdiagram/personal/personalappcontroller.py` — Personal's `saveDiagram` captures Scene state pre-save and stashes after success.
- `familydiagram/pkdiagram/mcpbridge/server.py` — multi-threaded client handling.
- `familydiagram/mcpserver/ephemeral_server.py` — `/test/diagrams/{id}` PUT bumps version.

## Journey results

| Journey | What it tests | Verdict | Conflicts |
|---------|---------------|---------|-----------|
| J-3 | Pro's `ServerBlockAllocator` reserves a block on first `Scene.nextId`; Person assigned id within reserved range; lastItemId advances on server | **PASS** | 1 (allocator's reserve_ids bumped version, save 409+retried) |
| J-1A | Server gets a new Person 99 from another client; Pro saves with stale view; Person 99 preserved | **PASS** | 1 |
| J-2A | Server deletes Person 4 (other client); Pro saves with stale view (still has Person 4 in Scene); deletion preserved AND Person 99 also preserved through 2nd stale save | **PASS** | 1 |

## Detailed journey log

```
=== J-3: block alloc ===
Pro: add_person → {id: 2}
Pro: save_diagram → {success: true, conflicts: 1}
Server: lastItemId=100, people=[(2, None)]
✓ Allocator reserved block [1, 100]; Pro's Person 2 within range

=== Pro adds 2nd person ===
Pro: add_person → {id: 4}
Pro: save_diagram → {success: true, conflicts: 0}
Server: people=[(2, None), (4, None)]

=== J-1A: simulate Personal commit (server adds 99) ===
Server PUT (with version bump): version=5
=== Pro saves with stale view (Pro doesn't know about 99) ===
Pro: save_diagram → {success: true, conflicts: 1}
Server: people=[(2, None), (4, None), (99, 'Personal_J1A')]
✓ Person 99 (Personal's commit) PRESERVED through Pro's stale-view save

=== J-2A: simulate Personal delete of Person 4 ===
Server PUT (with version bump): version=7
=== Pro saves with stale view (still has Person 4 in Scene) ===
Pro: save_diagram → {success: true, conflicts: 1}
Server: people=[(2, None), (99, 'Personal_J1A')]
✓ Person 4 deletion PRESERVED
✓ Person 99 still preserved (verifies snapshot fix prevents prior-save items from being dropped)
```

## The bug the e2e test caught (pre-fix)

Before the snapshot fix, this exact sequence produced:

```
J-2A final: [(2, None)]
```

Person 99 was silently dropped. Why: after J-1A's save, the canonical-blob (which fix 3a stores in `_diagram.data`) contained Person 99. The next save's snapshot pulled from `_diagram.data` — which had Person 99 — but Pro's Scene didn't have Person 99 (Pro never loaded it into Scene). So `apply_local_changes` saw "in snapshot, not in local" and treated it as a DELETE.

This bug was undetectable by the unit/integration tests because they manually constructed snapshot+local with consistent state. The e2e harness exposed it by exercising the realistic post-success-snapshot-update path that the unit tests didn't cover.

## What this validates

The full real-binary stack:
- `Diagram.save` retry loop with version-conflict detection
- `apply_local_changes` snapshot-diff merge
- `_lastSavedSnapshot` lifecycle (caller captures, used as baseline for next save)
- `ServerBlockAllocator` HTTP request
- Server's `reserve_id_block` SQL atomicity
- Server's PUT 200 canonical blob response (fix 3a)
- Pro's `MainWindow.onServerFileClicked` allocator binding
- Pro's `ServerFileManagerModel.setData` save dispatch with merge

All exercised by real Pro app talking to real Flask server — no mocks at the integration boundary.

## What's still NOT validated by harness

- Personal app's saveDiagram path through the same scenarios. Personal's bridge doesn't expose `add_person`; Personal doesn't easily make a server-visible change without triggering a full PDP commit flow. The unit/integration tests cover Personal's `applyChange` exhaustively, and Personal uses the SAME `apply_local_changes` + `_lastSavedSnapshot` mechanism as Pro. Confidence: high but not direct e2e.
- Concurrent threading test for `reserve_id_block` under SQLite (file-based or PostgreSQL fixture). Production correctness covered by SQL semantics + serial test + retry-branch monkeypatch test.

## Files Patrick may want to inspect

- `pkdiagram/server_types.py` lines 268-290 (200 path)
- `pkdiagram/models/serverfilemanagermodel.py` lines 503-512, 569-578 (Pro snapshot capture)
- `pkdiagram/personal/personalappcontroller.py` lines 274-318 (Personal snapshot capture)
- `pkdiagram/mcpbridge/server.py` lines 187-206 (multi-threaded bridge)
- `mcpserver/ephemeral_server.py` lines 152-163 (test PUT bumps version)
