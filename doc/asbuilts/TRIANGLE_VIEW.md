# Triangle View - As-Built Documentation

## Overview

Triangle View visualizes Inside/Outside shift events using private Layers. A triangle has 3 positions (clusters):
1. **Mover** - `Event.person` (always 1 person)
2. **Targets** - `Event.relationshipTargets` (1+ people)
3. **Triangles** - `Event.relationshipTriangles` (1+ people)

**Inside move**: Mover moves closer to Targets, further from Triangles
**Outside move**: Mover moves away from both; Targets and Triangles appear closer

## Components

### Scene Layer (scene/triangle.py)

`Triangle` class manages the triangle visualization:

```python
class Triangle:
    def __init__(self, event: Event):
        self._event = event
        self._layer = None  # Internal Layer for visualization

    def mover(self) -> Person: ...
    def targets(self) -> list[Person]: ...
    def triangles(self) -> list[Person]: ...
    def allPeople(self) -> list[Person]: ...
    def calculatePositions(self) -> dict[int, QPointF]: ...
    def applyPositionsToLayer(self): ...
```

Key methods:
- `calculatePositions()` - Computes equilateral triangle layout with proximity adjustments based on Inside/Outside
- `applyPositionsToLayer()` - Stores positions in Layer.itemProperties

### Event Integration (scene/event.py)

Events store reference to their Triangle:
- `Event._triangle` - Private attribute
- `Event.triangle()` - Getter
- `Event.setTriangle()` - Setter

### Scene Integration (scene/scene.py)

Triangle creation happens in three places:

1. **During `addItem`** (for new events with `relationshipTriangles` already set)
2. **In `onItemProperty`** (when `relationshipTriangles` property is set on existing event)
3. **During file load** (post-batch creation for events loaded with `relationshipTriangles`)

Each path creates:
1. `Triangle(event)`
2. `Layer(internal=True, storeGeometry=True)`
3. Links triangle to layer and event

### Person Badge (scene/person.py)

Triangle badge on mover Person:
- `triangleBadgeItem` - QGraphicsPathItem child for triangle icon
- `towardAwayBadgeItem` - QGraphicsPathItem child for Toward/Away arrow indicator
- `triangleEventsForMover()` - Finds triangle events where this person is mover
- `updateTriangleBadge()` - Shows/hides badge and Toward/Away indicators based on currentDateTime match
- `toggleTriangleLayer()` - Toggles triangle's Layer on/off on badge click
- `_findTowardAwayEventOnDate()` - Finds Toward/Away events on same date for compound display

Badge appears as small triangle shape using Event.color when currentDateTime matches event's date. If a Toward or Away event exists on the same date for the same person, an arrow indicator appears below the badge.

### QML Model (models/trianglemodel.py)

`TriangleModel` provides Qt model interface:
- Lists all triangle events
- Shows name, date, description
- Checkbox to activate layer
- Follows EmotionalUnitsModel pattern

### QML View (resources/qml/PK/TriangleView.qml)

