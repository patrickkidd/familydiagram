# Dangling-Refs Resilience

**Started:** 2026-05-02. **Status:** code complete; pending Patrick verification on rebuilt iPhone.

Branch: `2026-05-02-dangling-refs`.

Triggered by Patrick's iPhone failing to open diagram 1924 with `AttributeError: 'NoneType' object has no attribute 'updateEvents'`. The diagram blob carries 19 stored Events that reference Person ids 219–226 that no longer exist in `people` — a cascade-delete bug from before 2026-05-01 left the dangling refs. The data has sat untouched since 2026-03-09. Patrick's iPhone "Clear all events and people" attempts repeatedly silently no-op'd because `Scene.read` had crashed and `clearDiagramData` early-returns on `not self.scene`.

FMEA: [doc/fmea/2026-05-02--dangling-refs-load-crash.md](../../fmea/2026-05-02--dangling-refs-load-crash.md).

---

## TL;DR

Two failures, fixed together:

1. **Reader crash on dangling person refs.** Stored Events referencing missing Person ids made `Scene.read` raise `AttributeError`, leaving the in-memory scene null and the iPhone wedged.
2. **Failed-load wedges in-app recovery.** Personal app's `clearDiagramData` early-returns when `self.scene is None`. Combined with (1), users have no way to recover without sending Patrick the file.

Fix surface:

- `Event.read` now filters Nones from `relationshipTargets`/`relationshipTriangles` and logs which ids were dropped.
- `Scene.read` now scans Events post-resolve and drops any whose primary refs (`person`, `child` for Birth/Adopted, `spouse` for non-offspring PairBond) failed to resolve, plus Shift events with `relationship` set but no resolvable target. Full chunk is logged so data is recoverable on user request.
- `clearDiagramData` in `personalappcontroller.py` runs the server-side `applyChange` regardless of whether `self.scene` is populated. Users on a corrupt blob can now clear and re-extract from chat history.
- Inverted assert in `Event.__resolvePersonReferences` replaced with a proper missing-set warning.
- Writer-side defense: `Scene._reportDanglingRefs` walks outgoing chunks in `Scene.diagramData()` and emits a structured warning to the analytics logger if any event references a person id that isn't in `people`. Warn-only — no auto-strip.

---

## Goals

| # | Goal | Verifiable by |
|---|------|---------------|
| G1 | Diagram 1924 (and any blob with the same shape) loads on iPhone with the broken events dropped, no crash | Patrick rebuilds Personal app and re-opens diagram 1924 |
| G2 | "Clear all events and people" in Personal app works even when scene failed to load | Manual journey + `test_clearDiagramData_works_when_scene_is_None` |
| G3 | Dropped events are logged with full payload — user can email Patrick and Patrick can rebuild on request | Logs visible in `_log.warning` output / Datadog forwarding |
| G4 | Writer-side outgoing dangling refs are detected in telemetry without mutating user data | `test_diagramData_warns_on_outgoing_dangling_refs` |
| G5 | No regression on the 350-test scene suite or the personal-app suite | Full pytest run |

---

## Out of scope

- Hunting the original writer that produced the dangling refs in 1924. The cascade bug predates 2026-05-01 and the writer is unknown. Reader+writer telemetry now in place to catch any new instance.
- Reworking `apply_local_changes` (in `btcopilot/schema.py`) to validate cross-collection refs during merge. Server-side defense is a separate workstream.
- Surfacing a user-visible "diagram corrupt — clear and re-extract" banner. Logged as L5 in the FMEA, deferred.
- Data ticket on prod for diagram 1924. Not needed once iPhone rebuild lands — recovery mechanism is the in-app clear path now that it works regardless of scene state.

---

## Files changed

| File | Change |
|------|--------|
| `pkdiagram/scene/event.py` | `Event.read` filters Nones from relationship target/triangle lists, logs dangling ids. `__resolvePersonReferences` inverted assert replaced with proper warning. |
| `pkdiagram/scene/scene.py` | New `Scene._dropIrrecoverableEvents` helper. `Scene.read` invokes it after byId resolution to drop events that would crash `_do_addItem`. New `Scene._reportDanglingRefs` invoked from `Scene.diagramData()` — warn-only writer-side detection. |
| `pkdiagram/personal/personalappcontroller.py` | `clearDiagramData` runs `applyChange` whether or not `self.scene` is populated. |
| `pkdiagram/tests/scene/test_event.py` | Two pre-existing skipped tests un-skipped + 4 new tests covering primary-ref drops and writer-side warnings. |
| `pkdiagram/tests/personal/test_personalappcontroller.py` | New `test_clearDiagramData_works_when_scene_is_None`. |
| `doc/fmea/2026-05-02--dangling-refs-load-crash.md` | New FMEA. |
| `doc/fmea/README.md` | Index updated. |

---

## Verification record

- 26 tests in `test_event.py` pass (was 24 + 2 skipped; now 26 active + 1 unrelated skip).
- 2 clearDiagramData tests pass (existing batch-removal test + new scene-None test).
- Diagram 1924 blob loads end-to-end via `/tmp/verify_1924_load.py` — 21 people, 12 valid events kept, 19 dropped with full chunk payload logged.
- Full scene suite: 350 passed.

---

## Patrick's next steps

1. Rebuild Personal app on iPhone.
2. Open diagram 1924. Confirm no crash; confirm partial scene loads.
3. Tap "Clear all events and people" inside the app. Confirm save propagates.
4. Re-extract chat history (200 statements in discussion 55, 12 in discussion 58) to repopulate PDP.
5. Confirm Datadog logs show the structured warnings (`"dangling person refs"`, `"Dropping irrecoverable Event"`).
6. Watch Datadog after the release for `"Outgoing scene has dangling person refs"` — that's the writer-bug surface.
