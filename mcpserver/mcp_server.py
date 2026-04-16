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
    uv run python familydiagram/mcpserver/mcp_server.py

Configuration:
    Add to .mcp.json in project root to use with Claude Code.
"""

import atexit
import base64
import fcntl
import json
import logging
import os
import select
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import asdict
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

# Default port for the Qt test bridge (used as fallback only)
BRIDGE_PORT = 9876


# =============================================================================
# Helpers
# =============================================================================


def _find_free_port() -> int:
    """Find an available TCP port by binding to port 0."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


# -- Orphan prevention --
# Three layers ensure no leaked processes or temp dirs:
# 1. atexit: normal exit, unhandled exceptions
# 2. Signal handlers: SIGTERM/SIGINT from Claude Code
# 3. ppid watchdog: parent dies (SIGKILL/crash) — macOS has no PR_SET_PDEATHSIG

_ORIGINAL_PPID = os.getppid()


def _cleanup_all_instances():
    """Called by atexit / signal handlers. Import-safe — TestInstance may not exist yet."""
    if "TestInstance" in globals():
        TestInstance.close_all()


atexit.register(_cleanup_all_instances)


def _signal_handler(signum, frame):
    logger.info(f"Signal {signum} received, cleaning up")
    _cleanup_all_instances()
    sys.exit(0)


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


def _parent_death_watchdog():
    """Poll ppid every 2s. If parent dies (reparented to launchd), kill everything."""
    while True:
        time.sleep(2)
        if os.getppid() != _ORIGINAL_PPID:
            logger.warning("Parent process died, cleaning up all instances")
            _cleanup_all_instances()
            os._exit(1)


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

    def create_sandbox(self, personal: bool = False) -> Dict[str, str]:
        """
        Create isolated sandbox directories.

        Returns env vars dict. Caller must add FD_SERVER_URL_ROOT separately
        (depends on whether ephemeral server is used).
        """
        self.sandbox_dir = Path(tempfile.mkdtemp(prefix="fd_test_"))
        self.prefs_dir = self.sandbox_dir / "prefs"
        self.app_data_dir = self.sandbox_dir / "appdata"
        self.documents_dir = self.sandbox_dir / "Documents"

        for d in (self.prefs_dir, self.app_data_dir, self.documents_dir):
            d.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created test sandbox: {self.sandbox_dir}")

        return {
            "QT_QPA_PLATFORMTHEME": "offscreen",
            "HOME": str(self.sandbox_dir),
            "XDG_DATA_HOME": str(self.app_data_dir),
            "XDG_CONFIG_HOME": str(self.prefs_dir),
            "FD_TEST_DATA_DIR": str(self.app_data_dir / "Family Diagram"),
        }

    def populate_login(
        self,
        server_url: str,
        username: Optional[str] = None,
        personal: bool = False,
    ) -> None:
        """Get session from server and write to sandbox AppConfig."""
        if not self._check_server(server_url):
            raise RuntimeError(
                f"Server not responding at {server_url}. "
                "Start the Flask server or use ephemeral_server=True."
            )

        session_data = self._get_session(server_url, username)
        if not session_data:
            raise RuntimeError(
                f"Failed to get session from {server_url}. "
                "Ensure the user exists and auto-auth is configured."
            )

        appconfig_dir = self.app_data_dir / "Family Diagram"
        appconfig_dir.mkdir(parents=True, exist_ok=True)
        prefs_suffix = "-personal.alaskafamilysystems.com" if personal else ""
        appconfig_file = appconfig_dir / f"cherries{prefs_suffix}"

        appconfig = AppConfig(filePath=str(appconfig_file))
        appconfig.hardwareUUID = util.HARDWARE_UUID
        appconfig.set("lastSessionData", session_data, pickled=True)
        appconfig.write()

        user_email = (
            session_data.get("session", {}).get("user", {}).get("username", "unknown")
        )
        logger.info(f"Wrote session for {user_email} to {appconfig_file}")

    def _check_server(self, server_url: str) -> bool:
        import requests

        try:
            requests.get(f"{server_url}/", timeout=2)
            return True
        except requests.RequestException:
            return False

    def _get_session(
        self, server_url: str, username: Optional[str] = None
    ) -> Optional[dict]:
        """Call /v1/sessions to trigger dev auto-login."""
        import hashlib
        import pickle
        import time as time_module
        import wsgiref.handlers

        import requests

        url = f"{server_url}/v1/sessions"

        args = {}
        if username:
            args["username"] = username

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
            logger.error(f"Failed to connect to server at {server_url}: {e}")
            return None

        if response.status_code != 200:
            logger.error(
                f"Dev auto-login failed: {response.status_code} {response.text}"
            )
            return None

        return pickle.loads(response.content)

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


