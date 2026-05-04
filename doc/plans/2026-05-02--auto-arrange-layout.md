# Auto-Arrange Layout — Workstream Plan

**Status**: In progress  
**File under development**: `familydiagram/bin/fd_layout.py` (untracked — not yet committed)  
**Algorithm spec**: [btcopilot/doc/FAMILY_DIAGRAM_LAYOUT_ALGORITHM.md](../../btcopilot/doc/FAMILY_DIAGRAM_LAYOUT_ALGORITHM.md)  
**Test harness**: `familydiagram/bin/fd_arrange_test.py` → writes to `/tmp/arranged/` (ephemeral, lost on reboot)  
**Collision checker**: `/tmp/real_collisions.py` (ephemeral — see snippet below)  
**Ground truth**: 49 clinic case `.fd` files in `~/Library/Mobile Documents/iCloud~com~vedanamedia~familydiagram/Documents/Clinic Cases/`

---

## Goal

Given a Family Diagram `.fd` file, compute (x, y) positions for every Person such that:
1. No label-to-symbol or symbol-to-symbol collisions
2. Bowen topology is visually correct (partners adjacent, children below, male left)
3. Horizontal width is compact — close to what a practitioner would produce by hand

The reference practitioner is Patrick. The 49 GT clinic cases are the ground truth.

---

## Review Flow

Every iteration:
1. Run `uv run python familydiagram/bin/fd_arrange_test.py` → regenerates `/tmp/arranged/`
2. Run collision checker (see below) → `REAL (>buffer)` must be 0
3. Patrick opens files from `/tmp/arranged/` in the Pro app and reports specific diagrams that look off
4. Diagnose, fix, repeat

Patrick's feedback loop is the authoritative quality signal. Collision count is a floor, not a ceiling.

---

## Current Algorithm State

### Constants (`fd_layout.py` lines 19–26)

| Constant | Value | Notes |
|----------|-------|-------|
| GEN_GAP_FACTOR | 1.75 | generation gap as multiple of parent symbol height |
| PARTNER_FACTOR | 1.6 | couple center-to-center as multiple of avg size — already tighter than GT childless median (2.18x) |
| SIBLING_GAP_FACTOR | 0.5 | min edge-to-edge gap between siblings |
| SUBTREE_GAP_FACTOR | 0.3 | gap between independent root subtrees (reduced from 1.0) |
| LABEL_CHAR_WIDTH | 0.6 | char width as fraction of font height (35px) |
| LABEL_BUFFER | 20 | acceptable label-symbol overlap before flagging as collision |

### Key Functions

- **`_label_px(p)`**: minimum edge-to-edge distance from p's right symbol edge to the next symbol's left edge, given p's label. Formula: `int(0.2*sz) + int(len(name)*font_px*LABEL_CHAR_WIDTH) + LABEL_BUFFER`
- **`_sibling_gap(by_id, left_id, right_id)`**: min edge-to-edge between siblings; returns `max(size_gap, _label_px(left))`
- **`_subtree_width(by_id, pid, ...)`**: recursive width estimate for a person's subtree. For solo leaves: `sz + max(0, _label_px(p) - LABEL_BUFFER)` (the extension prevents sibling collisions from coupled children whose female partner label extends past the male)
- **`place_couple`**: label-aware minimum enforced here: `label_min = left_sz/2 + _label_px(left) + right_sz/2; spacing = max(spacing, label_min)` — prevents partner label-symbol collisions
- **`_sweep(by_id, positions)`**: post-placement push-right pass. Up to 20 iterations. Each pass: for every same-row pair (left, right), if left's label overlaps right's symbol, push right's entire subtree right by the overlap. Checks ALL right-side persons within label reach, not just adjacent.
- **`_compact(by_id, positions)`**: post-sweep pull-left pass. Up to 20 iterations. Bottom-up (deepest rows first), right-to-left. For each pair, computes both the row-level slack and the available pull across all descendant rows (`_available_pull`), pulls by the minimum of the two. Prevents compaction from creating collisions in child rows.

### Execution order in `layout()`

```
placement → _sweep → _compact → _sweep
```

The second sweep catches any collisions introduced by compaction.

### Collision Metrics (current)

