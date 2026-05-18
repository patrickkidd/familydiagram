# Data Sync Flow

How diagram data flows between client apps (Pro, Personal) and the server.

For the data structures, see
[DATA_MODEL.md](../../../btcopilot/doc/DATA_MODEL.md). For how AI-extracted
data flows through the PDP, see
[PDP_DATA_FLOW.md](../../../btcopilot/doc/specs/PDP_DATA_FLOW.md).

## File Reference

| File | Contains |
|------|----------|
| `btcopilot/schema.py` | `DiagramData`, `PDP`, `Person`, `Event`, `PairBond`, `commit_pdp_items()`, `merge_scene_collection()`, `asdict()`, `from_dict()` |
| `btcopilot/pdp.py` | `apply_deltas()`, `cleanup_pair_bonds()`, `cumulative()`, `validate_pdp_deltas()` |
| `btcopilot/pro/models/diagram.py` | Server-side `get_diagram_data()`, `set_diagram_data()`, `update_with_version_check()` |
| `familydiagram/server_types.py` | Client-side `getDiagramData()`, `setDiagramData()`, `mutate()`, `pushToServer()`, `save()` |
| `familydiagram/personal/personalappcontroller.py` | Personal app: `saveDiagram()`, `_doAcceptPDPItem()`, `_doRejectPDPItem()`, `_addCommittedItemsToScene()` |
| `familydiagram/models/serverfilemanagermodel.py` | Pro app: blocking `save()` with `handleDiagramConflict()`, `applyChange` merge logic |
| `familydiagram/scene/commands.py` | Undo command stack — caches some item ids in `RemoveItems._unmapped` |
| `familydiagram/scene/scene.py` | `Scene.nextId()`, `itemRegistry` keyed by id, `Scene.diagramData()` snapshot dump |

## Functional Requirements

### FR-1: Single Blob, Shared Ownership

A diagram is a single pickle blob. Both Pro and Personal apps read and write the
same blob. Neither app may silently overwrite the other's changes.

### FR-2: Optimistic Concurrency with Functional Mutations

Every diagram write is a **mutation function** applied to the latest server
state. The mutation receives a `DiagramData`, modifies it, and returns it.

On version conflict (409), the client accepts the server's latest state and
**replays** the mutation on top of it. This continues until the write succeeds
or retries are exhausted.

**Mutation rules:**
1. A mutation MUST modify and return its input — never discard it and return a
   replacement. Discarding the input destroys whatever the other app wrote.
2. A mutation MUST be safe to replay. If the callback captures values in a
   closure (e.g. PDP item IDs), those values must remain valid across retries,
   or the caller must provide a validation hook that aborts when they're stale.
3. A mutation SHOULD be a pure transform on its input — no side effects, no
   network I/O.
4. **Scene-collection fields use `DiagramData.apply_local_changes`** — snapshot-diff
   merge (added 2026-05-02). The mutation captures the caller's local Scene view
   (`_lastSavedSnapshot`) at successful save; on the next save's `applyChange`,
   `apply_local_changes(server, snapshot, local)` takes the user's actual changes
   and applies them on top of server's current state. Items the user didn't touch
   pass through from server, preserving concurrent edits at item level. See
   [doc/plans/2026-05-01--mvp-merge-fix/](../plans/2026-05-01--mvp-merge-fix/README.md).
5. **New scene-collection items get ids via server-side block allocation** (Pro app
   only; Personal allocates server-side via `commit_pdp_items`). On server-diagram
   open, Pro binds a `ServerBlockAllocator` that pulls non-overlapping id ranges
   via `POST /v1/diagrams/{id}/reserve_ids`. Eliminates `lastItemId` collision
   between concurrent writers. Local `.fd` files unchanged.

### FR-3: Domain Partitioning

For now, each app is authoritative over a disjoint partition of DiagramData:

