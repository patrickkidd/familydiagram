# FD-319 manual test journeys

Run in the Personal app (pointed at the FD-319 backend) with the Pro app open
on the same diagram for inspection. Re-run after any code change.

## What FD-319 covers (test these)

### J1 — Additive re-extraction, 3 cycles
1. New discussion. Chat 4–6 turns describing a family (you, a parent or two, a
   sibling, a spouse) with ≥1 relationship and ≥1 date.
2. Extract → review → **Accept all**.
   - PASS: accept completes, no error screen; described people/relationships
     appear in the diagram (check in Pro app).
3. Add 2–3 more turns mentioning some already-accepted people **and** 1–2
   genuinely new people. Extract.
   - PASS: only the new people/events are staged; already-accepted people are
     NOT re-proposed as new.
4. Accept all. Repeat steps 3–4 once more.
   - PASS each cycle: only new items added; **no duplicate of a close
     relative** (no second mother/father/spouse); no relationship to a person
     not in the diagram; no error screen.

### J2 — Extract button only when dirty
- After a full Accept, the Extract button is **hidden** (nothing new since the
  cursor).
- Add one chat turn → Extract button **reappears**.
- PASS: button visibility tracks "statements after the last accepted extract".

### J3 — Pro edit survives re-extraction
1. After J1, open the diagram in the Pro app; hand-edit one extracted person
   (rename, add a date).
2. Back in Personal: add a chat turn, Extract, Accept all.
   - PASS: your Pro edit is still there (not regenerated/wiped).

### J4 — No crash on a messy real diagram
- Run J1 on a diagram with many people/relationships and loose phrasing.
  - PASS: every Accept completes; no error screen; opening in Pro shows no
    orphaned/duplicated people.

FAIL (any journey) = error screen on accept, duplicated close relative,
relationship to a nonexistent person, already-accepted people re-staged, or the
Extract button wrong.

## Explicitly NOT FD-319 — do not fail FD-319 on these (tracked in FD-322)

- PDP review sheet is blank/empty when the only changes are updates to
  already-committed people (e.g., setting parents on an existing person).
- "Set existing kids under an existing parent" / re-parenting people who are
  already in the diagram does not take effect.

Both are the FD-322 committed-mutation work (visibility + application),
deferred from FD-319 by decision 2026-05-17.
