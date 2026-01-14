# Triangle View Vision

## Overview

Triangle View visualizes Inside/Outside shift events using private Layers with animated positioning to show emotional proximity in Bowen theory triangles.

## Core Concept

A triangle has 3 **positions** (clusters of people):

| Position | Source | Count |
|----------|--------|-------|
| Mover | `Event.person` | Always 1 |
| Targets | `Event.relationshipTargets` | 1+ people |
| Triangles | `Event.relationshipTriangles` | 1+ people |

**Inside move**: Mover moves closer to Targets, further from Triangles
**Outside move**: Mover moves away from both; Targets and Triangles appear closer to each other

## Emotion Symbols

### Main Diagram (dated emotions, tied to Event)

| Event Type | mover→targets | mover→triangles | targets→triangles |
|------------|---------------|-----------------|-------------------|
| Inside | Inside | Outside | Outside |
| Outside | Outside | Outside | Inside |

These emotions are created in `Scene._do_addItem()` when the event is added, saved to the file, and show/hide based on `Scene.currentDateTime`. One emotion is created for **each unique pair** - so an event with 2 targets and 2 triangles creates 8 emotions (2 mover→target + 2 mover→triangle + 4 target→triangle).

### Triangle View (layer-specific symbols)

| Event Type | mover↔targets | mover↔triangles | targets↔triangles |
|------------|---------------|-----------------|-------------------|
| Inside | Inside | Outside | Outside |
| Outside | Outside | Outside | Inside |

Triangle View always shows exactly **3 symbols** - one between each position cluster centroid, regardless of how many people are in each position. Created by `Triangle.createSymbols()` when the layer is activated.

## User Interface

### Entry Points

1. **Badge on Mover Person** (in diagram)
   - Appears when `Scene.currentDateTime` matches a triangle event's date
   - Triangle shape using `Event.color`
   - Corresponding Toward/Away symbols shown alongside
   - Click activates triangle Layer

2. **Triangle View in CaseProperties** (right panel)
   - New view following Timeline, Settings, Chat pattern
   - Toolbar button with icon in RightToolBar
   - QAction in main menu
   - Lists all triangle events: date, mover name, description
   - Click to activate triangle's Layer
   - Filterable/searchable

### Exit Methods

- Escape key
- Close button
- Layer change (automatic)
- `Scene.currentDateTime` change

## Animation Sequence

**Phase 1 - Gather** (existing Layer machinery):
- People animate from default diagram positions to final triangle Layer positions
- Positions arranged to fill available space (PowerPoint-style)

**Phase 2 - Shift** (emphasis animation, runs on top of Phase 1):
1. Mover **jumps** (instant) from final position → neutral equilateral position
2. Mover **animates** from neutral → final position
3. Repeat 2-3 times, then stop at final position

The jump-animate pattern draws the eye to the movement without smooth back-and-forth sliding.

## What's Displayed in Triangle View

- 3 position clusters with names visible
- Inside/Outside symbols between all 3 positions (connecting cluster centroids)
- Callout (LayerItem subclass) with `Event.description`

## Technical Design

### Triangle Class

Similar to EmotionalUnit pattern:
- Holds reference to Event
- Manages adding 3 position clusters to Layer
- Stores/calculates layered `itemPos` for each person
- Creates Inside/Outside symbols between positions
- Creates Callout with event description

### Layer Configuration

- `Layer(internal=True)` - private, not user-created
- `storeGeometry=True` - positions stored in Layer
- Created on file load and event creation

### Position Calculations

1. **Neutral position**: Equilateral triangle centered on centroid of 3 clusters' original diagram positions
2. **Final position**: Reflects emotional proximity:
   - Inside: Mover closer to Targets
   - Outside: Mover distant from both

3. **Cluster layout**: Tight cluster (triangular/circular) when multiple people in a position

### Symbol Rendering

- Symbols connect to cluster centroid (single point per position)
- 3 symbols total: mover↔targets, mover↔triangles, targets↔triangles
- May need `pathFor_Inside`/`pathFor_Outside` modification or ClusterAnchor abstraction

## Future: Baseline Triangles

Current scope: Only dated Shift events with Inside/Outside relationship.

Future requirements:
- New data structure to identify baseline triangles independent of events
- Implementation must be flexible to support any source providing:
  - 3 position clusters
  - Inside/Outside state
  - Optional description
