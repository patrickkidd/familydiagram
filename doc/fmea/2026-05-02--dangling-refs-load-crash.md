# FMEA: Dangling Person Refs Brick Diagram Load

Date: 2026-05-02
Scope: Personal/Pro app load-time crash when stored Events reference Person ids that no longer exist in the scene's `people` list, plus the user-visible no-op of in-app recovery actions.

## Context

Discovered when diagram 1924 on the prod server crashed Personal app load on iPhone with `AttributeError: 'NoneType' object has no attribute 'updateEvents'`. Root cause: 19 of 31 Events referenced Person ids 219–226 (Birth/Bonded/Married/Divorced/Death/Shift) that were missing from `people`. Cascade-delete bug in code older than the 2026-05-01 MVP merge fix left the dangling refs; the data has sat untouched since 2026-03-09.

The user attempted to recover via "Clear all events and people" on the iPhone repeatedly. **Every attempt was a silent no-op** — `clearDiagramData` early-returned on `not self.scene` because `Scene.read` had crashed and `setScene` was never called. The diagram was unrecoverable from the user's side.

## Failure Modes

| # | Failure Mode | Trigger | Severity | Detection | Status |
|---|---|---|---|---|---|
| L1 | `Event.read` writes `None` into `_relationshipTargets`/`_relationshipTriangles` when `byId` can't find a referenced person | Stored Event has Person ids in `relationshipTargets`/`relationshipTriangles` whose Person rows are missing | Critical | Personal app log: `AttributeError: 'NoneType' has no attribute 'updateEvents'` at scene.py:552 | **FIXED** — `Event.read` filters Nones, logs warning |
| L2 | `Scene._do_addItem` accesses `item.person()` (which asserts `_person is not None`) when adding Events with unresolved primary refs | `_person`/`_spouse`/`_child` resolved to None during `Event.read` | Critical | Same crash path — different line | **FIXED** — `Scene._dropIrrecoverableEvents` removes these events before addItem |
| L3 | Event.`__resolvePersonReferences` has inverted assert: `assert set(ids) != set(...)` fires on the *valid* case | Anywhere this code path runs (re-resolution after edit, etc.) | Medium | Asserts hide the actual error class | **FIXED** — replaced with proper `missing = set(ids) - {x.id ...}` warning |
| L4 | `clearDiagramData` early-returns when `self.scene is None` | Personal app loaded a corrupt blob, `Scene.read` raised, `setScene` was never called | High — user has no recovery path inside the app, must email Patrick the file | Patrick's iPhone observation: "I cleared all events and people but I still get the error on re-open" | **FIXED** — clear path runs `applyChange` regardless of in-memory scene state |
| L5 | `personalappcontroller._refreshDiagram` swallows `Scene.read` exceptions silently | `try/except (KeyError, ValueError, TypeError, AttributeError): _log.exception(...)` then returns without surfacing to user | Medium — hides broken-blob state from the user; UI looks "loaded" because `_diagram` is populated, but no scene → all interactions silently broken | Diagnosed via stack trace inspection | **OPEN** — Phase 2: surface user-visible "diagram corrupt — try Clear & Re-extract" toast |
| W1 | Outgoing scene blob may carry dangling refs from an in-memory scene that was loaded with reader-resilience drops | If the user saves before re-extracting, dropped-event chunks are gone but other parts of the blob are not validated | Low — reader resilience now handles inbound; this catches outbound writer bugs in newer code | `Scene._reportDanglingRefs` logs `"Outgoing scene has dangling person refs in N event(s)"` to Datadog via `_log.warning` | **FIXED (warn-only)** — does not auto-strip; surfaces writer bugs in telemetry |

## Detection / Telemetry

All warning paths route through `pkdiagram.scene.event` and `pkdiagram.scene.scene` loggers. Logs forward to Datadog via `pkdiagram.app.analytics.Analytics`. Recommended Datadog filters:
- `service:familydiagram message:"dangling person refs"` — reader-side filter events
- `service:familydiagram message:"Dropping irrecoverable Event"` — reader-side dropped events (full chunk in payload — recoverable)
- `service:familydiagram message:"Outgoing scene has dangling person refs"` — writer-side; indicates active corruption source

## Tests

- `pkdiagram/tests/scene/test_event.py::test_read_filters_invalid_relationshipTargets`
- `pkdiagram/tests/scene/test_event.py::test_read_filters_invalid_relationshipTriangles`
- `pkdiagram/tests/scene/test_event.py::test_read_drops_shift_with_unresolvable_person`
- `pkdiagram/tests/scene/test_event.py::test_read_drops_birth_with_unresolvable_child`
- `pkdiagram/tests/scene/test_event.py::test_read_drops_shift_with_no_resolved_targets`
- `pkdiagram/tests/scene/test_event.py::test_diagramData_warns_on_outgoing_dangling_refs`
- `pkdiagram/tests/personal/test_personalappcontroller.py::test_clearDiagramData_works_when_scene_is_None`

## Recovery for Diagram 1924

No data ticket required. Mechanism: rebuild + reinstall Personal app on iPhone → reader resilience loads the diagram (drops 19 broken events, keeps 21 people, 12 valid events, 4 marriages, all chat history) → user taps "Clear all events and people" in app → save propagates clean state to server → user re-extracts from chat to rebuild PDP.

## Open Items

- **L5**: Personal app should surface a banner when load partially fails, not just log silently. Track in `doc/plans/2026-05-02--dangling-refs-resilience/`.
- **Writer-side root cause**: never identified. Reader + writer warnings now in place to catch any new instance of corruption.
