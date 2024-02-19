import sys, os
import pickle
from PyQt5 import QtCore, QtGui, sip

with open(sys.argv[1], "rb") as f:
    bdata = f.read()

data = pickle.loads(bdata)

num_people = 0
for item in data.get("items", []):
    if item["kind"] == "Person":
        num_people += 1

print(f"Persons: {num_people}")
