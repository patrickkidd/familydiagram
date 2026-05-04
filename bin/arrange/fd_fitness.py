"""
GT-comparison fitness function for the auto-arrange algorithm.

Loads each clinic case's GT positions, runs the current algorithm, computes
per-person delta after normalization, and aggregates into a single fitness
score that can be used to:

1. Objectively compare two algorithm versions
2. Drive grid-search over constants
3. Surface systematic biases (vertical, horizontal, per-role)

Usage:
    uv run python familydiagram/bin/fd_fitness.py
        # baseline: current constants in fd_layout.py

    uv run python familydiagram/bin/fd_fitness.py --search
        # grid-search over GEN_GAP_FACTOR, SUBTREE_GAP_FACTOR, SIBLING_GAP_FACTOR
        # reports best combination

    uv run python familydiagram/bin/fd_fitness.py --case "<case-name>"
        # detail for one case (substring match)

GT diagrams are NOT strict ground truth. Patrick's manual layouts are loose.
The fitness function uses GT statistics as a SIGNAL, not an exact target.
Hard Bowen invariants (children below parents, no collisions) are weighted
heavily; aesthetic deltas are scored softly.
"""

import argparse
import math
import os
import sys
import itertools
import pickle

import PyQt5.sip  # noqa: F401

sys.path.insert(0, os.path.dirname(__file__))
import btcopilot.arrange.layout as fd_layout
import fd_arrange_test as fat

CASES_DIR = os.path.expanduser(
    "~/Library/Mobile Documents/iCloud~com~vedanamedia~familydiagram/Documents/Clinic Cases"
)

SIZE_PX = {1: 8, 2: 16, 3: 40, 4: 80, 5: 125}
LABEL_BUFFER = fd_layout.LABEL_BUFFER

INVARIANT_PENALTY_PX = 500   # one Bowen violation = 500px equivalent delta
COLLISION_PENALTY_PX = 200   # one real label-symbol collision = 200px equivalent delta


def _load_gt_positions(case_path):
    """Return {pid: (x, y)} from the GT clinic case .fd file."""
    pickle_path = os.path.join(case_path, "diagram.pickle")
    with open(pickle_path, "rb") as f:
        data = pickle.load(f)
    items = data.get("items", [])
    pos = {}
    for item in items:
        if item.get("kind") != "Person":
            continue
        pid = item["id"]
        pt = item.get("itemPos") or item.get("nonLayerPos")
        if pt:
            pos[pid] = (pt.x(), pt.y())
    return pos


def _normalize(pos_dict):
    """Translate so centroid is at origin. Compares relative arrangement only."""
    if not pos_dict:
        return pos_dict
    cx = sum(v[0] for v in pos_dict.values()) / len(pos_dict)
    cy = sum(v[1] for v in pos_dict.values()) / len(pos_dict)
    return {pid: (x - cx, y - cy) for pid, (x, y) in pos_dict.items()}


def _check_invariants(people, positions):
    """Return number of hard Bowen invariant violations.

    Currently checks:
    - INV-4: children below parents (child.y > parent.y)
    - INV-2: partners at same Y (within 30px)
    """
    by_id = {p["id"]: p for p in people}
    violations = 0
    for p in people:
        pid = p["id"]
        if pid not in positions:
            continue
        py = positions[pid][1]
        for parent_id in (p.get("parent_a"), p.get("parent_b")):
            if parent_id and parent_id in positions:
                if positions[parent_id][1] >= py:
                    violations += 1
        for partner_id in (p.get("partners") or []):
            if partner_id in positions and partner_id < pid:
                if abs(positions[partner_id][1] - py) > 30:
                    violations += 1
    return violations


def _count_real_collisions(people, positions):
    """Same logic as /tmp/real_collisions.py — overlap > LABEL_BUFFER."""
    by_id = {p["id"]: p for p in people}

    def _px(p):
        return SIZE_PX.get(p.get("size", 5), 125)

    def _label_px(p):
        return fd_layout._label_px(p)

    rows = {}
    for pid, (x, y) in positions.items():
        rows.setdefault(round(y), []).append(pid)
    real = 0
    for row in rows.values():
        row.sort(key=lambda p: positions[p][0])
        for i in range(len(row) - 1):
            pid, qid = row[i], row[i + 1]
            p, q = by_id.get(pid), by_id.get(qid)
            if not p or not q:
                continue
            px, qx = positions[pid][0], positions[qid][0]
            label_right = px + _px(p) / 2 + _label_px(p) - LABEL_BUFFER
            overlap = label_right - (qx - _px(q) / 2)
            if overlap > LABEL_BUFFER:
                real += 1
    return real


