# Family Diagram MCP Testing Server

An MCP (Model Context Protocol) server that enables Claude Code to perform end-to-end UI testing of the Family Diagram PyQt5+QML application, similar to how `chrome-devtools-mcp` works for web applications.

---

## TL;DR - Getting Claude Code to Use It

Just tell Claude Code:

```
Use the familydiagram-testing MCP tools to test the app. Launch it, find elements
by objectName, interact with them, and take screenshots to verify the UI.
```

The MCP server is auto-configured via `.mcp.json`. Key tools:

| Action | Tool |
|--------|------|
| Start the app | `launch_app()` |
| Find a widget/QML item | `find_element(object_name="myButton")` |
| Click an element | `click_element(object_name="myButton")` |
| Type into a field | `type_into_element(object_name="nameField", text="John")` |
| Take a screenshot | `take_screenshot(name="test_state")` |
| Stop the app | `close_app()` |

---

## Concept

This MCP server provides Claude Code with the ability to:

1. **Launch and control** the Family Diagram application
2. **Inspect UI elements** by their `objectName` (both QtWidgets and QML items)
3. **Interact with elements** programmatically (click, type, set properties)
4. **Capture screenshots** for visual verification
5. **Access the scene graph** to inspect diagram items (Person, Marriage, etc.)

The goal is autonomous end-to-end testing where Claude Code can:
- Make code changes
- Launch the app with test bridge enabled
- Navigate the UI by element names (not brittle coordinates)
- Verify behavior via screenshots and element state
- Close the app and report results

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
│  │  - Screenshot capture (pyautogui)                            │   │
│  │  - Coordinate-based input (pyautogui)                        │   │
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
   - Uses pyautogui for screenshots and fallback input
   - Manages app lifecycle (subprocess control)
   - Speaks MCP protocol to Claude Code

2. **Qt Test Bridge (in-app)**
   - Has direct access to Qt object tree
   - Can find elements by `objectName` (stable, not coordinate-dependent)
   - Can read/write Qt properties
   - Can invoke Qt input simulation via QTest
   - Runs on Qt main thread for thread safety

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
| `take_screenshot(name, region)` | Capture screen to file |
| `list_screenshots()` | List saved screenshots |
| `compare_screenshots(baseline, current, threshold)` | Visual diff comparison |

### Coordinate-Based Input (fallback)

| Tool | Description |
|------|-------------|
| `click(x, y, button, clicks)` | Click at screen coordinates |
| `type_text(text, interval)` | Type text via keyboard |
| `press_key(key, modifiers)` | Press a key with modifiers |
| `hotkey(*keys)` | Press key combination |
| `move_mouse(x, y)` | Move cursor |
| `drag(start_x, start_y, end_x, end_y)` | Drag operation |
| `scroll(clicks, x, y)` | Mouse wheel scroll |

### Utilities

| Tool | Description |
|------|-------------|
| `wait(seconds)` | Pause execution |
| `get_screen_size()` | Get display dimensions |
| `get_mouse_position()` | Get cursor location |

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
# Capture baseline
take_screenshot(name="baseline_main_window")

# ... make changes ...

# Capture current state
take_screenshot(name="current_main_window")

# Compare
result = compare_screenshots(
    baseline_path="screenshots/baseline_main_window.png",
    current_path="screenshots/current_main_window.png",
    threshold=0.95
)
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
- Ensure `pyautogui` and `Pillow` are installed

### Debugging

1. **Enable bridge logging** in `pkdiagram/testbridge/server.py`:
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
- `pyautogui>=0.9.54` - Screenshot and input simulation
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
│   ├── testbridge/
│   │   ├── __init__.py
│   │   ├── inspector.py           # QtInspector - finds elements
│   │   └── server.py              # TCP server - JSON protocol
│   └── mapserver/                 # Legacy utilities (optional)
│       ├── app_controller.py
│       ├── element_finder.py
│       ├── input_simulator.py
│       └── snapshot.py
└── screenshots/                   # Screenshot storage (gitignored)
```

---

## Comparison with chrome-devtools-mcp

| Feature | chrome-devtools-mcp | familydiagram-testing |
|---------|--------------------|-----------------------|
| Element selection | CSS selectors | Qt objectName |
| Protocol | Chrome DevTools Protocol | Custom JSON-over-TCP |
| Screenshots | CDP screenshot | pyautogui + Qt |
| Input | CDP Input domain | QTest + pyautogui |
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
