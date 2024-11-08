import pytest

import os.path
import json

from pkdiagram.extras import actions_2_appcast, OS


@pytest.mark.no_gui
@pytest.mark.parametrize("_os", [OS.Windows, OS.MacOS])
def test_actions_2_appcast(snapshot, data_root, _os):
    with open(os.path.join(data_root, "github_releases.json"), "r") as f:
        releases = json.load(f)

    pretty_xml = actions_2_appcast(_os, releases, "patrickidd", "familydiagram")
    print(pretty_xml)
    snapshot.assert_match(pretty_xml)
