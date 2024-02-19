# Switches Xcode Workspace project to new build system.

fpath = "build/osx/Family Diagram.xcodeproj/project.xcworkspace/xcshareddata/WorkspaceSettings.xcsettings"
data = open(fpath, "rt").read()
data = data.replace(
    """	<key>BuildSystemType</key>
	<string>Original</string>""",
    """	<key>BuildSystemType</key>
	<string>Latest</string>""",
)
with open(fpath, "wt") as f:
    f.write(data)