- **0 real collisions** (`REAL (>buffer)`) across all 49 clinic cases
- ~360 within-buffer contacts (expected — compaction intentionally pushes things to the boundary)

---

## GT Calibration Data

Measured from 49 clinic cases:

| Metric | GT value | Algorithm value | Notes |
|--------|----------|-----------------|-------|
| Childless couple c-to-c / avg_sz | median 2.18x (273px) | 1.6x (200px) | Ours is tighter than GT — don't reduce PARTNER_FACTOR |
| Couples w/children c-to-c / avg_sz | median 3.89x (487px) | driven by children span | correct by construction |
| Sibling edge-to-edge / avg_sz | median 0.74x (92px) | min 0.5x (62px) | ours is tighter minimum — compaction targets this minimum |

Key finding: **wideness is not from couple spacing** (ours is already tighter than GT). It comes from SUBTREE_GAP_FACTOR between root clusters and from subtree-width overestimation cascading upward.

---

## Decision Log

| # | Decision | Rationale | Alternative rejected |
|---|----------|-----------|----------------------|
| D-1 | Remove label-aware spacing from `_subtree_width` for coupled persons | Was inflating couple_width by full label width on top of partner spacing, causing cascading wideness (694px extra in Case A — a parent couple with 7 named children) | Keeping it caused every subtree estimate to be too wide |
| D-2 | Keep label-aware spacing in `place_couple` | Mathematically necessary — left partner's label must clear right partner's symbol. Removing it would require the sweep to fix every couple in the diagram | Removing it caused ~45 real collisions in test |
| D-3 | Keep solo leaf extension in `_subtree_width`: `couple_width = sz + max(0, _label_px(p) - LABEL_BUFFER)` | Without it, collisions jumped from 23 to 45 baseline. Root cause: `_sibling_gap` uses left sibling's label, but when a sibling has a coupled partner whose female is to the right, her label extends further than accounted for | Removing it requires the sweep to handle ALL cross-subtree same-row collisions reliably |
| D-4 | Do NOT fix `_sibling_gap` to include partner label | Attempted: changed `_sibling_gap` to use rightmost partner's label instead of just left sibling. Increased adjacent sibling collisions from 11 to 18. Reverted completely | The fix overcorrected |
| D-5 | Add `_sweep` post-placement push-right pass | Reduced real collisions from 23 baseline to 3, then to 0 after tuning. Mirrors Patrick's manual "sweep" approach | Pure placement-time collision avoidance is too conservative and inflates wideness |
| D-6 | Do NOT reduce PARTNER_FACTOR | GT childless median (273px) is already wider than our 200px. Reducing would make ours tighter than GT with no benefit | Reducing to 1.1 was proposed; measurement proved unnecessary |
| D-7 | Reduce SUBTREE_GAP_FACTOR 1.0 → 0.3 | Main driver of wideness for diagrams with multiple root clusters. 125px × N root groups adds up fast | Keeping at 1.0 made multi-root diagrams excessively wide |
| D-8 | Add `_compact` post-sweep pull-left pass | Mirrors Patrick's manual compaction. Handles excess whitespace from `_subtree_width` overestimation. Uses `_available_pull` to limit pull to what descendant rows can accommodate | Naive compact (without `_available_pull`) would pull parent rows and leave children floating too far right in their rows |
| D-9 | Do NOT compare directly against GT positions as a metric | GT spacings are contextual and relative; a fixed ratio metric would optimize toward an average that doesn't reflect any specific diagram. GT is useful for calibrating constants, not as an optimization target | Building a full GT comparison framework was proposed; would consume significant effort for unclear gain |
| D-10 | **Reverse D-9** — build GT-comparison fitness function as Phase 1 | Aggregate delta over 49 GT diagrams DOES surface systematic biases (D-9 underestimated this). Required to objectively compare any future structural change. Becomes the "done" oracle for iterative approaches | Continuing with corrections-only learning is slow and asymmetric (corrections tell what's wrong, not what's right) |
| D-11 | GT diagrams are signal source, not strict ground truth | Patrick's manual layouts are loose, inconsistent, reflect personal preferences. Algorithm is allowed to define a new standard that compromises between manual subtlety and practical automation. Hard requirement is Bowen conventions (chalkboard tradition); GT-similarity is a soft objective | Treating GT as gold-standard targets would over-fit to inconsistencies and waste effort matching variance |
| D-12 | **Painter / iterative local search added as preferred structural option (Option A in plan)** | Patrick's mental model is a painter iteratively massaging pieces in relation to the whole, sometimes returning to the same area, stopping when it intuitively feels "done." Distinct from priority-queue (one-shot) and force-directed (continuous gradient). Maps to simulated annealing / iterative local search with discrete moves. The "intuitive done" maps to fitness-function plateau detection. Decision deferred to Phase 2 — only pursued if Phase 1 (GT fitness + constant tuning) is insufficient | Pursuing structural rework before having a fitness function would mean we can't measure whether it's actually better |
| D-13 | GEN_GAP_FACTOR 1.75 → 2.0 | GT median = 1.95x size-5 height. Corrections data showed 59 people moved down vs 13 up, average +0.78 generations | Stayed at 1.75 — confirmed too tight |
| D-14 | Did NOT raise SIBLING_GAP_FACTOR 0.5 → 0.7 (attempted, reverted) | Cascades through `_subtree_width` via `_sibling_gap`, changing placement geometry. Introduced 4 real collisions. Effect on aesthetic spacing is real but the side-effect on subtree estimation is unsafe. Revisit after Phase 1 fitness function exists | Keeping at 0.5 means compaction may still pull siblings tighter than GT median (0.74x) — acceptable for now |
| D-15 | Built `fd_fitness.py` — GT-comparison fitness function | Phase 1 of recommended approach. Loads each clinic case, runs algorithm, computes per-person centroid-normalized delta vs GT. Aggregates: weighted mean delta + invariant penalty + collision penalty. Single fitness number for objective comparison | Tried D-9 originally (don't compare against GT) — reversed because aggregate signal across 49 cases is robust enough to drive parameter search and verify changes |
| D-16 | Grid search 54 combos: best is GEN=1.75, PRT=1.4, SIB=0.5, SUB=0.3 | Improved baseline 1652.8→1588.5 (4%). Constants near-optimal — confirms further tuning is exhausted. PARTNER_FACTOR=1.4 means tighter couples than GT median (couples are wider in GT, but tightness improves fitness because relative positions match better) | Higher PARTNER_FACTOR/GEN values made fitness worse |
| D-17 | Built `fd_refine.py` — iterative hill-climbing post-pass | Three move types: (1) slide subtree by ±[500,300,150,75,30,10], (2) cluster-compress children toward midpoint at scales [0.95..0.3], (3) recenter couples above their children. Quality function: bbox_width + hard rejection of invariant violations / collisions. Runs after _sweep+_compact+_sweep | Phase 2 of recommended approach. Hill-climbing is the painter analogy in mechanical form |
| D-18 | **Sub-agent investigation** confirmed Patrick's GT routinely tolerates label-symbol overlap | 240/783 same-row pairs in GT have label overlap with adjacent symbol (30.7%). Median overlap 38px, p75 60px, p90 97px. The strict no-overlap rule was the structural cause of "too wide" complaint | Continuing with strict no-overlap meant accepting wide layouts everywhere |
| D-19 | Added `LABEL_OVERLAP_TOLERANCE = 100` constant | Allows up to ~80px label-symbol overlap (between GT's p75 and p90) before pushing or flagging real collision. _label_px now returns `max(0, raw_width - LABEL_OVERLAP_TOLERANCE)`. Improved aggregate fitness 1540 → 1245 (-19%). Case A: 3032 → 1452 (-52%) | TOL=200 gave more improvement (1204) but with 8 real collisions vs 3. TOL=100 better balance |
| D-20 | **Sub-agent investigation** of Case B outlier (21608px mean delta) | Found cross-generation marriage topology: a person is both partner and ancestor of another via a parent-child path. Creates cyclic Y-constraint: descendant must be below ancestor AND equal-Y to ancestor (as partner). Iteration diverged to y=43000+ | Excluding the case would mask similar bugs in other cases with cross-generation marriage topologies |
| D-21 | Skip partner-Y-equalization when one partner is the other's descendant | Added `_is_descendant()` check in `_compute_y_levels`. When detected, preserve INV-4 (children below parents) over INV-2 (partners same Y). Iteration cap also lowered 200→50. Case B: 21608 → 1429 (-93%). Aggregate fitness 1193 → 959 (-19%) | Forcing INV-2 even with cyclic constraints produced absurd Y values (43000+) |
| D-22 | Added `_recenter_children_move` (children-under-parents, inverse of D-17 phase 3) | Phase 4 in refine. Slides the children's collective subtree to align with parents' center. Complements recenter-couples (which moves the couple) when parents are constrained by their own ancestors | Was missing the inverse direction; both directions sometimes wanted |
| D-23 | Added `_swap_siblings_move` (sibling reorder) | Phase 5 in refine. For each parent, tries swapping each pair of adjacent children (and their subtrees). If GT had a different birth-order assumption, this can recover. Skips entangled subtrees (sub1 & sub2 ≠ ∅) | Without it, sibling order from `_sort_children` is locked even when wrong |
| D-24 | Re-tuned LABEL_OVERLAP_TOLERANCE 100 → 80 after adding new moves | New moves changed the optimum because they enable tighter compaction independently of the tolerance. TOL=80 now beats TOL=100 (894 vs 939). Real collisions also dropped 2 → 1 | TOL=100 was best with 3 moves but became sub-optimal with 5 moves |
| D-25 | Added symbol-symbol overlap check to refine quality function | Discovered 2026-05-03: refine's `_quality()` only checked label-symbol overlaps and accepted moves that physically stacked person symbols on top of each other. Cluster-compress at scales 0.4-0.5 was creating these overlaps undetected. Added `_has_symbol_overlap()` returning float('inf') hard reject. Aggregate fitness rose 884 → 1138 because compressing moves were no longer cheating; this reflects the true ceiling | Without this, refine's "improvements" were destroying readability — a metric/visual mismatch |
| D-26 | Built and rejected the Strict Bowen Grid alternative | Built `fd_grid.py` + `fd_grid_test.py` as a defensive pivot: canonical layout grammar with strict generational rows, fixed couple/sibling spacing, no recursive subtree estimation. Two variants: in-laws-on-row-0 vs in-laws-inherit-partner-row. Patrick visual review on 14 A-D cases: "that was so bad I don't see any use for it." Files deleted | Current algorithm is acceptable; grid grammar's hard rules produced layouts that lost too much practical readability |

---

## What Was Tried and Failed

These must not be re-attempted without new information:

| Approach | Outcome | Why it failed |
|----------|---------|---------------|
| Label-aware spacing in `_subtree_width` for couples | Too wide | Double-counts with partner spacing; cascades to grandparent width |
| Fixing `_sibling_gap` to use rightmost partner label | More collisions | Overcorrects — the solo extension already handles this partially |
| Removing solo leaf extension | 45 collisions | `_sibling_gap` doesn't account for female partner labels extending right |
| GT position comparison as optimization metric | Abandoned | Spacings are relative and contextual; median ratio misleads |

---

## Collision Checker Script

The checker at `/tmp/real_collisions.py` is ephemeral. Recreate when needed:

```python
import sys, os, pickle
sys.path.insert(0, 'familydiagram/bin')
import fd_layout, fd_arrange_test as fat

CASES_DIR = "/Users/patrick/Library/Mobile Documents/iCloud~com~vedanamedia~familydiagram/Documents/Clinic Cases"
LABEL_BUFFER = fd_layout.LABEL_BUFFER

def _px(p): return fd_layout.SIZE_PX.get(p.get("size", 5), 125) if p else 125
def _label_px(p): return fd_layout._label_px(p) if p else 0

total_all, total_real = 0, 0
for fd_name in sorted(os.listdir(CASES_DIR)):
    if not fd_name.endswith(".fd"): continue
    path = os.path.join(CASES_DIR, fd_name)
    try:
        people, r_pairs = fat.extract_people(path), fat.extract_r_pairs(path)
    except Exception: continue
    by_id = {p["id"]: p for p in people}
    positions = fd_layout.layout(people, r_pairs)
    rows = {}
    for pid, (x, y) in positions.items():
        rows.setdefault(round(y), []).append(pid)
    t, r = 0, 0
    msgs = []
    for y_row, row in rows.items():
        row.sort(key=lambda p: positions[p][0])
        for i in range(len(row) - 1):
            pid, qid = row[i], row[i+1]
            p, q = by_id.get(pid), by_id.get(qid)
            if not p: continue
            px, qx = positions[pid][0], positions[qid][0]
            label_right = px + _px(p)/2 + _label_px(p) - LABEL_BUFFER
            overlap = label_right - (qx - _px(q)/2)
            if overlap > 0:
                t += 1
                name = p.get("name") or "None"
                qname = q.get("name") or "None"
                if overlap > LABEL_BUFFER:
                    r += 1
                    msgs.append(f"  REAL: {name} label → {qname} sym  ox={overlap:.0f}")
                else:
                    msgs.append(f"  (within-buffer): {name} label → {qname} sym  ox={overlap:.0f}")
    if t:
        print(f"\n{fd_name[:-3]}: total={t} real={r}")
        for m in msgs: print(m)
    total_all += t; total_real += r
print(f"\nTOTAL same-row: {total_all}  REAL (>buffer): {total_real}")
```

---

## MVP Context (CRITICAL)

This feature is **the last major MVP blocker**. The chat-thread-to-diagram pipeline (extract family members from a conversation, save as `.fd`, open in Pro app) requires a usable arrangement to be visually intelligible. Without auto-arrange, the user opens an unreadable jumble.

Implications:
- Cannot pursue every direction in parallel — must be smart and efficient
- "Good enough for MVP" beats "matches GT exactly"
- Phased approach (cheap wins first, structural rework only if needed)

## Quality Bar (Revised)

GT diagrams are **not strict ground truth**. Patrick's manual layouts are loose, inconsistent, and reflect personal preferences. The algorithm is allowed (and likely required) to define a **new standard** that compromises between:
- Subtle quality of fully-manual arrangement
- What's practical to automate

**Hard constraints** (must not violate):
- Bowen conventions originating from the Murray Bowen chalkboard tradition (children below parents, partners adjacent, male left of female by default, no symbol/label collisions, generation-aligned within a nuclear chain)

**Soft objectives** (target distributions from GT statistics):
- Sibling spacing, partner spacing, generation gaps, compactness — calibrated from GT but not strictly matched

This frames GT as **signal source**, not optimization target.

---

## Structural Direction (Pending Decision)

The corrections data (multiple cases with cross-family marriage and large extended families) shows 700–1600px misplacements of entire family clusters. No constant tuning fixes that. Options ranked by fit to Patrick's mental model and MVP feasibility:

### Option A: Painter / Iterative Local Search (Patrick's preferred mental model)

Patrick's analogy: a painter doesn't place each element once — they iteratively massage pieces in relation to the whole, sometimes returning to the same area multiple times, stopping when it intuitively feels "done."

This is distinct from priority-queue (one-shot) and force-directed (continuous gradient). The mechanical equivalent is **simulated annealing / iterative local search with discrete moves**:

- Start from any reasonable initial placement (current algorithm output is fine)
- Repeatedly:
  1. Pick a "piece" (single person, couple, subtree, sibling group)
  2. Try a discrete move: slide left/right, swap with neighbor, reflect, re-anchor under different parent
  3. Evaluate global quality (fitness function)
  4. Accept if quality improves; reject (or accept with decreasing probability) if worse
- Stop when the fitness function plateaus for N iterations OR a max budget is hit

**"Done" criterion** — three candidate stopping rules to combine:
1. No improving move found in last K full passes (plateau)
2. Aggregate quality reached a target threshold (good enough)
3. Iteration cap (compute budget)

The "intuitive done" the painter feels translates to: the fitness function stops finding improvements. Combined with a hard cap, the endless-loop risk Patrick raised is bounded.

**Why this fits the data better than the alternatives**: the corrections show entire clusters in the wrong region. Local search can pick up an entire cluster and try moving it, evaluate, and either keep or revert. Priority-queue placement is one-shot — no "let me try moving this cluster 500px right and see." Force-directed bumps things continuously and can't make discrete jumps over local minima.

**Risks**:
- Move-set design is the hard problem (what counts as a valid "discrete move"?)
- Quality function must be principled or local search optimizes the wrong thing
- Compute cost grows with diagram size

### Option B: Priority-Queue Greedy Placement

Place persons in order of "readiness" (most placed neighbors first). Cross-family marriages resolved while both sides flexible. Deterministic, fast.
Limitation: still one-shot per person. Can't undo a bad early choice without backtracking machinery.

### Option C: Force-Directed Relaxation

Standard graph-drawing technique. Continuous attraction/repulsion forces converge to equilibrium.
Limitation: violates Bowen invariants by default (no notion of "children below parents"); patching this requires constraint penalties that bias the energy landscape and create the same local-minima problems.

### Option D: Stay with Current Algorithm + Constants + Corrections

Cheapest. Likely insufficient for MVP given the structural errors observed. Use only as fallback.

---

## Recommended Phased Approach

**Phase 1 (immediate, low risk)**: Build the GT-comparison fitness function. Use it to:
- Verify any future change is actually better, not just "looks ok on a few diagrams"
- Drive automated parameter search over current constants
- Become the "intuitive done" oracle for any iterative approach later

**Phase 2 (if Phase 1 insufficient for MVP)**: Build Option A (painter / iterative local search) as a refinement layer on top of current algorithm. The current algorithm produces an initial state; local search refines it. Move-set starts simple (slide cluster left/right) and grows as needed.

**Phase 3 (~~last resort~~ TRIED AND REJECTED 2026-05-03)**: Strict Bowen Grid pivot — built (`fd_grid.py` + `fd_grid_test.py`), tested across 14 A-D cases, Patrick rejected on visual review ("that was so bad I don't see any use for it"). Files deleted. Decision logged as D-26.

This sequence respects MVP urgency: each phase has bounded cost, and we stop as soon as quality is acceptable.

---

## Open Problems / Next Priorities

**This PR (2026-05-03)**: ship the deterministic algorithm + wire to Pro app's existing `Arrange Selection` action. Algorithm lives in `btcopilot.arrange` (package), called locally by `DocumentController.onArrangeSelection` — no HTTP roundtrip. Server's old LLM-based `/arrange` endpoint is commented out in `btcopilot/btcopilot/pro/routes.py` for future-improvement reference. Dev tools in `familydiagram/bin/arrange/` (with README).

Next PR(s) — deferred work:

1. **Incremental positioning** (`add_person()`) — Personal app extracts new family members from chat threads incrementally; cannot full-relayout each time. Design approved 2026-05-03: local-place-by-relation with push-aside fallback. Algorithm receives `(existing_positions, new_person, by_id, r_pairs)`, computes one position based on relation to anchors (parent above child, child below couple-midpoint, partner adjacent, sibling next-to), pushes right-side subtree right by overlap amount if slot occupied. Reuses `_sweep` machinery.

2. **Personal app integration trigger points** — three callsites to identify and wire:
   - First save of freshly-extracted family → full `layout()` (clean slate)
   - Person added later to existing diagram → `add_person()` (incremental)
   - The Pro app `Arrange Selection` action (already wired) is the third trigger — user-initiated full layout
   - Personal app cannot import Python directly; will need to re-enable the server `/arrange` endpoint (currently commented out) calling `btcopilot.arrange.layout()` instead of the LLM

3. **isMovable awareness** — current Pro app integration runs `layout()` on the full diagram and only applies positions to selected people. This means non-selected anchors don't constrain the layout — selected people may move into bad positions relative to fixed people. Acceptable for MVP (user can re-arrange) but should be addressed in a follow-up by passing fixed positions as constraints to the algorithm.

4. **Address Case G residual** (worst non-outlier post-overnight) — wide multi-cluster layout, not visually fixed by current algorithm. Investigate when corrections data accumulates.

5. **Hybrid LLM + deterministic** (speculative future improvement) — the commented-out LLM endpoint in `routes.py` is preserved as a reference point. A potential future architecture: LLM picks ordering and side placement, deterministic algorithm computes coordinates. Not on the roadmap; here only so the work isn't lost.

## Open Improvement Ideas (Patrick's Brainstorm — preserve for future consideration)

Captured here so they survive context compaction. These are not commitments; revisit when relevant.

### Idea 1: Personal-app-generated diagrams as alternative GT source

Diagrams created by the Personal app (extract-from-chat-thread feature) have simpler topologies than the manually-built clinical cases. Patrick can produce GT (manually-arranged truth) from those once they exist. Strategy: build a second GT corpus from Personal-app outputs, evaluate algorithm against it separately. May reveal that the algorithm is strong on the actual MVP target distribution even if it struggles on complex clinical cases.

### Idea 2: "Painter intuitive done" — beyond plateau detection

Patrick's mental model is a painter that iteratively massages pieces in relation to the whole and stops when it intuitively feels "done." Current implementation (`fd_refine.py`) maps this to fitness-plateau detection plus a hard iteration cap. The subtlety Patrick noted: a painter doesn't just stop when no improvement is found — they have a holistic, qualitative sense of completion that may include accepting imperfect spots because the overall composition is right. Possible future direction: composite quality function that weights "global balance" (aspect ratio, density distribution) alongside per-element minima.

### Idea 3: Markovian / token-prediction analogy

Patrick's framing: like an LLM predicting the next token from all prior context, the algorithm could predict the next move from the current full diagram state. Each move is informed by everything placed so far. Differs from priority-queue (one-shot per person) and force-directed (continuous gradient). Closest mechanical analog: iterative local search with discrete moves and rich state evaluation (already partly built).

### Idea 4: Design a NEW visual standard the algorithm can actually hit

Patrick: "It is perfectly OK that this process does indeed define a new standard altogether and that that standard is a compromise between what I can do manually to a very subtle level and what is actually practical to automate. The result just has to adhere to the Bowen conventions originating on the chalkboard with Murray Bowen that everyone is used to."

**The generative interpretation** (what Patrick actually meant): invent a canonical visual grammar — a set of mechanical rules the algorithm can produce reliably and that a clinician will read as a correct Bowen diagram, even if it's not as nuanced as Patrick's hand layouts. Examples of what such a standard might prescribe:

- **Strict generational rows** — every person at exactly `row_index × GEN_GAP`, no inter-generation Y variation, even when in-laws would normally be placed at their partner's row. Trade-off: more pair-bond verticals; gain: predictable, readable, easy to compute.
- **Standardized sibling intervals** — fixed center-to-center spacing per generation, no per-person variation based on label width. Trade-off: long names overlap symbols; gain: visually rhythmic siblings.
- **Canonical couple spacing** — fixed per-size constant, regardless of children span. Children are placed in a centered cluster of fixed width, with secondary rows if needed.
- **Symmetric subtree placement** — children always centered under parents, never offset by their own subtree's content.
- **Multi-row sibling groups** — for couples with >N children, stack siblings into multiple rows rather than spreading horizontally (like text wrapping).

These are choices, not derivations. Each one trades some manual subtlety for a property the algorithm can guarantee. The work is to pick the smallest set of rules that produces output a clinician accepts.

**Implementation implication**: the optimization target shifts from "match GT positions" to "produce a layout that follows the chosen grammar exactly while satisfying Bowen invariants." Fitness becomes "rules followed × invariants preserved," not "distance from Patrick's hand layout."

### Idea 5: Patrick's visual evaluation pattern (pre-night)

Pre-night, Patrick separated cases into two qualitative buckets:
- **Acceptable**: 5 cases — small, single-family or simple multi-family, mostly nuclear topology
- **Terrible**: 4 cases — large, multi-cluster, cross-family marriages, very wide horizontally

Post-night, the previously-acceptable cases regressed visually (per Patrick's review on 2026-05-03), while previously-terrible cases improved per fitness. This pattern is the empirical signal that the optimization moved in the wrong direction for already-good cases.

Practical use: if a future evaluation function is built, validate it against this split — it should rate the formerly-acceptable cases as "fine" and not push them in directions that visibly degrade them.

### Idea 6: Hybrid evaluation — only refine when needed

Run the iterative refine layer only when initial layout has detectable problems (real collisions, extreme aspect ratio, very wide bbox relative to person count). Leave already-good simple cases untouched. Heuristic gates avoid the over-optimization that hurt simple cases overnight.

## Overnight Session Summary (2026-05-02 → 2026-05-03)

**Starting fitness**: 1652.8px (mean per-person delta vs GT)  
**Ending fitness**: 884.6px (-46%)  
**MVP target met**: yes (well below 1000px)

Key wins:
1. Built `fd_fitness.py` — objective oracle for any algorithm change
2. Grid search confirmed constants near-optimal (only 4% to gain)
3. Built `fd_refine.py` — iterative hill-climbing post-pass with 5 move types: subtree-slide, cluster-compress, recenter-couples, recenter-children, swap-siblings
4. Sub-agent discovered GT tolerates ~60-100px label-symbol overlap → relaxed strict no-overlap (LABEL_OVERLAP_TOLERANCE=80) → -19% fitness
5. Sub-agent discovered Case B had cross-generation marriage topology causing cyclic Y constraints → fix → -93% on that case, -19% aggregate

Worst-case improvements (mean delta vs GT):
| Case | Before | After | Change |
|------|--------|-------|--------|
| Case B (cyclic-Y) | 24800 | 1443 | -94% |
| Case A (wide grandfamily) | 3134 | 961 | -69% |
| Case G (cross-family marriage) | n/a | 1418 | (new worst non-Case-B) |
| Case D (large multi-gen) | n/a | 669 | (was high) |
| Case F (multi-cluster) | n/a | 863 | (was high) |

Per-case status:
- Median case: 717px (most cases well-arranged)
- p95 case: 1421px
- Worst case: 1894px
- 1 invariant violation (Case B residual), 1 real collision

Files (all untracked):
- `familydiagram/bin/fd_layout.py` — added LABEL_OVERLAP_TOLERANCE, _is_descendant cyclic skip, refine() integration
- `familydiagram/bin/fd_refine.py` — NEW — 5-phase iterative refinement layer
- `familydiagram/bin/fd_fitness.py` — NEW — GT-comparison fitness function
- `familydiagram/bin/fd_arrange_test.py` — modified to sync `~/Desktop/fd_algorithm/` + `fd_corrections/`

Files changed (all untracked):
- `familydiagram/bin/fd_layout.py` — added LABEL_OVERLAP_TOLERANCE, _is_descendant cyclic-skip, _compact, refine integration, new constants
- `familydiagram/bin/fd_refine.py` — NEW — iterative refinement layer
- `familydiagram/bin/fd_fitness.py` — NEW — GT comparison fitness function
- `familydiagram/bin/fd_arrange_test.py` — modified to sync `~/Desktop/fd_algorithm/` + `fd_corrections/`

---

## Watchdog Protocol

**Purpose**: Prevent rabbit holes. The layout problem is highly iterative and easy to spiral on a single constant or formula.

**How to invoke**: At the start of any session working on this file, or after Patrick reports dissatisfaction for the second time in a row, spawn a watchdog sub-agent:

```
Agent({
  subagent_type: "general-purpose",
  prompt: """
You are a watchdog for the fd_layout.py auto-arrange workstream.
Read: familydiagram/doc/plans/auto-arrange-layout.md (full context, decision log, what failed)
Read: familydiagram/bin/fd_layout.py (current implementation)

Your job: evaluate whether the current approach is productive or stuck.

Report (under 150 words):
1. What is the current open problem being worked on?
2. Has this exact problem (or a close variant) been tried before per the decision log?
3. Is there a higher-leverage approach not yet tried?
4. Should we pivot? If so, to what?

Be blunt. Patrick loses context to compaction and needs an outside check.
"""
})
```

**Trigger conditions** (Claude should self-trigger, not wait for Patrick to ask):
- Same root cause has appeared in 3+ consecutive iterations without measurable improvement in collision count or Patrick's visual approval
- A proposed fix was already in the "What Was Tried and Failed" table
- More than 4 back-and-forth exchanges on a single constant value
- Patrick expresses frustration or asks "why is this so hard?"

**Pivot criteria**: If the watchdog identifies a better path, stop the current thread immediately and document the pivot in the decision log before starting the new approach.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-05-02 | Created — captured full workstream history, decision log, GT calibration data, watchdog protocol |
