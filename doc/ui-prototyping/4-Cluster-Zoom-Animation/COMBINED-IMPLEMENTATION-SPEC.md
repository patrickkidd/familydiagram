# Combined Cluster Timeline + Zoom Animation Implementation Spec

This spec combines the approved C9 zoomed-out view with the animated zoom transition to the focused cluster view.

## Part 1: Zoomed-Out View (C9)

**Full spec**: [../3-Cluster-Timeline/C9-IMPLEMENTATION-SPEC.md](../3-Cluster-Timeline/C9-IMPLEMENTATION-SPEC.md)

The zoomed-out view is fully specified in the C9 implementation spec. That spec covers:
- Zoom/pan properties
- Pattern legend
- PinchArea for pinch-to-zoom
- xPosZoomed() function
- Stacked cluster bars (3 rows)
- Drag-to-pan handler
- Scroll indicator and reset button
- Pattern colors

**Do not modify C9 behavior** - it is approved as-is.

---

## Part 2: Zoom Animation Transition

**Status**: Prototyping in progress

**Prototype variants**:
- `1-zoom-anim-A.qml` - Zoom + Crossfade
- `1-zoom-anim-B.qml` - Hero Expansion
- `1-zoom-anim-C.qml` - Slide Reveal

### Pending: User selection of animation variant

Once a variant is approved, this section will be updated with:
- Animation properties and state machine
- Transition timing and easing curves
- Focus/unfocus animation sequences
- Focused view layout and content

---

## Part 3: Focused Cluster View

**Status**: Pending animation selection

The focused view shows:
- Cluster header (title, event count, pattern color)
- Back button to return to overview
- Event list for the cluster
- SARF timeline lines (if applicable)

Layout and behavior TBD based on selected animation variant.

---

## Integration Notes

### State Machine

```
Overview (C9) <---> Focused View
     |                    |
     v                    v
  isFocused=false    isFocused=true
  animProgress=0     animProgress=1
```

### Shared Functions

Both views share:
- `patternColor(pattern)` - returns color for SARF pattern
- `focusCluster(index)` - triggers focus animation
- `clearFocus()` - triggers unfocus animation

### File to Modify

`familydiagram/pkdiagram/resources/qml/Personal/LearnView.qml`