| Partition | Authoritative app | Fields |
|-----------|-------------------|--------|
| Scene collections | Pro (or Personal when standalone) | `people`, `events`, `pair_bonds`, `emotions`, `multipleBirths`, `layers`, `layerItems`, `items`, `pruned` |
| PDP | Personal | `pdp` |
| Clusters | Personal | `clusters`, `clusterCacheKey` |
| Metadata | Both | `lastItemId`, `version`, `versionCompat`, `name` |
| UI flags | Pro (or Personal when standalone) | `hideNames`, `showAliases`, `scaleFactor`, etc. |

Because mutations only modify their own partition and preserve the rest, 409
replays merge correctly without coordination.

**Future**: When the Personal app is embedded in the Pro app, both will share a
single scene and the partitioning becomes moot — all mutations operate on the
same in-process DiagramData.

### FR-4: Scene Loading with Deferred Validation

When items are added to the Qt scene in bulk (initial load or PDP accept-all),
pair-bond validation must be deferred until all items exist. The scene's
`isInitializing` flag controls this — it suppresses Marriage-existence checks
during `addItem()` so that Birth/Married events can reference Marriages that
haven't been added yet.

Any code path that adds multiple interdependent items to the scene must set
`isInitializing = True` for the duration, matching `Scene.read()` behavior.

### FR-5: Async Transport, No Blocking Event Loops

Diagram saves MUST NOT block the Qt event loop. Blocking (via
`QEventLoop.exec_()`) allows Qt to process pending events mid-save, enabling
reentrant saves and race conditions.

The target architecture is: `mutate()` (instant, local) + `pushToServer()`
(async, non-blocking). The Pro app's blocking `save()` method is legacy and
will be deprecated when the Personal app is embedded.

## Data Model

A diagram's state is a single pickle blob stored in `diagrams.data` (PostgreSQL
`LARGEBINARY`). The blob deserializes to a Python dict whose keys map to
`DiagramData` fields (defined in `btcopilot/schema.py`).

The PDP uses negative IDs (e.g. -1, -2) to distinguish pending items from
committed items (positive IDs). When a PDP item is accepted,
`DiagramData.commit_pdp_items()` assigns a new positive ID, moves the item from
`pdp.*` to the top-level `people`/`events`/`pair_bonds` lists, and remaps all
references.

### Re-extraction cursor signal (FD-319)

Accept commits items locally then saves the blob (above). Separately,
`_doAcceptPDPItem` / `acceptAllPDPItems` fire a best-effort
`POST /personal/discussions/<id>/commit-pdp` with `{item_ids, full_accept}`
(`PersonalAppController._postCommitPdp`). `full_accept` = the staged PDP is
fully drained after this accept. The server advances the re-extraction cursor
(`discussions.extracted_through_order`) only on `full_accept`, so the next
extract treats already-accepted conversation as context-only. Failure is safe:
the cursor simply doesn't advance and the next extract re-windows, with the
server-side committed-duplicate guard absorbing any repeat. The cursor never
advances until this client call ships (legacy behaviour preserved). Concurrency
hardening of extract/accept is tracked in FD-331.

## Version Tracking

Each diagram has a `version` integer. The server increments it atomically on
every successful write via SQL `WHERE version = expected_version`. Clients send
`expected_version` with every PUT. Version mismatch → 409 with current data +
version. Standard optimistic locking.

Implementation: `Diagram.update_with_version_check()` in
`btcopilot/pro/models/diagram.py`.

## Operations

### 1. Load

Client fetches the diagram blob, deserializes to `DiagramData`.

- **Pro app**: `GET /v1/diagrams/{id}` → pickle
- **Personal app**: `GET /personal/diagrams/{id}` → JSON with base64 blob

Deserialization MUST load ALL known `DiagramData` fields dynamically via
`dataclasses.fields()`. Unknown keys are ignored (forward compat). Missing keys
use defaults.

```python
known = {f.name for f in fields(DiagramData)} - {"pdp"}
kwargs = {k: data[k] for k in known if k in data}
kwargs["pdp"] = from_dict(PDP, pdp_dict) if pdp_dict else PDP()
return DiagramData(**kwargs)
```

This logic is duplicated in `btcopilot/pro/models/diagram.py:get_diagram_data()`
(server-side) and `familydiagram/pkdiagram/server_types.py:getDiagramData()`
(client-side). They MUST stay in sync. The duplication exists because the
server-side version runs in Flask and the client-side runs in Qt with no Flask
dependency.