class TestInstance:
    """
    Manages a single test instance: app process + optional ephemeral server.

    Multiple instances can run simultaneously, each on dynamic ports with its
    own sandbox. Replaces the old TestSession singleton.
    """

    _instances: Dict[str, "TestInstance"] = {}
    _current_id: Optional[str] = None

    def __init__(self, instance_id: str):
        self.id = instance_id
        self.process: Optional[subprocess.Popen] = None
        self.server_process: Optional[subprocess.Popen] = None
        self.start_time: Optional[float] = None
        self.project_root = Path(__file__).parent.parent
        self._screenshot_counter = 0
        self._bridge: Optional[BridgeClient] = None
        self._bridge_port: Optional[int] = None
        self._server_port: Optional[int] = None
        self._sim_udid: Optional[str] = None
        self._sim_bundle_id: Optional[str] = None
        self._stdout_lines: List[str] = []
        self._stderr_lines: List[str] = []
        self._stdout_partial: str = ""
        self._stderr_partial: str = ""
        self._sandbox = SandboxManager()

    @classmethod
    def create(cls) -> "TestInstance":
        instance_id = str(uuid.uuid4())[:8]
        instance = cls(instance_id)
        cls._instances[instance_id] = instance
        cls._current_id = instance_id
        return instance

    @classmethod
    def get(cls, instance_id: Optional[str] = None) -> "TestInstance":
        """Resolve by ID, or return most recently launched."""
        if instance_id:
            if instance_id not in cls._instances:
                raise ValueError(
                    f"No instance '{instance_id}'. "
                    f"Active: {list(cls._instances.keys()) or 'none'}"
                )
            return cls._instances[instance_id]
        if cls._current_id and cls._current_id in cls._instances:
            return cls._instances[cls._current_id]
        raise ValueError("No active instance. Call launch_app first.")

    @classmethod
    def close_all(cls) -> List[str]:
        closed = []
        for iid in list(cls._instances.keys()):
            try:
                cls._instances[iid]._do_close(force=True)
            except Exception as e:
                logger.warning(f"Error closing instance {iid}: {e}")
            closed.append(iid)
        cls._instances.clear()
        cls._current_id = None
        return closed

    @property
    def is_running(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None

    @property
    def pid(self) -> Optional[int]:
        if self.is_running:
            return self.process.pid
        return None

    @property
    def uptime(self) -> Optional[float]:
        if self.is_running and self.start_time:
            return time.time() - self.start_time
        return None

    @property
    def bridge(self) -> Optional[BridgeClient]:
        return self._bridge

    @property
    def server_port(self) -> Optional[int]:
        return self._server_port

    # -- Ephemeral server --

    def _start_ephemeral_server(self, auto_auth_user: str) -> Tuple[bool, str]:
        self._server_port = _find_free_port()
        db_dir = str(self._sandbox.sandbox_dir / "db")
        os.makedirs(db_dir, exist_ok=True)

        workspace_root = self.project_root.parent
        cmd = [
            "uv",
            "run",
            "--directory",
            str(workspace_root),
            "python",
            "-u",
            str(self.project_root / "mcpserver" / "ephemeral_server.py"),
            "--port",
            str(self._server_port),
            "--db-dir",
            db_dir,
        ]

        env = os.environ.copy()
        env.pop("VIRTUAL_ENV", None)
        env["PYTHONUNBUFFERED"] = "1"
        env["FLASK_CONFIG"] = "development"
        env["FLASK_AUTO_AUTH_USER"] = auto_auth_user

        logger.info(
            f"[{self.id}] Starting ephemeral server on port {self._server_port}"
        )

        self.server_process = subprocess.Popen(
            cmd,
            cwd=str(workspace_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        start = time.time()
        while time.time() - start < 30:
            if self.server_process.poll() is not None:
                stderr = self.server_process.stderr.read().decode()
                return False, f"Ephemeral server exited early: {stderr[-500:]}"
            ready, _, _ = select.select([self.server_process.stdout], [], [], 0.5)
            if not ready:
                continue
            line = self.server_process.stdout.readline().decode().strip()
            if line.startswith("READY:"):
                # READY is printed before app.run() binds the socket.
                # Poll health endpoint until it responds.
                import requests

                for _ in range(20):
                    try:
                        requests.get(
                            f"http://127.0.0.1:{self._server_port}/test/health",
                            timeout=1,
                        )
                        break
                    except requests.ConnectionError:
                        time.sleep(0.25)
                logger.info(
                    f"[{self.id}] Ephemeral server ready on port {self._server_port}"
                )
                return True, f"Server started on port {self._server_port}"

        if self.server_process.poll() is None:
            self.server_process.kill()
        return False, "Ephemeral server timed out (30s)"

    def _seed_default_user(self, email: str) -> None:
        import requests

        response = requests.post(
            f"http://127.0.0.1:{self._server_port}/test/seed",
            json={
                "users": [
                    {"username": email, "password": "test", "status": "confirmed"}
                ],
                "hardware_uuid": util.HARDWARE_UUID,
            },
            timeout=10,
        )
        if response.status_code != 200:
            raise RuntimeError(f"Failed to seed default user: {response.text}")

    def _stop_ephemeral_server(self) -> None:
        if self.server_process and self.server_process.poll() is None:
            pid = self.server_process.pid
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                self.server_process.wait(timeout=3)
        self.server_process = None
        self._server_port = None

    # -- iOS Simulator --

    def _launch_in_simulator(
        self,
        app_path: str,
        bundle_id: str = "com.vedanamedia.familydiagram",
        udid: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Install and launch app in iOS simulator, connect bridge on port 9876."""
        # Boot simulator if not already booted
        if udid:
            ok, out = _simctl("boot", udid, timeout=60)
            if not ok and "booted" not in out.lower():
                return False, f"Failed to boot simulator {udid}: {out}"
            self._sim_udid = udid
        else:
            # Find first booted, or boot one
            self._sim_udid = _booted_udid()
            if not self._sim_udid:
                ok, out = _simctl("list", "devices", "available", "--json")
                if ok:
                    data = json.loads(out)
                    for runtime_devices in data.get("devices", {}).values():
                        for d in runtime_devices:
                            if "iPhone" in d.get("name", ""):
                                self._sim_udid = d["udid"]
                                break
                        if self._sim_udid:
                            break
                if not self._sim_udid:
                    return False, "No available iPhone simulator found"
                ok, out = _simctl("boot", self._sim_udid, timeout=60)
                if not ok and "booted" not in out.lower():
                    return False, f"Failed to boot simulator: {out}"

        self._sim_bundle_id = bundle_id

        # Install
        ok, out = _simctl("install", self._sim_udid, app_path, timeout=60)
        if not ok:
            return False, f"Failed to install app: {out}"

        # Launch
        ok, out = _simctl("launch", self._sim_udid, bundle_id, timeout=30)
        if not ok:
            return False, f"Failed to launch app: {out}"

        self.start_time = time.time()

        # Bridge auto-starts on port 9876 in simulator builds
        self._bridge_port = 9876
        time.sleep(4)  # QML startup

        self._bridge = BridgeClient(port=self._bridge_port)
        if not self._bridge.connect(timeout=15):
            return (
                False,
                "Bridge not reachable. App may not have the test bridge compiled in.",
            )

        response = self._bridge.send_command({"command": "ping"})
        if not response.get("success"):
            return False, f"Bridge ping failed: {response}"

        logger.info(
            f"[{self.id}] Simulator app connected via bridge on port {self._bridge_port}"
        )
        return True, f"App running in simulator {self._sim_udid}"

    def _terminate_simulator_app(self) -> None:
        if self._sim_bundle_id and self._sim_udid:
            _simctl("terminate", self._sim_udid, self._sim_bundle_id)
        self._sim_udid = None
        self._sim_bundle_id = None

    # -- App lifecycle --

    def launch(
        self,
        headless: bool = True,
        personal: bool = False,
        enable_bridge: bool = True,
        open_file: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        timeout: int = 30,
        login_state: LoginState = LoginState.NoData,
        username: str = None,
        ephemeral_server: bool = False,
        auto_auth_user: str = "test@example.com",
        server_url: Optional[str] = None,
    ) -> Tuple[bool, str]:
        if self.is_running:
            return False, f"Instance {self.id} already running (PID: {self.pid})"

        self._stdout_lines.clear()
        self._stderr_lines.clear()

        try:
            # 1. Create sandbox
            sandbox_env = self._sandbox.create_sandbox(personal=personal)

            # 2. Determine server URL
            if server_url:
                # Use explicitly provided server (e.g. another instance's ephemeral server)
                pass
            elif ephemeral_server:
                ok, msg = self._start_ephemeral_server(auto_auth_user)
                if not ok:
                    self._sandbox.cleanup()
                    return False, msg
                server_url = f"http://127.0.0.1:{self._server_port}"
                if login_state == LoginState.LoggedIn:
                    self._seed_default_user(username or auto_auth_user)
            else:
                server_url = "http://127.0.0.1:8888"

            sandbox_env["FD_SERVER_URL_ROOT"] = server_url

            # 3. Populate login if requested
            if login_state == LoginState.LoggedIn:
                self._sandbox.populate_login(
                    server_url, username or auto_auth_user, personal
                )

            # 4. Build app command
            workspace_root = self.project_root.parent
            cmd = [
                "uv",
                "run",
                "--directory",
                str(workspace_root),
                "python",
                "-u",
                "-m",
                "pkdiagram",
            ]
            if personal:
                cmd.append("--personal")

            self._bridge_port = _find_free_port()
            if enable_bridge:
                cmd.extend(
                    ["--test-server", "--test-server-port", str(self._bridge_port)]
                )

            if open_file:
                cmd.extend(["--open-file", open_file])
            if extra_args:
                cmd.extend(extra_args)

            # 5. Environment
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env.pop("VIRTUAL_ENV", None)
            env.update(sandbox_env)
            if headless:
                env["QT_QPA_PLATFORM"] = "offscreen"
            env["QT_QUICK_BACKEND"] = "software"

            logger.info(f"[{self.id}] Launching: {' '.join(cmd)}")
            logger.info(
                f"[{self.id}] Server: {server_url}, Bridge port: {self._bridge_port}"
            )

            self.process = subprocess.Popen(
                cmd,
                cwd=str(self.project_root),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.start_time = time.time()
            time.sleep(2)

            if not self.is_running:
                stderr = (
                    self.process.stderr.read().decode() if self.process.stderr else ""
                )
                self._stop_ephemeral_server()
                self._sandbox.cleanup()
                return False, f"App failed to start: {stderr[-500:]}"

            # 6. Connect bridge
            if enable_bridge:
                self._bridge = BridgeClient(port=self._bridge_port)
                if not self._bridge.connect(timeout=10):
                    logger.warning(f"[{self.id}] Failed to connect to test bridge")
                else:
                    response = self._bridge.send_command({"command": "ping"})
                    if response.get("success"):
                        logger.info(f"[{self.id}] Bridge connected and verified")

            logger.info(f"[{self.id}] App started (PID: {self.pid})")
            return True, f"Instance {self.id} started (PID: {self.pid})"

        except Exception as e:
            logger.exception(f"[{self.id}] Failed to launch")
            # Kill app process if it was already started
            if self.process and self.process.poll() is None:
                self.process.kill()
                self.process.wait(timeout=5)
            self.process = None
            self._stop_ephemeral_server()
            self._sandbox.cleanup()
            return False, f"Failed to launch: {e}"

    def close(self, force: bool = False, timeout: int = 10) -> Tuple[bool, str]:
        """Close this instance. Removes from registry."""
        try:
            return self._do_close(force=force, timeout=timeout)
        finally:
            TestInstance._instances.pop(self.id, None)
            if TestInstance._current_id == self.id:
                remaining = list(TestInstance._instances.keys())
                TestInstance._current_id = remaining[-1] if remaining else None

    def _do_close(self, force: bool = False, timeout: int = 10) -> Tuple[bool, str]:
        if (
            not self.is_running
            and self.server_process is None
            and self._sim_bundle_id is None
        ):
            self._sandbox.cleanup()
            return True, f"Instance {self.id} not running"

        pid = self.pid

        if self._bridge:
            self._bridge.disconnect()
            self._bridge = None

        try:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    if force:
                        self.process.kill()
                        self.process.wait(timeout=5)
                    else:
                        return False, "Graceful shutdown timed out. Use force=True."
        except OSError as e:
            logger.exception(f"[{self.id}] Error closing app: {e}")
        finally:
            self.process = None
            self.start_time = None

        self._terminate_simulator_app()
        self._stop_ephemeral_server()
        self._sandbox.cleanup()
        return True, f"Instance {self.id} closed"

    # -- Output collection --

    def collect_output(self) -> None:
        if not self.process or not self.is_running:
            return

        def read_nonblocking(pipe, buffer_list, partial_buffer):
            if not pipe:
                return partial_buffer
            fd = pipe.fileno()
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
                        while "\n" in partial_buffer:
                            line, partial_buffer = partial_buffer.split("\n", 1)
                            buffer_list.append(line)
                    except BlockingIOError:
                        break
            except (OSError, ValueError):
                pass
            finally:
                fcntl.fcntl(fd, fcntl.F_SETFL, flags)
            return partial_buffer

        self._stdout_partial = read_nonblocking(
            self.process.stdout, self._stdout_lines, self._stdout_partial
        )
        self._stderr_partial = read_nonblocking(
            self.process.stderr, self._stderr_lines, self._stderr_partial
        )

    _ERROR_PATTERNS = (
        "ERROR",
        "Traceback",
        "AssertionError",
        "AttributeError",
        "KeyError",
        "TypeError",
        "RuntimeError",
    )

    def collectErrors(self, since: int = 0) -> List[str]:
        """Collect error lines from stdout since a given line index.

        The app logs errors to stdout, not stderr. This method scans stdout
        for ERROR/Traceback/Exception patterns and returns matching lines.

        Usage:
            mark = len(instance._stdout_lines)
            # ... do something ...
            instance.collect_output()
            errors = instance.collectErrors(since=mark)
        """
        self.collect_output()
        return [
            l
            for l in self._stdout_lines[since:]
            if any(p in l for p in self._ERROR_PATTERNS)
        ]

    def get_screenshot_path(self, name: Optional[str] = None) -> Path:
        screenshot_dir = self.project_root / "screenshots"
        screenshot_dir.mkdir(exist_ok=True)
        if name:
            return screenshot_dir / f"{name}.png"
        self._screenshot_counter += 1
        timestamp = int(time.time())
        return screenshot_dir / f"screenshot_{timestamp}_{self._screenshot_counter}.png"


# =============================================================================
# Instance resolution helpers
# =============================================================================


def _resolve_instance(instance_id: Optional[str] = None):
    try:
        return TestInstance.get(instance_id), None
    except ValueError as e:
        return None, {"success": False, "error": str(e)}


def _resolve_bridge(instance_id: Optional[str] = None):
    instance, err = _resolve_instance(instance_id)
    if err:
        return None, err
    if not instance.bridge or not instance.bridge.is_connected:
        return None, {"success": False, "error": "Bridge not connected"}
    return instance.bridge, None


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
    ephemeral_server: bool = False,
    auto_auth_user: str = "test@example.com",
    server_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Launch app. Returns {success, instance_id, pid, bridge_connected}.

    Set ephemeral_server=True for a fully isolated btcopilot server (no external
    Flask server needed). Each instance gets its own dynamic ports.

    Use server_url to point at another instance's ephemeral server (for shared-diagram
    tests where Pro and Personal need the same backend).

    Args:
        username: User email for dev auto-login
        ephemeral_server: Start isolated btcopilot server for this instance
        auto_auth_user: Email for ephemeral server auto-auth (default test@example.com)
        server_url: Override server URL (e.g. http://127.0.0.1:{other_instance.server_port})
    """
    instance = TestInstance.create()

    try:
        login_enum = LoginState(login_state)
    except ValueError:
        valid_values = [e.value for e in LoginState]
        TestInstance._instances.pop(instance.id, None)
        return {
            "success": False,
            "instance_id": None,
            "message": f"Invalid login_state: {login_state}. Use one of: {valid_values}",
        }

    success, message = instance.launch(
        headless=headless,
        personal=personal,
        enable_bridge=enable_bridge,
        open_file=open_file,
        login_state=login_enum,
        username=username,
        ephemeral_server=ephemeral_server,
        auto_auth_user=auto_auth_user,
        server_url=server_url,
    )

    if success and wait_seconds > 0:
        time.sleep(wait_seconds)

    if not success:
        TestInstance._instances.pop(instance.id, None)
        if TestInstance._current_id == instance.id:
            remaining = list(TestInstance._instances.keys())
            TestInstance._current_id = remaining[-1] if remaining else None

    return {
        "success": success,
        "instance_id": instance.id if success else None,
        "pid": instance.pid,
        "message": message,
        "bridge_connected": instance.bridge.is_connected if instance.bridge else False,
        "bridge_port": instance._bridge_port,
        "server_port": instance._server_port,
    }


@mcp.tool()
def close_app(force: bool = False, instance_id: Optional[str] = None) -> Dict[str, Any]:
    """Close app instance. Use force=True to kill. Defaults to most recent instance."""
    instance, err = _resolve_instance(instance_id)
    if err:
        return err
    success, message = instance.close(force=force)
    return {"success": success, "message": message}


@mcp.tool()
def close_all_instances() -> Dict[str, Any]:
    """Close all running test instances. Use for cleanup."""
    closed = TestInstance.close_all()
    return {"success": True, "closed": closed, "count": len(closed)}


@mcp.tool()
def launch_app_in_simulator(
    app_path: Optional[str] = None,
    bundle_id: str = "com.vedanamedia.familydiagram",
    udid: Optional[str] = None,
    ephemeral_server: bool = False,
    auto_auth_user: str = "test@example.com",
    login_state: str = LoginState.LoggedIn.value,
) -> Dict[str, Any]:
    """Launch the Personal app in the iOS Simulator with full bridge interactivity.

    The app must be pre-built for the simulator. Default app_path is the
    Debug-iphonesimulator build in the repo. Bridge auto-starts on port 9876
    in simulator builds — all interaction tools (click, scroll, etc.) work.

    Args:
        app_path: Path to .app bundle (defaults to build/ios/Debug-iphonesimulator/Family Diagram.app)
        bundle_id: iOS bundle identifier
        udid: Simulator UDID (auto-selects iPhone if omitted)
        ephemeral_server: Start isolated btcopilot server
        auto_auth_user: Email for auto-auth
        login_state: 'no_data' or 'logged_in'
    """
    if app_path is None:
        default_path = (
            Path(__file__).parent.parent
            / "build"
            / "ios"
            / "Debug-iphonesimulator"
            / "Family Diagram.app"
        )
        if not default_path.exists():
            return {
                "success": False,
                "error": f"No iOS simulator build found at {default_path}. Build the app first.",
            }
        app_path = str(default_path)

    try:
        login_enum = LoginState(login_state)
    except ValueError:
        return {"success": False, "error": f"Invalid login_state: {login_state}"}

    instance = TestInstance.create()

    try:
        # Optional ephemeral server
        if ephemeral_server:
            sandbox_env = instance._sandbox.create_sandbox(personal=True)
            ok, msg = instance._start_ephemeral_server(auto_auth_user)
            if not ok:
                instance._sandbox.cleanup()
                TestInstance._instances.pop(instance.id, None)
                return {"success": False, "error": msg}

            server_url = f"http://127.0.0.1:{instance._server_port}"
            if login_enum == LoginState.LoggedIn:
                instance._seed_default_user(auto_auth_user)

        # Launch in simulator
        ok, msg = instance._launch_in_simulator(app_path, bundle_id, udid)
        if not ok:
            instance._stop_ephemeral_server()
            instance._sandbox.cleanup()
            TestInstance._instances.pop(instance.id, None)
            return {"success": False, "error": msg}

        return {
            "success": True,
            "instance_id": instance.id,
            "sim_udid": instance._sim_udid,
            "bridge_port": instance._bridge_port,
            "server_port": instance._server_port,
            "message": msg,
        }
    except Exception as e:
        instance._terminate_simulator_app()
        instance._stop_ephemeral_server()
        instance._sandbox.cleanup()
        TestInstance._instances.pop(instance.id, None)
        return {"success": False, "error": str(e)}


@mcp.tool()
def get_app_state(
    include_process: bool = False, instance_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get app state. Use FIRST before other tools. Returns windows, dialogs, semantic state."""
    instance, err = _resolve_instance(instance_id)
    if err:
        return err

    result = {}
    if include_process:
        result.update(
            {
                "instance_id": instance.id,
                "running": instance.is_running,
                "pid": instance.pid,
                "uptime": instance.uptime,
                "server_port": instance.server_port,
                "bridge_port": instance._bridge_port,
            }
        )

    if not instance.bridge or not instance.bridge.is_connected:
        result["success"] = False
        result["error"] = "Bridge not connected"
        return result

    response = instance.bridge.send_command({"command": "get_app_state"})
    result.update(response)
    return result


@mcp.tool()
def open_file(file_path: str, instance_id: Optional[str] = None) -> Dict[str, Any]:
    """Open .fd file by path."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err
    return bridge.send_command({"command": "open_file", "filePath": file_path})


@mcp.tool()
def open_server_diagram(
    diagram_id: int, instance_id: Optional[str] = None
) -> Dict[str, Any]:
    """Open a server diagram by ID — same code path as clicking in the file manager.
    Requires the app to be logged in (login_state='logged_in').
    """
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err
    return bridge.send_command(
        {"command": "open_server_diagram", "diagramId": diagram_id}
    )


# =============================================================================
# MCP Tools - Element Inspection (via Bridge)
# =============================================================================


@mcp.tool()
def find_element(name: str, instance_id: Optional[str] = None) -> Dict[str, Any]:
    """Find element by objectName. Returns {name, type, text}."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err

    return bridge.send_command({"command": "find_element", "objectName": name})


@mcp.tool()
def list_elements(
    type: Optional[str] = None,
    depth: int = 3,
    limit: int = 50,
    verbose: bool = False,
    instance_id: Optional[str] = None,
) -> Dict[str, Any]:
    """List named visible elements. Returns [{name, type, text}]. Use get_app_state() first."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err

    response = bridge.send_command(
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
def prop(
    name: str, property: str, value: Any = None, instance_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get/set element property. Omit value to get, provide value to set."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err

    if value is None:
        return bridge.send_command(
            {"command": "get_property", "objectName": name, "property": property}
        )
    else:
        return bridge.send_command(
            {
                "command": "set_property",
                "objectName": name,
                "property": property,
                "value": value,
            }
        )


@mcp.tool()
def click(
    name: str,
    double: bool = False,
    button: str = "left",
    instance_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Click element. Use double=True for double-click."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err

    cmd = "double_click" if double else "click"
    return bridge.send_command({"command": cmd, "objectName": name, "button": button})


@mcp.tool()
def drag(
    name: str,
    startX: int,
    startY: int,
    endX: int,
    endY: int,
    button: str = "left",
    steps: int = 10,
    instance_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Drag within element from (startX, startY) to (endX, endY). Coordinates relative to element."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err

    return bridge.send_command(
        {
            "command": "drag",
            "objectName": name,
            "startPos": [startX, startY],
            "endPos": [endX, endY],
            "button": button,
            "steps": steps,
        }
    )


@mcp.tool()
def input(
    text: str = None,
    key: str = None,
    name: str = None,
    modifiers: List[str] = None,
    instance_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Type text or press key. Provide text for typing, key for key press."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err

    if text is not None:
        return bridge.send_command(
            {"command": "type_text", "text": text, "objectName": name}
        )
    elif key is not None:
        return bridge.send_command(
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
def hover(
    name: str,
    x: Optional[int] = None,
    y: Optional[int] = None,
    instance_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Hover over element (triggers tooltips, hover states). Maps to iOS long-press entry."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err
    pos = [x, y] if x is not None and y is not None else None
    return bridge.send_command({"command": "hover", "objectName": name, "pos": pos})


@mcp.tool()
def scroll(
    name: str,
    direction: str = "up",
    amount: int = 100,
    instance_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Scroll element by simulating a swipe drag. direction: up/down/left/right. amount: pixels.
    iOS semantics: scroll 'up' moves content upward (finger drags up)."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err
    return bridge.send_command(
        {
            "command": "scroll",
            "objectName": name,
            "direction": direction,
            "amount": amount,
        }
    )


@mcp.tool()
def long_press(
    name: str, duration_ms: int = 500, instance_id: Optional[str] = None
) -> Dict[str, Any]:
    """Long-press element (iOS context menu / haptic trigger equivalent)."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err
    return bridge.send_command(
        {"command": "long_press", "objectName": name, "durationMs": duration_ms}
    )


@mcp.tool()
def get_text(name: str, instance_id: Optional[str] = None) -> Dict[str, Any]:
    """Read visible text from element without knowing property name."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err
    return bridge.send_command({"command": "get_text", "objectName": name})


@mcp.tool()
def get_bounds(name: str, instance_id: Optional[str] = None) -> Dict[str, Any]:
    """Get element bounding box {x, y, width, height} in global screen coordinates."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err
    return bridge.send_command({"command": "get_bounds", "objectName": name})


# iPhone viewport presets (logical points, not pixels)
_IPHONE_PRESETS = {
    "iphone_se": (375, 667),
    "iphone_14": (390, 844),
    "iphone_14_pro_max": (430, 932),
    "iphone_16_pro": (393, 852),
}


@mcp.tool()
def resize_window(
    width: Optional[int] = None,
    height: Optional[int] = None,
    preset: Optional[str] = None,
    instance_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Resize app window to simulate iPhone viewport. preset: iphone_se / iphone_14 / iphone_14_pro_max / iphone_16_pro."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err

    if preset:
        if preset not in _IPHONE_PRESETS:
            return {
                "success": False,
                "error": f"Unknown preset '{preset}'. Options: {list(_IPHONE_PRESETS)}",
            }
        width, height = _IPHONE_PRESETS[preset]
    elif width is None or height is None:
        return {"success": False, "error": "Provide width+height or preset"}

    return bridge.send_command(
        {"command": "resize_window", "width": width, "height": height}
    )


@mcp.tool()
def layout_bounds(instance_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get scene bounding rects for all persons, their name labels (ItemDetails), and R symbols (Emotions).
    Returns {persons: [{id, name, gender, rect}], labels: [{parent_id, text, rect}], emotions: [{id, kind, person_id, target_id, rect}]}.
    rect fields: x, y, w, h (scene coordinates).
    Use to detect label/R-symbol collisions and calibrate the layout algorithm.
    """
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err
    return bridge.send_command({"command": "get_layout_bounds"})


@mcp.tool()
def scene(
    action: str = "list",
    name: str = None,
    type: str = None,
    button: str = "left",
    instance_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Scene items. action="list" to list items, action="click" with name to click."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err

    if action == "list":
        return bridge.send_command({"command": "get_scene_items", "type": type})
    elif action == "click" and name:
        return bridge.send_command(
            {"command": "click_scene_item", "name": name, "button": button}
        )
    else:
        return {
            "success": False,
            "error": "Use action='list' or action='click' with name",
        }


@mcp.tool()
def window(name: str = None, instance_id: Optional[str] = None) -> Dict[str, Any]:
    """List windows if no name, activate window if name provided."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err

    if name is None:
        return bridge.send_command({"command": "get_windows"})
    else:
        return bridge.send_command({"command": "activate_window", "objectName": name})


@mcp.tool()
def screenshot(
    action: str = "take",
    name: str = None,
    baseline: str = None,
    current: str = None,
    threshold: float = 0.01,
    instance_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Screenshots. action="take"(default), "list", or "compare" with baseline path."""
    instance, err = _resolve_instance(instance_id)
    if err:
        return err

    if action == "list":
        screenshot_dir = instance.project_root / "screenshots"
        if not screenshot_dir.exists():
            return {"success": True, "screenshots": [], "count": 0}
        screenshots = sorted(screenshot_dir.glob("*.png"))
        return {
            "success": True,
            "screenshots": [str(p) for p in screenshots],
            "count": len(screenshots),
        }

    elif action == "take":
        if not instance.is_running:
            return {"success": False, "error": "App not running"}
        if not instance.bridge or not instance.bridge.is_connected:
            return {"success": False, "error": "Bridge not connected"}

        try:
            from PIL import Image
            from datetime import datetime
            import io

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"{timestamp}_{name}" if name else timestamp
            output_path = instance.get_screenshot_path(fname)

            response = instance.bridge.send_command({"command": "take_screenshot"})
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
                if not instance.bridge or not instance.bridge.is_connected:
                    return {"success": False, "error": "Bridge not connected"}
                response = instance.bridge.send_command({"command": "take_screenshot"})
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
    stream: str = "both",
    last_n: Optional[int] = None,
    clear: bool = False,
    instance_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get app stdout/stderr. stream="stdout", "stderr", or "both"."""
    instance, err = _resolve_instance(instance_id)
    if err:
        return err

    if not instance.is_running:
        return {"success": False, "error": "App not running"}

    instance.collect_output()
    result = {"success": True}

    if stream in ("stdout", "both"):
        lines = instance._stdout_lines[-last_n:] if last_n else instance._stdout_lines
        result["stdout"] = lines
    if stream in ("stderr", "both"):
        lines = instance._stderr_lines[-last_n:] if last_n else instance._stderr_lines
        result["stderr"] = lines

    if clear:
        if stream in ("stdout", "both"):
            instance._stdout_lines.clear()
        if stream in ("stderr", "both"):
            instance._stderr_lines.clear()

    return result


@mcp.tool()
def check_app_errors(
    since: int = 0,
    instance_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Check for errors in app output (stdout). Returns error lines since a given index.

    The app logs errors to stdout, not stderr. Always use this instead of
    manually checking stderr.

    Args:
        since: Only check lines after this index (use 0 for all). Pass the
               'next_index' from a previous call to check only new errors.
    """
    instance, err = _resolve_instance(instance_id)
    if err:
        return err

    errors = instance.collectErrors(since=since)
    return {
        "success": True,
        "errors": errors,
        "count": len(errors),
        "next_index": len(instance._stdout_lines),
    }


@mcp.tool()
def report_testing_limitation(
    feature: str,
    missing_controls: List[str],
    workaround: Optional[str] = None,
    instance_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Report missing objectNames needed to test a feature. Logged for developer action."""
    instance, err = _resolve_instance(instance_id)
    if err:
        return err

    limitation = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "feature": feature,
        "missing_controls": missing_controls,
        "workaround": workaround,
    }

    logger.warning(
        f"Testing limitation: {feature} - missing: {', '.join(missing_controls)}"
    )

    limitations_file = (
        instance.project_root / "screenshots" / "testing_limitations.json"
    )
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
# MCP Tools - Data Seeding
# =============================================================================


@mcp.tool()
def seed_server_data(
    data: Dict[str, Any], instance_id: Optional[str] = None
) -> Dict[str, Any]:
    """Seed test data into the ephemeral server. Requires ephemeral_server=True on launch.

    data: dict with optional 'users' and 'diagrams' lists.
    Users: {username, password, first_name, last_name, status}
    Diagrams: {user_id, data}
    """
    instance, err = _resolve_instance(instance_id)
    if err:
        return err

    if not instance.server_port:
        return {
            "success": False,
            "error": "No ephemeral server for this instance. Launch with ephemeral_server=True.",
        }

    import requests

    try:
        response = requests.post(
            f"http://127.0.0.1:{instance.server_port}/test/seed",
            json=data,
            timeout=10,
        )
        return response.json()
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# MCP Tools - Personal App State
# =============================================================================


@mcp.tool()
def personal_state(
    component: str = "all", instance_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get Personal app state. component: 'all', 'learn', 'discuss', 'plan', 'pdp'."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err

    return bridge.send_command(
        {"command": "get_personal_state", "component": component}
    )


@mcp.tool()
def inject_pdp_data(
    data: Dict[str, Any], instance_id: Optional[str] = None
) -> Dict[str, Any]:
    """Inject test PDP data into the running Personal app.

    data: dict with 'people', 'events', 'pair_bonds' lists.
    People: {id, name, last_name, gender}
    Events: {id, kind, person, description, notes, dateTime, symptom, anxiety, functioning, ...}
    EventKind: 'shift', 'birth', 'married', 'separated', 'divorced', 'death', 'moved', 'bonded', 'adopted'
    VariableShift: 'up', 'down', 'same'
    """
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err

    return bridge.send_command({"command": "inject_pdp_data", "data": data})


@mcp.tool()
def open_pdp_sheet(instance_id: Optional[str] = None) -> Dict[str, Any]:
    """Open the PDP sheet drawer in the Personal app."""
    bridge, err = _resolve_bridge(instance_id)
    if err:
        return err

    return bridge.send_command({"command": "open_pdp_sheet"})


# =============================================================================
# MCP Tools - iOS Simulator
# =============================================================================


def _simctl(*args, timeout: int = 30) -> Tuple[bool, str]:
    """Run xcrun simctl command. Returns (success, output)."""
    cmd = ["xcrun", "simctl"] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip() or result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s"
    except FileNotFoundError:
        return False, "xcrun not found — Xcode command line tools required"


def _booted_udid() -> Optional[str]:
    """Return UDID of first booted simulator, or None."""
    ok, out = _simctl("list", "devices", "booted", "--json")
    if not ok:
        return None
    try:
        data = json.loads(out)
        for runtime_devices in data.get("devices", {}).values():
            for device in runtime_devices:
                if device.get("state") == "Booted":
                    return device["udid"]
    except (json.JSONDecodeError, KeyError):
        pass
    return None


@mcp.tool()
def sim_list() -> Dict[str, Any]:
    """List available iOS simulators with their UDIDs and boot state."""
    ok, out = _simctl("list", "devices", "available", "--json")
    if not ok:
        return {"success": False, "error": out}
    try:
        data = json.loads(out)
        devices = []
        for runtime, runtime_devices in data.get("devices", {}).items():
            for d in runtime_devices:
                devices.append(
                    {
                        "name": d["name"],
                        "udid": d["udid"],
                        "state": d["state"],
                        "runtime": runtime.replace(
                            "com.apple.CoreSimulator.SimRuntime.", ""
                        ),
                    }
                )
        booted = [d for d in devices if d["state"] == "Booted"]
        return {"success": True, "devices": devices, "booted": booted}
    except (json.JSONDecodeError, KeyError) as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def sim_boot(udid: Optional[str] = None) -> Dict[str, Any]:
    """Boot a simulator. Omit udid to boot first available device. Opens Simulator.app."""
    if udid is None:
        ok, out = _simctl("list", "devices", "available", "--json")
        if not ok:
            return {"success": False, "error": out}
        try:
            data = json.loads(out)
            for runtime_devices in data.get("devices", {}).values():
                for d in runtime_devices:
                    udid = d["udid"]
                    break
                if udid:
                    break
        except (json.JSONDecodeError, KeyError):
            pass
        if not udid:
            return {"success": False, "error": "No available simulator found"}

    ok, out = _simctl("boot", udid, timeout=60)
    if not ok and "already booted" not in out.lower():
        return {"success": False, "error": out}

    # Open Simulator.app so the window is visible
    subprocess.Popen(["open", "-a", "Simulator"])

    return {"success": True, "udid": udid, "message": "Booted. Simulator.app opened."}


@mcp.tool()
def sim_screenshot(udid: Optional[str] = None) -> Dict[str, Any]:
    """Take screenshot of booted simulator. Returns base64 PNG + saves to screenshots/."""
    target = udid or _booted_udid() or "booted"

    screenshot_dir = Path(__file__).parent.parent / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = screenshot_dir / f"sim_{timestamp}.png"

    ok, out = _simctl("io", target, "screenshot", str(output_path), timeout=15)
    if not ok:
        return {"success": False, "error": out}

    try:
        from PIL import Image
        import io as _io

        img = Image.open(str(output_path))
        max_dim = 1920
        if img.width > max_dim or img.height > max_dim:
            ratio = min(max_dim / img.width, max_dim / img.height)
            img = img.resize(
                (int(img.width * ratio), int(img.height * ratio)),
                Image.Resampling.LANCZOS,
            )
            img.save(str(output_path), "PNG")

        buf = _io.BytesIO()
        img.save(buf, "PNG")
        image_data = base64.b64encode(buf.getvalue()).decode("utf-8")
        return {
            "success": True,
            "path": str(output_path),
            "width": img.width,
            "height": img.height,
            "data": image_data,
        }
    except ImportError:
        with open(output_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        return {"success": True, "path": str(output_path), "data": image_data}


@mcp.tool()
def sim_install(app_path: str, udid: Optional[str] = None) -> Dict[str, Any]:
    """Install .app bundle to simulator. app_path must be path to .app directory."""
    target = udid or _booted_udid() or "booted"
    ok, out = _simctl("install", target, app_path, timeout=60)
    return {"success": ok, "message": out}


@mcp.tool()
def sim_launch(
    bundle_id: str,
    udid: Optional[str] = None,
    wait_for_debugger: bool = False,
) -> Dict[str, Any]:
    """Launch app in simulator by bundle ID. Returns pid."""
    target = udid or _booted_udid() or "booted"
    args = ["launch", target, bundle_id]
    if wait_for_debugger:
        args.append("--wait-for-debugger")
    ok, out = _simctl(*args, timeout=30)
    return {"success": ok, "message": out}


@mcp.tool()
def sim_terminate(bundle_id: str, udid: Optional[str] = None) -> Dict[str, Any]:
    """Terminate running app in simulator."""
    target = udid or _booted_udid() or "booted"
    ok, out = _simctl("terminate", target, bundle_id)
    return {"success": ok, "message": out}


@mcp.tool()
def sim_log(
    bundle_id: Optional[str] = None,
    last_n: int = 50,
    udid: Optional[str] = None,
) -> Dict[str, Any]:
    """Get recent simulator log entries. Optionally filter by bundle_id process name."""
    target = udid or _booted_udid() or "booted"

    # Use log stream with a short timeout to capture recent entries
    cmd = [
        "xcrun",
        "simctl",
        "spawn",
        target,
        "log",
        "show",
        "--last",
        "30s",
        "--style",
        "compact",
    ]
    if bundle_id:
        # Extract process name from bundle ID (last component)
        process = bundle_id.split(".")[-1]
        cmd += ["--predicate", f'process == "{process}"']

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        lines = (result.stdout or result.stderr or "").strip().splitlines()
        return {"success": True, "lines": lines[-last_n:], "count": len(lines)}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Log command timed out"}
    except FileNotFoundError:
        return {"success": False, "error": "xcrun not found"}


if __name__ == "__main__":
    threading.Thread(target=_parent_death_watchdog, daemon=True).start()
    logger.info("Starting Family Diagram MCP Testing Server")
    mcp.run(transport="stdio")
