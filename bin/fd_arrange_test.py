"""
Auto-arrange test harness.

For each clinical case:
1. Copy .fd to /tmp/arranged/
2. Clear all person positions
3. Apply layout algorithm
4. Write positions back to .fd (for opening in pro app)
5. Generate HTML rendering to /tmp/arranged_html/

Usage:
    uv run python familydiagram/bin/fd_arrange_test.py [--count N] [--case NAME]

Options:
    --count N     Process first N cases (default: all)
    --case NAME   Process only the case matching NAME (substring match)
"""

import argparse
import json
import os
import pickle
import shutil
import sys

import PyQt5.sip  # Required for unpickling QtCore objects
from PyQt5.QtCore import QPointF

sys.path.insert(0, os.path.dirname(__file__))
from fd_layout import layout
from fd_render_html import render_html

CASES_DIR = os.path.expanduser(
    "~/Library/Mobile Documents/iCloud~com~vedanamedia~familydiagram/Documents/Clinic Cases"
)
OUT_FD_DIR = "/tmp/arranged"
OUT_HTML_DIR = "/tmp/arranged_html"
TMP_DIR = "/tmp/fd_arrange_tmp"

SIZE_PX = {1: 8, 2: 16, 3: 40, 4: 80, 5: 125}


def load_fd(src_path):
    name = os.path.basename(src_path)
    tmp = os.path.join(TMP_DIR, name)
    shutil.copytree(src_path, tmp, dirs_exist_ok=True)
    with open(os.path.join(tmp, "diagram.pickle"), "rb") as f:
        return pickle.load(f)


R_SYMBOL_KINDS = {"Conflict", "Cutoff", "Distance", "Fusion", "Inside", "Outside", "Projection", "Reciprocity", "Toward"}


def extract_people(data):
    """Extract people + marriage graph from raw pickle data."""
    items = data.get("items", [])
    persons = {i["id"]: i for i in items if i.get("kind") == "Person"}
    marriages = {i["id"]: i for i in items if i.get("kind") == "Marriage"}

    people = []
    for pid, p in persons.items():
        parent_a = parent_b = None
        child_of = p.get("childOf") or {}
        parent_mid = (
            child_of.get("parents") if isinstance(child_of, dict) else None
        ) or p.get("parents")
        if parent_mid and parent_mid in marriages:
            m = marriages[parent_mid]
            parent_a = m.get("person_a")
            parent_b = m.get("person_b")

        partners = []
        for mid in p.get("marriages") or []:
            if mid in marriages:
                m = marriages[mid]
                other = m.get("person_b") if m.get("person_a") == pid else m.get("person_a")
                if other:
                    partners.append(other)

        people.append({
            "id": pid,
            "name": p.get("name", ""),
            "gender": p.get("gender", ""),
            "size": p.get("size", 5),
            "size_px": SIZE_PX.get(p.get("size", 5), 125),
            "partners": partners,
            "parent_a": parent_a,
            "parent_b": parent_b,
        })
    return people


def extract_r_pairs(data):
    """Return set of frozenset({id_a, id_b}) for couples with relationship symbols."""
    items = data.get("items", [])
    return {
        frozenset([i["person_a"], i["person_b"]])
        for i in items
        if i.get("kind") in R_SYMBOL_KINDS
        and i.get("person_a") is not None
        and i.get("person_b") is not None
    }


def apply_positions(data, positions):
    """Write computed (x, y) positions back into the pickle data."""
    items = data.get("items", [])
    for item in items:
        if item.get("kind") != "Person":
            continue
        pid = item["id"]
        if pid not in positions:
            continue
        x, y = positions[pid]
        item["itemPos"] = QPointF(x, y)
        # Clear alternate position field if present
        if "nonLayerPos" in item:
            item["nonLayerPos"] = QPointF(x, y)
    return data


def save_fd(data, dest_path):
    os.makedirs(dest_path, exist_ok=True)
    pickle_path = os.path.join(dest_path, "diagram.pickle")
    with open(pickle_path, "wb") as f:
        pickle.dump(data, f)
    # Copy the icon if present in tmp
    for fname in ["PKDiagram-Filled.ico", "PKDiagram.ico"]:
        src_icon = os.path.join(TMP_DIR, os.path.basename(dest_path), fname)
        if os.path.exists(src_icon):
            shutil.copy(src_icon, os.path.join(dest_path, fname))


def process_case(fd_path):
    name = os.path.basename(fd_path).replace(".fd", "")
    print(f"  {name}...", end=" ", flush=True)

    data = load_fd(fd_path)
    people = extract_people(data)
    if not people:
        print("skipped (no people)")
        return None

    r_pairs = extract_r_pairs(data)
    positions = layout(people, r_pairs=r_pairs)

    # Build people with positions for HTML rendering
    pos_people = []
    for p in people:
        if p["id"] in positions:
            x, y = positions[p["id"]]
            pos_people.append({**p, "x": x, "y": y})

    # Write .fd with new positions
    out_fd = os.path.join(OUT_FD_DIR, f"{name}.fd")
    apply_positions(data, positions)
    save_fd(data, out_fd)

    # Write HTML rendering
    out_html = os.path.join(OUT_HTML_DIR, f"{name}.html")
    with open(out_html, "w") as f:
        f.write(render_html(pos_people, title=name))

    print(f"{len(people)} people → ok")
    return name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=None)
    parser.add_argument("--case", type=str, default=None)
    args = parser.parse_args()

    os.makedirs(OUT_FD_DIR, exist_ok=True)
    os.makedirs(OUT_HTML_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)

    all_cases = sorted(
        f for f in os.listdir(CASES_DIR)
        if f.endswith(".fd") and not f.endswith("~.fd")
    )

    if args.case:
        all_cases = [f for f in all_cases if args.case.lower() in f.lower()]
    if args.count:
        all_cases = all_cases[: args.count]

    print(f"Processing {len(all_cases)} cases...")
    done = []
    for fname in all_cases:
        result = process_case(os.path.join(CASES_DIR, fname))
        if result:
            done.append(result)

    # Write index.html
    index_path = os.path.join(OUT_HTML_DIR, "index.html")
    links = "\n".join(
        f'<li><a href="{name}.html">{name}</a></li>' for name in done
    )
    with open(index_path, "w") as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Auto-Arrange Test Results</title>
<style>body{{font-family:sans-serif;margin:20px}}li{{margin:4px 0}}</style>
</head>
<body>
<h1>Auto-Arrange Test Results</h1>
<p>{len(done)} diagrams processed</p>
<ul>{links}</ul>
</body>
</html>""")

    print(f"\nHTML renderings: {OUT_HTML_DIR}/index.html")
    print(f"Arranged .fd files: {OUT_FD_DIR}/")
    print(f"\nTo view in pro app: open any .fd file from {OUT_FD_DIR}/")


if __name__ == "__main__":
    main()