### 2. Mutate

Apply a mutation to the local blob. Pure data, no network.

```
Diagram.mutate(applyChange):
    diagramData = getDiagramData()     # deserialize
    diagramData = applyChange(diagramData)  # transform
    self.data = pickle.dumps(asdict(diagramData))  # reserialize
    return diagramData
```

The caller's post-processing (update scene, emit signals) runs immediately
after `mutate()` returns.

### 3. Push

Send the local blob to the server. Async, non-blocking.

```
Diagram.pushToServer(server, applyChange, onDone):
    PUT self.data + expected_version → server
    200 → update local version, onDone(True)
    409 → accept server data/version
         → mutate(applyChange)   # replay on server's latest
         → pushToServer(...)      # retry
    else → onDone(False)
```

The push stores `applyChange` for replay on 409. The callback is re-executed on
the server's latest data, which may contain changes from the other app or from
server-side processing (AI extraction).

### 4. Blocking Save (Pro App — Legacy)

`Diagram.save()` fuses mutate + push into a blocking call via
`QEventLoop.exec_()`. Adds `stillValidAfterRefresh` — a callback that inspects
the server's data on 409 and can abort the retry.

The Pro app uses this to show a conflict dialog ("Overwrite Their Changes" /
"Reload Their Changes") in `ServerFileManagerModel.handleDiagramConflict()`.

**Known issue**: The Pro app's `applyChange` callback replaces the entire
`DiagramData` instead of merging, violating FR-2 rule 1. On 409 retry it
discards the server's latest state. This means "Overwrite" destroys PDP and
other Personal app changes. Fixing this requires making the Pro app's callback
a proper merge (copy scene fields into the incoming DiagramData, like the
Personal app's `saveDiagram()` does).

**Deprecation path**: When the Personal app embeds into the Pro app,
`pushToServer()` becomes the single transport. An optional validation hook
replaces `stillValidAfterRefresh` for cases where human review is needed (e.g.
multi-user Pro app conflict).

## Mutation Types

### Scene Persistence (saveDiagram)

Copies the Qt scene's current state into DiagramData's scene collection fields.
Called after event edits, event deletes, undo, and cluster detection.

The callback copies scene fields INTO the incoming `diagramData`, preserving PDP
and other non-scene fields. This is a proper merge per FR-2.

### PDP Accept

Calls `DiagramData.commit_pdp_items([id])` on the incoming `diagramData`:
1. Finds the PDP item and all transitively referenced items
2. Assigns new positive IDs via `_next_id()`
3. Moves items from `pdp.*` to top-level committed lists
4. Remaps all references

After mutate, the caller adds committed items to the Qt scene
(`_addCommittedItemsToScene`) with `isInitializing = True` per FR-4, then emits
`pdpChanged`.

### PDP Reject

Removes the item and cascade-dependent items from PDP:
- Events referencing the rejected person
- Pair bonds referencing the rejected person
- People whose `parents` references the rejected pair bond

### PDP Update

Modifies a single field on a PDP item. Used for inline editing in the PDP sheet.

### PDP Review Surface (FD-332)

The review sheet (`PDPSheet.qml`) renders a card for **every** PDP entry kind —
`people`, `events`, AND `pair_bonds` — with no positive/negative id filter.
Pair bonds (including those linking already-committed people, e.g. setting a
person's parents) get `PDPPairBondCard.qml`, styled as an entity card like the
person card (not an event/SARF pill). `PersonalAppController.resolvePairBondChildren`
names the person whose `parents` points at the bond ("Parents of"). The badge
count (`PersonalContainer.qml`) counts all three collections, so a non-empty
pool can never show "0".

An extraction that yields nothing does NOT open an empty deck: `onExtractCompleted`
shows the "Nothing New" info dialog and calls
`PersonalAppController.dismissEmptyExtraction()`, which advances the
re-extraction cursor via `_postCommitPdp([], True)` (same bookkeeping as a full
accept of an empty pool) so the Extract button clears.

Out of scope (deferred): edits to already-committed people/events and deletes
of committed entities are not carried in the pool today and have no card.

### Clear Diagram Data

Wipes events, PDP, and optionally people/pair_bonds/emotions. Dev/test reset.

## Scene Loading (Two-Phase)

Both initial load (`Scene.read()`) and PDP accept
(`_addCommittedItemsToScene`) use two-phase loading:

1. **Phase 1**: Create all Item objects with IDs, build an ID → Item map
2. **Phase 2**: Call `item.read(chunk, byId)` to resolve cross-references

This handles circular references (e.g. Event references Person, Person
references Marriage, Marriage references Person).

During both phases, `scene.isInitializing = True` suppresses validation that
would reject items whose dependencies haven't been added yet (e.g. pair-bond
events without a Marriage).

## Outstanding Issues

### ~~Concurrent Multi-App Edit Corruption~~ — RESOLVED 2026-05-02

**Status as of 2026-05-02:** Fixed by the [2026-05-01--mvp-merge-fix workstream](../plans/2026-05-01--mvp-merge-fix/README.md). `merge_scene_collection` removed; replaced by `apply_local_changes` (snapshot-diff). Server-side block id allocation via `POST /v1/diagrams/{id}/reserve_ids` eliminates `lastItemId` collisions. Verified: 7/8 manual journeys PASS on real hardware (J-6 deferred until Personal exposes `editEvent` UI). 46 unit tests + 3 e2e harness journeys.

The original problem statement and proposals deliberation history is preserved below for context.

---

**Original status (2026-05-01)**: The current `merge_scene_collection` (`schema.py:437`, "union by id, local wins") protects pure additions but silently corrupts every other concurrent pattern. The "merge" feature creates a false sense of safety.

**What works today** (additive case only):
- Pro adds a new item, Personal saves anything → Pro's add survives.
- Personal adds a new item, Pro saves anything → Personal's add survives.
- Pro edits an item Personal didn't touch (and didn't have in its snapshot) → survives.
- Personal-owned scalars (`pdp`, `clusters`) pass through Pro's `applyChange` because Pro doesn't write them.

