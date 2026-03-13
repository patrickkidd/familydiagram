"""
Compare corrected .fd layouts against the algorithm's output.

Usage:
    uv run python familydiagram/bin/fd_compare.py [CASE ...]

    CASE — one or more case name substrings (e.g. "Peyton" "Karla")
           if omitted, compares all files in ~/Desktop/fd_corrections/
           that differ from ~/Desktop/fd_algorithm/

Reads from:
  ~/Desktop/fd_algorithm/    — algorithm output snapshot (never edited)
  ~/Desktop/fd_corrections/  — corrected by Patrick

Reports per-person movements so the algorithm can be improved.
"""

import argparse
import math
import os
import pickle

import PyQt5.sip  # noqa: F401

ALGO_DIR = os.path.expanduser("~/Desktop/fd_algorithm")
CORR_DIR = os.path.expanduser("~/Desktop/fd_corrections")

SIZE_PX = {1: 8, 2: 16, 3: 40, 4: 80, 5: 125}
GEN_GAP = 312  # approximate, for categorising Y-level changes


def _load(fd_path):
    """Return {pid: (x, y)}, {pid: name}, {pid: person_dict}.

    Handles both old format (items list with kind field) and new format
    (separate people + pair_bonds lists).
    """
    with open(os.path.join(fd_path, "diagram.pickle"), "rb") as f:
        data = pickle.load(f)

    # New format: separate people / pair_bonds lists
    if "people" in data:
        raw_persons = data.get("people", [])
        raw_marriages = {m["id"]: m for m in data.get("pair_bonds", [])}
    else:
        raw_persons = [i for i in data.get("items", []) if i.get("kind") == "Person"]
        raw_marriages = {i["id"]: i for i in data.get("items", []) if i.get("kind") == "Marriage"}

    pos, names, persons = {}, {}, {}
    for item in raw_persons:
        pid = item["id"]
        p = item.get("itemPos")
        if p:
            pos[pid] = (p.x(), p.y())
        names[pid] = item.get("name") or ""
        child_of = item.get("childOf") or {}
        parent_mid = (
            child_of.get("parents") if isinstance(child_of, dict) else None
        ) or item.get("parents")
        pa = pb = None
        if parent_mid and parent_mid in raw_marriages:
            m = raw_marriages[parent_mid]
            pa, pb = m.get("person_a"), m.get("person_b")
        partners = []
        for mid in item.get("marriages") or []:
            if mid in raw_marriages:
                m = raw_marriages[mid]
                other = m.get("person_b") if m.get("person_a") == pid else m.get("person_a")
                if other:
                    partners.append(other)
        persons[pid] = {
            "id": pid,
            "name": names[pid],
            "gender": item.get("gender", ""),
            "size": item.get("size", 5),
            "partners": partners,
            "parent_a": pa,
            "parent_b": pb,
        }
    return pos, names, persons


def _normalize(pos_dict):
    """Shift so min-x = 0, min-y = 0."""
    if not pos_dict:
        return pos_dict
    ox = min(v[0] for v in pos_dict.values())
    oy = min(v[1] for v in pos_dict.values())
    return {pid: (x - ox, y - oy) for pid, (x, y) in pos_dict.items()}


