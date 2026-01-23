# Timeline Vignettes - Brainstorming

## Problem Statement

The graphical timeline in the Personal app is unusable with dense data. Imported journal data clusters events into narrow time ranges (e.g., one year), causing visual stacking that makes the timeline unreadable.

**Observed behavior**: All events stack up into a couple of years, making the timeline useless for pattern recognition.

**Domain insight**: Events naturally cluster into "vignettes" - episodes spanning a series of days with gaps in between. These episodes represent clinically meaningful sequences of SARF variable interactions.

## Refined Requirements (from Patrick)

### Keep
- **Semantic zoom**: Cards at high zoom, dots at medium zoom, aggregate markers at low zoom
- **Snap-to-density**: Zoom automatically jumps to useful levels based on event density
- **LLM-detected vignettes**: AI analyzes events to identify episode boundaries
- **SARF semantics**: Clustering must understand how S, A, R, F interact in Bowen theory
- **Caching**: Cache LLM results, invalidate on new/edited events
- **All UI for clusters**:
  - Visual brackets or background shading connecting events
  - Collapsible vignette summary cards
  - Timeline shows episode markers at low zoom
  - Clickable in both timeline and list views

### Reject
- Embeddings-based clustering (events cluster by time more than semantics)
- Swimlanes (want all variables on same graph space)
- Event compression (need to understand SARF semantics first)

## Core Feature: LLM Vignette Detection

### Clinical Context

The SARF model tracks four variables:
- **S (Symptom)**: Physical/emotional symptom worsening (up) or improving (down)
- **A (Anxiety)**: Anxiety level changes - "infectious" between people
- **R (Relationship)**: Mechanisms like Conflict, Distance, Overfunctioning, Inside/Outside triangles
- **F (Functioning)**: The clinical independent variable - toward solid self (up) or pseudo-self (down)

**Clinical hypothesis**: "S is modulated by R via A, and F is the clinical independent variable"

This means vignettes should capture:
- A↑ events followed by S↑ events (anxiety driving symptoms)
- R changes (conflict, distance shifts) correlating with A/S changes
- F changes that precede or follow system shifts
- Triangle dynamics where anxiety moves through the family system

### Vignette Detection Approach

**Input**: List of events with timestamps and SARF codes

**LLM Task**: Identify episode boundaries based on:
1. Temporal clustering (events within N days)
2. SARF interaction patterns (A→S cascades, R shifts, F changes)
3. Narrative coherence (events that "go together" clinically)

**Output**: List of vignettes, each containing:
- `id`: Unique identifier
- `title`: Brief descriptive title (LLM-generated)
- `summary`: 1-2 sentence summary of the episode
- `eventIds`: List of event IDs in this vignette
- `startDate`, `endDate`: Time bounds
- `dominantVariable`: Which SARF variable is most prominent (S, A, R, or F)
- `pattern`: Optional clinical pattern label (e.g., "anxiety cascade", "functioning shift")

### Prompt Design Considerations

The LLM needs to understand:
1. SARF variable interactions per Bowen theory
2. What makes events "clinically related" vs "just close in time"
3. How to title/summarize vignettes meaningfully

**Example prompt structure**:
```
You are analyzing a family therapy case timeline to identify clinically meaningful episodes (vignettes).

SARF Theory Context:
- S (Symptom): Physical/emotional dysfunction (sleep, mood, physical illness) - up=worsening, down=improving
- A (Anxiety): Reactivity levels, "infectious" between people - up=more reactive
- R (Relationship): Patterns like conflict, distance, toward, triangles (inside/outside positions)
- F (Functioning): Differentiation of self - up=toward solid self, down=toward pseudo-self

Clinical Hypothesis: "S is modulated by R via A, and F is the clinical independent variable"

Common SARF Patterns:
- Anxiety Cascade: A↑ → S↑ (anxiety leads to sleep/physical symptoms)
- Triangle Activation: R: triangle → A↑ (positioning in triangles raises anxiety)
- Conflict-Resolution Arc: R: conflict → processing → R: toward
- Reciprocal Disturbance: One person's A/S triggers partner's A/S
- Functioning Gain: Stressor → emotional processing → F↑

Events (chronological):
[Event list with dates, descriptions, SARF codes]

Task: Identify episode boundaries. Events belong in the same vignette when they:
1. Occur within a short time period (typically 1-15 days, up to 3 weeks for major life events)
2. Show SARF interaction patterns (cascades, reciprocal effects)
3. Involve the same relational dynamics or stressor
4. Form a narrative arc (trigger → escalation → peak → processing → resolution)

Vignette sizing:
- Short (1-6 days): Single incident or brief cascade
- Medium (1-2 weeks): Conflict-resolution arc
- Long (2-3 weeks): Major life event with processing
- Isolated events (1 day) can be their own vignette if significant

Return JSON array of vignettes with abstract titles (no names)...
```

