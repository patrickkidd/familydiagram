# Merge correctness gap — bi-directional edits silently lost

**Date:** 2026-05-01
**Status:** Blocking. Item 1 cannot be declared done until this is resolved.
**Context for new session:** Read this file in full. Then read [README.md](README.md) for the parent workstream. The journeys in the README (1A PASS, 1B planned) only validate the one case the current merge actually handles correctly.

## Problem statement

The current `merge_scene_collection` in `btcopilot/btcopilot/schema.py` is a union-by-id with whole-item replacement on conflict ("local wins"). This protects pure additions but silently corrupts every other bi-directional change pattern.

```python
@staticmethod
def merge_scene_collection(server: list[dict], local: list[dict]) -> list[dict]:
    """Union by id; local wins on conflict."""
    merged = {item["id"]: item for item in server if item.get("id") is not None}
    merged.update({item["id"]: item for item in local if item.get("id") is not None})
    return list(merged.values())
```

When the same id appears on both sides, **the entire local item dict replaces the server's dict**. There is no field-level reconciliation and no way for the merge to distinguish "this app edited this item" from "this app has a stale copy of this item."

## What this means in practice

Person id=5 starts with `cutoff=False` everywhere.

1. Personal edits person 5 → sets `cutoff=True`. Saves. Server now has `cutoff=True`.
2. Pro (still holding a stale snapshot where `cutoff=False`) edits person 6's name. Saves → 409.
3. Pro's `applyChange` merges: server's person 5 (`cutoff=True`) is replaced by Pro's local person 5 (`cutoff=False`), because Pro's snapshot included the whole person 5 object.
4. Personal's edit is silently lost. Pro never even touched person 5.

## Coverage matrix (what actually works today)

| Operation | Result |
|---|---|
| Pro adds new item, Personal saves anything | ✅ Pro's add survives (new id) |
| Personal adds new item, Pro saves anything | ✅ Personal's add survives |
| Pro edits item Personal didn't touch | ✅ Pro's edit survives (Personal had matching state) |
| Personal edits item Pro didn't touch but had in stale snapshot | ❌ **Personal's edit silently lost** |
| Either side deletes any item | ❌ Resurrected by other side's stale snapshot |
| Personal-owned scalars (`pdp`, `clusters`) | ✅ Pass through (Pro's `applyChange` doesn't write them) |

The "merge" feature protects exactly one case (pure additions) and gives a false sense of safety for everything else. The pre-merge code (always overwrite server) was strictly worse, but the new behavior is now the regression hiding in plain sight: any user editing concurrently in Personal + Pro will lose data on every save.

## Why journeys 1A/1B don't catch this

- 1A: Pro adds person, Personal deletes an event (only to bump the version). Reload Pro → person present. Tests addition only.
- 1B: Personal deletes event (version bump), Pro adds person, hits 409. Tests addition only, opposite direction.

Neither journey involves an edit to an item that exists on both sides. Neither verifies Personal-owned scalar preservation. Neither tests deletion outcome. See parent README for adversarial review summary.

## Options to fix

### Option A — Diff-based saves
Client sends `{added, modified, deleted}` instead of full state. Server applies the delta. On 409 retry, the same delta is re-applied against the new server state. Pro's stale copies of unmodified items never enter the merge.
- Pros: clean. Eliminates union ambiguity for adds, edits, and deletes simultaneously.
- Cons: changes save protocol on both client and server. Largest diff.

### Option B — Per-item dirty tracking (cheapest fit)
Both apps already have a command stack and undo machinery that knows which items were modified in this session. Thread that information into the save payload as a list of dirty ids. On 409, only those items participate in conflict resolution; every other item is taken from the server unmodified.
- Pros: small protocol change. Existing infrastructure already tracks the data.
- Cons: deletes still need a tombstone field separate from dirty-tracking.

### Option C — Field-level versioning (CRDT)
Each field carries a version vector. Merge picks the field with the higher version.
- Pros: fully general; handles every concurrent pattern.
- Cons: bloats every item; large refactor; reader code must understand versioned fields.

### Option D — Lock out concurrent editing
Detect when the other app has recent activity and refuse to open / refuse to save with a clear error.
- Pros: avoids the problem entirely. Smallest diff.
- Cons: bad UX. Defeats the purpose of having both apps for the same diagram. Patrick will likely reject.

**Recommendation:** Option B for this workstream, plus a tombstone field (`deleted_ids`) for deletion support. Smallest correct fix using existing infrastructure.

## What's also still open from the prior adversarial review

These remain undetected by current journeys but are downstream of fixing the edit-merge problem:

- **Personal-owned scalars under Pro 409**: `pdp`/`clusters` theoretically pass through unmodified, but no journey verifies it. Worth a unit test that asserts Pro's `applyChange` does not write Personal-owned fields.
- **`lastItemId` collision**: `max(server, local)` prevents counter regression but doesn't prevent two apps from allocating the same id locally before either synced. PDP commit + Pro item-add in close succession can collide.
- **`stillValid` is hardcoded to `True`**: dead validation hook. Either document as intentional or remove the parameter.

## Decisions needed before resuming

1. **Pick fix scope**: A, B, C, or D above. My recommendation is B + tombstones.
2. **Decide deletion semantics**: lossy-deletes documented as a limitation, or full deletion support via tombstones.
3. **Decide `lastItemId` collision policy**: accept-and-document, or fix via id renumbering on retry / switch to UUIDs.

Once 1–3 are decided, the README's journey list needs to be rewritten:
- 1A/1B kept as the "additive case" baseline
- Add 1C (Personal scalar preservation under Pro 409)
- Add 1D (deletion preservation — pass criterion depends on decision 2)
- Add 1E (lastItemId collision — pass criterion depends on decision 3)
- Add a new journey: edit-on-one-side-survives-save-on-other (the case that currently silently fails)

## Files to read in a fresh session

- [README.md](README.md) — parent workstream
- `btcopilot/btcopilot/schema.py` — `DiagramData`, `SCENE_COLLECTION_FIELDS`, `merge_scene_collection`
- `familydiagram/pkdiagram/models/serverfilemanagermodel.py` — Pro's `applyChange` in `setData`, the `stillValid = lambda d: True` line
- `familydiagram/pkdiagram/personal/personalappcontroller.py` — Personal's `applyChange` in `saveDiagram`
- `btcopilot/btcopilot/tests/schema/test_merge_scene_collection.py` — existing merge unit tests (do not validate the edit case)
