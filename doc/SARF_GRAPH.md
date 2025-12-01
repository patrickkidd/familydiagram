# SARF Graph Visualization Feature Plan

## 1. Executive Summary

This document outlines the design for a SARF graph visualization feature that
provides an aesthetic, evaluative view of how the four main SARF variables
(Symptoms, Anxiety, Reactivity, FunctionalLevel) change over time across
timeline events. This visualization aims to help users identify patterns of
reactivity and anxiety overlapping with symptoms in a low-resolution, gut-feel
manner aligned with Bowen theory.

## 2. Core Requirements

### 2.1 Functional Goals
- Provide visual correlation between SARF variables over time
- Support the clinical hypothesis: "S is modulated by R via A, and F is the
  clinical independent variable"
- Offer a qualitative, aesthetic view rather than precise scientific measurement
- Enable pattern recognition at a glance

### 2.2 Technical Integration
- New button with graph icon in right toolbar
- New QAction in main menu (under View menu)
- QmlDrawer implementation following existing patterns
- Should be its own tab OR separate drawer (to be determined)
- Expandable view like timeline for detail
- QML frontend with Python backend for data/logic

### 2.3 Data Characteristics
- **S, A, R variables**: Qualitative shifts ("up", "down", "same")
- **F variable**: RelationshipKind enum (doesn't map directly to up/down but
  indicates shifts)
- Low temporal resolution (gut-feel correlations)
- Subjective interpretation of event nature

## 3. Design Options

### 3.1 Integration Approach Options

#### Option A: Fourth Tab in CaseProperties Drawer
```
CaseProperties.qml
├── Timeline (Tab 0)
├── Settings (Tab 1)
├── Copilot (Tab 2)
└── SARF Graph (Tab 3) ← NEW
```
**Pros:**
- Minimal UI changes
- Reuses existing drawer infrastructure
- Easy tab navigation

**Cons:**
- May feel crowded with 4 tabs
- Limited horizontal space when not expanded

#### Option B: Separate Drawer (Like EventForm)
```
DocumentView
├── CaseProperties (Timeline/Settings/Copilot)
├── EventForm
└── SarfGraphView ← NEW (own drawer)
```
**Pros:**
- Dedicated space for visualization
- Can be shown alongside timeline
- Independent expand/contract control

**Cons:**
- More complex state management
- Need to handle drawer swapping

**❓ Question 1:** Which integration approach do you prefer? Or should we make it
a floating window that can be positioned independently?

### 3.2 Visualization Approach Options

#### Option A: Traditional Line Graph
- Four colored lines (one per variable)
- Time on X-axis, qualitative scale on Y-axis
- Smooth interpolation between points

```
     ↑
  High│   ╱─╲ S (red)
      │  ╱   ╲_╱─╲
  Med │ ╱         ╲ A (blue)
      │╱           ╲
  Low │─────────────→
      └─────────────→ Time
```

#### Option B: Stacked Area Chart
- Shows cumulative effect
- Better for seeing overall "emotional load"
- Each variable fills area with transparency

#### Option C: Heat Map / Color Bands
- Horizontal bands for each variable
- Color intensity represents value
- Time flows left to right

```
S: ████░░░░████████░░░░
A: ░░████████░░░░████░░
R: ██░░░░████░░████░░██
F: ░░████░░░░██░░████░░
   ─────────────────→ Time
```

#### Option D: Circular/Radial Visualization
- Time spirals outward from center
- Variables shown as colored rings
- Good for seeing cycles/patterns

#### Option E: Multi-View Dashboard
- Multiple small graphs in one view
- Each variable gets its own mini-chart
- Side-by-side comparison

**❓ Question 2:** Which visualization style resonates most with your clinical
understanding? Should we prototype multiple views?

### 3.3 Data Processing Approach

#### Option A: Rules-Based Processing
```python
def calculateSarfValues(events):
    # Apply heuristics based on event types
    # Map EventKind to SARF shifts
    # Interpolate between events
```

**Rules Examples:**
- Birth events → F shifts down
- Death events → S, A spike up
- Marriage → F changes, R shifts
- Conflict events → A, R increase

#### Option B: AI-Based Processing
```python
def generateSarfGraph(events):
    # Send event narrative to LLM
    # Get back SARF values with interpretation
    # LLM provides aesthetic/subjective view
```

**Prompt Structure:**
- Event list with descriptions
- Request qualitative SARF values
- Ask for narrative interpretation

#### Option C: Hybrid Approach
- Basic rules for obvious patterns
- AI for nuanced interpretation
- User can toggle between views

**❓ Question 3:** Should we start with rules-based and add AI later? Or go
straight to AI for the subjective/aesthetic quality you mentioned?

## 4. Implementation Questions

### 4.1 Data Source Questions

**❓ Question 4:** Which events should be included in the graph?
- All events on timeline?
- Only events with certain EventKinds?
- Only events for selected person(s)?
- Events within a date range?