### Caching Strategy

**Storage**: Local SQLite or JSON file in app data directory

**Cache key**: Hash of event IDs + timestamps + SARF codes

**Invalidation**:
- New event added → Re-analyze affected time window only
- Event edited → Re-analyze vignette containing that event + adjacent vignettes
- Event deleted → Re-analyze adjacent vignettes

**Incremental updates**: For large journals, don't re-analyze everything. Use windowed analysis with overlap to catch cross-boundary episodes.

## Timeline Improvements

### Semantic Zoom Levels

| Zoom Level | Display | Interaction |
|------------|---------|-------------|
| Low (years) | Vignette markers only | Click → zoom to vignette |
| Medium (months) | Event dots with vignette brackets | Hover → tooltip, click → select |
| High (days) | Full event cards | Expand/collapse, full interaction |

### Snap-to-Density

Auto-detect useful zoom levels based on event density:
1. Calculate events per time unit at each potential zoom level
2. Find levels where density is "readable" (not too sparse, not too crowded)
3. Zoom snaps to these levels when user zooms

### Vignette UI Elements

**Timeline view**:
- Horizontal bracket or background shading connecting vignette events
- Vignette marker at low zoom (replaces individual events)
- Color-coded by dominant SARF variable

**List view**:
- Collapsible vignette cards showing summary
- Expand to see individual events
- Visual indicator of SARF pattern (icons or color)

**Both views**:
- Click vignette → highlight/scroll to it in the other view
- Sync selection between timeline and list

## Technical Architecture

### New Files

```
familydiagram/pkdiagram/personal/
├── vignettemodel.py          # QObject model for vignettes
├── vignettedetector.py       # LLM vignette detection service
└── vignettecache.py          # Caching layer

familydiagram/pkdiagram/resources/qml/Personal/
├── VignetteCard.qml          # Collapsible vignette card component
└── VignetteBracket.qml       # Timeline bracket visualization
```

### Data Flow

```
Scene Events
     │
     ▼
SARFGraphModel (existing)
     │
     ├── events: list[dict]
     └── cumulative: list[dict]
     │
     ▼
VignetteDetector
     │
     ├── LLM API call (with caching)
     └── Returns: list[Vignette]
     │
     ▼
VignetteModel (new)
     │
     ├── vignettes: QVariantList
     ├── eventToVignette: dict[int, int]  # event_id → vignette_id
     └── selectedVignetteId: int
     │
     ▼
QML Views
     │
     ├── Timeline: VignetteBracket components
     └── List: VignetteCard components
```

### Integration with Existing Code

**SARFGraphModel** (`sarfgraphmodel.py:14`):
- Already builds event data with SARF variables
- Already calculates year range
- Add: Signal when events change to trigger vignette re-detection

**TimelineModel** (`models/timelinemodel.py`):
- Already has event data
- Add: Vignette ID column for grouping

## Challenges and Risks

### Token Limits
Large journals may exceed LLM context windows. Mitigation:
- Batch events into overlapping windows
- Use sliding window analysis
- Merge vignettes that span window boundaries

### Cache Invalidation Complexity
Adding one event could shift multiple vignette boundaries. Mitigation:
- Re-analyze wider window around change
- Accept some redundant analysis for correctness

### LLM Cost
Each vignette detection is an API call. Mitigation:
- Aggressive caching
- Only re-analyze on explicit refresh or significant changes
- Consider local LLM option for privacy/cost

### Clinical Accuracy
LLM may not perfectly understand Bowen theory nuances. Mitigation:
- Detailed prompt with SARF interaction rules
- Allow user to manually adjust vignette boundaries
- Iterate based on clinical feedback

