import pytest

import os
import os.path
import json
import sys

from pkdiagram.extras import actions_2_appcast, OS


@pytest.mark.no_gui
@pytest.mark.parametrize("_os", [OS.Windows, OS.MacOS])
def test_actions_2_appcast(snapshot, data_root, _os, monkeypatch):
    test_changelog_path = os.path.join(data_root, "test_changelog.md")

    def extract_changelog_stub(version: str) -> str:
        bin_dir = os.path.join(os.path.dirname(__file__), "..", "..", "bin")
        sys.path.insert(0, bin_dir)
        try:
            from extract_changelog import extract_changelog

            return extract_changelog(version, test_changelog_path)
        finally:
            if bin_dir in sys.path:
                sys.path.remove(bin_dir)

    import pkdiagram.extras

    monkeypatch.setattr(
        pkdiagram.extras, "extract_changelog_for_version", extract_changelog_stub
    )

    with open(os.path.join(data_root, "github_releases.json"), "r") as f:
        releases = json.load(f)

    pretty_xml = actions_2_appcast(
        _os, releases, "patrickidd", "familydiagram", prerelease=True
    )
    print(pretty_xml)
    snapshot.assert_match(pretty_xml)
