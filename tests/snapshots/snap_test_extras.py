# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['test_actions_2_appcast[OS.MacOS] 1'] = '''<?xml version="1.0" ?>
<rss version="2.0">
    <channel>
        <title>familydiagram Releases</title>
        <link>https://github.com/patrickidd/familydiagram/releases</link>
        <description>Latest updates for github.com/patrickidd/familydiagram</description>
        <item>
            <title>2.0.0b5</title>
            <link>https://github.com/patrickkidd/familydiagram/releases/tag/2.0.0b5</link>
            <pubDate>Fri, 11 Oct 2024 18:23:02 +0000</pubDate>
            <description/>
            <enclosure url="https://github.com/patrickkidd/familydiagram/releases/download/2.0.0b5/Family.Diagram.2.0.0b5.dmg" length="122638956" type="application/octet-stream"/>
        </item>
    </channel>
</rss>
'''

snapshots['test_actions_2_appcast[OS.Windows] 1'] = '''<?xml version="1.0" ?>
<rss version="2.0">
    <channel>
        <title>familydiagram Releases</title>
        <link>https://github.com/patrickidd/familydiagram/releases</link>
        <description>Latest updates for github.com/patrickidd/familydiagram</description>
        <item>
            <title>2.0.0b5</title>
            <link>https://github.com/patrickkidd/familydiagram/releases/tag/2.0.0b5</link>
            <pubDate>Fri, 11 Oct 2024 18:23:02 +0000</pubDate>
            <description/>
            <enclosure url="https://github.com/patrickkidd/familydiagram/releases/download/2.0.0b5/Family.Diagram.2.0.0b5.zip" length="25551219" type="application/octet-stream"/>
        </item>
    </channel>
</rss>
'''