## Decisions (from Patrick)

1. **Vignette granularity**: See data analysis below - typically 5-15 days, up to 3 weeks for major life events
2. **Isolated events**: Own vignette (not grouped with neighbors)
3. **Manual override**: LLM-only for now (manual UI would be complex)
4. **Titles**: Keep abstract (no names)
5. **Pattern labels**: Discover from data (see analysis below)
6. **Offline**: Cloud-only acceptable
7. **Export**: Not needed yet

## Data Analysis: Example Journal

Analyzed `/Users/patrick/Desktop/example_journal.txt` - real journal data spanning May 2025 to Jan 2026.

### Observed Vignette Clusters

| Vignette | Dates | Duration | Key Pattern |
|----------|-------|----------|-------------|
| Race Committee Episode | May 16-31 | ~15 days | A↑ from social conflict, triangle positioning, lingering emotional content |
| Work Stress + Physical | May 29-Jun 4 | ~6 days | Work A↑ → S↑ (allergies, sleep), meditation resolve |
| Connie/Martha Conflict | Jun 29-Jul 3 | ~5 days | R: conflict/triangle → S↑ (Connie sleep) → S↓ resolution |
| Work + Sailing Incident | Jul 16-21 | ~6 days | Work A↑ → couple conflict → triangling |
| Airport Triangle | Aug 10 | 1 day | Rich interlocking triangles (isolated but significant) |
| Relocation News | Aug 18 | 1 day | Major A↑/S↑ stressor (isolated) |
| Charlie Kirk Death | Sep 10 | 1 day | Shock event (isolated) |
| Cold/Travel | Sep 23-29 | ~6 days | S fluctuation during travel |
| IVF Cycle | Oct 20-Nov 11 | ~22 days | Major life event arc: start → complications → failure → processing → F↑ |
| Holiday Deep Work | Dec 27-Jan 3 | ~8 days | A↑ anticipation → S↑/R: distance → emotional processing → R: toward → F↑ differentiation |

### Typical Vignette Size

- **Short**: 1-6 days (single incident or brief cascade)
- **Medium**: 1-2 weeks (conflict → resolution arc)
- **Long**: 2-3 weeks (major life event with processing)

**Gap indicator**: Clear temporal gaps (1+ weeks) between vignettes.

### SARF Patterns Discovered

1. **Anxiety Cascade**: A↑ → S↑ (very common - anxiety leads to sleep/physical symptoms)
2. **Triangle Activation**: R: triangle → A↑ (positioning in triangles raises anxiety)
3. **Conflict-Resolution Arc**: R: conflict → processing → R: toward
4. **Reciprocal Disturbance**: One person's A/S triggers partner's A/S
5. **Functioning Gain**: Stressor → emotional processing → F↑ (vignette often ends with differentiation)
6. **Work-Family Spillover**: Work A↑ cascades into family dynamics

### Key Insight for LLM Prompt

Vignettes often follow a **narrative arc**:
1. **Trigger**: External stressor or relational event
2. **Escalation**: A↑, S↑, R shifts
3. **Peak**: Most intense moment (conflict, emotional incident)
4. **Processing**: Conversation, reflection, meditation
5. **Resolution**: S↓, A↓, or F↑ (not always present)

## Implementation Phases

### Phase 1: Data Model
- [ ] Define Vignette dataclass
- [ ] Create VignetteModel QObject
- [ ] Add vignette caching layer

### Phase 2: LLM Detection
- [ ] Design prompt with SARF context
- [ ] Implement VignetteDetector service
- [ ] Add incremental re-analysis for edits

### Phase 3: Timeline UI
- [ ] Implement semantic zoom levels
- [ ] Add VignetteBracket QML component
- [ ] Implement snap-to-density zoom

### Phase 4: List UI
- [ ] Create VignetteCard QML component
- [ ] Add collapsible vignette sections
- [ ] Sync selection with timeline

### Phase 5: Polish
- [ ] Manual vignette adjustment (if needed)
- [ ] Performance optimization
- [ ] Clinical validation feedback loop

---

**Document Status**: Brainstorming - awaiting Patrick's input on questions before moving to implementation plan.

**Created**: 2026-01-16
