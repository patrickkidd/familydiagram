# As-Built: Trigger Scene.setCurrentDateTime from Tabular Timeline

**Implemented:** 2026-01-13

## Summary

Regular click on a timeline row in the tabular timeline (TimelineView.qml) now sets `Scene.currentDateTime` to the clicked event's date, matching the graphical timeline behavior.

## Behavior

| Action | Selection | Date |
|--------|-----------|------|
| Click | Clears selection, selects clicked row | Sets `currentDateTime` to event's date |
| Cmd/Ctrl+Click | Toggles row selection | No change |
| Shift+Click | Range select | No change |

## Files Modified

| File | Change |
|------|--------|
| [scenemodel.py](../../pkdiagram/models/scenemodel.py) | Added `setCurrentDateTime(QDateTime)` slot callable from QML |
| [TimelineView.qml](../../pkdiagram/resources/qml/PK/TimelineView.qml#L848) | Added `sceneModel.setCurrentDateTime()` call in regular click branch |
| [test_TimelineView.py](../../pkdiagram/tests/views/test_TimelineView.py) | Added `test_click_row_sets_current_date_time` test |

## Implementation Details

### SceneModel.setCurrentDateTime

```python
@pyqtSlot(QDateTime)
def setCurrentDateTime(self, dateTime: QDateTime):
    if self._scene:
        self._scene.setCurrentDateTime(dateTime, undo=True)
```

### TimelineView.qml onClicked Handler

In the regular click branch (no modifiers):
```qml
} else {
    selectionModel.select(root.model.index(thisRow, 0), ItemSelectionModel.ClearAndSelect | ItemSelectionModel.Rows)
    root.currentRow = thisRow
    sceneModel.setCurrentDateTime(root.model.dateTimeForRow(thisRow))
}
```

## Notes

- `TimelineModel.dateTimeForRow(row)` already existed as a slot, no modification needed
- The change uses `undo=True` so date changes can be undone
- Ctrl+click and Shift+click remain unchanged (selection only, no date change)