**What corrupts silently:**
- **Bidirectional edits to the same item** (different fields). Pro edits Person 5's name, Personal edits Person 5's cutoff. Whichever app saves second overwrites the other's field with its stale snapshot.
- **Deletes**. Either side deletes Person 5; the other side's stale snapshot resurrects them on next save.
- **`lastItemId` collision**. Both apps share one counter; both can independently allocate id 101 between syncs. `max(server, local)` keeps the counter consistent but does not prevent collision. When both apps save, `merge_scene_collection`'s "local wins" silently overwrites one entity with the other.

**What journeys 1A/1B in `doc/plans/2026-04-17--data-integrity/README.md` cover**: only the additive case (the one that works). They do not exercise edit-on-both-sides, delete-on-one-side, or `lastItemId` collision. They give a false-positive PASS.

**Realistic incidence today**: zero in production, because the Personal app is not yet released. Risk only materializes once Personal ships and a user opens the same diagram in both apps within a short window.

**Latent infrastructure bugs that any sync redesign must address:**

1. **`Diagram.data = newData` after 200** (`server_types.py:270`). Client sets the local snapshot to the bytes it just SENT, not what the server stored. If the server applied any post-processing (e.g. `ensure_chat_defaults` mutates people / bumps `lastItemId`), the client's snapshot is a lie. Any snapshot-based design (delta or dirty-tracking) inherits this.
2. **QtCore type equality** (`QDateTime`, `QPointF`, `QColor`). Two instances with identical content do not always compare equal (timezone state, etc.). A naive dict-equality diff produces false positives.
3. **`commit_pdp_items` inferred-item creation is non-idempotent across 409 retries.** `_create_inferred_birth_items`, `_create_inferred_pair_bond_items`, `_repair_dangling_parents` re-execute on each retry. Any retry-heavy design exposes this more often.
4. **PDP only lives in `DiagramData`, not in `Scene`.** A diff computed over `Scene.diagramData()` is structurally blind to PDP mutations. Personal's delta source must be `DiagramData`, not `Scene`.
5. **commit_pdp_items runs client-side inside `applyChange`** (`personalappcontroller.py:1011`), not server-side. Replays on every 409 retry.

