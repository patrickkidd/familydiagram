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
- `activateTriangleLayer()` - Activates triangle's Layer on badge click
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

1. **Badge on Mover Person** - Small triangle badge appears when currentDateTime matches event date. Click activates Layer. Toward/Away indicator shown if corresponding event exists on same date.

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

- `familydiagram/pkdiagram/tests/scene/test_event.py::test_triangle` - Tests Inside and Outside triangle creation
- Updated `test_scene_layers.py` item count (24 → 28 for new badge items per Person)

## Animation

### Phase 1 - Gather
Existing Layer machinery handles this - people animate from default diagram positions to final triangle Layer positions.

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

### Symbols Between Clusters
When Phase 2 animation starts, symbols are created between cluster centroids:

1. **Mover ↔ Targets** - Inside/Outside arrow symbols showing primary relationship direction
2. **Mover ↔ Triangles** - Opposite direction arrows (Inside with targets = Outside from triangles)
3. **Targets ↔ Triangles** - Dashed neutral connection line

Implementation in `Triangle`:
- `_arrowPath(fromPt, toPt, inward)` - Creates arrow path pointing inward (-->) or outward (<--)
- `_linePath(fromPt, toPt)` - Creates simple line for neutral connections
- `createSymbols()` - Creates all symbol QGraphicsPathItems based on relationship type
- `removeSymbols()` - Cleans up symbols on layer deactivation

### Description Callout
Text callout showing `Event.description` positioned above the mover:
- `createCallout()` - Creates QGraphicsTextItem with background rect
- `removeCallout()` - Cleans up on layer deactivation
- Only displayed if event has description text

## Future Work

- **Baseline Triangles** - Independent of events, new data structure needed
