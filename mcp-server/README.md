# Family Diagram MCP Testing Server

An MCP (Model Context Protocol) server that enables Claude Code to perform end-to-end UI testing of the Family Diagram PyQt5+QML application, similar to how `chrome-devtools-mcp` works for web applications.

## Table of Contents

- [TL;DR - Registering the MCP Server with Claude Code](#tldr---registering-the-mcp-server-with-claude-code)
  - [Option A: Copy config to your workspace root](#option-a-copy-config-to-your-workspace-root)
  - [Option B: Start Claude Code from familydiagram/](#option-b-start-claude-code-from-familydiagram)
  - [Verify Registration](#verify-registration)
  - [Configuring Permissions](#configuring-permissions-optional-but-recommended)
  - [Using the Tools](#using-the-tools)
- [Coding Guide: Setting objectName for Testability](#coding-guide-setting-objectname-for-testability)
  - [The Namespace](#the-namespace)
  - [QWidgets](#qwidgets-pythonc)
  - [QML Items](#qml-items-qquickitem)
  - [Dot Notation for Nested QML Items](#dot-notation-for-nested-qml-items)
  - [QGraphicsScene Items](#qgraphicsscene-items)
  - [Naming Conventions](#naming-conventions)
  - [What NOT to Name](#what-not-to-name)
- [Concept](#concept)
- [Architecture](#architecture)
- [Capabilities](#capabilities)
  - [Application Control](#application-control)
  - [Element Finding](#element-finding-via-qt-test-bridge)
  - [Element Interaction](#element-interaction-via-qt-test-bridge)
  - [Scene Graph Access](#scene-graph-access)
  - [Screenshots](#screenshots)
  - [Utilities](#utilities)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Extending the MCP Server](#extending-the-mcp-server)
- [Fixing Bugs](#fixing-bugs)
- [Dependencies](#dependencies)
- [File Structure](#file-structure)
- [Comparison with chrome-devtools-mcp](#comparison-with-chrome-devtools-mcp)
- [Future Improvements](#future-improvements)

---

## TL;DR - Registering the MCP Server with Claude Code

Claude Code reads MCP configuration from `.mcp.json` in the **working directory where CC was started**. Two options:

### Option A: Copy config to your workspace root

If you run Claude Code from a parent directory (e.g., `theapp-2/`), copy the config there:

```bash
# From theapp-2/
cp familydiagram/.mcp.json .
# Edit paths to be relative from theapp-2:
```

Then update `.mcp.json` to use correct relative paths:
```json
{
  "mcpServers": {
    "familydiagram-testing": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "familydiagram/mcp-server", "python", "mcp_server.py"],
      "env": {
        "PYTHONPATH": "familydiagram"
      }
    }
  }
}
```

### Option B: Start Claude Code from familydiagram/

```bash
cd familydiagram
claude  # .mcp.json in this directory will be read
```

### Verify Registration

After restarting Claude Code, run `/mcp` to see registered servers. You should see `familydiagram-testing` listed.

### Configuring Permissions (Optional but Recommended)

To avoid repeated permission prompts, add the familydiagram-testing server to your project's allowed tools. Edit `.claude/settings.local.json` in your project root:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "mcp__familydiagram-testing__launch_app",
      "mcp__familydiagram-testing__close_app",
      "mcp__familydiagram-testing__get_app_status",
      "mcp__familydiagram-testing__find_element",
      "mcp__familydiagram-testing__list_elements",
      "mcp__familydiagram-testing__get_element_property",
      "mcp__familydiagram-testing__set_element_property",
      "mcp__familydiagram-testing__click_element",
      "mcp__familydiagram-testing__double_click_element",
      "mcp__familydiagram-testing__type_into_element",
      "mcp__familydiagram-testing__press_key_on_element",
      "mcp__familydiagram-testing__focus_element",
      "mcp__familydiagram-testing__click_scene_item",
      "mcp__familydiagram-testing__get_scene_items",
      "mcp__familydiagram-testing__get_windows",
      "mcp__familydiagram-testing__activate_window",
      "mcp__familydiagram-testing__take_screenshot",
      "mcp__familydiagram-testing__list_screenshots",
      "mcp__familydiagram-testing__compare_screenshots",
      "mcp__familydiagram-testing__wait",
      "mcp__familydiagram-testing__get_app_output",
      "mcp__familydiagram-testing__report_testing_limitation"
    ]
  },
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": [
    "familydiagram-testing"
  ]
}
```

**Pattern explanation:**
- List each tool individually - wildcard patterns (`*`) are not supported
- Format: `mcp__<server-name>__<tool-name>`
- This prevents repeated permission prompts when using the tools
- Update this list when new tools are added to the MCP server

**Settings file locations:**
- **Global**: `~/.claude/settings.json` - applies to all projects
- **Project**: `<project-root>/.claude/settings.local.json` - applies only to this project (recommended)

### Using the Tools

Once registered, tell Claude Code:

```
Use the familydiagram-testing MCP tools to test the app. Launch it, find elements
by objectName, interact with them, and take screenshots to verify the UI.
```

Key tools:

| Action | Tool |
|--------|------|
| Start the app | `launch_app()` |
| Find a widget/QML item | `find_element(object_name="myButton")` |
| Click an element | `click_element(object_name="myButton")` |
| Type into a field | `type_into_element(object_name="nameField", text="John")` |
| Take a screenshot | `take_screenshot(name="test_state")` - Captures only the app window with timestamp prefix |
| Get console output | `get_app_output(stream="both")` - Read stdout/stderr for debugging |
| Report limitation | `report_testing_limitation(feature="...", reason="...")` - Document missing controls |
| Stop the app | `close_app()` |

---

## Coding Guide: Setting objectName for Testability

### The Namespace

**objectNames are NOT globally unique.** The inspector searches hierarchically:

1. **QWidgets**: Uses `QWidget.findChild(QWidget, objectName)` which searches the widget tree depth-first from each top-level window
2. **QML Items**: Uses recursive `childItems()` traversal from each `QQuickWidget.rootObject()`

If two elements have the same objectName, **the first one found wins** (depth-first order). So:
- Names must be unique within a window's widget subtree
- Names must be unique within a QML component tree
- A widget and QML item CAN have the same name (widgets are searched first)

### QWidgets (Python/C++)

Set `objectName` in your widget code:

```python
# In Python
button = QPushButton("Save")
button.setObjectName("saveButton")

# In __init__ of a custom widget
class MyPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("myPanel")

        self.nameField = QLineEdit()
        self.nameField.setObjectName("nameField")
```

**How widgets are found:**
```python
# inspector.py:_findWidget()
for window in app.topLevelWidgets():
    widget = window.findChild(QWidget, objectName)  # Qt's built-in recursive search
```

**How widgets are clicked:**
```python
# Uses QTest.mouseClick() directly on the widget
clickPos = widget.rect().center()
QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, clickPos)
```

### QML Items (QQuickItem)

Set `objectName` in your QML:

```qml
// In QML files
Rectangle {
    objectName: "mainPanel"

    Button {
        objectName: "saveButton"
        text: "Save"
    }

    TextField {
        objectName: "nameField"
        placeholderText: "Enter name"
    }
}
```

**How QML items are found:**
```python
# inspector.py:_findQmlItem()
# 1. Get all QQuickWidget instances from widget tree
# 2. Get rootObject() from each QQuickWidget
# 3. Recursively search childItems() for matching objectName

def _findQmlItemInChildren(parent: QQuickItem, objectName: str):
    if parent.objectName() == objectName:
        return parent
    for child in parent.childItems():
        result = _findQmlItemInChildren(child, objectName)
        if result:
            return result
    return None
```

**How QML items are clicked:**
```python
# inspector.py:_clickQmlItem()
# 1. Find the QQuickWidget containing the item
# 2. Map item coordinates to QQuickWidget coordinates
# 3. Send QTest.mouseClick() to the QQuickWidget at mapped position

quickWidget = self._findQuickWidgetForItem(item)
scenePos = item.mapToScene(QPointF(item.width()/2, item.height()/2))
widgetPos = scenePos.toPoint()
QTest.mouseClick(quickWidget, Qt.LeftButton, Qt.NoModifier, widgetPos)
```

**Key difference:** QML items can't receive QTest events directly—they must be routed through their parent `QQuickWidget`.

### Dot Notation for Nested QML Items

For deeply nested QML where names might conflict, use dot notation:

```qml
// sidebar.qml
Item {
    objectName: "sidebar"

    Button {
        objectName: "closeButton"  // sidebar.closeButton
    }
}

// header.qml
Item {
    objectName: "header"

    Button {
        objectName: "closeButton"  // header.closeButton
    }
}
```

```python
# Find the sidebar's close button specifically
click_element(object_name="sidebar.closeButton")
```

### QGraphicsScene Items

Scene items (Person, Marriage, etc.) don't use `objectName`. Instead:

1. Set a `name` attribute/property on your custom QGraphicsItem
2. Or use the item's `id` attribute if available

```python
# inspector.py:_getSceneItemInfo()
if hasattr(item, "name"):
    name = getattr(item, "name", None)
    if callable(name):
        name = name()
```

Use `click_scene_item(name="...")` or `get_scene_items(item_type="Person")`.

### Naming Conventions

```
# Pattern: <component><Element>
# Examples:
toolbarNewButton
toolbarSaveButton
sidebarCloseButton
personDialogNameField
personDialogBirthDatePicker
mainWindowMenuBar
```

### What NOT to Name

Don't bother naming:
- Layout containers (QVBoxLayout, Row, Column)
- Spacers and separators
- Internal implementation details
- Elements you'll never test

Only name elements that tests will interact with or verify.

---

## Concept

This MCP server provides Claude Code with the ability to:

1. **Launch and control** the Family Diagram application
2. **Inspect UI elements** by their `objectName` (both QtWidgets and QML items)
3. **Interact with elements** programmatically (click, type, set properties)
4. **Capture screenshots** for visual verification (app window only, timestamped)
5. **Access the scene graph** to inspect diagram items (Person, Marriage, etc.)
6. **Read console output** (stdout/stderr) from the app for debugging
7. **Report testing limitations** when controls are inaccessible

## Key Feature: Autonomous Testing (No Window Focus Required)

**The app can run minimized, on a secondary monitor, or completely headless** - you can continue working on your computer while tests run autonomously.

All element interaction and screenshot capture happens via Qt's internal APIs through the test bridge:
- ✅ **Element-based tools** (click_element, type_into_element, etc.) use `QTest` - works without focus
- ✅ **Screenshots** use `QWidget.grab()` - works minimized/headless
- ✅ **Headless mode** via `QT_QPA_PLATFORM=offscreen` - no GUI at all

The goal is autonomous end-to-end testing where Claude Code can:
- Make code changes
- Launch the app with test bridge enabled (headless optional)
- Navigate the UI by element names (not brittle coordinates)
- Verify behavior via screenshots and element state
- Debug issues by reading console output
- Document limitations when controls need objectNames
- Close the app and report results
- **All while you continue working on other tasks**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Claude Code                                  │
│                              │                                       │
│                         MCP Protocol                                 │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   MCP Server (mcp_server.py)                 │   │
│  │  - FastMCP-based server                                      │   │
│  │  - App lifecycle management (launch/close)                   │   │
│  │  - Screenshot capture (via Qt bridge)                        │   │
│  │  - Bridge client for element access                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                         TCP (port 9876)                              │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Qt Test Bridge (pkdiagram/testbridge/)          │   │
│  │  - Runs inside the Qt application                            │   │
│  │  - QtInspector: finds widgets/QML items by objectName        │   │
│  │  - JSON-over-TCP command protocol                            │   │
│  │  - Thread-safe Qt main thread execution                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                Family Diagram Application                    │   │
│  │  - QtWidgets (main window, dialogs)                          │   │
│  │  - QML/QtQuick (right-side drawer, mobile UI)                │   │
│  │  - QGraphicsScene (diagram canvas)                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Why Two Layers?

1. **MCP Server (external process)**
   - Persists across app restarts
   - Manages app lifecycle (subprocess control)
   - Captures stdout/stderr from app process for debugging
   - Receives screenshots and element data from Qt bridge
   - Speaks MCP protocol to Claude Code

2. **Qt Test Bridge (in-app)** - Located in `pkdiagram/tests/mcpbridge/`
   - Has direct access to Qt object tree
   - Can find elements by `objectName` (stable, not coordinate-dependent)
   - Can read/write Qt properties
   - Can invoke Qt input simulation via QTest (no OS window focus needed)
   - Captures screenshots via `QWidget.grab()` (works minimized/headless)
   - Runs on Qt main thread for thread safety
   - **Only loaded when --test-server flag is used** (never in production bundles)

---

## Capabilities

### Application Control

| Tool | Description |
|------|-------------|
| `launch_app(mode, headless)` | Launch app in "desktop" or "personal" mode |
| `close_app()` | Gracefully close the running app |
| `get_app_status()` | Check if app is running, get PID/uptime |

### Element Finding (via Qt Test Bridge)

| Tool | Description |
|------|-------------|
| `find_element(object_name, widget_type, timeout)` | Find element by objectName |
| `list_elements(parent_name, widget_type, recursive)` | List elements in the tree |
| `get_element_properties(object_name, properties)` | Get Qt properties of an element |
| `set_element_property(object_name, property, value)` | Set a Qt property |

### Element Interaction (via Qt Test Bridge)

| Tool | Description |
|------|-------------|
| `click_element(object_name)` | Click on an element by name |
| `type_into_element(object_name, text, clear_first)` | Type text into a field |
| `send_key_to_element(object_name, key, modifiers)` | Send key press to element |

### Scene Graph Access

| Tool | Description |
|------|-------------|
| `get_scene_items(item_type)` | List items in QGraphicsScene |
| `get_scene_item_properties(item_id)` | Get properties of a scene item |

### Screenshots

| Tool | Description |
|------|-------------|
| `take_screenshot(name, return_base64)` | Capture app window to file (auto-prefixed with timestamp) |
| `list_screenshots()` | List saved screenshots |
| `compare_screenshots(baseline, current, threshold)` | Visual diff comparison |

**Note**:
- Screenshots use Qt's `QWidget.grab()` via the bridge - no OS window focus required
- Captures only the application window (not the full desktop)
- Works when app is minimized, on secondary monitor, or running headless
- Auto-prefixed with timestamps (YYYYMMDD_HHMMSS) for chronological sorting
- Images are PNG format, resized if too large to stay within MCP limits

### Utilities

| Tool | Description |
|------|-------------|
| `wait(seconds)` | Pause execution |
| `get_app_output(stream, last_n_lines, clear_after_read)` | Read stdout/stderr from the app process |
| `report_testing_limitation(feature, reason, missing_controls, workaround)` | Document testing infrastructure limitations |

---

## Usage Examples

### Basic Element-Based Testing

```
# Launch the app with test bridge
launch_app(mode="desktop")

# Wait for startup
wait(seconds=2)

# Find and click the "New" button
click_element(object_name="newFileButton")

# Type a name into a text field
type_into_element(object_name="diagramNameField", text="Test Family")

# Click save
click_element(object_name="saveButton")

# Take a screenshot to verify
take_screenshot(name="after_save")

# Close the app
close_app()
```

### Inspecting Element State

```
# Check if a checkbox is checked
props = get_element_properties(object_name="autoSaveCheckbox", properties=["checked"])

# Get text from a label
props = get_element_properties(object_name="statusLabel", properties=["text"])

# List all buttons in a panel
elements = list_elements(parent_name="toolbarPanel", widget_type="QPushButton")
```

### Scene Graph Inspection

```
# Get all Person items in the diagram
persons = get_scene_items(item_type="Person")

# Get details of a specific person
props = get_scene_item_properties(item_id="person_123")
```

### Visual Regression Testing

```
# Capture baseline (automatically prefixed with timestamp)
take_screenshot(name="baseline_main_window")  # saves as YYYYMMDD_HHMMSS_baseline_main_window.png

# ... make changes ...

# Capture current state
take_screenshot(name="current_main_window")

# Compare
result = compare_screenshots(
    baseline_path="screenshots/20250125_143022_baseline_main_window.png",
    current_path="screenshots/20250125_143045_current_main_window.png",
    threshold=0.95
)
```

### Debugging with Console Output

```
# Launch app
launch_app()

# Perform some actions
click_element(object_name="debugButton")

# Check console output for debug messages
output = get_app_output(stream="stderr", last_n_lines=20)
print("Recent stderr:", output["stderr"])

# Clear the buffer after reading to save memory
get_app_output(stream="both", clear_after_read=True)
```

### Reporting Testing Limitations

```
# Try to interact with a control
find_result = find_element(object_name="fileOpenButton")

if not find_result["success"]:
    # Document the limitation
    report_testing_limitation(
        feature="File Open Dialog",
        reason="QFileDialog native dialog has no accessible objectName",
        missing_controls=["fileOpenButton", "fileNameField", "cancelButton"],
        workaround="Use keyboard shortcut Cmd+O and then type filename"
    )
    # This creates an entry in screenshots/testing_limitations.json
```

---

## Configuration

### MCP Configuration (`.mcp.json`)

```json
{
  "mcpServers": {
    "familydiagram-testing": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "mcp-server", "python", "mcp_server.py"],
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}
```

### App Command Line Flags

```bash
# Enable test bridge (done automatically by MCP server)
python main.py --test-server

# Custom port
python main.py --test-server --test-server-port 9877
```

---

## Extending the MCP Server

### Adding a New Tool

1. **Edit `mcp_server.py`** and add a new function with the `@mcp.tool()` decorator:

```python
@mcp.tool()
async def my_new_tool(param1: str, param2: int = 10) -> str:
    """
    Description of what this tool does.

    Args:
        param1: Description of param1
        param2: Description of param2 (default: 10)

    Returns:
        Description of return value
    """
    # Implementation
    result = do_something(param1, param2)
    return json.dumps({"success": True, "result": result})
```

2. **If it needs Qt access**, add a command handler in the bridge:

```python
# In pkdiagram/testbridge/server.py, add to _handleCommand():
elif cmd == "my_new_command":
    result = self._inspector.myNewMethod(data.get("param1"))
    return {"result": result}

# In pkdiagram/testbridge/inspector.py, add the method:
def myNewMethod(self, param1):
    # Qt operations here (runs on main thread)
    return some_result
```

3. **Call the bridge from MCP**:

```python
@mcp.tool()
async def my_new_tool(param1: str) -> str:
    """Tool description."""
    global _bridge_client
    if not _bridge_client or not _bridge_client.connected:
        return json.dumps({"error": "App not running with test bridge"})

    result = _bridge_client.send_command("my_new_command", {"param1": param1})
    return json.dumps(result)
```

### Adding Element Type Support

The `QtInspector` class in `pkdiagram/testbridge/inspector.py` handles element finding. To support new widget types:

1. **For custom widgets**, ensure they have an `objectName` set
2. **For QML items**, set `objectName` in QML: `objectName: "myItem"`
3. **For QGraphicsItems**, the inspector accesses via `QGraphicsView.scene()`

### Adding New Properties

To expose additional Qt properties:

```python
# In inspector.py, modify getProperty():
def getProperty(self, objectName, propertyName):
    element = self.findElement(objectName)
    if not element:
        return None

    # Add custom property handling
    if propertyName == "myCustomProp":
        return self._getCustomProp(element)

    # Default: use Qt property system
    return element.property(propertyName)
```

---

## Fixing Bugs

### Common Issues

#### "Bridge not connected"
- The app wasn't launched with `--test-server`
- The MCP server's `launch_app()` should add this flag automatically
- Check that port 9876 isn't in use

#### "Element not found"
- The `objectName` doesn't match exactly (case-sensitive)
- The element hasn't been created yet (add `wait()`)
- The element is in a different window/dialog (use `list_elements()` to explore)

#### "Screenshot fails"
- On headless systems, use `launch_app(headless=True)`
- Ensure the Qt test bridge is connected (check `get_app_status()`)

### Debugging

1. **Enable bridge logging** in `pkdiagram/tests/mcpbridge/server.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. **Test bridge directly** via netcat:
```bash
echo '{"command": "list", "data": {}}' | nc localhost 9876
```

3. **Check MCP server logs**: The server prints to stderr which Claude Code captures

### Testing Changes

```bash
# Run MCP server standalone for testing
cd mcp-server
uv run python mcp_server.py

# In another terminal, launch app with bridge
cd ..
uv run python main.py --test-server

# Test bridge connection
python -c "
import socket, json
s = socket.socket()
s.connect(('localhost', 9876))
s.send(json.dumps({'command': 'list', 'data': {}}).encode() + b'\n')
print(s.recv(4096).decode())
"
```

---

## Dependencies

### MCP Server (`mcp-server/pyproject.toml`)
- `mcp>=1.0.0` - Model Context Protocol SDK
- `Pillow>=10.0.0` - Image processing

### Qt Test Bridge (part of main app)
- Uses PyQt5 from main application
- No additional dependencies

---

## File Structure

```
familydiagram/
├── .mcp.json                      # Claude Code MCP configuration
├── mcp-server/
│   ├── mcp_server.py              # Main MCP server (FastMCP)
│   ├── pyproject.toml             # MCP server dependencies
│   └── README.md                  # This file
├── pkdiagram/
│   ├── main.py                    # App entry (--test-server flag)
│   ├── mainwindow/
│   │   └── welcome.py             # Welcome dialog with okButton objectName
│   └── tests/
│       └── mcpbridge/             # MCP test bridge (only loaded with --test-server)
│           ├── __init__.py
│           ├── inspector.py       # QtInspector - finds elements, takes screenshots
│           └── server.py          # TCP server - JSON protocol
└── screenshots/                   # Screenshot storage (gitignored)
    └── testing_limitations.json  # Logged testing limitations
```

---

## Comparison with chrome-devtools-mcp

| Feature | chrome-devtools-mcp | familydiagram-testing |
|---------|--------------------|-----------------------|
| Element selection | CSS selectors | Qt objectName |
| Protocol | Chrome DevTools Protocol | Custom JSON-over-TCP |
| Screenshots | CDP screenshot | Qt QWidget.grab() |
| Input | CDP Input domain | Qt QTest |
| DOM/Widget tree | Full DOM access | Qt widget + QML tree |
| Network | CDP Network domain | Not implemented |
| Console | CDP Console domain | Not implemented |

---

## Future Improvements

- [ ] Add accessibility tree inspection (QAccessible)
- [ ] Add network request monitoring
- [ ] Add Qt signal/slot interception for event verification
- [ ] Add record/playback for test generation
- [ ] Add visual element highlighting in screenshots
- [ ] Add support for multiple windows/dialogs
- [ ] Add QML-specific property access (attached properties)
