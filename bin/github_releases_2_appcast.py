import requests
import sys
import os

import importlib.util

current_dir = os.path.dirname(os.path.abspath(__file__))
extras_path = os.path.join(current_dir, os.path.join("..", "pkdiagram", "extras.py"))

spec = importlib.util.spec_from_file_location("extras", extras_path)
if spec is None:
    raise ImportError(f"Cannot find module at {extras_path}")
extras = importlib.util.module_from_spec(spec)
sys.modules["extras"] = extras
if spec.loader is None:
    raise ImportError(f"Cannot load module at {extras_path}")
spec.loader.exec_module(extras)


releases_json = requests.get(
    "https://api.github.com/repos/patrickkidd/familydiagram/releases"
)
appcast_xml = extras.actions_2_appcast(
    releases_json.json(), "patrickkidd", "familydiagram"
)
print("Appcast xml ------>")
print(appcast_xml)

with open("appcast.xml", "w") as f:
    f.write(appcast_xml)
