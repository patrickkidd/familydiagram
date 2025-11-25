"""
MCP Server for end-to-end testing of the Family Diagram PyQt+QML application.

This server provides tools for Claude Code to:
- Launch and control the application
- Take UI screenshots
- Send keyboard and mouse input events
- Query UI element state by objectName (via Qt test bridge)
- Interact with elements by objectName (click, type, etc.)
- Perform visual regression testing

Usage:
    # Run standalone
    python mcp_server.py

    # Or via uv
    uv run python mcp-server/mcp_server.py

Configuration:
    Add to .mcp.json in project root to use with Claude Code.
"""

import base64
import json
import logging
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Add parent directory to path to import pkdiagram modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("familydiagram-mcp")

# Initialize MCP server
mcp = FastMCP("familydiagram-testing")

# Default port for the Qt test bridge
BRIDGE_PORT = 9876


# =============================================================================
# Qt Test Bridge Client
# =============================================================================


class BridgeClient:
    """
    Client for communicating with the Qt test bridge running in the app.

    The bridge provides deep Qt integration:
    - Find elements by objectName
    - Get element properties
    - Click/type on elements by name
    - Access QML items and scene items
    """

    def __init__(self, host: str = "127.0.0.1", port: int = BRIDGE_PORT):
        self._host = host
        self._port = port
        self._socket: Optional[socket.socket] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to the bridge."""
        return self._connected and self._socket is not None

    def connect(self, timeout: float = 10.0) -> bool:
        """
        Connect to the Qt test bridge.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            True if connected successfully
        """
        if self._connected:
            return True

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.settimeout(5.0)
                self._socket.connect((self._host, self._port))
                self._connected = True
                logger.info(f"Connected to Qt test bridge at {self._host}:{self._port}")
                return True
            except (socket.error, ConnectionRefusedError):
                if self._socket:
                    self._socket.close()
                    self._socket = None
                time.sleep(0.5)

        logger.warning(f"Failed to connect to bridge after {timeout}s")
        return False

    def disconnect(self):
        """Disconnect from the bridge."""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        self._connected = False

    def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a command to the bridge and get response.

        Args:
            command: Command dict with 'command' key and parameters

        Returns:
            Response dict from the bridge
        """
        if not self.is_connected:
            if not self.connect():
                return {"success": False, "error": "Not connected to bridge"}

        try:
            # Send command
            data = json.dumps(command) + "\n"
            self._socket.sendall(data.encode("utf-8"))

            # Receive response
            buffer = b""
            while b"\n" not in buffer:
                chunk = self._socket.recv(4096)
                if not chunk:
                    raise ConnectionError("Connection closed")
                buffer += chunk

            line = buffer.split(b"\n")[0]
            return json.loads(line.decode("utf-8"))

        except Exception as e:
            logger.exception(f"Bridge communication error: {e}")
            self.disconnect()
            return {"success": False, "error": str(e)}


# =============================================================================
# Session Management
# =============================================================================


