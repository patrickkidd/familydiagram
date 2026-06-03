# Feature: Rebuild Diagram (deep re-extraction) — FD-338

## Purpose
Let a Personal-app user reconstruct a more complete, better-connected family
diagram from their discussions via async multi-sample consensus extraction. The
result arrives as a PDP delta and is reviewed/accepted through the **existing**
PDPSheet flow — no change to the accept/reject UI.

Prototype: `doc/ui-prototyping/5-Rebuild-Diagram/1-rebuild-A.qml`.

## Design decisions (constrained)
- The new UI is three small additions, each reusing an existing house pattern.
- The **fidelity toggle lives inside the cost modal**, not in the toolbar — so
  the toolbar gains only one icon button and the K choice is part of the confirm
  step.
- The cost modal is **temporary**: it must carry an in-code comment to remove it
  once a customer pricing model exists.

## 1. Rebuild button (PersonalContainer.qml)
- 28×28 circular `Rectangle` mirroring `extractButton` (~line 240).
  `objectName: "rebuildButton"`. Anchored `right: extractButton.left`,
  `rightMargin: 8`, vertically centered.
- Glyph: circular-arrows ("rebuild") via `Canvas`, stroke = `util.QML_TEXT_COLOR`.
- Neutral fill (`#3A3938` dark / `#E9E9EB` light) to distinguish from the blue
  Extract action.
- `visible: tabBar.currentIndex === 0 && !!personalApp && personalApp.canRebuild`
  — new controller property; true when the current discussion has a diagram with
  at least one discussion to rebuild from. (Independent of `canExtract`; a rebuild
  is valid even with no unextracted statements.)
- `MouseArea.onClicked: rebuildDialog.open()` — opens the modal; never enqueues
  directly.

## 2. Cost-confirm modal `rebuildDialog` (PersonalContainer.qml)
- `Popup`, parent `Overlay.overlay`, `modal: true`, mirrors `clearDataDialog`
  (~line 948): radius-14 `itemBg` background, OutBack enter, fade exit.
- Content (Column, padding 20):
  - Title "Rebuild Diagram" (17px bold).
  - Body (14px secondary, wrapped, no exclamation points): explains it re-runs the
    AI several times to reconstruct a more complete diagram, costs Alaska Family
    Systems about $0.50 each time, and to check with
    patrick@alaskafamilysystems.com before continuing.
  - **Max-fidelity row** (rounded `QML_ITEM_ALTERNATE_BG`): label "Max fidelity"
    + caption that flips with state ("Best accuracy, about $0.50" when ON /
    "Faster, about $0.25" when OFF) and a `Switch`, default **checked = K=6**.
  - Buttons row: "Cancel" (neutral) closes; "Continue" (accent) calls
    `personalApp.rebuildDiagram(maxFidelity ? 6 : 4)` then closes.
- **In-code comment** above the dialog: `TEMPORARY: remove this cost-confirmation
  dialog once a customer pricing model is added to the app.`

## 3. Progress overlay (LoadingOverlay.qml — shared component)
- Add `property real progress: -1` (and keep `property string text`).
  `progress < 0` → indeterminate spinner (legacy `importOverlay` behaviour,
  unchanged). `progress >= 0` → determinate `ProgressBar` (0–100) + label with
  percentage.
- Driven by a new controller signal during a rebuild (e.g. `rebuildProgress(int
  percent, string message)` where message is like "Rebuild 3 of 6").
- Backward compatible: existing `importOverlay` sets only `text`, so `progress`
  stays −1 and rendering is identical to today.

## Lifecycle / states
- **Idle**: rebuild button visible when `canRebuild`.
- **Confirming**: modal open; fidelity toggle set; Cancel or Continue.
- **Running**: overlay visible, determinate progress from status polling.
- **Complete**: controller deserializes the PDP into `diagram_data.pdp`,
  `setDiagramData`, emits `pdpChanged` + `extractCompleted` → existing
  `DiscussView.onExtractCompleted` opens the PDPSheet (reused).
- **Error / empty**: reuse existing `extractFailed` / "Nothing New" paths.

## Controller (personalappcontroller.py) — Python, not QML JS
- `canRebuild` (pyqtProperty/notify) — gating per above.
- `rebuildDiagram(int k)` — POST `/personal/discussions/<id>/deep-reextract`
  `{k}`; on `task_id`, begin polling `GET
  /personal/discussions/<id>/deep-reextract-status/<task_id>`; emit
  `extractStarted` + set overlay determinate.
- Poll handler: on PROGRESS emit `rebuildProgress`; on complete, deserialize
  `pdp`, `setDiagramData`, emit `pdpChanged` + `extractCompleted`; on error emit
  `extractFailed`. Reuse the existing async non-blocking request + the
  AssemblyAI-style polling pattern already in the controller.

## Tests
- Controller unit test: `rebuildDiagram` posts with the right k; polling state
  machine handles progress→complete (PDP applied, signals emitted) and
  progress→error (extractFailed), with the server mocked.
- Component test: rebuild button opens modal; Continue invokes
  `rebuildDiagram(6)` by default and `rebuildDiagram(4)` when toggle off.
- Note (rules I017): the Personal app has no person/event list view — any check
  of the *committed* result after accept must be done in the Pro app.
