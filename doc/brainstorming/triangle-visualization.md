# Triangle Visualization Brainstorming

Date: 2026-01-09

## Problem Statement

Inside/Outside shift events represent triangle dynamics in Bowen theory. Currently:
- Scene creates ONE Emotion symbol per person in `relationshipTargets`
- Symbol drawn between `Event.person` and each target via `pathFor_Inside`/`pathFor_Outside`
- `relationshipTriangles` stores third party but is NOT visualized on diagram
- The dyadic symbols were "60% hack" reusing existing emotion code

## Key Insight: Spatial vs Process Tension

Triangle participants can be *anywhere* on the diagram - a cousin can triangle with an aunt/uncle from a different nuclear family. Drawing geometric shapes or arcs between scattered people creates crossing-line chaos.

**Realization:**
- Spatial diagram = good for *structure* (relationships, generations, marriages)
- Triangle events = about *process* (movement, alignment at a moment in time)
- A triangle shift is ONE FRAME in timeline animation - not a permanent spatial relationship

Overlaying process onto structure may be the wrong approach.

## Triangle Semantics (Bowen Theory)

A triangle always has two on the inside and one on the outside:
- **Inside**: In low anxiety, inside position is favorable - implies emotional alignment/closeness between the two inside positions
- **Outside**: In high anxiety, outside position is preferred - "you guys are nuts, unlike me" - moving to emotional misalignment/distance

For an **Inside** move: Event.person moves toward Event.relationshipTargets, away from Event.relationshipTriangles
For an **Outside** move: Event.person moves away from both, leaving relationshipTargets and relationshipTriangles closer to each other

## Approaches Explored

### Spatial Approaches (All have scattered-people problem)

| Approach | Assessment |
|----------|------------|
| Geometric triangle overlay | Lines cross entire diagram when people scattered |
| Hub-and-spoke from mover | Still looks like dyadic, doesn't convey triadic |
| Curved arcs connecting 3 | Bezier paths crossing everything |
| Triangle badge + connecting lines | Badge OK, lines still problematic |

### Non-Spatial Approaches (Promising direction)

| Approach | Assessment |
|----------|------------|
| Timeline-centric | Triangle shifts as timeline events; click to see 3-node mini-snapshot |
| Event annotation | Metadata in inspector, no spatial drawing |
| Person-centric query | "Show triangles involving X" → list with mini-snapshots |
| Matrix/table view | All triangles in filterable list |

### Selected Approach: Layer-Based Triangle View

Use existing Layer infrastructure with exclusive selection:

1. **Private Layer per triangle event** - isolates the 3 people
2. **Custom geometry** - arranges people in triangle formation using available space
3. **Animation** - emphasizes the movement (inside/outside) visually
4. **Two entry points**:
   - Badge on mover person (when at relevant date)
   - Triangle list in CaseProperties

## Animation Design

**Phase 1 - Gather**: Existing Layer machinery animates people from default positions to triangle Layer positions (PowerPoint-style layout)

**Phase 2 - Shift**: Emphasis animation showing the movement
1. Mover **jumps** (instant) from final position to neutral equilateral position
2. Mover **animates** from neutral to final position (showing the move)
3. Repeat 2-3 times, then stop

This draws the eye to who moved and in what direction.

## Baseline Triangles (Future)

Currently only dated Shift events with Inside/Outside relationship are supported.

Future work needs:
- New data structure to identify baseline triangles independent of events
- Possibly undated Inside/Outside emotions define baseline triangles
- Triangle View should work with any source providing: 3 position clusters, Inside/Outside state, optional description

## Key Design Decisions

1. **3 positions** (not people): Event.person, Event.relationshipTargets, Event.relationshipTriangles - each is a cluster
2. **Cluster centroid** for symbol connections - one Inside/Outside symbol per position pair
3. **Tight cluster layout** when multiple people in a position
4. **Layer lifecycle**: Create on file load and event creation
5. **Exit handlers**: Escape, close button, layer change, currentDateTime change

## Files Identified

Create:
- `familydiagram/pkdiagram/scene/triangle.py` - Triangle class (like EmotionalUnit)
- `familydiagram/pkdiagram/models/trianglemodel.py` - Model for triangle list
- `familydiagram/pkdiagram/resources/qml/PK/TriangleView.qml` - CaseProperties view

Modify:
- `familydiagram/pkdiagram/scene/scene.py` - create Triangle Layer for Inside/Outside events
- `familydiagram/pkdiagram/scene/person.py` - badge rendering
- `familydiagram/pkdiagram/documentview/toolbars.py` - RightToolBar button
- `familydiagram/pkdiagram/documentview/documentview.py` - QAction