def evaluate_case(case_name):
    """Return per-case metrics dict, or None if case unusable."""
    case_path = os.path.join(CASES_DIR, case_name)
    try:
        gt_pos = _load_gt_positions(case_path)
        data = fat.load_fd(case_path)
        people = fat.extract_people(data)
        r_pairs = fat.extract_r_pairs(data)
    except Exception:
        return None
    if not people or not gt_pos:
        return None

    algo_pos = fd_layout.layout(people, r_pairs=r_pairs)
    common = set(gt_pos) & set(algo_pos)
    if not common:
        return None

    gt_n = _normalize({k: gt_pos[k] for k in common})
    algo_n = _normalize({k: algo_pos[k] for k in common})

    deltas = []
    dx_signed, dy_signed = [], []
    for pid in common:
        gx, gy = gt_n[pid]
        ax, ay = algo_n[pid]
        d = math.hypot(ax - gx, ay - gy)
        deltas.append(d)
        dx_signed.append(ax - gx)
        dy_signed.append(ay - gy)

    violations = _check_invariants(people, algo_pos)
    collisions = _count_real_collisions(people, algo_pos)

    return {
        "case": case_name.replace(".fd", ""),
        "n_people": len(common),
        "mean_delta": sum(deltas) / len(deltas),
        "median_delta": sorted(deltas)[len(deltas) // 2],
        "max_delta": max(deltas),
        "p95_delta": sorted(deltas)[int(0.95 * len(deltas))],
        "mean_dx": sum(dx_signed) / len(dx_signed),
        "mean_dy": sum(dy_signed) / len(dy_signed),
        "violations": violations,
        "collisions": collisions,
    }


def aggregate(results):
    """Combine per-case results into a single fitness score + breakdown."""
    if not results:
        return None
    total_people = sum(r["n_people"] for r in results)
    weighted_mean_delta = (
        sum(r["mean_delta"] * r["n_people"] for r in results) / total_people
    )
    total_violations = sum(r["violations"] for r in results)
    total_collisions = sum(r["collisions"] for r in results)

    # Single fitness number (lower is better):
    # weighted-mean delta + violation penalty + collision penalty
    fitness = (
        weighted_mean_delta
        + total_violations * INVARIANT_PENALTY_PX / total_people
        + total_collisions * COLLISION_PENALTY_PX / total_people
    )

    return {
        "n_cases": len(results),
        "total_people": total_people,
        "weighted_mean_delta": weighted_mean_delta,
        "median_case_delta": sorted(r["mean_delta"] for r in results)[len(results) // 2],
        "p95_case_delta": sorted(r["mean_delta"] for r in results)[int(0.95 * len(results))],
        "max_case_delta": max(r["mean_delta"] for r in results),
        "total_violations": total_violations,
        "total_collisions": total_collisions,
        "mean_dx_bias": sum(r["mean_dx"] * r["n_people"] for r in results) / total_people,
        "mean_dy_bias": sum(r["mean_dy"] * r["n_people"] for r in results) / total_people,
        "fitness": fitness,
    }


def score(constants_override=None, case_filter=None, quiet=True):
    """Single entry point for parameter search.

    constants_override: dict of {const_name: value} to monkey-patch into fd_layout.
    Returns aggregate dict (lower 'fitness' is better).
    """
    if constants_override:
        original = {}
        for k, v in constants_override.items():
            original[k] = getattr(fd_layout, k)
            setattr(fd_layout, k, v)

    cases = sorted(
        n for n in os.listdir(CASES_DIR)
        if n.endswith(".fd") and not n.endswith("~.fd")
    )
    if case_filter:
        cases = [c for c in cases if case_filter.lower() in c.lower()]

    results = []
    for case in cases:
        r = evaluate_case(case)
        if r:
            results.append(r)
            if not quiet:
                print(
                    f"  {r['case']:<35} "
                    f"mean={r['mean_delta']:>5.0f}px  "
                    f"max={r['max_delta']:>5.0f}px  "
                    f"viol={r['violations']:>2d}  "
                    f"coll={r['collisions']:>2d}"
                )

    if constants_override:
        for k, v in original.items():
            setattr(fd_layout, k, v)

    return aggregate(results)


def grid_search():
    """Try combinations of key constants; report the best fitness."""
    grid = {
        "GEN_GAP_FACTOR":     [1.75, 2.0, 2.25],
        "SUBTREE_GAP_FACTOR": [0.3, 0.5, 0.7],
        "SIBLING_GAP_FACTOR": [0.5, 0.7],
        "PARTNER_FACTOR":     [1.4, 1.6, 1.8],
    }
    keys = list(grid.keys())
    combos = list(itertools.product(*grid.values()))
    print(f"Grid: {len(combos)} combinations × ~49 cases each")
    print(f"      ({' × '.join(f'{k}={len(v)}' for k, v in grid.items())})")
    print()

    baseline = score()
    print(f"Baseline fitness: {baseline['fitness']:.1f}px")
    print(f"  weighted_mean_delta={baseline['weighted_mean_delta']:.1f}  "
          f"viol={baseline['total_violations']}  coll={baseline['total_collisions']}")
    print()

    best, best_constants = baseline, {k: getattr(fd_layout, k) for k in keys}
    print(f"{'#':>4} {'GEN':>5} {'SUB':>5} {'SIB':>5} {'PRT':>5} {'fitness':>9}")
    for i, combo in enumerate(combos):
        constants = dict(zip(keys, combo))
        r = score(constants_override=constants)
        marker = ""
        if r["fitness"] < best["fitness"]:
            best, best_constants = r, constants
            marker = " ← best"
        print(
            f"{i+1:>4} {combo[0]:>5.2f} {combo[1]:>5.2f} {combo[2]:>5.2f} {combo[3]:>5.2f} "
            f"{r['fitness']:>9.1f}{marker}"
        )

    print()
    print(f"BEST: fitness={best['fitness']:.1f}px")
    for k, v in best_constants.items():
        print(f"  {k} = {v}")
    print(f"  improvement vs baseline: {baseline['fitness'] - best['fitness']:+.1f}px")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", help="Filter to one case (substring match)")
    parser.add_argument("--search", action="store_true", help="Grid-search over constants")
    parser.add_argument("--detail", action="store_true", help="Per-case breakdown")
    args = parser.parse_args()

    if args.search:
        grid_search()
        return

    print("Current constants:")
    for k in ("GEN_GAP_FACTOR", "PARTNER_FACTOR", "SIBLING_GAP_FACTOR", "SUBTREE_GAP_FACTOR"):
        print(f"  {k} = {getattr(fd_layout, k)}")
    print()

    result = score(case_filter=args.case, quiet=not args.detail)
    if not result:
        print("No results.")
        return

    print()
    print(f"Cases evaluated: {result['n_cases']}")
    print(f"Total people:    {result['total_people']}")
    print()
    print(f"Per-person delta (algorithm vs GT, centroid-normalized):")
    print(f"  weighted mean:  {result['weighted_mean_delta']:>6.1f}px")
    print(f"  median case:    {result['median_case_delta']:>6.1f}px")
    print(f"  p95 case:       {result['p95_case_delta']:>6.1f}px")
    print(f"  worst case:     {result['max_case_delta']:>6.1f}px")
    print()
    print(f"Systematic bias (signed mean, after centroid normalization):")
    print(f"  dx (left/right): {result['mean_dx_bias']:+.1f}px")
    print(f"  dy (up/down):    {result['mean_dy_bias']:+.1f}px")
    print()
    print(f"Hard constraints:")
    print(f"  Bowen invariant violations: {result['total_violations']}")
    print(f"  Real collisions:            {result['total_collisions']}")
    print()
    print(f"FITNESS (lower is better): {result['fitness']:.1f}px")
    print(f"  = weighted_mean_delta + ({INVARIANT_PENALTY_PX}/p × violations)"
          f" + ({COLLISION_PENALTY_PX}/p × collisions)")


if __name__ == "__main__":
    main()