class TestSession:
    """
    Manages the PyQt application test session.

    This class handles:
    - Application lifecycle (launch, close)
    - Process management
    - Communication with the Qt test bridge
    """

    _instance: Optional["TestSession"] = None

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.start_time: Optional[float] = None
        self.project_root = Path(__file__).parent.parent
        self._screenshot_counter = 0
        self._bridge: Optional[BridgeClient] = None
        self._bridge_port = BRIDGE_PORT

    @classmethod
    def get_instance(cls) -> "TestSession":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = TestSession()
        return cls._instance

    @property
    def is_running(self) -> bool:
        """Check if the application is running."""
        if self.process is None:
            return False
        return self.process.poll() is None

    @property
    def pid(self) -> Optional[int]:
        """Get process ID if running."""
        if self.is_running:
            return self.process.pid
        return None

    @property
    def uptime(self) -> Optional[float]:
        """Get uptime in seconds."""
        if self.is_running and self.start_time:
            return time.time() - self.start_time
        return None

    @property
    def bridge(self) -> Optional[BridgeClient]:
        """Get the bridge client."""
        return self._bridge

    def launch(
        self,
        headless: bool = False,
        personal: bool = False,
        enable_bridge: bool = True,
        bridge_port: int = BRIDGE_PORT,
        extra_args: Optional[List[str]] = None,
        timeout: int = 30,
    ) -> Tuple[bool, str]:
        """
        Launch the Family Diagram application.

        Args:
            headless: Run in headless mode (for CI/testing)
            personal: Run the personal/mobile UI
            enable_bridge: Enable the Qt test bridge for element inspection
            bridge_port: Port for the test bridge
            extra_args: Additional command-line arguments
            timeout: Maximum time to wait for startup

        Returns:
            Tuple of (success, message)
        """
        if self.is_running:
            return False, f"Application already running (PID: {self.pid})"

        try:
            # Build command
            cmd = ["uv", "run", "python", "-m", "pkdiagram"]

            if personal:
                cmd.append("--personal")

            if enable_bridge:
                cmd.extend(["--test-server", "--test-server-port", str(bridge_port)])
                self._bridge_port = bridge_port

            if extra_args:
                cmd.extend(extra_args)

            # Set up environment
            env = os.environ.copy()

            if headless:
                env["QT_QPA_PLATFORM"] = "offscreen"

            # Disable GPU for stability
            env["QT_QUICK_BACKEND"] = "software"

            logger.info(f"Launching application: {' '.join(cmd)}")

            self.process = subprocess.Popen(
                cmd,
                cwd=str(self.project_root),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.start_time = time.time()

            # Wait for app to start
            time.sleep(2)

            if not self.is_running:
                stderr = self.process.stderr.read().decode() if self.process.stderr else ""
                return False, f"Application failed to start: {stderr}"

            # Connect to bridge if enabled
            if enable_bridge:
                self._bridge = BridgeClient(port=bridge_port)
                if not self._bridge.connect(timeout=10):
                    logger.warning("Failed to connect to test bridge")
                else:
                    # Verify connection
                    response = self._bridge.send_command({"command": "ping"})
                    if response.get("success"):
                        logger.info("Qt test bridge connected and verified")

            logger.info(f"Application started (PID: {self.pid})")
            return True, f"Application started successfully (PID: {self.pid})"

        except Exception as e:
            logger.exception("Failed to launch application")
            return False, f"Failed to launch: {str(e)}"

    def close(self, force: bool = False, timeout: int = 10) -> Tuple[bool, str]:
        """
        Close the application.

        Args:
            force: Force kill if graceful shutdown fails
            timeout: Timeout for graceful shutdown

        Returns:
            Tuple of (success, message)
        """
        if not self.is_running:
            return True, "Application not running"

        pid = self.pid

        # Disconnect bridge
        if self._bridge:
            self._bridge.disconnect()
            self._bridge = None

        try:
            # Try graceful shutdown first
            self.process.terminate()

            try:
                self.process.wait(timeout=timeout)
                logger.info(f"Application terminated gracefully (PID: {pid})")
                return True, f"Application terminated (PID: {pid})"
            except subprocess.TimeoutExpired:
                if force:
                    self.process.kill()
                    self.process.wait(timeout=5)
                    logger.warning(f"Application force killed (PID: {pid})")
                    return True, f"Application force killed (PID: {pid})"
                else:
                    return False, "Graceful shutdown timed out. Use force=True to kill."

        except Exception as e:
            logger.exception("Failed to close application")
            return False, f"Failed to close: {str(e)}"
        finally:
            self.process = None
            self.start_time = None

    def get_screenshot_path(self, name: Optional[str] = None) -> Path:
        """Get a unique screenshot path."""
        screenshot_dir = self.project_root / "screenshots"
        screenshot_dir.mkdir(exist_ok=True)

        if name:
            return screenshot_dir / f"{name}.png"

        self._screenshot_counter += 1
        timestamp = int(time.time())
        return screenshot_dir / f"screenshot_{timestamp}_{self._screenshot_counter}.png"


# =============================================================================
# MCP Tools - Application Control
# =============================================================================


@mcp.tool()
def launch_app(
    headless: bool = False,
    personal: bool = False,
    enable_bridge: bool = True,
    wait_seconds: int = 3,
) -> Dict[str, Any]:
    """
    Launch the Family Diagram application.

    Args:
        headless: Run in headless mode without display (for CI/automated testing)
        personal: Run the personal/mobile UI instead of desktop
        enable_bridge: Enable Qt test bridge for element-level interaction
        wait_seconds: Seconds to wait after launch for app to initialize

    Returns:
        Status dict with success, pid, message, and bridge_connected
    """
    session = TestSession.get_instance()
    success, message = session.launch(
        headless=headless,
        personal=personal,
        enable_bridge=enable_bridge,
    )

    if success and wait_seconds > 0:
        time.sleep(wait_seconds)

    return {
        "success": success,
        "pid": session.pid,
        "message": message,
        "bridge_connected": session.bridge.is_connected if session.bridge else False,
    }


@mcp.tool()
def close_app(force: bool = False) -> Dict[str, Any]:
    """
    Close the Family Diagram application.

    Args:
        force: Force kill if graceful shutdown fails

    Returns:
        Status dict with success and message
    """
    session = TestSession.get_instance()
    success, message = session.close(force=force)

    return {
        "success": success,
        "message": message,
    }


@mcp.tool()
def get_app_status() -> Dict[str, Any]:
    """
    Get the current application status.

    Returns:
        Status dict with running state, pid, uptime, and bridge connection
    """
    session = TestSession.get_instance()

    return {
        "running": session.is_running,
        "pid": session.pid,
        "uptime_seconds": session.uptime,
        "bridge_connected": session.bridge.is_connected if session.bridge else False,
    }


# =============================================================================
# MCP Tools - Element Inspection (via Bridge)
# =============================================================================


@mcp.tool()
def find_element(object_name: str) -> Dict[str, Any]:
    """
    Find a UI element by its objectName.

    This uses the Qt test bridge to find widgets and QML items by their
    objectName property. Returns position and state information.

    Args:
        object_name: The objectName of the element (supports dot notation for nested QML)

    Returns:
        Element info including type, position, visibility, enabled state, text
    """
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected. Launch app with enable_bridge=True"}

    response = session.bridge.send_command({
        "command": "find_element",
        "objectName": object_name,
    })

    return response


@mcp.tool()
def list_elements(
    element_type: Optional[str] = None,
    max_depth: int = 5,
) -> Dict[str, Any]:
    """
    List all UI elements in the application.

    This scans the Qt widget tree, QML items, and scene items.

    Args:
        element_type: Filter by type - "widget", "qml", "scene", or None for all
        max_depth: Maximum depth to traverse (default 5 to avoid huge output)

    Returns:
        List of elements with their properties
    """
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    response = session.bridge.send_command({
        "command": "list_elements",
        "type": element_type,
        "maxDepth": max_depth,
    })

    return response


@mcp.tool()
def get_element_property(object_name: str, property_name: str) -> Dict[str, Any]:
    """
    Get a property value from a UI element.

    Args:
        object_name: Element objectName
        property_name: Property to get (e.g., "text", "checked", "enabled")

    Returns:
        Dict with property value
    """
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    response = session.bridge.send_command({
        "command": "get_property",
        "objectName": object_name,
        "property": property_name,
    })

    return response


@mcp.tool()
def set_element_property(
    object_name: str,
    property_name: str,
    value: Any,
) -> Dict[str, Any]:
    """
    Set a property value on a UI element.

    Args:
        object_name: Element objectName
        property_name: Property to set
        value: New value

    Returns:
        Dict with success status
    """
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    response = session.bridge.send_command({
        "command": "set_property",
        "objectName": object_name,
        "property": property_name,
        "value": value,
    })

    return response


# =============================================================================
# MCP Tools - Element Interaction (via Bridge)
# =============================================================================


@mcp.tool()
def click_element(
    object_name: str,
    button: str = "left",
) -> Dict[str, Any]:
    """
    Click on a UI element by its objectName.

    This is more reliable than clicking by coordinates as it finds the
    element's current position automatically.

    Args:
        object_name: Element objectName
        button: Mouse button - "left", "right", or "middle"

    Returns:
        Dict with success status
    """
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    response = session.bridge.send_command({
        "command": "click",
        "objectName": object_name,
        "button": button,
    })

    return response


@mcp.tool()
def double_click_element(object_name: str) -> Dict[str, Any]:
    """
    Double-click on a UI element by its objectName.

    Args:
        object_name: Element objectName

    Returns:
        Dict with success status
    """
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    response = session.bridge.send_command({
        "command": "double_click",
        "objectName": object_name,
    })

    return response


@mcp.tool()
def type_into_element(
    text: str,
    object_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Type text into a UI element.

    Uses Qt's QTest for accurate text input. If object_name is provided,
    focuses that element first.

    Args:
        text: Text to type
        object_name: Optional element to focus before typing

    Returns:
        Dict with success status
    """
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    response = session.bridge.send_command({
        "command": "type_text",
        "text": text,
        "objectName": object_name,
    })

    return response


@mcp.tool()
def press_key_on_element(
    key: str,
    object_name: Optional[str] = None,
    modifiers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Press a key, optionally on a specific element.

    Args:
        key: Key name (e.g., "return", "tab", "escape", "a")
        object_name: Optional element to focus first
        modifiers: Optional list of modifiers (e.g., ["ctrl"], ["ctrl", "shift"])

    Returns:
        Dict with success status
    """
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    response = session.bridge.send_command({
        "command": "press_key",
        "key": key,
        "objectName": object_name,
        "modifiers": modifiers,
    })

    return response


@mcp.tool()
def focus_element(object_name: str) -> Dict[str, Any]:
    """
    Set focus to a UI element.

    Args:
        object_name: Element objectName

    Returns:
        Dict with success status
    """
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    response = session.bridge.send_command({
        "command": "focus",
        "objectName": object_name,
    })

    return response


# =============================================================================
# MCP Tools - Scene Items (via Bridge)
# =============================================================================


@mcp.tool()
def click_scene_item(name: str, button: str = "left") -> Dict[str, Any]:
    """
    Click on a scene item in the diagram view.

    Scene items are Person, Marriage, Event, etc. in the QGraphicsView.

    Args:
        name: Scene item name
        button: Mouse button

    Returns:
        Dict with success status
    """
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    response = session.bridge.send_command({
        "command": "click_scene_item",
        "name": name,
        "button": button,
    })

    return response


@mcp.tool()
def get_scene_items(item_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Get all scene items in the diagram.

    Args:
        item_type: Optional type filter (e.g., "Person", "Marriage", "Event")

    Returns:
        List of scene items with their properties
    """
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    response = session.bridge.send_command({
        "command": "get_scene_items",
        "type": item_type,
    })

    return response


# =============================================================================
# MCP Tools - Windows (via Bridge)
# =============================================================================


@mcp.tool()
def get_windows() -> Dict[str, Any]:
    """
    Get all top-level windows.

    Returns:
        List of windows with titles and geometry
    """
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    response = session.bridge.send_command({
        "command": "get_windows",
    })

    return response


@mcp.tool()
def activate_window(object_name: str) -> Dict[str, Any]:
    """
    Activate (bring to front) a window.

    Args:
        object_name: Window objectName

    Returns:
        Dict with success status
    """
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    response = session.bridge.send_command({
        "command": "activate_window",
        "objectName": object_name,
    })

    return response


# =============================================================================
# MCP Tools - Screenshots (via pyautogui)
# =============================================================================


@mcp.tool()
def take_screenshot(
    name: Optional[str] = None,
    return_base64: bool = False,
) -> Dict[str, Any]:
    """
    Take a screenshot of the application window.

    Args:
        name: Optional name for the screenshot file (without extension)
        return_base64: If True, include base64-encoded image data in response

    Returns:
        Dict with success, path, dimensions, and optionally base64 data
    """
    session = TestSession.get_instance()

    if not session.is_running:
        return {
            "success": False,
            "error": "Application not running. Use launch_app first.",
        }

    try:
        import pyautogui
        from PIL import Image

        # Get screenshot path
        output_path = session.get_screenshot_path(name)

        # Capture screenshot
        screenshot = pyautogui.screenshot()

        # Resize if too large (to stay within MCP response limits)
        max_dimension = 1920
        if screenshot.width > max_dimension or screenshot.height > max_dimension:
            ratio = min(max_dimension / screenshot.width, max_dimension / screenshot.height)
            new_size = (int(screenshot.width * ratio), int(screenshot.height * ratio))
            screenshot = screenshot.resize(new_size, Image.Resampling.LANCZOS)

        # Save
        screenshot.save(str(output_path), "PNG")

        result = {
            "success": True,
            "path": str(output_path),
            "width": screenshot.width,
            "height": screenshot.height,
        }

        if return_base64:
            import io
            buffer = io.BytesIO()
            screenshot.save(buffer, format="PNG")
            result["base64_data"] = base64.b64encode(buffer.getvalue()).decode("utf-8")

        logger.info(f"Screenshot saved: {output_path}")
        return result

    except ImportError:
        return {
            "success": False,
            "error": "pyautogui or Pillow not installed. Run: pip install pyautogui Pillow",
        }
    except Exception as e:
        logger.exception("Screenshot failed")
        return {
            "success": False,
            "error": str(e),
        }


@mcp.tool()
def list_screenshots() -> Dict[str, Any]:
    """
    List all saved screenshots.

    Returns:
        Dict with list of screenshot files
    """
    session = TestSession.get_instance()
    screenshot_dir = session.project_root / "screenshots"

    if not screenshot_dir.exists():
        return {
            "success": True,
            "screenshots": [],
            "directory": str(screenshot_dir),
        }

    screenshots = sorted(screenshot_dir.glob("*.png"))

    return {
        "success": True,
        "screenshots": [str(p) for p in screenshots],
        "count": len(screenshots),
        "directory": str(screenshot_dir),
    }


@mcp.tool()
def compare_screenshots(
    baseline_path: str,
    current_path: Optional[str] = None,
    threshold: float = 0.01,
) -> Dict[str, Any]:
    """
    Compare two screenshots for visual differences.

    Args:
        baseline_path: Path to the baseline screenshot
        current_path: Path to current screenshot (if None, takes a new screenshot)
        threshold: Maximum acceptable difference ratio (0.0 to 1.0)

    Returns:
        Dict with comparison results
    """
    try:
        from PIL import Image

        # Load baseline
        baseline = Image.open(baseline_path)

        # Get current (either from file or take new)
        if current_path:
            current = Image.open(current_path)
        else:
            import pyautogui
            current = pyautogui.screenshot()

        # Resize current to match baseline if needed
        if baseline.size != current.size:
            current = current.resize(baseline.size, Image.Resampling.LANCZOS)

        # Compare pixels
        baseline_data = list(baseline.getdata())
        current_data = list(current.getdata())

        if len(baseline_data) != len(current_data):
            return {
                "success": False,
                "error": "Image sizes don't match",
            }

        different_pixels = sum(1 for b, c in zip(baseline_data, current_data) if b != c)
        total_pixels = len(baseline_data)
        difference_ratio = different_pixels / total_pixels

        match = difference_ratio <= threshold

        return {
            "success": True,
            "match": match,
            "difference_ratio": difference_ratio,
            "different_pixels": different_pixels,
            "total_pixels": total_pixels,
            "threshold": threshold,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# =============================================================================
# MCP Tools - Coordinate-based Input (via pyautogui)
# =============================================================================


@mcp.tool()
def click(
    x: int,
    y: int,
    button: str = "left",
    clicks: int = 1,
) -> Dict[str, Any]:
    """
    Click at screen coordinates.

    For element-based clicking, use click_element() instead.

    Args:
        x: X coordinate on screen
        y: Y coordinate on screen
        button: Mouse button - "left", "right", or "middle"
        clicks: Number of clicks (1 for single, 2 for double-click)

    Returns:
        Dict with success status
    """
    session = TestSession.get_instance()

    if not session.is_running:
        return {"success": False, "error": "Application not running"}

    try:
        import pyautogui
        pyautogui.click(x=x, y=y, button=button, clicks=clicks)

        logger.info(f"Clicked at ({x}, {y}) with {button} button, {clicks} time(s)")
        return {"success": True, "message": f"Clicked at ({x}, {y})"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def type_text(text: str, interval: float = 0.02) -> Dict[str, Any]:
    """
    Type text using the keyboard (coordinate-independent).

    For typing into a specific element, use type_into_element() instead.

    Args:
        text: Text to type
        interval: Delay between keystrokes in seconds

    Returns:
        Dict with success status
    """
    try:
        import pyautogui
        pyautogui.write(text, interval=interval)

        logger.info(f"Typed text: {text[:50]}{'...' if len(text) > 50 else ''}")
        return {"success": True, "message": f"Typed {len(text)} characters"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def press_key(key: str, modifiers: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Press a keyboard key (coordinate-independent).

    Args:
        key: Key to press (e.g., "enter", "tab", "escape", "a", "f1")
        modifiers: Optional list of modifier keys (e.g., ["ctrl"], ["ctrl", "shift"])

    Returns:
        Dict with success status
    """
    try:
        import pyautogui

        if modifiers:
            keys = modifiers + [key]
            pyautogui.hotkey(*keys)
            logger.info(f"Pressed: {'+'.join(keys)}")
        else:
            pyautogui.press(key)
            logger.info(f"Pressed: {key}")

        return {"success": True, "message": f"Pressed {'+'.join(modifiers + [key]) if modifiers else key}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: float = 0.5,
    button: str = "left",
) -> Dict[str, Any]:
    """
    Drag from one position to another.

    Args:
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        end_x: Ending X coordinate
        end_y: Ending Y coordinate
        duration: Time for the drag operation
        button: Mouse button to hold during drag

    Returns:
        Dict with success status
    """
    try:
        import pyautogui

        pyautogui.moveTo(start_x, start_y)
        pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration, button=button)

        logger.info(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
        return {"success": True, "message": f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def scroll(clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
    """
    Scroll the mouse wheel.

    Args:
        clicks: Number of scroll clicks (positive = up, negative = down)
        x: Optional X coordinate to scroll at
        y: Optional Y coordinate to scroll at

    Returns:
        Dict with success status
    """
    try:
        import pyautogui
        pyautogui.scroll(clicks, x=x, y=y)

        direction = "up" if clicks > 0 else "down"
        return {"success": True, "message": f"Scrolled {direction} {abs(clicks)} clicks"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def wait(seconds: float) -> Dict[str, Any]:
    """
    Wait for a specified number of seconds.

    Args:
        seconds: Time to wait in seconds

    Returns:
        Dict with success status
    """
    time.sleep(seconds)
    return {"success": True, "message": f"Waited {seconds} seconds"}


@mcp.tool()
def get_screen_size() -> Dict[str, Any]:
    """
    Get the screen dimensions.

    Returns:
        Dict with width and height of the screen
    """
    try:
        import pyautogui
        size = pyautogui.size()
        return {"success": True, "width": size.width, "height": size.height}

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def get_mouse_position() -> Dict[str, Any]:
    """
    Get the current mouse cursor position.

    Returns:
        Dict with x and y coordinates
    """
    try:
        import pyautogui
        pos = pyautogui.position()
        return {"success": True, "x": pos.x, "y": pos.y}

    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Main Entry Point
# =============================================================================


if __name__ == "__main__":
    logger.info("Starting Family Diagram MCP Testing Server")
    mcp.run(transport="stdio")
