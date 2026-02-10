# LearnView As-Built Specification

## Overview

The LearnView is a Personal app screen that visualizes a user's life events on a SARF (Symptom, Anxiety, Relationship, Functioning) graph. Events are grouped into AI-detected clusters that represent meaningful patterns in the user's life. The view supports both an overview mode showing all clusters and a focused mode for examining a single cluster in detail.

## Data Model

### Event Properties
Each event has:
- **Date**: When the event occurred (required for graph positioning)
- **Kind**: Event type - either "shift" (SARF change) or life events (birth, death, married, divorced, moved, bonded, adopted)
- **SARF Variables**: Optional up/down/same shifts for symptom, anxiety, and functioning
- **Relationship**: Optional relationship dynamics (conflict, distance, toward, outside, inside, overfunctioning, defined-self)
- **Relationship Targets**: People involved in relationship events
- **Relationship Triangles**: People forming a triangle dynamic
- **Description**: Brief event title
- **Notes**: Extended notes about the event

### Cluster Properties
Clusters are AI-detected groupings with:
- **Title**: AI-generated descriptive name
- **Date Range**: Start and end dates
- **Event IDs**: List of events in the cluster
- **Dominant Variable**: Which SARF variable drives this cluster (A/S/R/F)
- **Pattern**: Optional detected pattern type (e.g., "work_family_spillover", "triangle_activation")

## View Modes

### Overview Mode (Default)
- Shows horizontal cluster bars arranged in up to 3 staggered rows
- Each bar spans the cluster's date range on the timeline
- Bar color is randomly assigned per cluster (for visual distinction)
- Timeline supports pinch-to-zoom and pan gestures
- Tapping a cluster bar transitions to focused mode

### Focused Mode
- Full-width hero graph showing the selected cluster's SARF data
- Animated transition from cluster bar to hero graph (400ms)
- Previous/next arrows to navigate between clusters
- "Close" button returns to overview mode
- Event list scrolls to show the focused cluster's events

## Graph Visualization

### SARF Lines
Three quantitative cumulative lines are drawn:
- **Symptom** (red): Physical/behavioral symptoms
- **Anxiety** (green): Emotional anxiety level
- **Functioning** (gray): Overall life functioning

Values are cumulative within the cluster, relative to a baseline established at the first event.

### Relationship Events
Relationship shifts are shown as vertical dashed lines in blue at the event's x-position.

### Event Dots
- Dots are drawn ONLY where a specific event changed that variable
- For example, if an event only changed anxiety (not symptom or functioning), only an anxiety dot appears at that position
- This prevents misleading dots that don't represent actual changes

### Selection Ring
- A focus ring appears around the selected event's dot(s) on the graph
- Only draws rings for SARF variables that the event actually changed
- For relationship-only events (no S/A/F changes), highlights the vertical relationship line instead
- The ring always follows the single selected event

## Event List

### Structure
- Events are grouped under collapsible cluster headers
- Each cluster header shows: title, date range, event count, expand/collapse indicator
- Events not belonging to any cluster are hidden when cluster view is enabled

### Event Delegate
Each event row shows:
- Timeline line (vertical connector)
- Event symbol based on type:
  - Life events: Filled circle
  - Death events: Gray square
  - Shift events: Stacked SARF symbols for changed variables
- Date and description
- "Who" attribution (which person the event is about)

### Selection Behavior
- **All events**: Clicking selects the event (shows graph ring + highlighted background)
- **Expandable events**: Also expands the event to show detail fields
- **Non-expandable events**: Selects without expanding (all fields already visible at normal height)

An event is expandable if it has content that requires more vertical space:
- Relationship data AND is a shift event, OR
- Relationship triangles, OR
- Notes

### Swipe Actions
- **Swipe right**: Reveals "Edit" action
- **Swipe left**: Reveals "Delete" action

## Interaction Behaviors

### Cluster Bar Click (Overview Mode)
1. Captures bar position for animation origin
2. Collapses all cluster headers in the event list
3. Scrolls event list to show the focused cluster's header
4. Expands only the focused cluster's event list section
5. Animates hero graph from bar position to full width
6. Selects the first event in the cluster (shows graph ring on it)

### Hero Graph Click (Focused Mode)
1. Calculates click position in graph coordinates
2. Builds list of visible dots (only where events changed that variable)
3. Finds nearest dot using 2D Euclidean distance
4. If within 40px threshold, selects that event (scrolls list to it and expands if expandable)

### Event List Click
1. Selects the clicked event (shows graph ring + highlighted background)
2. If expandable: toggles expansion state (expand if collapsed, collapse if expanded)
3. If non-expandable: only selects, no expansion needed
4. Collapses previously expanded event when expanding a new one (only one expanded at a time)

### Pinch/Zoom (Hero Graph)
- Pinch gesture zooms the focused graph (1x to 20x)
- Pan gesture scrolls horizontally when zoomed
- Scroll wheel also pans horizontally

## Selection Model

Two distinct concepts govern event focus:

### selectedEvent
- The single event that has user focus
- Shows a **focus ring** around its dot(s) on the graph
- Shows a **different background color** in the event list
- Only one event can be selected at a time
- Clicking any event in the list or on the graph sets this

