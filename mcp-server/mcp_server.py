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
import fcntl
import json
import logging
import os
import select
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple


# Add parent directory to path to import pkdiagram modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP

import btcopilot
from pkdiagram.app import AppConfig
from pkdiagram.server_types import (
    User,
    Diagram,
    License,
    Policy,
    Activation,
)
import pkdiagram.util as util


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
        if self._socket:
            try:
                self._socket.close()
            except OSError:
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

        except (socket.error, ConnectionError, json.JSONDecodeError) as e:
            logger.exception(f"Bridge communication error: {e}")
            self.disconnect()
            return {"success": False, "error": str(e)}


# =============================================================================
# Enums
# =============================================================================


class LoginState(str, Enum):
    NoData = "no_data"
    LoggedIn = "logged_in"


# =============================================================================
# Sandbox Management
# =============================================================================


class SandboxManager:
    """Creates and manages isolated test sandboxes for application test sessions."""

    def __init__(self):
        self.sandbox_dir: Optional[Path] = None
        self.prefs_dir: Optional[Path] = None
        self.app_data_dir: Optional[Path] = None
        self.documents_dir: Optional[Path] = None

    def create_sandbox(
        self,
        login_state: LoginState = LoginState.NoData,
        username: Optional[str] = None,
        personal: bool = False,
    ) -> Dict[str, str]:
        """
        Create isolated sandbox for test session.

        Args:
            login_state: LoginState.NoData for fresh login test, LoginState.LoggedIn for pre-authenticated
            username: Optional username for dev auto-login (defaults to FLASK_AUTO_AUTH_USER on server)
            personal: True for Personal app (uses different prefs file)

        Returns:
            Dict with environment variables to pass to app
        """
        self.sandbox_dir = Path(tempfile.mkdtemp(prefix="fd_test_"))
        self.prefs_dir = self.sandbox_dir / "prefs"
        self.app_data_dir = self.sandbox_dir / "appdata"
        self.documents_dir = self.sandbox_dir / "Documents"

        self.prefs_dir.mkdir(parents=True, exist_ok=True)
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created test sandbox: {self.sandbox_dir}")
        logger.info(f"Documents directory: {self.documents_dir}")

        env = {
            "QT_QPA_PLATFORMTHEME": "offscreen",
            "HOME": str(self.sandbox_dir),
            "XDG_DATA_HOME": str(self.app_data_dir),
            "XDG_CONFIG_HOME": str(self.prefs_dir),
            "FD_TEST_DATA_DIR": str(self.app_data_dir / "Family Diagram"),
            "FD_SERVER_URL_ROOT": "http://127.0.0.1:8888",
        }

        if login_state == LoginState.LoggedIn:
            if not self._check_btcopilot_server():
                raise RuntimeError(
                    "btcopilot server not running on port 8888. "
                    "Please start the Flask server before launching with login_state='logged_in'"
                )
            self._populate_logged_in_data(username, personal=personal)

        return env

    def _check_btcopilot_server(self) -> bool:
        """Check if btcopilot Flask server is running."""
        import requests

        try:
            requests.get("http://127.0.0.1:8888/", timeout=2)
            return True
        except requests.RequestException:
            return False

    def _get_dev_session(self, username: Optional[str] = None) -> Optional[dict]:
        """Call /v1/sessions without password to trigger dev auto-login."""
        import pickle
        import hashlib
        import time as time_module
        import wsgiref.handlers
        import requests

        url = "http://127.0.0.1:8888/v1/sessions"

        # Build signed request (anonymous auth, no password = dev auto-login)
        args = {}
        if username:
            args["username"] = username
        # No password field → triggers dev auto-login on server

        data = pickle.dumps(args)
        content_md5 = hashlib.md5(data).hexdigest()
        content_type = "text/html"
        date = wsgiref.handlers.format_date_time(
            time_module.mktime(datetime.now().timetuple())
        )

        signature = btcopilot.sign(
            btcopilot.ANON_SECRET,
            "POST",
            content_md5,
            content_type,
            date,
            "/v1/sessions",
        )
        auth_header = btcopilot.httpAuthHeader(btcopilot.ANON_USER, signature)

        headers = {
            "FD-Authentication": auth_header,
            "FD-Client-Version": "99.99.99",
            "Date": date,
            "Content-MD5": content_md5,
            "Content-Type": content_type,
        }

        try:
            response = requests.post(url, data=data, headers=headers, timeout=10)
        except requests.RequestException as e:
            logger.error(f"Failed to connect to btcopilot server: {e}")
            return None

        if response.status_code != 200:
            logger.error(
                f"Dev auto-login failed: {response.status_code} {response.text}"
            )
            return None

        return pickle.loads(response.content)

    def _populate_logged_in_data(
        self, username: Optional[str] = None, personal: bool = False
    ) -> None:
        """Get real session from btcopilot server and write to sandbox AppConfig."""
        appconfig_dir = self.app_data_dir / "Family Diagram"
        appconfig_dir.mkdir(parents=True, exist_ok=True)
        # Personal app uses different prefs name
        prefs_suffix = "-personal.alaskafamilysystems.com" if personal else ""
        appconfig_file = appconfig_dir / f"cherries{prefs_suffix}"

        logger.info(f"Getting real session from btcopilot server (personal={personal})")

        session_data = self._get_dev_session(username)
        if not session_data:
            raise RuntimeError(
                "Failed to get session from btcopilot server. "
                "Ensure FLASK_AUTO_AUTH_USER is set and the user exists."
            )

        appconfig = AppConfig(filePath=str(appconfig_file))
        appconfig.hardwareUUID = util.HARDWARE_UUID
        appconfig.set("lastSessionData", session_data, pickled=True)
        appconfig.write()

        user_email = (
            session_data.get("session", {}).get("user", {}).get("username", "unknown")
        )
        logger.info(f"Wrote real session for {user_email} to {appconfig_file}")

    def cleanup(self) -> None:
        """Remove sandbox directory."""
        if self.sandbox_dir and self.sandbox_dir.exists():
            try:
                shutil.rmtree(self.sandbox_dir)
                logger.info(f"Cleaned up sandbox: {self.sandbox_dir}")
            except OSError as e:
                logger.warning(f"Failed to clean up sandbox: {e}")
            self.sandbox_dir = None


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
        self._stdout_partial: str = ""
        self._stderr_partial: str = ""
        self._sandbox = SandboxManager()

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
        login_state: LoginState = LoginState.NoData,
        username: str = None,
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
            login_state: LoginState.NoData (fresh) or LoginState.LoggedIn (pre-auth)
            username: Optional username for dev auto-login (defaults to FLASK_AUTO_AUTH_USER on server)

        Returns:
            Tuple of (success, message)
        """
        if self.is_running:
            return False, f"Application already running (PID: {self.pid})"

        # Clear output buffers from previous run
        self._stdout_lines.clear()
        self._stderr_lines.clear()

        try:
            # Use uv run from workspace root to get proper venv with built _pkdiagram
            workspace_root = self.project_root.parent
            cmd = [
                "uv",
                "run",
                "--directory",
                str(workspace_root),
                "python",
                "-u",  # Force unbuffered stdout/stderr
                "-m",
                "pkdiagram",
            ]

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

            # Force unbuffered stdout/stderr from child process
            env["PYTHONUNBUFFERED"] = "1"

            # Clear problematic virtual environment variable from MCP server venv
            env.pop("VIRTUAL_ENV", None)

            # Create sandbox and get sandbox-specific env vars
            sandbox_env = self._sandbox.create_sandbox(
                login_state=login_state, username=username, personal=personal
            )
            env.update(sandbox_env)

            if headless:
                env["QT_QPA_PLATFORM"] = "offscreen"

            # Disable GPU for stability
            env["QT_QUICK_BACKEND"] = "software"

            # Log sandbox environment for debugging
            logger.info(f"Launching application: {' '.join(cmd)}")
            logger.info(f"Sandbox HOME: {env.get('HOME', 'NOT SET')}")
            logger.info(f"FD_TEST_DATA_DIR: {env.get('FD_TEST_DATA_DIR', 'NOT SET')}")

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

        except OSError as e:
            logger.exception("Failed to launch application")
            return False, f"Failed to launch: {str(e)}"

    def collect_output(self) -> None:
        """Collect non-blocking stdout/stderr from the running process."""
        if not self.process or not self.is_running:
            return

        def read_nonblocking(pipe, buffer_list, partial_buffer):
            """Read available data from pipe without blocking."""
            if not pipe:
                return partial_buffer

            fd = pipe.fileno()

            # Set non-blocking mode
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            try:
                while True:
                    ready, _, _ = select.select([pipe], [], [], 0)
                    if not ready:
                        break
                    try:
                        chunk = os.read(fd, 4096)
                        if not chunk:
                            break
                        partial_buffer += chunk.decode("utf-8", errors="replace")
                        # Split into lines, keep partial line for next time
                        while "\n" in partial_buffer:
                            line, partial_buffer = partial_buffer.split("\n", 1)
                            buffer_list.append(line)
                    except BlockingIOError:
                        break
            except (OSError, ValueError):
                pass
            finally:
                # Restore blocking mode
                fcntl.fcntl(fd, fcntl.F_SETFL, flags)

            return partial_buffer

        self._stdout_partial = read_nonblocking(
            self.process.stdout, self._stdout_lines, self._stdout_partial
        )
        self._stderr_partial = read_nonblocking(
            self.process.stderr, self._stderr_lines, self._stderr_partial
        )

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

        except OSError as e:
            logger.exception("Failed to close application")
            return False, f"Failed to close: {str(e)}"
        finally:
            self.process = None
            self.start_time = None
            self._sandbox.cleanup()

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
    login_state: str = LoginState.LoggedIn.value,
    username: Optional[str] = None,
) -> Dict[str, Any]:
    """Launch app. Returns {success, pid, bridge_connected}. Default login_state is 'logged_in'.

    Args:
        username: Optional username for dev auto-login (defaults to FLASK_AUTO_AUTH_USER on server)
    """
    session = TestSession.get_instance()

    try:
        login_enum = LoginState(login_state)
    except ValueError:
        valid_values = [e.value for e in LoginState]
        return {
            "success": False,
            "pid": None,
            "message": f"Invalid login_state: {login_state}. Use one of: {valid_values}",
            "bridge_connected": False,
        }

    success, message = session.launch(
        headless=headless,
        personal=personal,
        enable_bridge=enable_bridge,
        open_file=open_file,
        login_state=login_enum,
        username=username,
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
        except (OSError, IOError, ValueError) as e:
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
        except (OSError, IOError, ValueError) as e:
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
        except (OSError, json.JSONDecodeError):
            pass

    limitations_list.append(limitation)
    # Keep only last 100 entries
    limitations_list = limitations_list[-100:]

    with open(limitations_file, "w") as f:
        json.dump(limitations_list, f, indent=2)

    return {"success": True, "limitation": limitation}


# =============================================================================
# MCP Tools - Personal App State
# =============================================================================


@mcp.tool()
def personal_state(component: str = "all") -> Dict[str, Any]:
    """Get Personal app state. component: 'all', 'learn', 'discuss', 'plan', 'pdp'."""
    session = TestSession.get_instance()

    if not session.bridge or not session.bridge.is_connected:
        return {"success": False, "error": "Bridge not connected"}

    return session.bridge.send_command(
        {"command": "get_personal_state", "component": component}
    )


# =============================================================================
# Main Entry Point
# =============================================================================


if __name__ == "__main__":
    logger.info("Starting Family Diagram MCP Testing Server")
    mcp.run(transport="stdio")
