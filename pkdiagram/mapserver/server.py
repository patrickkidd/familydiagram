"""
HTTP API server for the Map Server.

This server runs in a separate thread and communicates with the Qt application
through thread-safe queues.
"""

import base64
import json
import logging
import threading
import queue
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any, Callable
from urllib.parse import urlparse, parse_qs

from pkdiagram.pyqt import Qt, QTimer, QObject, pyqtSignal

from .app_controller import AppTestController
from .input_simulator import InputSimulator
from .snapshot import SnapshotManager
from .element_finder import ElementFinder

log = logging.getLogger(__name__)


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Map Server API."""

    def log_message(self, format, *args):
        """Override to use logging module."""
        log.debug(f"{self.address_string()} - {format % args}")

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        """Send a JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _send_error_json(self, message: str, status: int = 400):
        """Send an error response."""
        self._send_json({"success": False, "error": message}, status)

    def _read_json_body(self) -> Optional[Dict[str, Any]]:
        """Read and parse JSON request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}

        body = self.rfile.read(content_length)
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            log.error(f"Invalid JSON: {e}")
            return None

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # Convert single-value params
        params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

        self.server.map_server._handleRequest("GET", path, params, self)

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        body = self._read_json_body()
        if body is None:
            self._send_error_json("Invalid JSON body")
            return

        self.server.map_server._handleRequest("POST", path, body, self)


class MapServer(QObject):
    """
    Main Map Server class that manages the HTTP server and Qt integration.

    The server runs in a separate thread but executes Qt operations on the
    main thread using signals/slots.
    """

    # Signal to execute operations on the main thread
    _executeOnMain = pyqtSignal(object, object)

    def __init__(
        self,
        port: int = 8765,
        host: str = "127.0.0.1",
        headless: bool = False,
    ):
        super().__init__()

        self._port = port
        self._host = host
        self._headless = headless

        self._server: Optional[HTTPServer] = None
        self._serverThread: Optional[threading.Thread] = None
        self._running = False

        # Qt components
        self._controller = AppTestController()
        self._inputSimulator: Optional[InputSimulator] = None
        self._snapshotManager: Optional[SnapshotManager] = None
        self._elementFinder: Optional[ElementFinder] = None

        # Thread communication
        self._resultQueue = queue.Queue()

        # Connect signal for main thread execution
        self._executeOnMain.connect(self._onExecuteOnMain)

        # Route handlers
        self._routes: Dict[str, Dict[str, Callable]] = {
            "GET": {},
            "POST": {},
        }
        self._setupRoutes()

    def _setupRoutes(self):
        """Set up API route handlers."""
        # Application control
        self._routes["POST"]["/app/init"] = self._handleAppInit
        self._routes["POST"]["/app/shutdown"] = self._handleAppShutdown
        self._routes["POST"]["/app/create-window"] = self._handleCreateWindow
        self._routes["POST"]["/app/load-file"] = self._handleLoadFile
        self._routes["POST"]["/app/new-document"] = self._handleNewDocument
        self._routes["POST"]["/app/process-events"] = self._handleProcessEvents
        self._routes["GET"]["/app/status"] = self._handleAppStatus

        # Input simulation
        self._routes["POST"]["/input/click"] = self._handleClick
        self._routes["POST"]["/input/double-click"] = self._handleDoubleClick
        self._routes["POST"]["/input/type"] = self._handleType
        self._routes["POST"]["/input/key"] = self._handleKeyPress
        self._routes["POST"]["/input/keys"] = self._handleKeySequence
        self._routes["POST"]["/input/drag"] = self._handleDrag
        self._routes["POST"]["/input/scroll"] = self._handleScroll
        self._routes["POST"]["/input/focus"] = self._handleFocus
        self._routes["POST"]["/input/mouse-move"] = self._handleMouseMove

        # Graphics items
        self._routes["POST"]["/graphics/click"] = self._handleGraphicsClick
        self._routes["POST"]["/graphics/double-click"] = self._handleGraphicsDoubleClick
        self._routes["POST"]["/graphics/drag"] = self._handleGraphicsDrag

        # Snapshots
        self._routes["POST"]["/snapshot/capture"] = self._handleSnapshotCapture
        self._routes["POST"]["/snapshot/compare"] = self._handleSnapshotCompare
        self._routes["POST"]["/snapshot/save"] = self._handleSnapshotSave
        self._routes["GET"]["/snapshot/load"] = self._handleSnapshotLoad
        self._routes["GET"]["/snapshot/list"] = self._handleSnapshotList
        self._routes["POST"]["/snapshot/assert"] = self._handleSnapshotAssert

        # Element finding
        self._routes["GET"]["/element/find"] = self._handleFindElement
        self._routes["GET"]["/element/info"] = self._handleElementInfo
        self._routes["GET"]["/element/tree"] = self._handleElementTree
        self._routes["GET"]["/element/property"] = self._handleGetProperty
        self._routes["POST"]["/element/property"] = self._handleSetProperty
        self._routes["POST"]["/element/wait"] = self._handleWaitForElement
        self._routes["POST"]["/element/wait-property"] = self._handleWaitForProperty

        # Scene operations
        self._routes["GET"]["/scene/items"] = self._handleSceneItems
        self._routes["GET"]["/scene/find"] = self._handleSceneFind

    def _handleRequest(
        self,
        method: str,
        path: str,
        params: Dict[str, Any],
        handler: RequestHandler,
    ):
        """Handle an incoming request."""
        routes = self._routes.get(method, {})
        routeHandler = routes.get(path)

        if routeHandler is None:
            handler._send_error_json(f"Unknown route: {method} {path}", 404)
            return

        try:
            # Execute on main thread and wait for result
            self._executeOnMain.emit(routeHandler, params)
            result = self._resultQueue.get(timeout=30)

            if isinstance(result, Exception):
                handler._send_error_json(str(result), 500)
            else:
                handler._send_json(result)

        except queue.Empty:
            handler._send_error_json("Request timeout", 504)
        except Exception as e:
            log.exception(f"Error handling request: {e}")
            handler._send_error_json(str(e), 500)

    def _onExecuteOnMain(self, handler: Callable, params: Dict[str, Any]):
        """Execute a handler on the main thread."""
        try:
            result = handler(params)
            self._resultQueue.put(result)
        except Exception as e:
            log.exception(f"Error in handler: {e}")
            self._resultQueue.put(e)

    # -------------------------------------------------------------------------
    # Server Control
    # -------------------------------------------------------------------------

    def start(self):
        """Start the HTTP server."""
        if self._running:
            log.warning("Server already running")
            return

        self._server = HTTPServer((self._host, self._port), RequestHandler)
        self._server.map_server = self

        self._serverThread = threading.Thread(target=self._runServer, daemon=True)
        self._serverThread.start()
        self._running = True

        log.info(f"Map Server started on http://{self._host}:{self._port}")

    def _runServer(self):
        """Run the HTTP server (in background thread)."""
        try:
            self._server.serve_forever()
        except Exception as e:
            log.error(f"Server error: {e}")
        finally:
            self._running = False

    def stop(self):
        """Stop the HTTP server."""
        if not self._running:
            return

        if self._server is not None:
            self._server.shutdown()
            self._server = None

        if self._serverThread is not None:
            self._serverThread.join(timeout=5)
            self._serverThread = None

        self._running = False
        log.info("Map Server stopped")

    def run(self):
        """
        Run the server with the Qt event loop.

        This starts both the HTTP server and the Qt application.
        """
        self.start()

        # Initialize the app
        if not self._controller.initialize(headless=self._headless):
            log.error("Failed to initialize application")
            self.stop()
            return

        self._inputSimulator = InputSimulator(self._controller)
        self._snapshotManager = SnapshotManager(self._controller)
        self._elementFinder = ElementFinder(self._controller)

        # Run Qt event loop
        from pkdiagram.pyqt import QApplication
        app = self._controller.app
        if app is not None:
            app.exec()

        self.stop()
        self._controller.shutdown()

    @property
    def port(self) -> int:
        """Get the server port."""
        return self._port

    @property
    def isRunning(self) -> bool:
        """Check if the server is running."""
        return self._running

    # -------------------------------------------------------------------------
    # Route Handlers - Application Control
    # -------------------------------------------------------------------------

    def _handleAppInit(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize the application."""
        headless = params.get("headless", self._headless)

        if not self._controller.initialize(headless=headless):
            return {"success": False, "error": "Failed to initialize application"}

        self._inputSimulator = InputSimulator(self._controller)
        self._snapshotManager = SnapshotManager(self._controller)
        self._elementFinder = ElementFinder(self._controller)

        return {"success": True}

    def _handleAppShutdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Shutdown the application."""
        self._controller.shutdown()
        return {"success": True}

    def _handleCreateWindow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create the main window."""
        show = params.get("show", True)

        if not self._controller.createMainWindow(showWindow=show):
            return {"success": False, "error": "Failed to create main window"}

        return {"success": True}

    def _handleLoadFile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Load a file."""
        filePath = params.get("path")
        if not filePath:
            return {"success": False, "error": "Missing 'path' parameter"}

        if not self._controller.loadFile(filePath):
            return {"success": False, "error": f"Failed to load file: {filePath}"}

        return {"success": True}

    def _handleNewDocument(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document."""
        if not self._controller.newDocument():
            return {"success": False, "error": "Failed to create new document"}

        return {"success": True}

    def _handleProcessEvents(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process Qt events."""
        timeout = params.get("timeout", 100)
        self._controller.processEvents(timeout)
        return {"success": True}

    def _handleAppStatus(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get application status."""
        return {
            "success": True,
            "initialized": self._controller._initialized,
            "hasMainWindow": self._controller.mainWindow is not None,
            "hasDocument": self._controller.documentView is not None,
            "hasScene": self._controller.scene is not None,
        }

    # -------------------------------------------------------------------------
    # Route Handlers - Input Simulation
    # -------------------------------------------------------------------------

    def _handleClick(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle click request."""
        target = params.get("target")
        if not target:
            return {"success": False, "error": "Missing 'target' parameter"}

        button = params.get("button", Qt.LeftButton)
        pos = params.get("pos")
        modifiers = params.get("modifiers", Qt.NoModifier)

        success = self._inputSimulator.click(target, button, pos, modifiers)
        return {"success": success}

    def _handleDoubleClick(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle double-click request."""
        target = params.get("target")
        if not target:
            return {"success": False, "error": "Missing 'target' parameter"}

        button = params.get("button", Qt.LeftButton)
        pos = params.get("pos")
        modifiers = params.get("modifiers", Qt.NoModifier)

        success = self._inputSimulator.doubleClick(target, button, pos, modifiers)
        return {"success": success}

    def _handleType(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle type request."""
        text = params.get("text")
        if text is None:
            return {"success": False, "error": "Missing 'text' parameter"}

        target = params.get("target")
        modifiers = params.get("modifiers", Qt.NoModifier)

        success = self._inputSimulator.type(text, target, modifiers)
        return {"success": success}

    def _handleKeyPress(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle key press request."""
        key = params.get("key")
        if key is None:
            return {"success": False, "error": "Missing 'key' parameter"}

        target = params.get("target")
        modifiers = params.get("modifiers", Qt.NoModifier)

        success = self._inputSimulator.keyPress(key, target, modifiers)
        return {"success": success}

    def _handleKeySequence(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle key sequence request."""
        keys = params.get("keys")
        if not keys:
            return {"success": False, "error": "Missing 'keys' parameter"}

        target = params.get("target")

        success = self._inputSimulator.keySequence(keys, target)
        return {"success": success}

    def _handleDrag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle drag request."""
        target = params.get("target")
        startPos = params.get("startPos")
        endPos = params.get("endPos")

        if not target or not startPos or not endPos:
            return {"success": False, "error": "Missing required parameters"}

        button = params.get("button", Qt.LeftButton)
        modifiers = params.get("modifiers", Qt.NoModifier)
        steps = params.get("steps", 10)

        success = self._inputSimulator.drag(
            target,
            tuple(startPos),
            tuple(endPos),
            button,
            modifiers,
            steps,
        )
        return {"success": success}

    def _handleScroll(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scroll request."""
        target = params.get("target")
        delta = params.get("delta")

        if not target or delta is None:
            return {"success": False, "error": "Missing required parameters"}

        orientation = params.get("orientation", Qt.Vertical)
        pos = params.get("pos")

        success = self._inputSimulator.scroll(target, delta, orientation, pos)
        return {"success": success}

    def _handleFocus(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle focus request."""
        target = params.get("target")
        if not target:
            return {"success": False, "error": "Missing 'target' parameter"}

        success = self._inputSimulator.focus(target)
        return {"success": success}

    def _handleMouseMove(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle mouse move request."""
        target = params.get("target")
        pos = params.get("pos")

        if not target or not pos:
            return {"success": False, "error": "Missing required parameters"}

        modifiers = params.get("modifiers", Qt.NoModifier)

        success = self._inputSimulator.mouseMove(target, tuple(pos), modifiers)
        return {"success": success}

    # -------------------------------------------------------------------------
    # Route Handlers - Graphics Items
    # -------------------------------------------------------------------------

    def _handleGraphicsClick(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle graphics item click."""
        item = params.get("item")
        if not item:
            return {"success": False, "error": "Missing 'item' parameter"}

        button = params.get("button", Qt.LeftButton)
        modifiers = params.get("modifiers", Qt.NoModifier)

        success = self._inputSimulator.clickGraphicsItem(item, button, modifiers)
        return {"success": success}

    def _handleGraphicsDoubleClick(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle graphics item double-click."""
        item = params.get("item")
        if not item:
            return {"success": False, "error": "Missing 'item' parameter"}

        button = params.get("button", Qt.LeftButton)
        modifiers = params.get("modifiers", Qt.NoModifier)

        success = self._inputSimulator.doubleClickGraphicsItem(item, button, modifiers)
        return {"success": success}

    def _handleGraphicsDrag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle graphics item drag."""
        item = params.get("item")
        deltaX = params.get("deltaX", 0)
        deltaY = params.get("deltaY", 0)

        if not item:
            return {"success": False, "error": "Missing 'item' parameter"}

        button = params.get("button", Qt.LeftButton)
        modifiers = params.get("modifiers", Qt.NoModifier)

        success = self._inputSimulator.dragGraphicsItem(
            item, deltaX, deltaY, button, modifiers
        )
        return {"success": success}

    # -------------------------------------------------------------------------
    # Route Handlers - Snapshots
    # -------------------------------------------------------------------------

    def _handleSnapshotCapture(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Capture a snapshot."""
        target = params.get("target")
        format = params.get("format", "PNG")

        if target is None:
            data = self._snapshotManager.captureWindow(format=format)
        elif target == "__screen__":
            data = self._snapshotManager.captureScreen(format=format)
        else:
            # Try widget, then QML item
            widget = self._elementFinder.findWidget(target)
            if widget is not None:
                data = self._snapshotManager.captureWidget(widget, format=format)
            else:
                item = self._elementFinder.findQmlItem(target)
                if item is not None:
                    data = self._snapshotManager.captureQmlItem(item, format=format)
                else:
                    return {"success": False, "error": f"Target not found: {target}"}

        if data is None:
            return {"success": False, "error": "Failed to capture snapshot"}

        return {
            "success": True,
            "data": base64.b64encode(data).decode("utf-8"),
            "format": format,
        }

    def _handleSnapshotCompare(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compare a snapshot with baseline."""
        name = params.get("name")
        current = params.get("current")
        threshold = params.get("threshold", 0.0)

        if not name:
            return {"success": False, "error": "Missing 'name' parameter"}

        if current:
            currentData = base64.b64decode(current)
        else:
            # Capture current
            target = params.get("target")
            if target is None:
                currentData = self._snapshotManager.captureWindow()
            else:
                widget = self._elementFinder.findWidget(target)
                if widget:
                    currentData = self._snapshotManager.captureWidget(widget)
                else:
                    item = self._elementFinder.findQmlItem(target)
                    currentData = self._snapshotManager.captureQmlItem(item) if item else None

            if currentData is None:
                return {"success": False, "error": "Failed to capture current snapshot"}

        result = self._snapshotManager.compare(name, currentData, threshold)
        return {"success": True, **result}

    def _handleSnapshotSave(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Save a snapshot."""
        name = params.get("name")
        data = params.get("data")

        if not name:
            return {"success": False, "error": "Missing 'name' parameter"}

        if data:
            imageData = base64.b64decode(data)
        else:
            # Capture current
            target = params.get("target")
            imageData = self._snapshotManager.captureWindow() if target is None else None
            if imageData is None:
                return {"success": False, "error": "Failed to capture snapshot"}

        metadata = params.get("metadata")
        path = self._snapshotManager.saveSnapshot(name, imageData, metadata)

        return {"success": True, "path": path}

    def _handleSnapshotLoad(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Load a snapshot."""
        name = params.get("name")
        if not name:
            return {"success": False, "error": "Missing 'name' parameter"}

        data = self._snapshotManager.loadSnapshot(name)
        if data is None:
            return {"success": False, "error": f"Snapshot not found: {name}"}

        metadata = self._snapshotManager.loadSnapshotMetadata(name)

        return {
            "success": True,
            "data": base64.b64encode(data).decode("utf-8"),
            "metadata": metadata,
        }

    def _handleSnapshotList(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all snapshots."""
        snapshots = self._snapshotManager.listSnapshots()
        return {"success": True, "snapshots": snapshots}

    def _handleSnapshotAssert(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Assert snapshot match."""
        name = params.get("name")
        if not name:
            return {"success": False, "error": "Missing 'name' parameter"}

        target = params.get("target")
        threshold = params.get("threshold", 0.0)
        updateOnFail = params.get("updateOnFail", False)

        try:
            self._snapshotManager.assertMatch(name, target, threshold, updateOnFail)
            return {"success": True, "match": True}
        except AssertionError as e:
            return {"success": True, "match": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Route Handlers - Element Finding
    # -------------------------------------------------------------------------

    def _handleFindElement(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find an element."""
        objectName = params.get("objectName")
        if not objectName:
            return {"success": False, "error": "Missing 'objectName' parameter"}

        # Try widget first
        widget = self._elementFinder.findWidget(objectName)
        if widget is not None:
            return {"success": True, "found": True, "type": "widget"}

        # Try QML item
        item = self._elementFinder.findQmlItem(objectName)
        if item is not None:
            return {"success": True, "found": True, "type": "qml"}

        return {"success": True, "found": False}

    def _handleElementInfo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get element information."""
        objectName = params.get("objectName")
        if not objectName:
            return {"success": False, "error": "Missing 'objectName' parameter"}

        info = self._elementFinder.getElementInfo(objectName)
        if info is None:
            return {"success": False, "error": f"Element not found: {objectName}"}

        return {"success": True, **info}

    def _handleElementTree(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get element tree."""
        treeType = params.get("type", "widget")
        maxDepth = int(params.get("maxDepth", 10))

        if treeType == "widget":
            tree = self._elementFinder.getWidgetTree(maxDepth=maxDepth)
        elif treeType == "qml":
            tree = self._elementFinder.getQmlTree(maxDepth=maxDepth)
        else:
            return {"success": False, "error": f"Unknown tree type: {treeType}"}

        return {"success": True, "tree": tree}

    def _handleGetProperty(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get element property."""
        objectName = params.get("objectName")
        propertyName = params.get("property")

        if not objectName or not propertyName:
            return {"success": False, "error": "Missing required parameters"}

        value = self._controller.getProperty(objectName, propertyName)
        return {"success": True, "value": value}

    def _handleSetProperty(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set element property."""
        objectName = params.get("objectName")
        propertyName = params.get("property")
        value = params.get("value")

        if not objectName or not propertyName:
            return {"success": False, "error": "Missing required parameters"}

        success = self._controller.setProperty(objectName, propertyName, value)
        return {"success": success}

    def _handleWaitForElement(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Wait for an element."""
        objectName = params.get("objectName")
        if not objectName:
            return {"success": False, "error": "Missing 'objectName' parameter"}

        timeout = int(params.get("timeout", 5000))
        checkVisible = params.get("checkVisible", True)

        element = self._elementFinder.waitForElement(objectName, timeout, checkVisible)
        return {"success": True, "found": element is not None}

    def _handleWaitForProperty(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Wait for element property."""
        objectName = params.get("objectName")
        propertyName = params.get("property")
        expectedValue = params.get("value")

        if not objectName or not propertyName:
            return {"success": False, "error": "Missing required parameters"}

        timeout = int(params.get("timeout", 5000))

        found = self._elementFinder.waitForProperty(
            objectName, propertyName, expectedValue, timeout
        )
        return {"success": True, "found": found}

    # -------------------------------------------------------------------------
    # Route Handlers - Scene Operations
    # -------------------------------------------------------------------------

    def _handleSceneItems(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get scene items."""
        itemType = params.get("type")

        items = self._elementFinder.findAllSceneItems(itemType=itemType)

        itemList = []
        for item in items:
            itemList.append({
                "type": type(item).__name__,
                "name": getattr(item, "name", None),
                "id": getattr(item, "id", None),
            })

        return {"success": True, "items": itemList}

    def _handleSceneFind(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find a scene item."""
        name = params.get("name")
        itemType = params.get("type")

        item = self._elementFinder.findSceneItem(name=name, itemType=itemType)

        if item is None:
            return {"success": True, "found": False}

        return {
            "success": True,
            "found": True,
            "item": {
                "type": type(item).__name__,
                "name": getattr(item, "name", None),
                "id": getattr(item, "id", None),
            },
        }
