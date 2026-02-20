# Data Sync Flow

How diagram data flows between client apps (Pro, Personal) and the server.

For the data structures, see
[DATA_MODEL.md](../../../btcopilot/doc/DATA_MODEL.md). For how AI-extracted
data flows through the PDP, see
[PDP_DATA_FLOW.md](../../../btcopilot/doc/specs/PDP_DATA_FLOW.md).

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

### Accept-All Scene Addition Failure (IDENTIFIED, FIX NOT YET COMMITTED)

`_addCommittedItemsToScene` does not set `scene.isInitializing = True` during
Phase 3. Birth events with parent references trigger `ValueError` in
`Scene._do_addItem()` because the pair-bond Marriage validation fires before all
items exist.

The save to server succeeds BEFORE scene addition, so PDP is cleared on the
server but items aren't in the scene. Any subsequent `saveDiagram()` overwrites
server data with the scene state (which lacks the committed items), completing
the data loss.

Fix: set `scene.isInitializing = True` during Phase 3 of
`_addCommittedItemsToScene`, reset in `finally` block. Matches `Scene.read()`.

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

### Pro App applyChange Violates FR-2

`ServerFileManagerModel.setData()` builds an `applyChange` that ignores its
input and returns a full replacement `DiagramData`. On 409 retry, the server's
latest state (including Personal app changes) is discarded. This must be fixed
before embedding the Personal app into the Pro app.

## File Reference

| File | Contains |
|------|----------|
| `btcopilot/schema.py` | `DiagramData`, `PDP`, `Person`, `Event`, `PairBond`, `commit_pdp_items()`, `asdict()`, `from_dict()` |
| `btcopilot/pdp.py` | `apply_deltas()`, `cleanup_pair_bonds()`, `cumulative()`, `validate_pdp_deltas()` |
| `btcopilot/pro/models/diagram.py` | Server-side `get_diagram_data()`, `set_diagram_data()`, `update_with_version_check()` |
| `familydiagram/server_types.py` | Client-side `getDiagramData()`, `setDiagramData()`, `mutate()`, `pushToServer()`, `save()` |
| `familydiagram/personal/personalappcontroller.py` | Personal app: `saveDiagram()`, `_doAcceptPDPItem()`, `_doRejectPDPItem()`, `_addCommittedItemsToScene()` |
| `familydiagram/models/serverfilemanagermodel.py` | Pro app: blocking `save()` with `handleDiagramConflict()` |

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
