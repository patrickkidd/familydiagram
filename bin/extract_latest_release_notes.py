#!/usr/bin/env python3
"""
Extract the latest release notes from doc/CHANGELOG-RELEASE.txt for use in GitHub releases.
This makes it easy to maintain user-friendly release notes separately from developer commits.
"""

import sys
import re
from pathlib import Path


def extract_latest_release_notes(changelog_path: str) -> tuple[str, str]:
    """
    Extract the latest version and its release notes from CHANGELOG-RELEASE.txt.

    Returns:
        tuple: (version, notes) where notes are formatted for GitHub release body
    """
    content = Path(changelog_path).read_text()

    # Split into sections by version headers (version followed by dashes)
    # Pattern: version number on one line, followed by line of dashes
    # Match both start of string and newline before version
    sections = re.split(r'(?:^|\n)(\d+\.\d+\.\d+[^\n]*)\n-{10,}\n', content, flags=re.MULTILINE)

    if len(sections) < 3:
        print("Error: Could not find version sections in CHANGELOG-RELEASE.txt", file=sys.stderr)
        sys.exit(1)

    # sections[0] is text before first version (usually empty)
    # sections[1] is first version number
    # sections[2] is first version's notes
    version = sections[1].strip()
    notes = sections[2].strip()

    # Split into lines and remove empty lines at start/end
    lines = [line.rstrip() for line in notes.split('\n')]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    # Convert to markdown list format (lines starting with '-' are already bullet points)
    formatted_notes = '\n'.join(lines)

    return version, formatted_notes


def main():
    repo_root = Path(__file__).parent.parent
    changelog_path = repo_root / "doc" / "CHANGELOG-RELEASE.txt"

    if not changelog_path.exists():
        print(f"Error: CHANGELOG file not found at {changelog_path}", file=sys.stderr)
        sys.exit(1)

    version, notes = extract_latest_release_notes(str(changelog_path))

    # Output just the notes (version is already in the GitHub release tag)
    print(notes)


if __name__ == "__main__":
    main()
