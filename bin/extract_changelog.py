#!/usr/bin/env python3
import re
import sys


def parse_version(version_str: str) -> tuple[int, int, int, str, int]:
    match = re.match(r"(\d+)\.(\d+)\.(\d+)([ab])?(\d+)?", version_str)
    if not match:
        raise ValueError(f"Invalid version format: {version_str}")

    major = int(match.group(1))
    minor = int(match.group(2))
    micro = int(match.group(3))
    alphabeta = match.group(4) or ""
    suffix = int(match.group(5)) if match.group(5) else 0

    return major, minor, micro, alphabeta, suffix


def get_base_version(version_str: str) -> str:
    major, minor, micro, _, _ = parse_version(version_str)
    return f"{major}.{minor}.{micro}"


def extract_section_content(changelog_content: str, version: str) -> list[str]:
    lines = changelog_content.split("\n")
    in_section = False
    bullets = []

    for line in lines:
        if re.match(rf"^##\s+\[?{re.escape(version)}\]?", line):
            in_section = True
            continue

        if in_section:
            if line.startswith("## "):
                break

            match = re.match(r"^\s*-\s+(.+)$", line)
            if match:
                bullets.append(match.group(1))

    return bullets


def find_beta_versions(changelog_content: str, base_version: str) -> list[str]:
    lines = changelog_content.split("\n")
    versions = []

    for line in lines:
        match = re.match(r"^##\s+\[?(\d+\.\d+\.\d+[ab]\d+)\]?", line)
        if match:
            version = match.group(1)
            if get_base_version(version) == base_version:
                versions.append(version)

    return versions


def extract_changelog(version: str, changelog_path: str = None) -> str:
    if changelog_path is None:
        import os

        script_dir = os.path.dirname(os.path.abspath(__file__))
        changelog_path = os.path.join(script_dir, "..", "CHANGELOG.md")

    with open(changelog_path, "r") as f:
        changelog_content = f.read()

    bullets = extract_section_content(changelog_content, version)

    _, _, _, alphabeta, _ = parse_version(version)

    if not bullets and not alphabeta:
        base_version = get_base_version(version)
        beta_versions = find_beta_versions(changelog_content, base_version)

        for beta_version in beta_versions:
            bullets.extend(extract_section_content(changelog_content, beta_version))

    if not bullets:
        return ""

    html_items = "\n".join(f"  <li>{bullet}</li>" for bullet in bullets)
    return f"<ul>\n{html_items}\n</ul>"


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_changelog.py <version> [changelog_path]")
        sys.exit(1)

    version = sys.argv[1]
    changelog_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        html = extract_changelog(version, changelog_path)
        if html:
            print(html)
        else:
            print(f"No changelog found for version {version}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
