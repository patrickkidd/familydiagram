# Timeline Vignettes - Vision

## Overview

LLM-detected episode clustering for the Personal app timeline. Events are automatically grouped into clinically meaningful "vignettes" based on temporal proximity and SARF interaction patterns.

## Problem

Dense journal data makes the graphical timeline unusable. Events stack into narrow time ranges, preventing pattern recognition.

## Solution

1. **LLM vignette detection**: Analyze events to identify episode boundaries using SARF theory
2. **Semantic zoom**: Show vignette markers at low zoom, individual events at high zoom
3. **Vignette UI**: Collapsible cards in list view, brackets/shading in timeline view

## Vignette Definition

A vignette is a clinically meaningful episode containing related events. Characteristics:

- **Duration**: 1 day (isolated significant event) to 3 weeks (major life event)
- **Typical size**: 5-15 days
- **Boundary indicator**: 1+ week gap between vignettes
- **Grouping criteria**: Temporal proximity + SARF interaction patterns + narrative arc

### SARF Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| Anxiety Cascade | A↑ → S↑ | Work stress leads to insomnia |
| Triangle Activation | R: triangle → A↑ | Positioning in triangle raises anxiety |
| Conflict-Resolution | R: conflict → R: toward | Fight followed by reconciliation |
| Reciprocal Disturbance | Person A's S↑ → Person B's A↑ | Partner's symptoms trigger other's anxiety |
| Functioning Gain | Stressor → processing → F↑ | Crisis leads to differentiation |
| Work-Family Spillover | Work A↑ → family R changes | Job stress affects marriage |

### Narrative Arc

Vignettes typically follow: Trigger → Escalation → Peak → Processing → Resolution

## Data Model

```python
@dataclass
class Vignette:
    id: str                      # UUID
    title: str                   # Abstract title (no names), e.g., "Work Stress Cascade"
    summary: str                 # 1-2 sentence description
    pattern: str | None          # Primary SARF pattern if detected
    eventIds: list[int]          # Event IDs in this vignette
    startDate: str               # ISO date
    endDate: str                 # ISO date
    dominantVariable: str | None # "S", "A", "R", or "F"
```

## Architecture

```
Scene Events
     │
     ▼
SARFGraphModel (existing)
     │
     ▼
VignetteDetector ──────► LLM API (cloud)
     │                        │
     │                   VignetteCache
     │                        │
     ▼                        ▼
VignetteModel ◄──────── cached results
     │
     ▼
QML Views (timeline + list)
```

### Files

| File | Purpose |
|------|---------|
| `pkdiagram/personal/vignette.py` | Vignette dataclass |
| `pkdiagram/personal/vignettedetector.py` | LLM detection service |
| `pkdiagram/personal/vignettemodel.py` | QObject model for QML |
| `pkdiagram/resources/qml/Personal/VignetteCard.qml` | List view card |

## LLM Prompt Design

Input: Chronological event list with dates, descriptions, SARF codes

Output: JSON array of vignettes

Key prompt elements:
- SARF theory context (S/A/R/F definitions, clinical hypothesis)
- Common SARF patterns with examples
- Vignette sizing guidelines (short/medium/long)
- Narrative arc structure
- Abstract title requirement (no names)

## Caching Strategy

- **Storage**: JSON file in app data directory
- **Cache key**: Hash of event IDs + timestamps + SARF codes
- **Invalidation**: On event add/edit/delete, re-detect affected time window
- **Incremental**: Only re-analyze windows containing changes

## UI Behavior

### Timeline View
- **Low zoom**: Vignette markers replace individual events
- **Medium zoom**: Event dots with vignette bracket/shading connecting them
- **High zoom**: Full event cards with vignette grouping visible

### List View
- Collapsible vignette cards showing title + summary
- Expand to see individual events
- Click vignette → scroll timeline to that range

### Interaction
- Click vignette in either view → highlight in both views
- Semantic zoom snaps to density-appropriate levels

## Implementation Phases

### Phase 1: Core Detection
- [ ] Vignette dataclass
- [ ] VignetteDetector with LLM prompt
- [ ] Basic caching (full re-detect on any change)

### Phase 2: Model Integration
- [ ] VignetteModel QObject
- [ ] Connect to SARFGraphModel
- [ ] Expose to QML

### Phase 3: List UI
- [ ] VignetteCard.qml component
- [ ] Collapsible sections in event list
- [ ] Vignette headers with title/summary

### Phase 4: Timeline UI
- [ ] Vignette brackets/shading
- [ ] Semantic zoom levels
- [ ] Snap-to-density

### Phase 5: Polish
- [ ] Incremental cache invalidation
- [ ] Loading states
- [ ] Error handling

## Constraints

- Cloud LLM only (no offline requirement)
- No manual vignette editing (LLM-only)
- Abstract titles (no person names)
- No export functionality yet

---

**Status**: Ready for implementation
**Created**: 2026-01-16