**ID-keyed state in the Pro app** (relevant if any design renumbers ids client-side):

| State | Location |
|-------|----------|
| Item Property values storing ids | `Event.person/spouse/child/relationshipTargets/relationshipTriangles`, `Emotion.event/target/person/layers`, `Person.layers`, `LayerItem.layers/parentId`, `Marriage.custody` — all `Property` instances of type `int` or `list[int]`. Serialized to disk. |
| `Scene.itemRegistry` | `dict[int, Item]` keyed by id. ~14 read sites in `scene.py`. |
| `Layer.itemProperties` | `dict[itemId, dict[propName, value]]` per Layer. Read in `layer.py`, `commands.py:160,245`, `property.py`, `scenelayermodel.py`. |
| `AddItem._calloutParentId` | Cached parent id for callout undo (`commands.py:33`). |
| Cluster JSON cache | `clusters_{diagramId}.json` — `eventIds` lists persisted to disk by `clustermodel.py`. |
| Model `_sortedIds` | `peoplemodel.py`, `layeritempropertiesmodel.py`. |
| `RemoveItems._unmapped["events" / "emotions"]` cached id fields | `personId`, `spouseId`, `childId`, `targetIds`, `triangleIds`, `eventId`, `targetId` — verified dead code (stored, never read). Safe to delete. |

A renumber-on-collision design that misses any item in the first six rows produces silent data loss on next save/reload.

### Proposals Considered (2026-05-01 deliberation)

| Proposal | Approach | Verdict |
|----------|----------|---------|
| **Delta-via-applyChange (Scene-level)** | Capture original snapshot before save loop. In `applyChange(serverState)`, diff (snapshot vs current Scene), apply diff to serverState. Server unchanged. | **Insufficient.** A Scene-level diff is blind to PDP mutations. Must compute over `DiagramData`. Also still requires id-collision handling. |
| **Delta-via-applyChange (DiagramData-level)** | Same, but diff over `DiagramData`. Picks up PDP changes. | Better foundation but still needs id-collision strategy and the latent fixes (snapshot-after-200, QtCore equality). |
| **Renumber-in-flight on collision** | On 409, walk in-flight ids, detect collisions, renumber locally + patch all id-keyed state. | **Rejected.** Patching surface includes ~10 distinct id-storage sites across Properties, Layer overrides, cluster cache, model lists, undo stack object closures. Topological order required. Missing one site = silent corruption. Estimated 200-400 lines + comprehensive tests. |
| **Server-side block allocation** | On diagram open, server allocates a block of ids (e.g. 100). Client uses ids from the block. No collision possible. Tiny integer leak (~1100 years per diagram to exhaust 2^31). | Eliminates renumber entirely. Server change ~50 lines, client change ~30 lines. Patrick objected aesthetically to the leak. |
| **Server-side per-add allocation** | Client uses negative temp ids; server returns mapping on save. | Same patching surface as renumber-in-flight. No improvement. |
| **Per-app id namespace** | Pro uses ids in [1, 2^30); Personal in [2^30, 2^31). | Rejected — apps share data, should share namespace. |
| **UUIDs** | Globally unique ids. | Rejected — current id space is integer. |
| **Per-item dirty tracking (Option B from gap doc)** | Client sends full blob + `dirty_ids` per collection + `deleted_ids`. Merge: take server's copy for non-dirty/non-deleted, take client's for dirty, drop deleted. | Smaller fix (~100 LOC). Does NOT fix `lastItemId` collision (same overwrite hazard). Does NOT do field-level last-write-wins (item-level only). Compatible with existing infrastructure. |
| **v3 file format overhaul (option Patrick raised 2026-05-01)** | Coordinate with Personal app launch: switch to JSON, design deltas + server-allocated ids from the start, deprecate v1/v2 endpoints. | Largest change. Cleanest result. Justified if Personal launch is the trigger and Pro v3 is a non-compat release. |

