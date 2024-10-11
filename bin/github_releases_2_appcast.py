import requests
import sys
import os

import importlib.util


def import_module_from_file(relative_fpath: str):
    this_path = os.path.dirname(os.path.abspath(__file__))
    relative_fpath = os.path.join(this_path, relative_fpath.replace("/", os.sep))
    spec = importlib.util.spec_from_file_location("extras", relative_fpath)
    if spec is None:
        raise ImportError(f"Cannot find module at {relative_fpath}")
    extras = importlib.util.module_from_spec(spec)
    sys.modules["extras"] = extras
    if spec.loader is None:
        raise ImportError(f"Cannot load module at {relative_fpath}")
    spec.loader.exec_module(extras)
    return extras


extras = import_module_from_file("../pkdiagram/extras.py")
version = import_module_from_file("../pkdiagram/version.py")


releases_json = requests.get(
    "https://api.github.com/repos/patrickkidd/familydiagram/releases"
)

for _os in [extras.OS.Windows, extras.OS.MacOS]:
    appcast_xml = extras.actions_2_appcast(
        _os, releases_json.json(), "patrickkidd", "familydiagram"
    )
    print(f"Appcast XML ({_os}) ------>")
    print(appcast_xml)

    if version.IS_BETA:
        FPATH = (
            "appcast_windows_beta.xml"
            if _os == extras.OS.Windows
            else "appcast_macos_beta.xml"
        )
    else:
        FPATH = (
            "appcast_windows.xml" if _os == extras.OS.Windows else "appcast_macos.xml"
        )

    with open(FPATH, "w") as f:
        f.write(appcast_xml)
