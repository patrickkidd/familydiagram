# MVP Merge Fix — Dirty-Tracking + Block Allocation

**Started:** 2026-05-01. **Status:** in progress.

Closes the data-integrity workstream's blocking gap ([2026-04-17--data-integrity/](../2026-04-17--data-integrity/)) for the MVP intake flow. Predecessor doc: [2026-05-01--merge-correctness-gap.md](../2026-04-17--data-integrity/2026-05-01--merge-correctness-gap.md).

For detailed problem statement, proposals considered, and the rejection of alternative approaches, see the **Outstanding Issues** section of [doc/specs/DATA_SYNC_FLOW.md](../../specs/DATA_SYNC_FLOW.md).

---

## TL;DR

Two bugs cause silent data loss the moment Pro and Personal both have the same diagram open:

1. **Stale-snapshot merge** — `merge_scene_collection` is "union by id, local wins", so the second-saver overwrites the other side's edits to any item present in both snapshots. (Fix: dirty-tracking via snapshot diff.)
2. **`lastItemId` collision** — both apps share one counter and can independently allocate the same id. (Fix: server-side block allocation for new ids.)

Both fix together meet the MVP intake requirement: a clinician can leave Pro open while a client uses Personal without losing client edits when the clinician saves.

Out of scope: field-level concurrent edits (item-level last-write-wins is fine for MVP), pickle→JSON migration, embedded-Personal-in-Pro architecture. All deferred to a later v3 file-format overhaul.

---

## Goals

| # | Goal | Verifiable by |
|---|------|---------------|
| G1 | Pro left open while Personal edits + auto-saves → clinician's Cmd+S preserves Personal's edits | Journey J-1A |
| G2 | Personal open while Pro edits + saves → Personal's auto-save preserves Pro's edits | Journey J-1B |
| G3 | Either side deletes an item → deletion survives the other side's save | Journey J-2A, J-2B |
| G4 | Both sides add new items concurrently → both adds survive with distinct ids | Journey J-3 |
| G5 | Pro × Pro on the same diagram (legacy edge case) → no traceback, last-write-wins per item is acceptable | Journey J-4 |
| G6 | Local `.fd` open in Pro (no server) → behaves exactly as today, no block requests | Journey J-5 |

---

## Design

### Part 1 — Dirty-tracking merge (snapshot-diff)

Today's `merge_scene_collection(server, local)` does `merged.update(local)` which clobbers server-side edits to any shared id. The fix: derive what the user actually changed by diffing against the original snapshot, then apply only those changes on top of the server's state.

**Snapshot capture:** when the diagram is opened, both apps already hold the server-returned blob in `Diagram.data`. We snapshot it explicitly.

```python
# In Pro's ServerFileManagerModel and Personal's PersonalAppController, at diagram open:
self._openSnapshot = pickle.loads(self._diagram.data)
```

**Merge function** (replaces `merge_scene_collection` in `btcopilot/schema.py`):

```python
def apply_local_changes(server: list[dict], snapshot: list[dict], local: list[dict]) -> list[dict]:
    """
    Apply only the user's actual changes (snapshot → local) on top of server state.
    Items the user didn't touch are taken from server (preserving concurrent edits).
    """
    snapshot_by_id = {item["id"]: item for item in snapshot if item.get("id") is not None}
    local_by_id    = {item["id"]: item for item in local    if item.get("id") is not None}
    server_by_id   = {item["id"]: item for item in server   if item.get("id") is not None}

    deleted = {id for id in snapshot_by_id if id not in local_by_id}
    added   = {id for id in local_by_id    if id not in snapshot_by_id}
    dirty   = {id for id in local_by_id
               if id in snapshot_by_id
               and pickle.dumps(local_by_id[id]) != pickle.dumps(snapshot_by_id[id])}

    result: dict[int, dict] = {}
    for id, server_item in server_by_id.items():
        if id in deleted:
            continue
        if id in dirty:
            result[id] = local_by_id[id]
        else:
            result[id] = server_item
    for id in added:
        result[id] = local_by_id[id]

    return list(result.values())
```

