"""
No pkdiagram dependencies allowed here except thirdparty packages
"""

import enum
import datetime
import xml.etree.ElementTree as ET
import xml.dom.minidom


class OS(enum.Enum):
    Windows = "windows"
    MacOS = "macos"


def actions_2_appcast(
    os: OS, releases: list, repo_owner: str, repo_name: str, prerelease: bool
):
    """
    Generate the Appcast XML from the GitHub releases.

    <rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle"
        xmlns:dc="http://purl.org/dc/elements/1.1/">
        <channel>
            <title>Family Diagram Beta</title>
            <link>/v0.1/public/sparkle/apps/f8ac3812-6a64-404a-a924-87e9173a694f</link>
            <item>
                <title>Version 2.0.0b4 (2.0.0b4)</title>
                <description>
                    <div>
                        <ul>
                            <li>Fix beta update url</li>
                        </ul>
                    </div>
                </description>
                <pubDate>Wed, 28 Aug 2024 18:47:51 GMT</pubDate>
                <enclosure sparkle:version="2.0.0b4" sparkle:shortVersionString="2.0.0b4"
                    url="https://appcenter-filemanagement-distrib2ede6f06e.azureedge.net/9924a740-ba85-4139-9340-59c348699bef/Family%20Diagram.dmg?sv=2019-07-07&sr=c&sig=E8WgBPLYIV5zPqO%2BPGE%2BHZUT556JcQOQEH3h4wFhRnM%3D&se=2024-10-12T22%3A03%3A03Z&sp=r"
                    length="116526409" type="application/octet-stream"></enclosure>
                <sparkle:minimumSystemVersion />
            </item>
        </channel>
    </rss>

    """
    root = ET.Element(
        "rss",
        version="2.0",
        attrib={
            "xmlns:sparkle": "http://www.andymatuschak.org/xml-namespaces/sparkle",
            "xmlns:dc": "http://purl.org/dc/elements/1.1/",
        },
    )
    channel = ET.SubElement(root, "channel")

    title = ET.SubElement(channel, "title")
    title.text = f"{repo_name} Releases"

    link = ET.SubElement(channel, "link")
    link.text = f"https://github.com/{repo_owner}/{repo_name}"

    for release in releases:
        if release["draft"]:
            return  # Skip drafts

        if release["prerelease"] and not prerelease:
            continue

        item = ET.SubElement(channel, "item")

        title = ET.SubElement(item, "title")
        title.text = release["name"] or release["tag_name"]

        # TODO: This is viewable & useful to the user, should have changelog.
        description = ET.SubElement(item, "description")
        description.text = release["body"]

        pubDate = ET.SubElement(item, "pubDate")
        pubDate.text = datetime.datetime.strptime(
            release["published_at"], "%Y-%m-%dT%H:%M:%SZ"
        ).strftime("%a, %d %b %Y %H:%M:%S +0000")

        enclosure = ET.SubElement(
            item,
            "enclosure",
            attrib={
                "sparkle:version": release["name"],
                "sparkle:shortVersionString": release["name"],
            },
        )

        _content_type = (
            "application/zip" if os == OS.Windows else "application/x-apple-diskimage"
        )
        asset = next(
            (x for x in release["assets"] if x["content_type"] == _content_type),
            None,
        )
        if asset:
            enclosure.set("url", asset["browser_download_url"])
            enclosure.set("length", str(asset["size"]))
            enclosure.set("type", "application/octet-stream")

        ET.SubElement(item, "sparkle:minimumSystemVersion")

    output = ET.tostring(root, encoding="utf8").decode("utf8")
    print(output)
    dom = xml.dom.minidom.parseString(output)
    pretty_xml = dom.toprettyxml(indent="    ")
    return pretty_xml
