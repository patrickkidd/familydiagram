"""
Test Bridge Server - TCP server for Qt inspection.

This server runs inside the PyQt application and accepts JSON commands
from the MCP server (or other clients) to inspect and interact with Qt elements.
"""

import json
import logging
import socket
import threading
from typing import Optional, Dict, Any, Callable

from pkdiagram.pyqt import QObject, QTimer, pyqtSignal, QApplication

from .inspector import QtInspector

log = logging.getLogger(__name__)

# Default port for the test bridge
DEFAULT_PORT = 9876


class TestBridgeServer(QObject):
    """
    TCP server for Qt test bridge.

    This server:
    - Runs in a background thread
    - Accepts JSON commands over TCP
    - Executes Qt operations on the main thread
    - Returns JSON responses
    """

    # Signal to execute commands on the main thread
    _executeOnMain = pyqtSignal(object, object)

    def __init__(
        self,
        port: int = DEFAULT_PORT,
        host: str = "127.0.0.1",
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)

        self._port = port
        self._host = host
        self._socket: Optional[socket.socket] = None
        self._serverThread: Optional[threading.Thread] = None
        self._running = False

        self._inspector: Optional[QtInspector] = None

        # Connect signal for main thread execution
        self._executeOnMain.connect(self._onExecuteOnMain)

        # Command handlers
        self._handlers: Dict[str, Callable] = {}
        self._setupHandlers()

    def _setupHandlers(self):
        """Set up command handlers."""
        self._handlers = {
            # App state (high-level)
            "get_app_state": self._handleGetAppState,
            # Element finding
            "find_element": self._handleFindElement,
            "list_elements": self._handleListElements,
            # Properties
            "get_property": self._handleGetProperty,
            "set_property": self._handleSetProperty,
            # Interaction
            "click": self._handleClick,
            "double_click": self._handleDoubleClick,
            "type_text": self._handleTypeText,
            "press_key": self._handlePressKey,
            "focus": self._handleFocus,
            # Scene items
            "click_scene_item": self._handleClickSceneItem,
            "get_scene_items": self._handleGetSceneItems,
            # Windows
            "get_windows": self._handleGetWindows,
            "activate_window": self._handleActivateWindow,
            # File operations
            "open_file": self._handleOpenFile,
            # Screenshots
            "take_screenshot": self._handleTakeScreenshot,
            # Status
            "ping": self._handlePing,
        }

    @property
    def port(self) -> int:
        """Get the server port."""
        return self._port

    @property
    def isRunning(self) -> bool:
        """Check if server is running."""
        return self._running

    def start(self) -> bool:
        """
        Start the server.

        Returns:
            True if started successfully
        """
        if self._running:
            log.warning("Server already running")
            return True

        try:
            # Create inspector
            self._inspector = QtInspector()

            # Create socket
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self._host, self._port))
            self._socket.listen(1)
            self._socket.settimeout(1.0)  # Allow periodic checking

            # Start server thread
            self._running = True
            self._serverThread = threading.Thread(target=self._runServer, daemon=True)
            self._serverThread.start()

            log.info(f"Test Bridge Server started on {self._host}:{self._port}")
            return True

        except Exception as e:
            log.exception(f"Failed to start server: {e}")
            self._running = False
            return False

    def stop(self):
        """Stop the server."""
        if not self._running:
            return

        self._running = False

        if self._socket is not None:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

        if self._serverThread is not None:
            self._serverThread.join(timeout=5)
            self._serverThread = None

        log.info("Test Bridge Server stopped")

    def _runServer(self):
        """Run the server (in background thread)."""
        while self._running:
            try:
                # Accept connection
                client, addr = self._socket.accept()
                log.info(f"Client connected: {addr}")

                try:
                    self._handleClient(client)
                except Exception as e:
                    log.exception(f"Error handling client: {e}")
                finally:
                    client.close()
                    log.info(f"Client disconnected: {addr}")

            except socket.timeout:
                # Check if still running
                continue
            except OSError:
                # Socket closed
                break
            except Exception as e:
                log.exception(f"Server error: {e}")
                break

    def _handleClient(self, client: socket.socket):
        """Handle a client connection."""
        client.settimeout(30.0)
        buffer = b""

        while self._running:
            try:
                # Receive data
                data = client.recv(4096)
                if not data:
                    break

                buffer += data

                # Process complete messages (newline-delimited JSON)
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line:
                        response = self._processCommand(line.decode("utf-8"))
                        client.sendall((response + "\n").encode("utf-8"))

            except socket.timeout:
                continue
            except Exception as e:
                log.exception(f"Error receiving data: {e}")
                break

    def _processCommand(self, line: str) -> str:
        """Process a command and return JSON response."""
        try:
            command = json.loads(line)
        except json.JSONDecodeError as e:
            return json.dumps({"success": False, "error": f"Invalid JSON: {e}"})

        cmdName = command.get("command")
        if not cmdName:
            return json.dumps({"success": False, "error": "Missing 'command' field"})

        handler = self._handlers.get(cmdName)
        if handler is None:
            return json.dumps(
                {"success": False, "error": f"Unknown command: {cmdName}"}
            )

        # Execute on main thread and wait for result
        result = {"pending": True}
        self._executeOnMain.emit(lambda: handler(command), result)

        # Wait for result (with timeout)
        import time

        timeout = 30
        start = time.time()
        while result.get("pending") and time.time() - start < timeout:
            time.sleep(0.01)

        if result.get("pending"):
            return json.dumps({"success": False, "error": "Command timeout"})

        return json.dumps(
            result.get("response", {"success": False, "error": "No response"})
        )

    def _onExecuteOnMain(self, handler: Callable, result: Dict):
        """Execute a handler on the main thread."""
        try:
            response = handler()
            result["response"] = response
        except Exception as e:
            log.exception(f"Error executing command: {e}")
            result["response"] = {"success": False, "error": str(e)}
        finally:
            result["pending"] = False

    # -------------------------------------------------------------------------
    # Command Handlers
    # -------------------------------------------------------------------------

    def _handlePing(self, command: Dict) -> Dict:
        """Handle ping command."""
        return {"success": True, "message": "pong"}

    def _handleGetAppState(self, command: Dict) -> Dict:
        """Handle get_app_state command."""
        return self._inspector.getAppState()

    def _handleFindElement(self, command: Dict) -> Dict:
        """Handle find_element command."""
        objectName = command.get("objectName")
        if not objectName:
            return {"success": False, "error": "Missing 'objectName'"}

        result = self._inspector.findElement(objectName)
        if result:
            return {"success": True, "element": result}
        return {"success": False, "error": f"Element not found: {objectName}"}

    def _handleListElements(self, command: Dict) -> Dict:
        """Handle list_elements command."""
        elementType = command.get("type")
        maxDepth = command.get("maxDepth", 3)
        visibleOnly = command.get("visibleOnly", True)
        namedOnly = command.get("namedOnly", True)
        verbose = command.get("verbose", False)
        limit = command.get("limit", 50)

        elements = self._inspector.listElements(
            elementType, maxDepth, visibleOnly, namedOnly, verbose, limit
        )
        return {"success": True, "elements": elements, "count": len(elements)}

    def _handleGetProperty(self, command: Dict) -> Dict:
        """Handle get_property command."""
        objectName = command.get("objectName")
        propertyName = command.get("property")

        if not objectName or not propertyName:
            return {"success": False, "error": "Missing 'objectName' or 'property'"}

        return self._inspector.getProperty(objectName, propertyName)

    def _handleSetProperty(self, command: Dict) -> Dict:
        """Handle set_property command."""
        objectName = command.get("objectName")
        propertyName = command.get("property")
        value = command.get("value")

        if not objectName or not propertyName:
            return {"success": False, "error": "Missing required fields"}

        return self._inspector.setProperty(objectName, propertyName, value)

    def _handleClick(self, command: Dict) -> Dict:
        """Handle click command."""
        objectName = command.get("objectName")
        if not objectName:
            return {"success": False, "error": "Missing 'objectName'"}

        pos = command.get("pos")
        if pos:
            pos = tuple(pos)

        from pkdiagram.pyqt import Qt

        button = command.get("button", "left")
        buttonMap = {
            "left": Qt.LeftButton,
            "right": Qt.RightButton,
            "middle": Qt.MiddleButton,
        }
        qtButton = buttonMap.get(button, Qt.LeftButton)

        return self._inspector.click(objectName, qtButton, pos)

    def _handleDoubleClick(self, command: Dict) -> Dict:
        """Handle double_click command."""
        objectName = command.get("objectName")
        if not objectName:
            return {"success": False, "error": "Missing 'objectName'"}

        pos = command.get("pos")
        if pos:
            pos = tuple(pos)

        from pkdiagram.pyqt import Qt

        return self._inspector.doubleClick(objectName, Qt.LeftButton, pos)

    def _handleTypeText(self, command: Dict) -> Dict:
        """Handle type_text command."""
        text = command.get("text")
        if text is None:
            return {"success": False, "error": "Missing 'text'"}

        objectName = command.get("objectName")
        return self._inspector.typeText(text, objectName)

    def _handlePressKey(self, command: Dict) -> Dict:
        """Handle press_key command."""
        key = command.get("key")
        if not key:
            return {"success": False, "error": "Missing 'key'"}

        objectName = command.get("objectName")
        modifiers = command.get("modifiers")

        return self._inspector.pressKey(key, objectName, modifiers)

    def _handleFocus(self, command: Dict) -> Dict:
        """Handle focus command."""
        objectName = command.get("objectName")
        if not objectName:
            return {"success": False, "error": "Missing 'objectName'"}

        return self._inspector.focus(objectName)

    def _handleClickSceneItem(self, command: Dict) -> Dict:
        """Handle click_scene_item command."""
        name = command.get("name")
        if not name:
            return {"success": False, "error": "Missing 'name'"}

        from pkdiagram.pyqt import Qt

        button = command.get("button", "left")
        buttonMap = {"left": Qt.LeftButton, "right": Qt.RightButton}
        qtButton = buttonMap.get(button, Qt.LeftButton)

        return self._inspector.clickSceneItem(name, qtButton)

    def _handleGetSceneItems(self, command: Dict) -> Dict:
        """Handle get_scene_items command."""
        itemType = command.get("type")
        return self._inspector.getSceneItems(itemType)

    def _handleGetWindows(self, command: Dict) -> Dict:
        """Handle get_windows command."""
        return self._inspector.getWindows()

    def _handleActivateWindow(self, command: Dict) -> Dict:
        """Handle activate_window command."""
        objectName = command.get("objectName")
        if not objectName:
            return {"success": False, "error": "Missing 'objectName'"}

        return self._inspector.activateWindow(objectName)

    def _handleOpenFile(self, command: Dict) -> Dict:
        """Handle open_file command."""
        filePath = command.get("filePath")
        if not filePath:
            return {"success": False, "error": "Missing 'filePath'"}

        return self._inspector.openFile(filePath)

    def _handleTakeScreenshot(self, command: Dict) -> Dict:
        """Handle take_screenshot command."""
        objectName = command.get("objectName")
        return self._inspector.takeScreenshot(objectName)


def startTestBridgeServer(port: int = DEFAULT_PORT) -> TestBridgeServer:
    """
    Start the test bridge server.

    This is a convenience function for starting the server from main.py.

    Args:
        port: Port to listen on

    Returns:
        The server instance
    """
    server = TestBridgeServer(port=port)
    server.start()
    return server
