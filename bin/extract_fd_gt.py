"""
Extract arrange-format GT JSON from .fd clinic case files.
Outputs one JSON file per diagram to /tmp/gt/.
"""
import json
import os
import pickle
import shutil

import PyQt5.sip  # Required for unpickling QtCore objects
from PyQt5.QtCore import QPointF

CASES_DIR = os.path.expanduser(
    "~/Library/Mobile Documents/iCloud~com~vedanamedia~familydiagram/Documents/Clinic Cases"
)
OUT_DIR = "/tmp/gt"
TMP_DIR = "/tmp/fd_tmp"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)


def load_fd(path):
    tmp = os.path.join(TMP_DIR, os.path.basename(path))
    shutil.copytree(path, tmp, dirs_exist_ok=True)
    with open(os.path.join(tmp, "diagram.pickle"), "rb") as f:
        return pickle.load(f)


def extract(data):
    items = data.get("items", [])
    persons = {i["id"]: i for i in items if i.get("kind") == "Person"}
    marriages = {i["id"]: i for i in items if i.get("kind") == "Marriage"}

    people = []
    for pid, p in persons.items():
        pos = p.get("itemPos") or p.get("nonLayerPos")
        parent_a = parent_b = None
        child_of = p.get("childOf") or {}
        parent_mid = (child_of.get("parents") if isinstance(child_of, dict) else None) or p.get("parents")
        if parent_mid and parent_mid in marriages:
            m = marriages[parent_mid]
            parent_a = m.get("person_a")
            parent_b = m.get("person_b")

        partners = []
        for mid in (p.get("marriages") or []):
            if mid in marriages:
                m = marriages[mid]
                other = m.get("person_b") if m.get("person_a") == pid else m.get("person_a")
                if other:
                    partners.append(other)

        if pos is None:
            continue
        people.append({
            "id": pid,
            "name": p.get("name", ""),
            "gender": p.get("gender", ""),
            "x": pos.x(),
            "y": pos.y(),
            "partners": partners,
            "parent_a": parent_a,
            "parent_b": parent_b,
        })

    return {"name": data.get("name", ""), "people": people}


results = []
for fname in sorted(os.listdir(CASES_DIR)):
    if not fname.endswith(".fd") or fname.endswith("~.fd"):
        continue
    path = os.path.join(CASES_DIR, fname)
    try:
        data = load_fd(path)
        gt = extract(data)
        out_path = os.path.join(OUT_DIR, fname.replace(".fd", ".json"))
        with open(out_path, "w") as f:
            json.dump(gt, f, indent=2)
        results.append((fname, len(gt["people"]), "ok"))
    except Exception as e:
        results.append((fname, 0, str(e)))

for fname, n, status in results:
    print(f"{fname}: {n} people — {status}")

print(f"\nOutputs in {OUT_DIR}")
