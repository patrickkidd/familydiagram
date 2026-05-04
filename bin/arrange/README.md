# Auto-Arrange Dev Workflow

Tools for developing, testing, and tuning the deterministic Bowen layout algorithm that ships in `btcopilot.arrange`.

**Production code lives in `btcopilot/btcopilot/arrange/` (layout.py + refine.py).** The scripts in this folder are dev/training-only — they read clinical case data from your local iCloud, run the algorithm, and write outputs to `~/Desktop/` for visual review.

## Workspace folders

| Path | Purpose |
|------|---------|
| `~/Library/Mobile Documents/iCloud~com~vedanamedia~familydiagram/Documents/Clinic Cases/` | Source GT — Patrick's manually-arranged clinical case `.fd` files. **PHI — never commit, copy, or expose.** |
| `~/Desktop/fd_algorithm/` | Algorithm output snapshot. Written by `fd_arrange_test.py`. Never edit — it's the snapshot baseline. |
| `~/Desktop/fd_corrections/` | Correction workspace. Auto-synced from `fd_algorithm/` by every test run. Edit cases here in the Pro app to give the algorithm corrective feedback. |
| `/tmp/arranged_html/` | HTML rendering of algorithm output (one HTML per case + index). Useful for browser preview. |

## Scripts

### `fd_arrange_test.py` — run algorithm on every clinic case

Loads each case, strips positions, runs `btcopilot.arrange.layout()`, writes the new `.fd` to `~/Desktop/fd_algorithm/` and renders an HTML preview to `/tmp/arranged_html/`. Auto-syncs `~/Desktop/fd_corrections/` from `fd_algorithm/` so you start each iteration fresh.

```bash
uv run python familydiagram/bin/arrange/fd_arrange_test.py
uv run python familydiagram/bin/arrange/fd_arrange_test.py --case "Smith"   # filter by name substring
uv run python familydiagram/bin/arrange/fd_arrange_test.py --count 5        # first N cases
```

### `fd_fitness.py` — GT-comparison fitness oracle

Single objective number (lower = better) measuring algorithm output vs Patrick's GT positions. Centroid-normalized per-person Euclidean delta + invariant/collision penalties. Use to objectively detect regressions in any algorithm change, and to drive automated parameter search.

```bash
uv run python familydiagram/bin/arrange/fd_fitness.py            # baseline
uv run python familydiagram/bin/arrange/fd_fitness.py --search   # grid search constants
uv run python familydiagram/bin/arrange/fd_fitness.py --case "Smith" --detail   # one case
```

**Caveat (learned 2026-05-03):** GT-distance is a useful regression signal but a poor optimization target — Patrick's GT layouts are loose/inconsistent. Optimizing fitness too hard pushed the algorithm into worse visual states on already-good cases. Use the fitness number as a smoke test, not a north star. Always pair with a visual review of `~/Desktop/fd_algorithm/`.

### `fd_compare.py` — see what corrections moved where

Compares your manual edits in `~/Desktop/fd_corrections/` against the algorithm snapshot in `~/Desktop/fd_algorithm/`. Reports per-person dx/dy, generation shifts, cross-family/root flags. Use to extract systematic patterns from manual corrections.

```bash
uv run python familydiagram/bin/arrange/fd_compare.py            # all corrected cases
uv run python familydiagram/bin/arrange/fd_compare.py "Smith"    # one case
```

### `fd_render_html.py`, `extract_fd_gt.py`

Helpers — HTML rendering of layout output, GT extraction to JSON. Used by the other scripts; rarely invoked directly.

## Iteration loop

1. Edit the algorithm in `btcopilot/btcopilot/arrange/{layout,refine}.py`
2. `uv run python familydiagram/bin/arrange/fd_arrange_test.py` — refresh both Desktop folders
3. `uv run python familydiagram/bin/arrange/fd_fitness.py` — confirm fitness didn't regress
4. Open a few cases from `~/Desktop/fd_algorithm/` in the Pro app — visual sanity check
5. (Optional) Edit specific cases in `~/Desktop/fd_corrections/`, then `fd_compare.py` to surface what changed

## Decision log + open ideas

Full workstream history, decisions D-1 through D-26, MVP context, painter analogy, alternative approaches considered (priority-queue, force-directed, grid grammar), and the GT-comparison fitness function design rationale all live in:

**[familydiagram/doc/plans/2026-05-02--auto-arrange-layout.md](../../doc/plans/2026-05-02--auto-arrange-layout.md)**

Read that doc before making meaningful algorithm changes — it documents what was tried and rejected so you don't burn cycles re-discovering the same dead ends.

## PHI safety

- Real case data lives ONLY in iCloud and `~/Desktop/fd_algorithm/` (your local machine)
- **Never** commit case names, person names, family identifiers, or clinical details to source code, docs, or commit messages — anonymize as Case A / Case B if you need to reference one
- The dev scripts hardcode the iCloud path which contains no patient identifiers (it's a generic folder name)
