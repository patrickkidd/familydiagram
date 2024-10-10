import pytest

import os.path
import json
import xml.etree.ElementTree as ET
import datetime

from conftest import DATA_ROOT

from pkdiagram.extras import actions_2_appcast


@pytest.mark.no_gui
def test_actions_2_appcast(snapshot):
    with open(os.path.join(DATA_ROOT, "github_releases.json"), "r") as f:
        releases = json.load(f)

    pretty_xml = actions_2_appcast(releases, "patrickidd", "familydiagram")
    print(pretty_xml)
    snapshot.assert_match(pretty_xml)