### expandedEvent
- The event list item showing expanded height to display all detail fields
- Pertains **only to the event list**, not the graph
- Only events with expandable content can be expanded (those with relationship data, triangles, or notes)

### Relationship Between Them
- When `expandedEvent >= 0`, it must equal `selectedEvent` (you can only expand the selected event)
- `selectedEvent` may exist without `expandedEvent` (non-expandable events can be selected)
- When selecting an event without expandable content, it becomes selected (gets ring + background) but not expanded
- The **background color** in the event list follows `selectedEvent`, not `expandedEvent`

### Code Implementation
The graph ring logic uses:
```
activeIdx = expandedEvent >= 0 ? expandedEvent : selectedEvent
```
This means: if an event is expanded, the ring follows it; otherwise the ring follows the selected event.

## State Properties

| Property | Type | Purpose |
|----------|------|---------|
| `selectedEvent` | int | Index of selected event with graph ring and highlighted background (-1 if none) |
| `expandedEvent` | int | Index of expanded event in list showing detail fields (-1 if none) |
| `focusedClusterIndex` | int | Index of focused cluster (-1 in overview) |
| `collapsedClusters` | object | Map of clusterId -> collapsed state |
| `animProgress` | real | Animation progress 0-1 for focus transitions |
| `focusedZoom` | real | Current zoom level in focused mode |
| `focusedScrollX` | real | Horizontal scroll offset in focused mode |

## Signals

| Signal | Parameters | Purpose |
|--------|------------|---------|
| `addEventRequested` | none | User wants to add a new event |
| `editEventRequested` | eventId: int | User swiped to edit an event |
| `deleteEventRequested` | eventId: int | User swiped to delete an event |

## Key Files

| File | Purpose |
|------|---------|
| `pkdiagram/resources/qml/Personal/LearnView.qml` | Main view implementation |
| `pkdiagram/personal/sarfgraphmodel.py` | Python model providing event/cumulative data |
| `pkdiagram/personal/clustermodel.py` | Python model for cluster detection and data |

## Known Constraints

1. **Event list scrolling**: When focusing a cluster, the list scrolls after a 700ms delay to allow layout to settle
2. **Cluster detection**: Clusters are AI-detected asynchronously; the view shows a loading state during detection
3. **Dark/light mode**: All colors adapt via `util.IS_UI_DARK_MODE`
4. **Minimum bar width**: Cluster bars are at least 30px wide to ensure tappability

## Recent Changes

### 2026-01-31: Relationship Line Click Detection
- **Issue**: Clicking on the vertical blue relationship event lines in the graph didn't select those events
- **Fix**: Added relationship line click detection in hero graph click handler - checks X distance to relationship lines (threshold: 20px)
- **Priority**: Dots are checked first (smaller click target), then relationship lines as fallback (can click anywhere along line height)
- **Impact**: Clicking anywhere on a relationship vertical line now selects that event

### 2026-01-31: Animated Event List Scroll
- **Issue**: When clicking an event dot in the hero graph, the event list jumped instantly without animation, making it hard to follow
- **Fix**: Replaced `positionViewAtIndex` with `eventScrollAnimation` (350ms OutCubic) and added `calculateEventY()` function to compute target scroll position
- **Impact**: Event list now smoothly animates to the selected event when clicking graph elements

### 2026-01-31: Reduced Collapsed Event Height
- **Issue**: Collapsed events had wasted vertical space (110px), showing fewer events on screen
- **Fix**: Reduced `collapsedEventHeight` from 110px to 76px (close to cluster header visual height of 76px)
- **Constants**: Added root-level constants `collapsedEventHeight: 76`, `expandedEventHeight: 200`, `clusterHeaderHeight: 84`
- **Impact**: More events visible on screen, denser information display

### 2026-01-31: Expanded Content Visibility Fix
- **Issue**: Notes and other expanded content wouldn't display when expanding an event - the expanded area was empty
- **Root cause**: QML Column's `implicitHeight` wasn't updating when children became visible after the parent visibility changed. The parent Item wrapper had `height: expandedCol.implicitHeight` which remained 0.
- **Fix**: Two-part fix:
  1. Changed parent Item's visibility from `visible: height > 0` to `visible: expandedEvent === index` to break circular dependency
  2. Set Column's `height: childrenRect.height` explicitly since `implicitHeight` is read-only and wasn't recalculating
- **Impact**: Expanded content (notes, relationship info, triangles) now displays correctly

### 2026-01-31: Graph Click Expansion Fix
- **Issue**: Clicking an event dot on the hero graph always expanded the event, even for non-expandable events
- **Fix**: `scrollToEventThenSelect` now uses `isEventExpandable()` helper to check before expanding
- **Impact**: Graph clicks select non-expandable events without expanding; expandable events still expand

### 2026-01-31: Selection Background Fix
- **Issue**: Non-expandable events showed no background highlight when selected
- **Fix**: Event list background color now follows `selectedEvent` instead of `expandedEvent`
- **Impact**: All selected events show highlighted background, regardless of expandability

### 2026-01-31: Per-Event Dot Drawing Fix
- **Issue**: Canvas was drawing dots at every event position for any variable that changed somewhere in the cluster
- **Fix**: Dots now only appear where the specific event changed that specific variable
- **Impact**: Click detection now matches visual dots; users can only click on dots that actually exist
