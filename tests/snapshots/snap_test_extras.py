# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['test_actions_2_appcast 1'] = '''<?xml version="1.0" ?>
<rss version="2.0">
    <channel>
        <title>familydiagram Releases</title>
        <link>https://github.com/patrickidd/familydiagram/releases</link>
        <description>Latest updates for github.com/patrickidd/familydiagram</description>
        <item>
            <title>macOS-2.0.0b5</title>
            <link>https://github.com/patrickkidd/familydiagram/releases/tag/macOS-2.0.0b5</link>
            <pubDate>Thu, 10 Oct 2024 17:01:41 +0000</pubDate>
            <description/>
            <enclosure/>
        </item>
    </channel>
</rss>
'''