def _dist(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _ygen(y):
    """Approximate generation number from y coordinate."""
    return round(y / GEN_GAP)


def compare_case(case_name):
    algo_fd = os.path.join(ALGO_DIR, case_name)
    corr_fd = os.path.join(CORR_DIR, case_name)

    if not os.path.isdir(algo_fd) or not os.path.isdir(corr_fd):
        return None

    algo_pos, _, persons = _load(algo_fd)
    corr_pos, names, _ = _load(corr_fd)

    common = set(algo_pos) & set(corr_pos)
    if not common:
        return None

    algo_n = _normalize({k: algo_pos[k] for k in common})
    corr_n = _normalize({k: corr_pos[k] for k in common})

    has_parents = {pid for pid in common if persons[pid].get("parent_a") or persons[pid].get("parent_b")}
    root_ids = common - has_parents

    movements = []
    for pid in common:
        dx = corr_n[pid][0] - algo_n[pid][0]
        dy = corr_n[pid][1] - algo_n[pid][1]
        d = _dist(corr_n[pid], algo_n[pid])
        if d < 20:  # ignore micro-nudges
            continue
        p = persons[pid]
        is_root = pid in root_ids
        n_partners = len(p.get("partners") or [])
        cross_family = (
            n_partners > 0
            and any(
                (persons.get(q, {}).get("parent_a") or persons.get(q, {}).get("parent_b"))
                != (p.get("parent_a") or p.get("parent_b"))
                for q in (p.get("partners") or [])
                if q in persons
            )
        )
        gen_shift = _ygen(corr_n[pid][1]) - _ygen(algo_n[pid][1])
        movements.append({
            "pid": pid,
            "name": names.get(pid, ""),
            "dist": d,
            "dx": dx,
            "dy": dy,
            "gen_shift": gen_shift,
            "is_root": is_root,
            "n_partners": n_partners,
            "cross_family": cross_family,
        })

    if not movements:
        return None

    return {
        "case": case_name.replace(".fd", ""),
        "n_people": len(common),
        "n_moved": len(movements),
        "mean_dist": sum(m["dist"] for m in movements) / len(movements),
        "movements": sorted(movements, key=lambda m: -m["dist"]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", nargs="*", help="Case name substrings")
    args = parser.parse_args()

    all_cases = sorted(
        n for n in os.listdir(CORR_DIR)
        if n.endswith(".fd") and os.path.isdir(os.path.join(CORR_DIR, n))
    )
    if args.cases:
        all_cases = [c for c in all_cases if any(s.lower() in c.lower() for s in args.cases)]

    results = [r for c in all_cases if (r := compare_case(c)) is not None]

    if not results:
        print("No differences found — nothing corrected yet, or case names don't match.")
        return

    # Summary
    print(f"\n{'Case':<35} {'Moved':>6} {'MeanΔ':>7}")
    print("-" * 52)
    for r in sorted(results, key=lambda x: -x["mean_dist"]):
        print(f"  {r['case']:<33} {r['n_moved']:>6} {r['mean_dist']:>7.0f}px")

    # Pattern analysis
    all_moves = [m for r in results for m in r["movements"]]
    if not all_moves:
        return

    gen_shifts = [m["gen_shift"] for m in all_moves if m["gen_shift"] != 0]
    if gen_shifts:
        up = sum(1 for g in gen_shifts if g < 0)
        down = sum(1 for g in gen_shifts if g > 0)
        print(f"\nGeneration-level shifts: {up} moved up, {down} moved down")
        if up + down > 0:
            avg = sum(gen_shifts) / len(gen_shifts)
            print(f"  Average gen shift: {avg:+.2f}  (negative = algorithm placed too deep)")

    cross = [m for m in all_moves if m["cross_family"]]
    roots = [m for m in all_moves if m["is_root"]]
    print(f"\nMoved cross-family people: {len(cross)}/{len(all_moves)}")
    print(f"Moved roots:               {len(roots)}/{len(all_moves)}")

    # Per-case detail
    print("\n=== Per-case detail ===")
    for r in sorted(results, key=lambda x: -x["mean_dist"]):
        print(f"\n{r['case']}  ({r['n_moved']} moved, mean={r['mean_dist']:.0f}px)")
        for m in r["movements"][:8]:
            tag = []
            if m["is_root"]:
                tag.append("root")
            if m["cross_family"]:
                tag.append("cross-fam")
            if m["gen_shift"]:
                tag.append(f"gen{m['gen_shift']:+d}")
            print(
                f"  {m['pid']:>4}: {m['name']!r:<15} "
                f"Δ={m['dist']:.0f}px  dx={m['dx']:+.0f}  dy={m['dy']:+.0f}"
                + (f"  [{', '.join(tag)}]" if tag else "")
            )


if __name__ == "__main__":
    main()
