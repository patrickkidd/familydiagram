# Family Diagram MCP Testing Server

An MCP (Model Context Protocol) server that enables Claude Code to perform end-to-end testing of the Family Diagram PyQt+QML application.

## Features

- **Application Control**: Launch and close the Family Diagram app
- **Screenshots**: Capture and compare UI screenshots
- **Mouse Input**: Click, double-click, right-click, drag operations
- **Keyboard Input**: Type text, press keys, key combinations (hotkeys)
- **Visual Testing**: Compare screenshots for regression testing
- **Image Location**: Find UI elements by their visual appearance

## Installation

The MCP server is automatically configured when you use Claude Code in this repository. The configuration is in `.mcp.json` at the project root.

### Manual Setup

1. Install dependencies:
   ```bash
   cd mcp-server
   uv pip install -e .
   ```

2. Or install globally:
   ```bash
   pip install pyautogui Pillow mcp
   ```

## Configuration

The server is configured in `.mcp.json`:

```json
{
  "mcpServers": {
    "familydiagram-testing": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "mcp-server", "python", "mcp_server.py"]
    }
  }
}
```

## Available Tools

### Application Control

| Tool | Description |
|------|-------------|
| `launch_app` | Launch the Family Diagram application |
| `close_app` | Close the running application |
| `get_app_status` | Check if app is running, get PID and uptime |

### Screenshots

| Tool | Description |
|------|-------------|
| `take_screenshot` | Capture the current screen |
| `list_screenshots` | List all saved screenshots |
| `compare_screenshots` | Compare two screenshots for differences |

### Mouse Input

| Tool | Description |
|------|-------------|
| `click` | Click at screen coordinates |
| `double_click` | Double-click at coordinates |
| `right_click` | Right-click at coordinates |
| `move_mouse` | Move cursor to coordinates |
| `drag` | Drag from one position to another |
| `scroll` | Scroll the mouse wheel |
| `get_mouse_position` | Get current cursor position |

### Keyboard Input

| Tool | Description |
|------|-------------|
| `type_text` | Type a string of text |
| `press_key` | Press a single key with optional modifiers |
| `hotkey` | Press a key combination |

### Utilities

| Tool | Description |
|------|-------------|
| `wait` | Wait for a specified time |
| `get_screen_size` | Get screen dimensions |
| `locate_on_screen` | Find an image on the screen |

## Usage Examples

### Basic Test Flow

```
1. Launch the app:
   launch_app(headless=False)

2. Wait for it to load:
   wait(seconds=2)

3. Take a screenshot:
   take_screenshot(name="initial_state")

4. Click on a button:
   click(x=100, y=200)

5. Type some text:
   type_text("John Doe")

6. Press Enter:
   press_key("enter")

7. Take another screenshot:
   take_screenshot(name="after_input")

8. Compare with baseline:
   compare_screenshots(baseline_path="screenshots/expected.png")

9. Close the app:
   close_app()
```

### Key Combinations

```
# Save (Ctrl+S)
press_key("s", modifiers=["ctrl"])

# Or using hotkey
hotkey("ctrl", "s")

# Undo (Ctrl+Z)
hotkey("ctrl", "z")

# Select All (Ctrl+A)
hotkey("ctrl", "a")
```

### Visual Element Location

```
# Find a button by its image
result = locate_on_screen("button_template.png", confidence=0.9)
if result["found"]:
    click(x=result["center_x"], y=result["center_y"])
```

## Notes

- **Display Required**: Most operations require a display. For headless CI, use `launch_app(headless=True)` which sets `QT_QPA_PLATFORM=offscreen`.
- **Coordinates**: All coordinates are screen-relative. Use `take_screenshot` to see the current state and determine coordinates.
- **Timing**: UI operations may need `wait()` calls between them for animations and state changes.
- **Screenshots**: Screenshots are saved to `screenshots/` in the project root.

## Troubleshooting

### "pyautogui not found"
```bash
pip install pyautogui Pillow
```

### "No display" errors
Run with headless mode:
```
launch_app(headless=True)
```

### Screenshot comparison fails
Ensure images are the same size. The comparison tool will resize if needed, but for best results, capture screenshots at consistent sizes.