Simple list view showing triangles:
- Checkbox for layer activation
- Date column
- Name column (mover's name)
- Used in both SearchDialog and CaseProperties

### CaseProperties Integration

Triangle View added as 4th tab in CaseProperties (Timeline, Settings, Copilot, **Triangles**):
- `RightDrawerView.Triangles` enum value
- `actionShow_Triangles` QAction with Ctrl+5 shortcut
- Toolbar button in RightToolBar
- `documentview.showTriangles()` method

## Entry Points

1. **Badge on Mover Person** - Small triangle badge appears when currentDateTime matches event date. Click toggles Layer on/off. Toward/Away indicator shown if corresponding event exists on same date.

2. **SearchDialog TriangleView** - Lists all triangles. Click checkbox to activate layer.

3. **CaseProperties Triangles Tab** - Accessed via toolbar button or Ctrl+5. Same list view as SearchDialog.

## File Changes

### Created
- `familydiagram/pkdiagram/scene/triangle.py`
- `familydiagram/pkdiagram/models/trianglemodel.py`
- `familydiagram/pkdiagram/resources/qml/PK/TriangleView.qml`
- `familydiagram/doc/TRIANGLE_VIEW_VISION.md`
- `familydiagram/doc/brainstorming/triangle-visualization.md`

### Modified
- `familydiagram/pkdiagram/scene/__init__.py` - Export Triangle
- `familydiagram/pkdiagram/scene/scene.py` - Create Triangle Layer, Phase 2 trigger, exit handlers
- `familydiagram/pkdiagram/scene/event.py` - Add triangle getter/setter
- `familydiagram/pkdiagram/scene/person.py` - Add triangle badge and towardAway badge
- `familydiagram/pkdiagram/documentview/view.py` - Add Escape key handler for deactivateTriangle
- `familydiagram/pkdiagram/documentview/__init__.py` - Add RightDrawerView.Triangles enum
- `familydiagram/pkdiagram/documentview/documentview.py` - Add showTriangles() method
- `familydiagram/pkdiagram/documentview/documentcontroller.py` - Connect actionShow_Triangles
- `familydiagram/pkdiagram/documentview/toolbars.py` - Add triangles button to RightToolBar
- `familydiagram/pkdiagram/mainwindow/mainwindow.ui` - Add actionShow_Triangles
- `familydiagram/pkdiagram/models/__init__.py` - Export TriangleModel
- `familydiagram/pkdiagram/util.py` - Add S_NO_TRIANGLES_TEXT
- `familydiagram/pkdiagram/app/qmlutil.py` - Export S_NO_TRIANGLES_TEXT
- `familydiagram/pkdiagram/resources/qml/PK/qmldir` - Register TriangleView
- `familydiagram/pkdiagram/resources/qml/SearchDialog.qml` - Add TriangleView section
- `familydiagram/pkdiagram/resources/qml/CaseProperties.qml` - Add Triangles tab

## Tests

- `test_event.py::test_triangle` - Tests Inside and Outside triangle creation
- `test_event.py::test_triangle_layer_activation_deactivation` - Activation/deactivation without errors
- `test_event.py::test_triangle_layer_reset_all` - resetAll properly deactivates triangle layer
- `test_event.py::test_triangle_layer_toggle_via_badge` - Badge click toggles layer on/off
- `test_event.py::test_triangle_layer_no_emotional_unit` - Triangle layers don't have emotional units
- `test_event.py::test_triangle_with_emotional_unit_layers` - Coexistence with EU layers
- `test_event.py::test_triangle_deactivate_via_scene_method` - scene.deactivateTriangle() works
- `test_event.py::test_triangle_next_layer_deactivates_triangle` - Next/Prev Layer deactivates triangle
- Updated `test_scene_layers.py` item count (24 → 28 for new badge items per Person)

## Position Calculation

Triangle positions are calculated relative to the **base (non-layered) positions** of people, not their visual/animated positions. This ensures stable behavior when layers activate/deactivate:

- `_calculateCentroid()` uses `person.itemPos(forLayers=[])` to get base positions
- `calculatePositions()` computes triangle layout around this centroid with proximity adjustments
- Positions are stored in `layer.itemProperties` via `applyPositionsToLayer()`

This design ensures Reset Diagram works correctly - when the triangle layer is deactivated, people return to their base positions as expected.

### Inside/Outside Positioning

A triangle always has two positions "inside" (closer to center) and one position "outside" (farther from center). The inside pair is at 1/3 base radius from centroid, the outside position is at 2/3 base radius (2:1 distance ratio).

**Inside Event** (Mover shifts toward Targets):
- Inside pair: Mover + Targets (1/3 radius)
- Outside: Triangles (2/3 radius)

**Outside Event** (Mover shifts away from both):
- Inside pair: Targets + Triangles (1/3 radius)
- Outside: Mover (2/3 radius)

Position angles are fixed: Mover at top (90°), Targets at bottom-left (210°), Triangles at bottom-right (330°). Only the radial distance changes based on inside/outside status.

## Animation

### Phase 1 - Gather
Existing Layer machinery handles this - people animate from base diagram positions to final triangle Layer positions.

### Phase 2 - Jump-Animate Emphasis
Implemented in `Triangle`:
```python
def startPhase2Animation(self):
    # Triggered after Phase 1 completes
    self._phase2RepeatCount = 0
    self._runPhase2Cycle()

def _runPhase2Cycle(self):
    # 1. Jump mover to neutral equilateral position (instant)
    # 2. Animate mover from neutral → final position
    # 3. Repeat 3 times total
```

Triggered via `Scene.onLayerAnimationFinished()` when a triangle layer's Phase 1 animation completes.

## Exit Handlers

Triangle visualization deactivates via:
1. **Escape key** - `view.py` calls `scene.deactivateTriangle()`
2. **Date change** - `scene.onProperty()` calls `deactivateTriangle()` when `currentDateTime` changes
3. **Layer deactivation** - `scene.onItemProperty()` stops Phase 2 animation when triangle layer is deactivated
4. **Next/Prev Layer** - `scene.setExclusiveLayerActive()` deactivates triangle layer before activating custom layer
5. **Badge toggle** - Clicking the triangle badge again calls `toggleTriangleLayer()` to deactivate
6. **Close button** - `triangleCloseButton` in `view.py` next to hidden items label calls `scene.deactivateTriangle()`

`Scene.deactivateTriangle()`:
```python
def deactivateTriangle(self):
    triangle = self.activeTriangle()
    if triangle:
        triangle.stopPhase2Animation()
        if triangle.layer():
            triangle.layer().setActive(False)
```

## Visual Elements in Triangle Layer

### Hidden Relationship Items
When a triangle layer is active, relationship items (Marriage, ChildOf, Emotion) are hidden to reduce visual clutter:
- `Marriage.shouldShowFor()`, `ChildOf.shouldShowFor()`, `Emotion.shouldShowFor()` return `False` when `scene.activeTriangle()` is truthy
- `Triangle.hideRelationshipItems()` explicitly hides these items on layer activation
- `Triangle.showRelationshipItems()` restores visibility on layer deactivation

### Symbols Between Clusters
Reuses existing `Emotion` class (from `emotions.py`) to show Inside/Outside symbols between clusters. Symbol placement depends on the event's relationship type:

**Inside Event:**
- Inside symbol: Mover → Targets
- Outside symbol: Mover → Triangles
- Outside symbol: Targets → Triangles

**Outside Event:**
- Outside symbol: Mover → Targets
- Outside symbol: Mover → Triangles
- Inside symbol: Targets → Triangles

Implementation in `Triangle`:
- `createSymbols()` - Creates `Emotion` items between cluster centroids based on relationship type
- `removeSymbols()` - Removes created Emotion items on layer deactivation
- Reuses `RelationshipKind.Inside` and `RelationshipKind.Outside` for symbol rendering

### Description Callout
Text callout showing `Event.description` positioned above the mover:
- `createCallout()` - Creates QGraphicsTextItem with background rect
- `removeCallout()` - Cleans up on layer deactivation
- Only displayed if event has description text

## File Persistence

### Triangle Layers are NOT Saved
Triangle layers are internal (`Layer(internal=True)`) and are not written to files. They are recreated on file load when events with `relationshipTriangles` are present.

### Triangle Symbol Emotions are Transient
The `Emotion` items created by `Triangle.createSymbols()` are stored in `triangle._symbolItems` and are:
- Created during `startPhase2Animation()`
- Removed during `stopPhase2Animation()`
- **Never saved to files** - `Scene.write()` skips them via `_isTriangleSymbol()` check
- **Skipped on load** - `Scene.read()` skips loading emotions that reference non-existent layers (orphaned triangle symbols from old files)

```python
# scene.py - Skip writing triangle symbols
if item.isEmotion:
    if self._isTriangleSymbol(item):
        continue  # Don't persist transient triangle symbols

# scene.py - Skip loading orphaned emotions
emotionLayers = chunk.get("layers", [])
if emotionLayers and all(lid not in by_ids for lid in emotionLayers):
    log.warning(f"Emotion references non-existent layers, skipping: {chunk}")
    skip = True
```

## Badge Color Logic

The triangle badge (`TriangleBadgeItem`) respects scene settings:

```python
# person.py - updateTriangleBadge()
if not self.scene() or self.scene().hideEmotionColors():
    color = util.PEN.color()  # Default pen color when colors hidden
else:
    eventColor = activeEvent.color()
    if eventColor in (None, "transparent", "#ffffff", "#000000"):
        # Use black/white based on dark mode
        color = QColor("#ffffff") if util.IS_UI_DARK_MODE else QColor("#000000")
    else:
        color = QColor(eventColor)
```

Badge updates are triggered by:
1. `currentDateTime` change → `updateTriangleBadge()` called for all people
2. Event color change → `Scene.onItemProperty()` calls `updateTriangleBadge()` on mover
3. `hideEmotionColors` setting change → `Scene.onProperty()` calls `updateTriangleBadge()` for all people

## QML Model Ownership

The `TriangleView.qml` component requires an explicit model to be passed:
```qml
property var model: null  // No default - must be provided by parent
```

Both `CaseProperties.qml` and `SearchDialog.qml` create their own `TriangleModel`:
```qml
PK.TriangleView {
    model: TriangleModel { scene: sceneModel.scene }
}
```

This prevents duplicate model instances that could cause checkbox synchronization issues.

### SceneModel.item() for QML Event Lookup
QML uses `sceneModel.item(eventId)` to get Event objects for the inspect button:
```python
# scenemodel.py
@pyqtSlot(int, result=QObject)
def item(self, id):
    ret = self.scene.findById(id)
    if isinstance(ret, QObject):  # Event is not a QObject
        QQmlEngine.setObjectOwnership(ret, QQmlEngine.CppOwnership)
    return ret
```

Note: `Event` inherits from `Item` (not `QObject`), so the ownership call is skipped.

## Future Work

- **Baseline Triangles** - Independent of events, new data structure needed