**❓ Question 5:** How should we handle events without explicit SARF values?
- Infer from EventKind?
- Use AI to interpret event descriptions?
- Allow manual SARF tagging of events?
- Show gaps in the graph?

### 4.2 Visual Detail Questions

**❓ Question 6:** What time scale should the graph use?
- Absolute dates on X-axis?
- Relative time between events?
- Compressed/expanded based on event density?
- User-adjustable zoom?

**❓ Question 7:** How should we handle the R variable (RelationshipKind)?
- Map to numeric scale (e.g., Conflict=1, Distant=2, Close=3)?
- Show as discrete states with step changes?
- Use different visual representation (not a line)?
- Exclude from main graph, show separately?

### 4.3 Interaction Questions

**❓ Question 8:** What interactions should the graph support?
- Hover to see event details?
- Click to jump to event in timeline?
- Drag to pan through time?
- Pinch/wheel to zoom?
- Select time range for focused view?

**❓ Question 9:** Should the graph update in real-time as events are
added/edited?
- Live updates as timeline changes?
- Manual refresh button?
- Automatic refresh on drawer open?

## 5. Technical Architecture Proposal

### 5.1 File Structure
```
familydiagram/
├── pkdiagram/
│   ├── models/
│   │   └── sarfgraphmodel.py    # Qt model for SARF data
│   ├── views/
│   │   └── sarfgraphview.py     # QmlDrawer wrapper
│   ├── analysis/
│   │   └── sarfanalyzer.py      # Rules/AI processing
│   └── resources/qml/
│       ├── SarfGraphView.qml    # Main view
│       └── PK/
│           ├── LineGraph.qml    # Graph component
│           └── GraphLegend.qml  # Legend component
```

### 5.2 Data Flow
```
Timeline Events → SarfAnalyzer → SarfGraphModel → QML Graph → Visual Display
                       ↑
                  AI Backend
                  (optional)
```

### 5.3 Model Structure
```python
class SarfGraphModel(QObjectHelper):
    # Properties exposed to QML
    sarfDataPoints = Property(list)  # [{time, s, a, r, f}, ...]
    timeRange = Property(tuple)      # (minDate, maxDate)
    interpretation = Property(str)   # AI narrative (optional)
```

## 6. UI/UX Considerations

### 6.1 Color Scheme
**❓ Question 10:** What colors should represent each variable?
- S (Symptoms): Red? Orange?
- A (Anxiety): Blue? Purple?
- R (Reactivity): Green? Yellow?
- F (FunctionalLevel): Gray? Brown?

Should colors have clinical meaning or just be visually distinct?

### 6.2 Graph Aesthetics
- Smooth curves vs sharp lines?
- Grid lines or clean background?
- Show data points or just lines?
- Animation on load/update?

### 6.3 Narrative Integration
If using AI interpretation:
- Where to show narrative text?
- Inline with graph or separate panel?
- Toggle between graph and narrative?
- Export/save interpretation?

## 7. Development Phases

### Phase 1: Basic Infrastructure
- [ ] Create SarfGraphView QML file
- [ ] Add toolbar button and menu action
- [ ] Implement basic drawer/tab integration
- [ ] Create SarfGraphModel with mock data

### Phase 2: Visualization
- [ ] Implement chosen graph type in QML
- [ ] Add basic interactivity (hover, zoom)
- [ ] Connect to real timeline data
- [ ] Implement rules-based SARF calculation

### Phase 3: Enhancement
- [ ] Add AI interpretation (if desired)
- [ ] Implement multiple view options
- [ ] Add export/save functionality
- [ ] Polish animations and transitions

### Phase 4: Integration
- [ ] Connect to event selection in timeline
- [ ] Add settings for graph customization
- [ ] Implement real-time updates
- [ ] Add help/tutorial overlay

## 8. Open Questions for Discussion

1. **Clinical Accuracy**: How important is it that the graph reflects "correct"
   clinical interpretation vs being a useful thinking tool?

2. **Training Data**: If using AI, do you have example cases with "correct" SARF
   graphs we could use for prompting?

3. **User Personas**: Who will use this most - clinicians, clients, or both? How
   does that affect design?

4. **Mobile Experience**: Should the graph work well on mobile (Personal app) or
   optimize for desktop (Pro app)?

5. **Export Needs**: Should users be able to export graphs for
   reports/documentation?

6. **Comparison View**: Should users be able to compare multiple people's SARF
   graphs?

7. **Annotation**: Should users be able to add notes/markers to the graph?

8. **Validation**: How will we know if the visualization is achieving its
   clinical goals?

## 9. Next Steps

Once we clarify the above questions, I recommend:

1. Create a minimal prototype with mock data
2. Test with real timeline data
3. Iterate on visual design based on feedback
4. Add advanced features incrementally

---

**Please review this plan and let me know:**
1. Which design options resonate with you?
2. Answers to the numbered questions (❓)
3. Any aspects I'm misunderstanding about SARF theory or the clinical use case?
4. What would make this most valuable for your users?

This is a living document - let's iterate until we have a clear vision before
implementing.