`pickle.dumps()` byte comparison avoids QtCore equality false positives (`QPointF`, `QDateTime`) flagged in the audit.

**Wire-up:** both apps' `applyChange` callbacks call `apply_local_changes(server_field, snapshot_field, local_field)` instead of `merge_scene_collection(server_field, local_field)`. The closure captures `self._openSnapshot` so it's available across 409 retries.

**Delete after wire-up:** `merge_scene_collection` and the existing `tests/schema/test_merge_scene_collection.py`. Keep `SCENE_COLLECTION_FIELDS` as the explicit list of fields that participate in snapshot-diff (no metadata-driven loop introduced — explicit list is grep-friendly and matches today's pattern).

**Snapshot lifecycle (CRITICAL — central correctness mechanism):**

```python
# In Pro (ServerFileManagerModel) and Personal (PersonalAppController):
def _onDiagramOpened(self):
    # Captured ONCE per diagram session, after Diagram.data is populated from server.
    self._openSnapshot = pickle.loads(self._diagram.data)

# Inside Diagram.save() retry loop (server_types.py):
def save(self, server, applyChange, stillValid, ..., onSnapshotRefresh):
    for attempt in range(maxRetries):
        diagramData = self.getDiagramData()
        diagramData = applyChange(diagramData)  # uses self._openSnapshot via closure
        # ... PUT ...
        if response.status_code == 200:
            self.data = response.body["data"]  # CANONICAL post-write blob from server (latent fix 3a)
            onSnapshotRefresh(self.data)  # caller updates _openSnapshot
            return True
        if response.status_code == 409:
            self.data = response.body["data"]  # server's NEW state
            # NOTE: do NOT refresh _openSnapshot here. _openSnapshot is the user's
            # "starting point" — it must remain frozen across 409 retries so the
            # diff (snapshot vs current Scene) keeps reflecting the user's intent.
            # On a successful retry (200), onSnapshotRefresh fires and brings the
            # snapshot forward to the agreed state.
            continue
```

**Why this lifecycle:**
- After a successful 200, both client and server agree on the new state. Snapshot must advance, otherwise a subsequent toggle-edit (e.g., user sets cutoff=True, saves, then toggles cutoff=False) won't be detected as dirty against a stale snapshot.
- After 409, the server's state has changed but the user's intent (snapshot → local diff) hasn't. Refreshing the snapshot at 409 would re-classify the OTHER side's changes as "dirty local" and clobber them on retry. Snapshot must stay frozen until the next 200.

### Part 2 — Server-side block allocation

`Scene.nextId()` today (`scene.py:1919`) does `lastItemId += 1` locally. Two clients with the same starting `lastItemId` can independently allocate the same value. Fix: for server-backed diagrams, pull ids from a server-allocated block.

**New endpoint** in `btcopilot/btcopilot/pro/routes/`:

```
POST /v1/diagrams/{id}/reserve_ids
Body: {"count": 100}
Response 200: {"start": 101, "end": 200, "version": 7}
```

Server-side handler:
```python
# Atomic SQL: bumps lastItemId by count, returns the allocated range.
stmt = sql_update(Diagram).where(Diagram.id == diagram_id).values(...)
# Reads diagram.data (pickled), updates lastItemId in the pickle, writes back, bumps version.
```

The `version` bump ensures any in-flight save will hit a 409 and refresh — protecting against an open Pro session using stale `lastItemId` after another client reserved ids.

**Client allocator** (new `pkdiagram/serverblockallocator.py`):

```python
class ServerBlockAllocator:
    BLOCK_SIZE = 100

    def __init__(self, diagram, server):
        self._diagram = diagram
        self._server = server
        self._next = None
        self._end = None

    def __call__(self) -> int:
        if self._next is None or self._next > self._end:
            self._refill()
        v = self._next
        self._next += 1
        return v

    def _refill(self):
        response = self._server.blockingRequest(
            "POST",
            f"/v1/diagrams/{self._diagram.id}/reserve_ids",
            data={"count": self.BLOCK_SIZE},
            headers={"Content-Type": "application/json"},
        )
        body = json.loads(response.body)
        self._next = body["start"]
        self._end = body["end"]
        # Pull the bumped version into the local Diagram so next save uses it
        self._diagram.version = body["version"]
```

**Scene wiring** (`pkdiagram/scene/scene.py`):
```python
def setIdAllocator(self, allocator):
    """Inject a callable() -> int. None = use local lastItemId counter."""
    self._idAllocator = allocator

def nextId(self):
    if self._idAllocator is not None:
        return self._idAllocator()
    self.setLastItemId(self.lastItemId() + 1)
    return self.lastItemId()
```

**Binding logic** (Pro's `DocumentView` / `MainWindow` open path):
- Server-backed diagram open (via `serverFileModel.reloadDiagramRequested`) → `scene.setIdAllocator(ServerBlockAllocator(diagram, server))`
- Local `.fd` open → no allocator set, falls back to local `lastItemId += 1` (today's behavior)
- New diagram created on server (via `mainwindow.py:1983` `POST /diagrams` `onFinished` handler) → after the response confirms server-side creation, bind `ServerBlockAllocator` to the new Scene before the user can add items
- Save-As that uploads existing local diagram to server → no such path exists in current code (Save-As writes locally only). Out of scope.

Personal app: no allocator binding needed. Personal allocates ids exclusively via `commit_pdp_items` server-side, which already operates on the server-authoritative `lastItemId`. No collision possible because allocations are serialized through the server.

**Allocator interaction with `Scene.addItem(item)` for items that already have an id** (e.g., loading from server data, undo of a delete):
- `addItem` at scene.py:404 bumps `lastItemId` to `item.id` if `item.id > lastItemId()`.
- This is fine alongside the allocator: pre-existing ids come from the server's blob (where the server already accounts for them in its `lastItemId`). The allocator's block range was reserved AFTER the server's existing `lastItemId`, so no overlap is possible.
- Invariant: `Scene.nextId()` always uses the allocator when one is bound. Pre-existing ids passed to `addItem` are not allocations — they're loads.

### Part 3 — Latent fixes (in scope, surfaced by audits)

**3a — Server returns canonical post-write blob on 200.** `Diagram.save()` post-200 (`server_types.py:270`) sets `self.data = newData` (bytes the client SENT), but the server may have post-processed. Snapshot is then a lie.

Fix: both endpoints return the canonical post-write blob in their 200 response.
- Pro's pickle endpoint (`PUT /v1/diagrams/{id}`): response body is `pickle.dumps({"data": <canonical pickle>, "version": <new>})` — adds `data` field that wasn't there before.
- Personal's JSON endpoint (`PUT /personal/diagrams/{id}`): response includes `{"version": ..., "data": "<base64-encoded canonical blob>"}` — adds `data` field.

Client `Diagram.save()` 200 path uses `response.body["data"]` instead of `newData`. Backwards-compat: if old server doesn't return `data`, fall back to `newData` (today's behavior). Servers and clients ship together for MVP, so this only matters during upgrade.

**3b — Idempotent inferred-item creation in `commit_pdp_items`.** `_create_inferred_birth_items`, `_create_inferred_pair_bond_items`, `_repair_dangling_parents` create new items each call. On 409 retry, they re-create, producing duplicates.

Fix: at the start of each function, check whether the inferred entity already exists in the canonical lists based on a stable identifying key:
- Inferred birth items: identifying key is `(child_id)` since each child has at most one Birth event.
- Inferred pair bonds: identifying key is the canonical-ordered tuple `(min(person_a, person_b), max(person_a, person_b))`.
- `_repair_dangling_parents`: idempotent by design once parents reference valid pair_bond ids.

If the entity exists, return without creating. Add unit tests calling each function twice and asserting no duplicates.

### Part 4 — PDP and clusters merge story (NOT snapshot-diff)

`apply_local_changes` is for **Scene collection fields only**: `people`, `events`, `pair_bonds`, `emotions`, `multipleBirths`, `layers`, `layerItems`, `items`, `pruned`. PDP and clusters do NOT use snapshot-diff — they're owned-pass-through.

**`pdp` field (Personal-owned):**
- Pro's `applyChange`: never touches `diagramData.pdp`. Pass-through from server. (Same as today.)
- Personal's regular `saveDiagram` `applyChange`: never touches `diagramData.pdp`. Pass-through from server. (Same as today.)
- Personal's `_doAcceptPDPItem` `applyChange`: calls `commit_pdp_items` on incoming `diagramData`, mutating both `pdp.*` (removes accepted items) and `people`/`events`/`pair_bonds` (adds them with new positive ids). On 409 retry, `commit_pdp_items` runs again on server's NEW state. Idempotency via fix 3b ensures no duplicates if inferred items were already created.
- Personal's `_doRejectPDPItem` and `updatePDPItem`: similar — operations mutate `pdp` directly inside `applyChange`, not snapshot-diff.

**`clusters` and `clusterCacheKey` (Personal-owned):**
- Pro's `applyChange`: never touches. Pass-through from server.
- Personal's `applyChange`: writes from `self.clusterModel.clusters`. Last-write-wins on the whole field (rare collision because clusters are auto-detected, not user-edited).

**`lastItemId`:**
- Both apps: `diagramData.lastItemId = max(server, local)` after applying scene-collection diff. Block allocator advances server's `lastItemId` ahead of any block; client's local `lastItemId` only matters for local files.

**Other DiagramData fields** (UI flags, name, version, version-compat, masterKey, alias, etc.): stay as today — Pro overwrites from local, Personal pass-through. Domain partitioning per FR-3.

---

## Files touched

| File | Change |
|------|--------|
| `btcopilot/btcopilot/schema.py` | Add `apply_local_changes()`. Mark `personal=True` and add `scene=True` metadata on appropriate `DiagramData` fields. Make `_create_inferred_*` idempotent. Delete `merge_scene_collection`, `SCENE_COLLECTION_FIELDS` after callers updated. |
| `btcopilot/btcopilot/pro/routes/diagrams.py` (or wherever `/v1/diagrams/` lives) | Add `POST /v1/diagrams/{id}/reserve_ids`. |
| `btcopilot/btcopilot/pro/models/diagram.py` | Helper for atomic id-block reservation in the diagram pickle. Update `update_with_version_check` to return canonical post-write blob in the 200 response body. |
| `familydiagram/pkdiagram/serverblockallocator.py` | New file: `ServerBlockAllocator`. |
| `familydiagram/pkdiagram/scene/scene.py` | Add `setIdAllocator()`. Modify `nextId()` to delegate when allocator set. |
| `familydiagram/pkdiagram/server_types.py` | `Diagram.save` 200 path: use server-returned canonical bytes. Add `_openSnapshot` lifecycle alongside `Diagram.data`. |
| `familydiagram/pkdiagram/models/serverfilemanagermodel.py` | Snapshot capture on diagram open. Rewrite `applyChange` to call `apply_local_changes()` per scene-owned field. Bind `ServerBlockAllocator` on server-diagram open. |
| `familydiagram/pkdiagram/personal/personalappcontroller.py` | Snapshot capture on diagram open. Rewrite `applyChange` to call `apply_local_changes()`. |
| `familydiagram/pkdiagram/documentview/` (open path) | Wire `ServerBlockAllocator` to Scene for server-backed diagrams. |

---

## Test surface

### Unit tests (btcopilot)

- `tests/schema/test_apply_local_changes.py` (new)
  - edit-survives (server unchanged item, local unchanged → take server)
  - edit-survives (server unchanged, local changed → take local)
  - edit-survives (server changed, local unchanged → take server) ← the bug
  - edit-conflict (both changed → take local, item-level LWW)
  - delete-survives (deleted on both → drop)
  - delete-survives (deleted on local, server unchanged → drop)
  - add-survives (added on local, not on server → keep)
  - add-on-both (collision → second one wins; documented)
  - QtCore field unchanged → not marked dirty (regression guard for false-positive)

- `tests/pro/test_reserve_ids.py` (new)
  - simple reserve returns block, bumps lastItemId, bumps version
  - two concurrent reserves return distinct blocks
  - reserve increments persist across reads

- `tests/schema/test_inferred_idempotent.py` (new)
  - calling `_create_inferred_birth_items` twice yields one item, not two
  - same for `_create_inferred_pair_bond_items`, `_repair_dangling_parents`

### Unit tests (familydiagram)

- `tests/scene/test_id_allocator.py` (new)
  - Scene with no allocator falls back to lastItemId+=1
  - Scene with allocator delegates
  - Allocator transitions don't break existing items

- `tests/models/test_serverfilemanagermodel.py` — flip the 7 concurrent simulation tests to assert correct snapshot-diff behavior

### E2E harness (this workstream)

See [JOURNEYS.md](JOURNEYS.md). Each journey is run via `familydiagram-testing` MCP with ephemeral server, both apps, and full bridge coordination. Logs and screenshots captured to `logs/<timestamp>--J-NNN/`.

---

## Out of scope (deferred)

| Concern | Why deferred | Where it goes |
|---------|--------------|---------------|
| Field-level concurrent edits (Pro and Personal both edit Person 5's different fields → field-level LWW) | Item-level LWW acceptable for MVP. Real fix needs field versioning (CRDT) or per-field deltas. | v3 file-format overhaul |
| Pickle → JSON wire format | Big refactor, no MVP value. | v3 |
| Cleaner `DiagramData` model | Same. | v3 |
| Embedded Personal-in-Pro shared in-process scene | Architectural rework. Future feature. | post-MVP |
| Renumber-in-flight on collision | Block allocation makes collision structurally impossible. | not needed |
| Per-app id namespace | Block allocation is cleaner. | not needed |

---

## Decisions log

- **2026-05-01**: Chose snapshot-diff over command-stack instrumentation for dirty tracking. Audit showed command stack covers ~60% of mutation paths; snapshot-diff is exhaustive by construction. (See gap doc deliberation.)
- **2026-05-01**: Chose server-side block allocation over renumber-on-collision. Audit identified ~10 distinct id-keyed state sites that would need patching on renumber (Property values, `Layer.itemProperties`, cluster cache, undo command closures). Block allocation makes patching unnecessary.
- **2026-05-01**: Block leak (~95 ids per session) accepted. Math: 2^31 / (10 instances × 5 sessions/day × 95 leaks) > 1100 years per diagram.
- **2026-05-01**: POST verb chosen for reserve-ids endpoint. PUT would imply idempotence; reserving ids is non-idempotent.
- **2026-05-01**: Endpoint under `/v1/` (Pro app namespace). Personal app doesn't need block reservation — its adds go through `commit_pdp_items` server-side, which is already serialization-safe.

---

## Status

| Item | Status |
|------|--------|
| Phase 0 — doc relocation | DONE |
| Phase 1 — plan + journeys written | IN PROGRESS |
| Phase 2 — sub-agent review of plan | pending |
| Phase 3a — server reserve_ids endpoint | pending |
| Phase 3b — Scene id allocator + Pro binding | pending |
| Phase 3c — apply_local_changes in schema | pending |
| Phase 3d — applyChange wiring (both apps) | pending |
| Phase 3e — latent fixes (post-200 GET, idempotent inferred) | pending |
| Phase 3f — unit tests | pending |
| Phase 4 — E2E harness journeys | pending |
| Phase 5 — final report | pending |

---

## Your next steps

1. Review this plan + [JOURNEYS.md](JOURNEYS.md). Approve before I touch code.
2. Once approved, no further input needed until Phase 5 report.
