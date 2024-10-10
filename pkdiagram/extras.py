"""
No pkdiagram dependencies allowed here except thirdparty packages
"""

import datetime
import xml.etree.ElementTree as ET
import xml.dom.minidom


def actions_2_appcast(releases: list, repo_owner: str, repo_name: str):
    """Generate the Appcast XML from the GitHub releases."""
    root = ET.Element("rss", version="2.0")
    channel = ET.SubElement(root, "channel")

    title = ET.SubElement(channel, "title")
    title.text = f"{repo_name} Releases"

    link = ET.SubElement(channel, "link")
    link.text = f"https://github.com/{repo_owner}/{repo_name}/releases"

    description = ET.SubElement(channel, "description")
    description.text = f"Latest updates for github.com/{repo_owner}/{repo_name}"

    for release in releases:
        if release["draft"] or release["prerelease"]:
            continue  # Skip drafts and pre-releases

        item = ET.SubElement(channel, "item")

        release_title = ET.SubElement(item, "title")
        release_title.text = release["name"] or release["tag_name"]

        release_link = ET.SubElement(item, "link")
        release_link.text = release["html_url"]

        release_pub_date = ET.SubElement(item, "pubDate")
        pub_date = datetime.datetime.strptime(
            release["published_at"], "%Y-%m-%dT%H:%M:%SZ"
        )
        release_pub_date.text = pub_date.strftime("%a, %d %b %Y %H:%M:%S +0000")

        release_description = ET.SubElement(item, "description")
        release_description.text = release["body"]

        release_enclosure = ET.SubElement(item, "enclosure")
        asset = next(
            (
                a
                for a in release["assets"]
                if a["content_type"] == "application/octet-stream"
            ),
            None,
        )
        if asset:
            release_enclosure.set("url", asset["browser_download_url"])
            release_enclosure.set("length", str(asset["size"]))
            release_enclosure.set("type", "application/octet-stream")

    output = ET.tostring(root, encoding="utf8").decode("utf8")
    dom = xml.dom.minidom.parseString(output)
    pretty_xml = dom.toprettyxml(indent="    ")
    return pretty_xml
