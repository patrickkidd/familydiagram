"""
Client library for the Map Server.

This module provides a Python client for interacting with the Map Server API,
making it easy to write end-to-end tests.
"""

import base64
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

log = logging.getLogger(__name__)


class MapClientError(Exception):
    """Exception raised for Map Server client errors."""
    pass


class MapClient:
    """
    Client for interacting with the Map Server.

    This client provides a convenient Python API for controlling the application
    and performing UI interactions through the Map Server.

    Usage:
        # Start server as subprocess
        client = MapClient(port=8765)
        client.startServer()

        # Or connect to existing server
        client = MapClient(port=8765)
        client.connect()

        # Initialize app and create window
        client.initApp()
        client.createWindow()

        # Interact with UI
        client.click("buttonName")
        client.type("Hello", target="textField")

        # Take snapshots
        snapshot = client.capture()
        client.assertSnapshot("baseline_name")

        # Cleanup
        client.shutdown()
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        timeout: float = 30.0,
    ):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._baseUrl = f"http://{host}:{port}"
        self._serverProcess: Optional[subprocess.Popen] = None
        self._connected = False

    @property
    def baseUrl(self) -> str:
        """Get the base URL for the server."""
        return self._baseUrl

    @property
    def isConnected(self) -> bool:
        """Check if connected to the server."""
        return self._connected

    # -------------------------------------------------------------------------
    # Server Management
    # -------------------------------------------------------------------------

    def startServer(
        self,
        headless: bool = True,
        snapshotDir: Optional[str] = None,
        waitForReady: bool = True,
        startupTimeout: float = 30.0,
    ) -> bool:
        """
        Start the Map Server as a subprocess.

        Args:
            headless: Run in headless mode (no display)
            snapshotDir: Directory for snapshots
            waitForReady: Wait for server to be ready
            startupTimeout: Maximum time to wait for startup

        Returns:
            True if server started successfully
        """
        if self._serverProcess is not None:
            log.warning("Server already running")
            return True

        # Build command
        cmd = [
            sys.executable,
            "-m",
            "pkdiagram.mapserver.runner",
            "--host", self._host,
            "--port", str(self._port),
        ]

        if headless:
            cmd.append("--headless")

        if snapshotDir:
            cmd.extend(["--snapshot-dir", snapshotDir])

        # Start process
        try:
            self._serverProcess = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            log.info(f"Started Map Server process (PID: {self._serverProcess.pid})")

        except Exception as e:
            log.error(f"Failed to start server: {e}")
            return False

        if waitForReady:
            return self._waitForServer(startupTimeout)

        return True

    def _waitForServer(self, timeout: float) -> bool:
        """Wait for the server to be ready."""
        startTime = time.time()

        while time.time() - startTime < timeout:
            try:
                response = self._get("/app/status")
                if response.get("success"):
                    self._connected = True
                    log.info("Map Server is ready")
                    return True
            except (URLError, MapClientError):
                pass

            # Check if process died
            if self._serverProcess and self._serverProcess.poll() is not None:
                stderr = self._serverProcess.stderr.read().decode() if self._serverProcess.stderr else ""
                log.error(f"Server process died: {stderr}")
                return False

            time.sleep(0.5)

        log.error("Timeout waiting for server")
        return False

    def connect(self, timeout: float = 5.0) -> bool:
        """
        Connect to an existing Map Server.

        Args:
            timeout: Connection timeout

        Returns:
            True if connected successfully
        """
        return self._waitForServer(timeout)

    def stopServer(self):
        """Stop the Map Server subprocess."""
        if self._serverProcess is None:
            return

        try:
            # Try graceful shutdown first
            self._post("/app/shutdown", {})
            self._serverProcess.wait(timeout=5)
        except Exception:
            # Force kill if needed
            self._serverProcess.terminate()
            try:
                self._serverProcess.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._serverProcess.kill()

        self._serverProcess = None
        self._connected = False
        log.info("Map Server stopped")

    # -------------------------------------------------------------------------
    # HTTP Communication
    # -------------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the server."""
        url = f"{self._baseUrl}{path}"

        if method == "GET" and data:
            # Add query params
            params = "&".join(f"{k}={v}" for k, v in data.items())
            url = f"{url}?{params}"
            body = None
        else:
            body = json.dumps(data).encode("utf-8") if data else None

        request = Request(url, data=body, method=method)
        request.add_header("Content-Type", "application/json")

        try:
            with urlopen(request, timeout=self._timeout) as response:
                return json.loads(response.read().decode("utf-8"))

        except HTTPError as e:
            body = e.read().decode("utf-8")
            try:
                error_data = json.loads(body)
                raise MapClientError(error_data.get("error", str(e)))
            except json.JSONDecodeError:
                raise MapClientError(f"HTTP {e.code}: {body}")

        except URLError as e:
            raise MapClientError(f"Connection error: {e.reason}")

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request."""
        return self._request("GET", path, params)

    def _post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request."""
        return self._request("POST", path, data)

    # -------------------------------------------------------------------------
    # Application Control
    # -------------------------------------------------------------------------

    def initApp(self, headless: bool = True) -> bool:
        """
        Initialize the application.

        Args:
            headless: Run in headless mode

        Returns:
            True if successful
        """
        response = self._post("/app/init", {"headless": headless})
        return response.get("success", False)

    def shutdown(self):
        """Shutdown the application and server."""
        try:
            self._post("/app/shutdown", {})
        except MapClientError:
            pass

        self.stopServer()

    def createWindow(self, show: bool = True) -> bool:
        """
        Create the main window.

        Args:
            show: Whether to show the window

        Returns:
            True if successful
        """
        response = self._post("/app/create-window", {"show": show})
        return response.get("success", False)

    def loadFile(self, path: str) -> bool:
        """
        Load a diagram file.

        Args:
            path: Path to the file

        Returns:
            True if successful
        """
        response = self._post("/app/load-file", {"path": str(path)})
        return response.get("success", False)

    def newDocument(self) -> bool:
        """
        Create a new document.

        Returns:
            True if successful
        """
        response = self._post("/app/new-document", {})
        return response.get("success", False)

    def processEvents(self, timeout: int = 100):
        """
        Process Qt events.

        Args:
            timeout: Processing timeout in ms
        """
        self._post("/app/process-events", {"timeout": timeout})

    def getStatus(self) -> Dict[str, Any]:
        """
        Get application status.

        Returns:
            Status dict with keys: initialized, hasMainWindow, hasDocument, hasScene
        """
        return self._get("/app/status")

    # -------------------------------------------------------------------------
    # Input Simulation
    # -------------------------------------------------------------------------

    def click(
        self,
        target: str,
        button: int = 1,  # Left button
        pos: Optional[Tuple[int, int]] = None,
        modifiers: int = 0,
    ) -> bool:
        """
        Click on an element.

        Args:
            target: Element objectName
            button: Mouse button (1=left, 2=right, 4=middle)
            pos: Optional (x, y) position
            modifiers: Keyboard modifiers

        Returns:
            True if successful
        """
        data = {"target": target, "button": button, "modifiers": modifiers}
        if pos:
            data["pos"] = list(pos)

        response = self._post("/input/click", data)
        return response.get("success", False)

    def doubleClick(
        self,
        target: str,
        button: int = 1,
        pos: Optional[Tuple[int, int]] = None,
        modifiers: int = 0,
    ) -> bool:
        """
        Double-click on an element.

        Args:
            target: Element objectName
            button: Mouse button
            pos: Optional position
            modifiers: Keyboard modifiers

        Returns:
            True if successful
        """
        data = {"target": target, "button": button, "modifiers": modifiers}
        if pos:
            data["pos"] = list(pos)

        response = self._post("/input/double-click", data)
        return response.get("success", False)

    def type(
        self,
        text: str,
        target: Optional[str] = None,
        modifiers: int = 0,
    ) -> bool:
        """
        Type text into an element.

        Args:
            text: Text to type
            target: Optional element to focus first
            modifiers: Keyboard modifiers

        Returns:
            True if successful
        """
        data = {"text": text, "modifiers": modifiers}
        if target:
            data["target"] = target

        response = self._post("/input/type", data)
        return response.get("success", False)

    def keyPress(
        self,
        key: str,
        target: Optional[str] = None,
        modifiers: int = 0,
    ) -> bool:
        """
        Press a single key.

        Args:
            key: Key name (e.g., "enter", "escape", "a")
            target: Optional element to focus first
            modifiers: Keyboard modifiers

        Returns:
            True if successful
        """
        data = {"key": key, "modifiers": modifiers}
        if target:
            data["target"] = target

        response = self._post("/input/key", data)
        return response.get("success", False)

    def keySequence(
        self,
        keys: List[str],
        target: Optional[str] = None,
    ) -> bool:
        """
        Press a sequence of keys.

        Args:
            keys: List of key names (e.g., ["ctrl+s", "escape"])
            target: Optional element to focus first

        Returns:
            True if successful
        """
        data = {"keys": keys}
        if target:
            data["target"] = target

        response = self._post("/input/keys", data)
        return response.get("success", False)

    def drag(
        self,
        target: str,
        startPos: Tuple[int, int],
        endPos: Tuple[int, int],
        button: int = 1,
        steps: int = 10,
    ) -> bool:
        """
        Drag from one position to another.

        Args:
            target: Element objectName
            startPos: Start position
            endPos: End position
            button: Mouse button
            steps: Number of intermediate steps

        Returns:
            True if successful
        """
        response = self._post("/input/drag", {
            "target": target,
            "startPos": list(startPos),
            "endPos": list(endPos),
            "button": button,
            "steps": steps,
        })
        return response.get("success", False)

    def scroll(
        self,
        target: str,
        delta: int,
        horizontal: bool = False,
        pos: Optional[Tuple[int, int]] = None,
    ) -> bool:
        """
        Scroll an element.

        Args:
            target: Element objectName
            delta: Scroll amount (positive = up/left)
            horizontal: If True, scroll horizontally
            pos: Optional position to scroll at

        Returns:
            True if successful
        """
        data = {
            "target": target,
            "delta": delta,
            "orientation": 2 if horizontal else 1,  # Qt.Horizontal=2, Qt.Vertical=1
        }
        if pos:
            data["pos"] = list(pos)

        response = self._post("/input/scroll", data)
        return response.get("success", False)

    def focus(self, target: str) -> bool:
        """
        Set focus to an element.

        Args:
            target: Element objectName

        Returns:
            True if successful
        """
        response = self._post("/input/focus", {"target": target})
        return response.get("success", False)

    def mouseMove(
        self,
        target: str,
        pos: Tuple[int, int],
        modifiers: int = 0,
    ) -> bool:
        """
        Move mouse to a position.

        Args:
            target: Element objectName
            pos: Position relative to element
            modifiers: Keyboard modifiers

        Returns:
            True if successful
        """
        response = self._post("/input/mouse-move", {
            "target": target,
            "pos": list(pos),
            "modifiers": modifiers,
        })
        return response.get("success", False)

    # -------------------------------------------------------------------------
    # Graphics Items
    # -------------------------------------------------------------------------

    def clickGraphicsItem(
        self,
        item: str,
        button: int = 1,
        modifiers: int = 0,
    ) -> bool:
        """
        Click on a graphics item in the scene.

        Args:
            item: Item name
            button: Mouse button
            modifiers: Keyboard modifiers

        Returns:
            True if successful
        """
        response = self._post("/graphics/click", {
            "item": item,
            "button": button,
            "modifiers": modifiers,
        })
        return response.get("success", False)

    def doubleClickGraphicsItem(
        self,
        item: str,
        button: int = 1,
        modifiers: int = 0,
    ) -> bool:
        """
        Double-click on a graphics item.

        Args:
            item: Item name
            button: Mouse button
            modifiers: Keyboard modifiers

        Returns:
            True if successful
        """
        response = self._post("/graphics/double-click", {
            "item": item,
            "button": button,
            "modifiers": modifiers,
        })
        return response.get("success", False)

    def dragGraphicsItem(
        self,
        item: str,
        deltaX: int,
        deltaY: int,
        button: int = 1,
    ) -> bool:
        """
        Drag a graphics item.

        Args:
            item: Item name
            deltaX: Horizontal drag distance
            deltaY: Vertical drag distance
            button: Mouse button

        Returns:
            True if successful
        """
        response = self._post("/graphics/drag", {
            "item": item,
            "deltaX": deltaX,
            "deltaY": deltaY,
            "button": button,
        })
        return response.get("success", False)

    # -------------------------------------------------------------------------
    # Snapshots
    # -------------------------------------------------------------------------

    def capture(
        self,
        target: Optional[str] = None,
        format: str = "PNG",
    ) -> bytes:
        """
        Capture a screenshot.

        Args:
            target: Optional element objectName (None = whole window)
            format: Image format

        Returns:
            Image data as bytes
        """
        data = {"format": format}
        if target:
            data["target"] = target

        response = self._post("/snapshot/capture", data)

        if not response.get("success"):
            raise MapClientError(response.get("error", "Failed to capture snapshot"))

        return base64.b64decode(response["data"])

    def captureScreen(self, format: str = "PNG") -> bytes:
        """
        Capture the entire screen.

        Args:
            format: Image format

        Returns:
            Image data as bytes
        """
        response = self._post("/snapshot/capture", {
            "target": "__screen__",
            "format": format,
        })

        if not response.get("success"):
            raise MapClientError(response.get("error", "Failed to capture screen"))

        return base64.b64decode(response["data"])

    def saveSnapshot(
        self,
        name: str,
        data: Optional[bytes] = None,
        target: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Save a snapshot.

        Args:
            name: Snapshot name
            data: Optional image data (captures current if not provided)
            target: Optional element to capture
            metadata: Optional metadata

        Returns:
            Path to saved snapshot
        """
        requestData = {"name": name}

        if data:
            requestData["data"] = base64.b64encode(data).decode("utf-8")
        elif target:
            requestData["target"] = target

        if metadata:
            requestData["metadata"] = metadata

        response = self._post("/snapshot/save", requestData)

        if not response.get("success"):
            raise MapClientError(response.get("error", "Failed to save snapshot"))

        return response["path"]

    def loadSnapshot(self, name: str) -> Tuple[bytes, Optional[Dict[str, Any]]]:
        """
        Load a snapshot.

        Args:
            name: Snapshot name

        Returns:
            Tuple of (image data, metadata)
        """
        response = self._get("/snapshot/load", {"name": name})

        if not response.get("success"):
            raise MapClientError(response.get("error", "Failed to load snapshot"))

        data = base64.b64decode(response["data"])
        metadata = response.get("metadata")

        return data, metadata

    def listSnapshots(self) -> List[str]:
        """
        List all saved snapshots.

        Returns:
            List of snapshot names
        """
        response = self._get("/snapshot/list")
        return response.get("snapshots", [])

    def compareSnapshot(
        self,
        name: str,
        current: Optional[bytes] = None,
        target: Optional[str] = None,
        threshold: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Compare current state with a baseline snapshot.

        Args:
            name: Baseline snapshot name
            current: Optional current image data
            target: Optional element to capture
            threshold: Acceptable difference threshold (0.0-1.0)

        Returns:
            Comparison result dict
        """
        data = {"name": name, "threshold": threshold}

        if current:
            data["current"] = base64.b64encode(current).decode("utf-8")
        elif target:
            data["target"] = target

        return self._post("/snapshot/compare", data)

    def assertSnapshot(
        self,
        name: str,
        target: Optional[str] = None,
        threshold: float = 0.0,
        updateOnFail: bool = False,
    ) -> bool:
        """
        Assert that current state matches baseline.

        Args:
            name: Baseline snapshot name
            target: Optional element to capture
            threshold: Acceptable difference threshold
            updateOnFail: Update baseline if comparison fails

        Returns:
            True if match

        Raises:
            AssertionError: If snapshots don't match
        """
        response = self._post("/snapshot/assert", {
            "name": name,
            "target": target,
            "threshold": threshold,
            "updateOnFail": updateOnFail,
        })

        if not response.get("match"):
            raise AssertionError(response.get("error", "Snapshot mismatch"))

        return True

    # -------------------------------------------------------------------------
    # Element Finding
    # -------------------------------------------------------------------------

    def findElement(self, objectName: str) -> Optional[Dict[str, Any]]:
        """
        Find an element by objectName.

        Args:
            objectName: Element objectName

        Returns:
            Dict with 'found' and 'type' keys, or None
        """
        response = self._get("/element/find", {"objectName": objectName})

        if response.get("found"):
            return response
        return None

    def getElementInfo(self, objectName: str) -> Dict[str, Any]:
        """
        Get detailed information about an element.

        Args:
            objectName: Element objectName

        Returns:
            Element information dict
        """
        response = self._get("/element/info", {"objectName": objectName})

        if not response.get("success"):
            raise MapClientError(response.get("error", "Element not found"))

        return response

    def getElementTree(
        self,
        treeType: str = "widget",
        maxDepth: int = 10,
    ) -> Dict[str, Any]:
        """
        Get the element tree structure.

        Args:
            treeType: "widget" or "qml"
            maxDepth: Maximum depth to traverse

        Returns:
            Tree structure
        """
        response = self._get("/element/tree", {
            "type": treeType,
            "maxDepth": maxDepth,
        })
        return response.get("tree", {})

    def getProperty(self, objectName: str, propertyName: str) -> Any:
        """
        Get an element's property value.

        Args:
            objectName: Element objectName
            propertyName: Property name

        Returns:
            Property value
        """
        response = self._get("/element/property", {
            "objectName": objectName,
            "property": propertyName,
        })
        return response.get("value")

    def setProperty(
        self,
        objectName: str,
        propertyName: str,
        value: Any,
    ) -> bool:
        """
        Set an element's property value.

        Args:
            objectName: Element objectName
            propertyName: Property name
            value: New value

        Returns:
            True if successful
        """
        response = self._post("/element/property", {
            "objectName": objectName,
            "property": propertyName,
            "value": value,
        })
        return response.get("success", False)

    def waitForElement(
        self,
        objectName: str,
        timeout: int = 5000,
        checkVisible: bool = True,
    ) -> bool:
        """
        Wait for an element to appear.

        Args:
            objectName: Element objectName
            timeout: Maximum wait time in ms
            checkVisible: Also wait for visibility

        Returns:
            True if element found
        """
        response = self._post("/element/wait", {
            "objectName": objectName,
            "timeout": timeout,
            "checkVisible": checkVisible,
        })
        return response.get("found", False)

    def waitForProperty(
        self,
        objectName: str,
        propertyName: str,
        expectedValue: Any,
        timeout: int = 5000,
    ) -> bool:
        """
        Wait for an element's property to reach a value.

        Args:
            objectName: Element objectName
            propertyName: Property name
            expectedValue: Expected value
            timeout: Maximum wait time in ms

        Returns:
            True if property reached expected value
        """
        response = self._post("/element/wait-property", {
            "objectName": objectName,
            "property": propertyName,
            "value": expectedValue,
            "timeout": timeout,
        })
        return response.get("found", False)

    # -------------------------------------------------------------------------
    # Scene Operations
    # -------------------------------------------------------------------------

    def getSceneItems(self, itemType: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get scene items.

        Args:
            itemType: Optional type filter (e.g., "Person", "Marriage")

        Returns:
            List of item info dicts
        """
        params = {}
        if itemType:
            params["type"] = itemType

        response = self._get("/scene/items", params)
        return response.get("items", [])

    def findSceneItem(
        self,
        name: Optional[str] = None,
        itemType: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a scene item.

        Args:
            name: Item name
            itemType: Item type

        Returns:
            Item info dict, or None if not found
        """
        params = {}
        if name:
            params["name"] = name
        if itemType:
            params["type"] = itemType

        response = self._get("/scene/find", params)

        if response.get("found"):
            return response.get("item")
        return None

    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------

    def waitAndClick(
        self,
        target: str,
        timeout: int = 5000,
        **kwargs,
    ) -> bool:
        """
        Wait for an element and click it.

        Args:
            target: Element objectName
            timeout: Maximum wait time
            **kwargs: Additional click arguments

        Returns:
            True if successful
        """
        if not self.waitForElement(target, timeout):
            return False
        return self.click(target, **kwargs)

    def typeAndEnter(
        self,
        text: str,
        target: Optional[str] = None,
    ) -> bool:
        """
        Type text and press Enter.

        Args:
            text: Text to type
            target: Optional element to focus

        Returns:
            True if successful
        """
        if not self.type(text, target):
            return False
        return self.keyPress("enter")

    def clearAndType(
        self,
        text: str,
        target: str,
    ) -> bool:
        """
        Clear a field and type new text.

        Args:
            text: Text to type
            target: Element objectName

        Returns:
            True if successful
        """
        # Select all and replace
        if not self.keySequence(["ctrl+a"], target):
            return False
        return self.type(text)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
        return False
