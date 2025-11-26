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
                self._socket.settimeout(60.0)  # Longer timeout for busy main thread
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
        self._stdout_lines: List[str] = []
        self._stderr_lines: List[str] = []

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
        headless: bool = True,
        personal: bool = False,
        enable_bridge: bool = True,
        bridge_port: int = BRIDGE_PORT,
        open_file: Optional[str] = None,
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
            open_file: Path to .fd file to open at startup
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

            if open_file:
                cmd.extend(["--open-file", open_file])

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
                stderr = (
                    self.process.stderr.read().decode() if self.process.stderr else ""
                )
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

    def collect_output(self) -> None:
        """Collect non-blocking stdout/stderr from the running process."""
        if not self.process or not self.is_running:
            return

        import select

        # Non-blocking read from stdout
        if self.process.stdout:
            try:
                while True:
                    if sys.platform != "win32":
                        ready, _, _ = select.select([self.process.stdout], [], [], 0)
                        if not ready:
                            break
                    line = self.process.stdout.readline()
                    if not line:
                        break
                    self._stdout_lines.append(
                        line.decode("utf-8", errors="replace").rstrip()
                    )
            except:
                pass

        # Non-blocking read from stderr
        if self.process.stderr:
            try:
                while True:
                    if sys.platform != "win32":
                        ready, _, _ = select.select([self.process.stderr], [], [], 0)
                        if not ready:
                            break
                    line = self.process.stderr.readline()
                    if not line:
                        break
                    self._stderr_lines.append(
                        line.decode("utf-8", errors="replace").rstrip()
                    )
            except:
                pass

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
    headless: bool = True,
    personal: bool = False,
    enable_bridge: bool = True,
    wait_seconds: int = 3,
    open_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Launch app. Returns {success, pid, bridge_connected}."""
    session = TestSession.get_instance()
    success, message = session.launch(
        headless=headless,
        personal=personal,
        enable_bridge=enable_bridge,
        open_file=open_file,
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
    """Close app. Use force=True to kill."""
    session = TestSession.get_instance()
    success, message = session.close(force=force)

    return {
        "success": success,
        "message": message,
    }


@mcp.tool()
def get_app_state(include_process: bool = False) -> Dict[str, Any]:
    """Get app state. Use FIRST before other tools. Returns windows, dialogs, semantic state."""
    session = TestSession.get_instance()

    result = {}
    if include_process:
        result.update(
            {
                "running": session.is_running,
                "pid": session.pid,
                "uptime": session.uptime,
            }
        )

    if not session.bridge or not session.bridge.is_connected:
        result["success"] = False
        result["error"] = "Bridge not connected"
        return result

    response = session.bridge.send_command({"command": "get_app_state"})
    result.update(response)
    return result


@mcp.tool()
def open_file(file_path: str) -> Dict[str, Any]:
    """Open .fd file by path."""
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    response = session.bridge.send_command(
        {"command": "open_file", "filePath": file_path}
    )

    # Return full response including verification info
    return response


# =============================================================================
# MCP Tools - Element Inspection (via Bridge)
# =============================================================================


@mcp.tool()
def find_element(name: str) -> Dict[str, Any]:
    """Find element by objectName. Returns {name, type, text}."""
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    return session.bridge.send_command({"command": "find_element", "objectName": name})


@mcp.tool()
def list_elements(
    type: Optional[str] = None,
    depth: int = 3,
    limit: int = 50,
    verbose: bool = False,
) -> Dict[str, Any]:
    """List named visible elements. Returns [{name, type, text}]. Use get_app_state() first."""
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    response = session.bridge.send_command(
        {
            "command": "list_elements",
            "type": type,
            "maxDepth": depth,
            "visibleOnly": True,
            "namedOnly": True,
            "verbose": verbose,
            "limit": limit,
        }
    )

    return response


@mcp.tool()
def prop(name: str, property: str, value: Any = None) -> Dict[str, Any]:
    """Get/set element property. Omit value to get, provide value to set."""
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    if value is None:
        return session.bridge.send_command(
            {"command": "get_property", "objectName": name, "property": property}
        )
    else:
        return session.bridge.send_command(
            {
                "command": "set_property",
                "objectName": name,
                "property": property,
                "value": value,
            }
        )


@mcp.tool()
def click(name: str, double: bool = False, button: str = "left") -> Dict[str, Any]:
    """Click element. Use double=True for double-click."""
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    cmd = "double_click" if double else "click"
    return session.bridge.send_command(
        {"command": cmd, "objectName": name, "button": button}
    )


@mcp.tool()
def input(
    text: str = None, key: str = None, name: str = None, modifiers: List[str] = None
) -> Dict[str, Any]:
    """Type text or press key. Provide text for typing, key for key press."""
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    if text is not None:
        return session.bridge.send_command(
            {"command": "type_text", "text": text, "objectName": name}
        )
    elif key is not None:
        return session.bridge.send_command(
            {
                "command": "press_key",
                "key": key,
                "objectName": name,
                "modifiers": modifiers,
            }
        )
    else:
        return {"success": False, "error": "Provide text or key"}


@mcp.tool()
def scene(
    action: str = "list", name: str = None, type: str = None, button: str = "left"
) -> Dict[str, Any]:
    """Scene items. action="list" to list items, action="click" with name to click."""
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    if action == "list":
        return session.bridge.send_command({"command": "get_scene_items", "type": type})
    elif action == "click" and name:
        return session.bridge.send_command(
            {"command": "click_scene_item", "name": name, "button": button}
        )
    else:
        return {
            "success": False,
            "error": "Use action='list' or action='click' with name",
        }


@mcp.tool()
def window(name: str = None) -> Dict[str, Any]:
    """List windows if no name, activate window if name provided."""
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    if name is None:
        return session.bridge.send_command({"command": "get_windows"})
    else:
        return session.bridge.send_command(
            {"command": "activate_window", "objectName": name}
        )


@mcp.tool()
def screenshot(
    action: str = "take",
    name: str = None,
    baseline: str = None,
    current: str = None,
    threshold: float = 0.01,
) -> Dict[str, Any]:
    """Screenshots. action="take"(default), "list", or "compare" with baseline path."""
    session = TestSession.get_instance()

    if action == "list":
        screenshot_dir = session.project_root / "screenshots"
        if not screenshot_dir.exists():
            return {"success": True, "screenshots": [], "count": 0}
        screenshots = sorted(screenshot_dir.glob("*.png"))
        return {
            "success": True,
            "screenshots": [str(p) for p in screenshots],
            "count": len(screenshots),
        }

    elif action == "take":
        if not session.is_running:
            return {"success": False, "error": "App not running"}
        if not session.bridge or not session.bridge.is_connected:
            return {"success": False, "error": "Bridge not connected"}

        try:
            from PIL import Image
            from datetime import datetime
            import io

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"{timestamp}_{name}" if name else timestamp
            output_path = session.get_screenshot_path(fname)

            response = session.bridge.send_command({"command": "take_screenshot"})
            if not response.get("success"):
                return {"success": False, "error": response.get("error", "Failed")}

            image_bytes = base64.b64decode(response["data"])
            img = Image.open(io.BytesIO(image_bytes))

            max_dim = 1920
            if img.width > max_dim or img.height > max_dim:
                ratio = min(max_dim / img.width, max_dim / img.height)
                img = img.resize(
                    (int(img.width * ratio), int(img.height * ratio)),
                    Image.Resampling.LANCZOS,
                )

            img.save(str(output_path), "PNG")
            return {
                "success": True,
                "path": str(output_path),
                "width": img.width,
                "height": img.height,
            }
        except ImportError:
            return {"success": False, "error": "Pillow not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif action == "compare" and baseline:
        try:
            from PIL import Image
            import io

            baseline_img = Image.open(baseline)
            if current:
                current_img = Image.open(current)
            else:
                if not session.bridge or not session.bridge.is_connected:
                    return {"success": False, "error": "Bridge not connected"}
                response = session.bridge.send_command({"command": "take_screenshot"})
                if not response.get("success"):
                    return {"success": False, "error": response.get("error", "Failed")}
                current_img = Image.open(io.BytesIO(base64.b64decode(response["data"])))

            if baseline_img.size != current_img.size:
                current_img = current_img.resize(
                    baseline_img.size, Image.Resampling.LANCZOS
                )

            baseline_data = list(baseline_img.getdata())
            current_data = list(current_img.getdata())
            different = sum(1 for b, c in zip(baseline_data, current_data) if b != c)
            ratio = different / len(baseline_data)
            return {
                "success": True,
                "match": ratio <= threshold,
                "difference_ratio": ratio,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    else:
        return {
            "success": False,
            "error": "Use action='take', 'list', or 'compare' with baseline",
        }


@mcp.tool()
def wait(seconds: float) -> Dict[str, Any]:
    """Wait seconds."""
    time.sleep(seconds)
    return {"success": True}


@mcp.tool()
def get_app_output(
    stream: str = "both", last_n: Optional[int] = None, clear: bool = False
) -> Dict[str, Any]:
    """Get app stdout/stderr. stream="stdout", "stderr", or "both"."""
    session = TestSession.get_instance()

    if not session.is_running:
        return {"success": False, "error": "App not running"}

    session.collect_output()
    result = {"success": True}

    if stream in ("stdout", "both"):
        lines = session._stdout_lines[-last_n:] if last_n else session._stdout_lines
        result["stdout"] = lines
    if stream in ("stderr", "both"):
        lines = session._stderr_lines[-last_n:] if last_n else session._stderr_lines
        result["stderr"] = lines

    if clear:
        if stream in ("stdout", "both"):
            session._stdout_lines.clear()
        if stream in ("stderr", "both"):
            session._stderr_lines.clear()

    return result


@mcp.tool()
def report_testing_limitation(
    feature: str, missing_controls: List[str], workaround: Optional[str] = None
) -> Dict[str, Any]:
    """Report missing objectNames needed to test a feature. Logged for developer action."""
    session = TestSession.get_instance()

    limitation = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "feature": feature,
        "missing_controls": missing_controls,
        "workaround": workaround,
    }

    logger.warning(
        f"Testing limitation: {feature} - missing: {', '.join(missing_controls)}"
    )

    limitations_file = session.project_root / "screenshots" / "testing_limitations.json"
    limitations_file.parent.mkdir(exist_ok=True)

    limitations_list = []
    if limitations_file.exists():
        try:
            with open(limitations_file) as f:
                limitations_list = json.load(f)
        except:
            pass

    limitations_list.append(limitation)
    # Keep only last 100 entries
    limitations_list = limitations_list[-100:]

    with open(limitations_file, "w") as f:
        json.dump(limitations_list, f, indent=2)

    return {"success": True, "limitation": limitation}


# =============================================================================
# Main Entry Point
# =============================================================================


if __name__ == "__main__":
    logger.info("Starting Family Diagram MCP Testing Server")
    mcp.run(transport="stdio")