**Decision (2026-05-02):** Server-side block id allocation + snapshot-diff merge (apply_local_changes) — combination of #4 and a refined version of "Per-item dirty tracking". Implemented and verified; see [doc/plans/2026-05-01--mvp-merge-fix/](../plans/2026-05-01--mvp-merge-fix/README.md). Field-level merge (same-item-different-fields conflicts → second saver wins) accepted as MVP behavior; v3 work item.

### Chat Response Race Condition

`_sendStatement()` is async. The server responds with updated PDP (from AI
extraction). The client calls `setDiagramData()` to update local state.

If a local mutation happened between send and receive (e.g. user accepted a PDP
item), `setDiagramData()` overwrites the local mutation with server data that
doesn't include it.

Fix requires either sequence numbers on mutations or a merge strategy that
reconciles server-side PDP deltas with client-side accepts.

### Undo Does Not Persist

`HandlePDPItem` restores a previous `DiagramData` snapshot locally via
`setDiagramData()` but does not push to the server. Undo is lost on app
restart. The undo command should call `pushToServer()` after restoring state.

### getDiagramData/setDiagramData Duplication

Deserialization is duplicated between btcopilot (`pro/models/diagram.py`) and
familydiagram (`server_types.py`). Unifying requires resolving the import
asymmetry: the server-side model needs `import PyQt5.sip` for unpickling Qt
objects, while the client has no Flask dependency.

### ~~Pro App applyChange Violates FR-2~~ (Fixed 2026-04-11)

Fixed. `ServerFileManagerModel.setData()` now merges Pro-owned fields into the
incoming `diagramData` via `dataclasses.fields()` iteration, skipping fields
tagged with `metadata={"personal": True}` on `DiagramData`. On 409 retry, the
server's latest PDP and cluster data are preserved. New Personal-owned fields
are automatically excluded via `DiagramData.personalFields()`.

## Historical Context

### Decisions

- **2025-06-11**: PDP stored directly in diagram pickle with negative IDs
  (Decision Log). Single blob is source of truth.
- **2025-06-11**: PDP deltas serve as both UX proposals and ML training signal
  (Decision Log).
- **2026-02-14**: PairBonds are first-class entities, explicitly extracted by AI
  (Decision Log).

### Superseded Issues (Fixed)

**Partial-load data loss in getDiagramData().** Both client and server only
loaded 7 of 40+ DiagramData fields. Fixed by loading all known fields via
`dataclasses.fields()`.

**Missing cascade delete in apply_deltas().** Deleting a person didn't remove
referencing pair bonds. Fixed by calling `cleanup_pair_bonds()` at the end of
`apply_deltas()`.

**Blocking saves enabled reentrancy.** Personal app used blocking `save()` →
`QEventLoop.exec_()` → pending Qt events fire → reentrant save. Fixed by
splitting into `mutate()` + `pushToServer()`.

**Pro App applyChange violated FR-2.** `ServerFileManagerModel.setData()` built
an `applyChange` that replaced the entire `DiagramData` instead of merging,
destroying PDP and cluster data from the Personal app on 409 retry. Fixed by
iterating `dataclasses.fields(DiagramData)` and skipping fields tagged with
`metadata={"personal": True}`. Ownership is declared on `DiagramData` in
`schema.py`; new Personal-owned fields are automatically excluded.

**Accept-All scene addition failure.** `_addCommittedItemsToScene` did not set
`scene.isInitializing = True` during Phase 3. `isPairBond()` events triggered
`ValueError` in `_do_addItem()` because Marriage validation fired before all
items existed. Fixed by setting `isInitializing = True` alongside batch mode.
Additionally, `commit_pdp_items()` was missing pair bond inference for several
`isPairBond()` event kinds (Separated, Divorced, Moved) and for Birth Case 2/3.
Fixed by expanding `_create_inferred_pair_bond_items()` to cover all non-offspring
`isPairBond()` kinds and ensuring `_create_inferred_birth_items()` always creates
pair bonds and sets `child.parents`.
