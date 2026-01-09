# Plan: Trigger Scene.setCurrentDateTime from Tabular Timeline

## Problem

Need a mouse-initiated way to call `Scene.setCurrentDateTime` from the tabular timeline in CaseProperties. Should match graphical timeline behavior where click sets the current date.

## Background

Currently in the tabular timeline (TimelineView.qml):
- All click variants (regular, Ctrl, Shift) only affect event **selection**
- `Scene.currentDateTime` can only be set via the graphical timeline or navigation buttons
- This creates a disconnect where users expect clicking an event in the table to "go to" that date

The graphical timeline already uses click = set date, so the tabular timeline should match.

## Solution

**Regular click = select event + set current date**

| Action | Selection | Date |
|--------|-----------|------|
| Click | Clears selection, selects clicked row | Sets `currentDateTime` to event's date |
| Cmd/Ctrl+Click | Toggles row selection | No change |
| Shift+Click | Range select | No change |

This brings tabular and graphical timelines into functional parity. Selection and date are not formally coupled - they just happen to both update on regular click.

## Implementation

### 1. TimelineView.qml (primary change)

In `familydiagram/pkdiagram/resources/qml/PK/TimelineView.qml` around lines 824-862, modify the `onClicked` handler in the MouseArea:

```qml
onClicked: {
    if((mouse.modifiers & Qt.ControlModifier) == Qt.ControlModifier) {
        // Toggle selection only, no date change
        selectionModel.select(root.model.index(thisRow, 0), ItemSelectionModel.Toggle | ItemSelectionModel.Rows)
    } else if((mouse.modifiers & Qt.ShiftModifier) == Qt.ShiftModifier && table.lastClickedRow > -1) {
        // Range select only, no date change
        // ... existing range select logic unchanged ...
    } else {
        // Regular click: select AND set date
        selectionModel.select(root.model.index(thisRow, 0), ItemSelectionModel.ClearAndSelect | ItemSelectionModel.Rows)
        root.currentRow = thisRow
        // NEW: Set current date to this event's dateTime
        sceneModel.setCurrentDateTime(root.model.dateTimeForRow(thisRow))
    }
    table.forceActiveFocus()
    table.lastClickedRow = thisRow
    root.rowClicked(thisRow)
}
```

### 2. TimelineModel (if needed)

In `familydiagram/pkdiagram/models/timelinemodel.py`, add a method to get the dateTime for a row if not already exposed:

```python
@Slot(int, result=QDateTime)
def dateTimeForRow(self, row: int) -> QDateTime:
    event = self.eventForRow(row)
    return event.dateTime() if event else QDateTime()
```

### 3. SceneModel (if needed)

In `familydiagram/pkdiagram/models/scenemodel.py`, ensure `setCurrentDateTime` is exposed as a slot callable from QML:

```python
@Slot(QDateTime)
def setCurrentDateTime(self, dateTime: QDateTime):
    if self.scene:
        self.scene.setCurrentDateTime(dateTime)
```

## Files to Modify

| File | Change |
|------|--------|
| `familydiagram/pkdiagram/resources/qml/PK/TimelineView.qml` | Add `setCurrentDateTime` call in regular click branch (~line 850) |
| `familydiagram/pkdiagram/models/timelinemodel.py` | Add `dateTimeForRow(row)` slot if not present |
| `familydiagram/pkdiagram/models/scenemodel.py` | Ensure `setCurrentDateTime` slot exists |

## Verification

Use the `familydiagram-testing` MCP server:

1. Launch app, open a file with multiple events at different dates
2. Click an event row → verify:
   - Row becomes selected (highlight)
   - Current date indicator line moves to that event's date
   - Diagram updates to show state at that date
3. Cmd+click another row → verify:
   - Selection toggles (adds/removes row)
   - Date indicator does NOT move
4. Shift+click to range select → verify:
   - Multiple rows selected
   - Date indicator does NOT move
5. Click graphical timeline → verify same behavior as before (sets date)
6. Verify no regressions in event editing, deletion, or other timeline operations
