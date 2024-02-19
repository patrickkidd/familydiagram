import sys, os
import pickle
from PyQt5 import QtCore, QtGui, sip

with open(sys.argv[1], "rb") as f:
    bdata = f.read()

index = pickle.loads(bdata)

for iScene, entry in enumerate(index):
    num_people = 0
    for item in entry.get("items", []):
        if item["kind"] == "Person":
            num_people += 1

    print(f"Scene: {iScene}")
    print(f"   Persons: {num_people}")
