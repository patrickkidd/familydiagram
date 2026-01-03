"""
Qt Inspector - Inspects Qt widgets and QML items.

This module provides deep inspection of the Qt object hierarchy,
including widgets, QML items, and QGraphicsView scene items.
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any, List, Union


class AppState(str, Enum):
    """Application process state (analogous to OS process states)."""

    Initializing = "initializing"
    Running = "running"
    Stopped = "stopped"
    Error = "error"


class AppLoginState(str, Enum):
    """Login state as observed from the app UI. Only valid when AppState is Running."""

    AccountDialogVisible = "account_dialog_visible"
    NotLoggedIn = "not_logged_in"
    LoggedIn = "logged_in"


class AppView(str, Enum):
    """Current view shown in the app. Only valid when AppState is Running."""

    # Pro app views
    FileManager = "file_manager"
    DocumentView = "document_view"
    AccountView = "account_view"
    WelcomeView = "welcome_view"
    # Personal app views
    DiscussView = "discuss_view"
    LearnView = "learn_view"
    PlanView = "plan_view"


from pkdiagram.pyqt import (
    Qt,
    QObject,
    QWidget,
    QApplication,
    QQuickItem,
    QQuickWidget,
    QGraphicsView,
    QGraphicsItem,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QTest,
    QMetaObject,
    Q_ARG,
    QPixmap,
    QBuffer,
    QByteArray,
    QIODevice,
    QTimer,
    QMessageBox,
    QDialog,
)

log = logging.getLogger(__name__)


class QtInspector:
    """
    Inspects Qt objects and provides element finding/interaction.

    This class enables:
    - Finding widgets and QML items by objectName
    - Listing all elements in the UI hierarchy
    - Getting element properties and geometry
    - Simulating input on elements
    """

    def __init__(self, app: Optional[QApplication] = None):
        self._app = app or QApplication.instance()

    # -------------------------------------------------------------------------
    # App State (High-level semantic state)
    # -------------------------------------------------------------------------

    def getAppState(self) -> Dict[str, Any]:
        """
        Get high-level semantic app state for MCP testing.
        Fails fast on unexpected states - this is a dev tool, not production code.
        """
        # Find MainWindow - required for running state
        mainWindow = None
        for window in self._app.topLevelWidgets():
            if type(window).__name__ == "MainWindow":
                mainWindow = window
                break

        if mainWindow is None:
            return {
                "success": True,
                "state": {
                    "appState": AppState.Initializing.value,
                    "loginState": None,
                    "currentView": None,
                },
            }

        # Collect visible dialogs
        visibleDialogs = []
        for window in self._app.topLevelWidgets():
            if window.isVisible():
                className = type(window).__name__
                if "Dialog" in className or "QMessageBox" in className:
                    visibleDialogs.append({
                        "objectName": window.objectName() or None,
                        "className": className,
                        "title": window.windowTitle() or None,
                    })

        # Determine loginState - no defensive coding, let it fail if session doesn't exist
        session = mainWindow.session
        if any(d["className"] == "AccountDialog" for d in visibleDialogs):
            loginState = AppLoginState.AccountDialogVisible.value
        elif session.isLoggedIn():
            loginState = AppLoginState.LoggedIn.value
        else:
            loginState = AppLoginState.NotLoggedIn.value

        # Determine currentView for Pro app
        currentView = None
        loadedFileName = None

        # Check for dialogs that define the view
        if any(d["className"] == "AccountDialog" for d in visibleDialogs):
            currentView = AppView.AccountView.value
        elif any(d["className"] == "WelcomeDialog" for d in visibleDialogs):
            currentView = AppView.WelcomeView.value
        else:
            # Pro app: FileManager vs DocumentView
            fileManager = mainWindow.fileManager
            documentView = mainWindow.documentView

            if fileManager.isVisible() and documentView.isVisible():
                # Both visible - check positions
                if fileManager.pos().x() == 0:
                    currentView = AppView.FileManager.value
                else:
                    currentView = AppView.DocumentView.value
            elif fileManager.isVisible():
                currentView = AppView.FileManager.value
            elif documentView.isVisible():
                currentView = AppView.DocumentView.value
            else:
                raise RuntimeError("Neither fileManager nor documentView is visible")

            # Get loaded file if in DocumentView
            if currentView == AppView.DocumentView.value:
                doc = mainWindow.scene.document()
                if doc:
                    url = doc.url()
                    if url and not url.isEmpty():
                        loadedFileName = url.toLocalFile()

        return {
            "success": True,
            "state": {
                "appState": AppState.Running.value,
                "loginState": loginState,
                "currentView": currentView,
                "loadedFileName": loadedFileName,
                "visibleDialogs": visibleDialogs,
            },
        }

    # -------------------------------------------------------------------------
    # Element Finding
    # -------------------------------------------------------------------------

    def findElement(self, objectName: str) -> Optional[Dict[str, Any]]:
        """
        Find an element by objectName and return its info.

        Args:
            objectName: The objectName to search for

        Returns:
            Element info dict, or None if not found
        """
        # Try widgets first
        widget = self._findWidget(objectName)
        if widget is not None:
            return self._getWidgetInfo(widget)

        # Try QML items
        item = self._findQmlItem(objectName)
        if item is not None:
            return self._getQmlItemInfo(item)

        return None

    def listElements(
        self,
        elementType: Optional[str] = None,
        maxDepth: int = 3,
        visibleOnly: bool = True,
        namedOnly: bool = True,
        verbose: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List UI elements. Returns compact format by default."""
        elements = []

        # Collect widgets
        if elementType is None or elementType == "widget":
            for window in self._app.topLevelWidgets():
                if visibleOnly and not window.isVisible():
                    continue
                self._collectWidgets(
                    window, elements, 0, maxDepth, visibleOnly, namedOnly, verbose
                )

        # Collect QML items
        if elementType is None or elementType == "qml":
            for root in self._getQmlRoots():
                self._collectQmlItems(
                    root, elements, 0, maxDepth, visibleOnly, namedOnly, verbose
                )

        # Collect scene items
        if elementType is None or elementType == "scene":
            for view in self._getGraphicsViews():
                self._collectSceneItems(view, elements, visibleOnly, verbose)

        return elements[:limit]

    def _findWidget(self, objectName: str) -> Optional[QWidget]:
        """Find a widget by objectName."""
        for window in self._app.topLevelWidgets():
            if window.objectName() == objectName:
                return window
            widget = window.findChild(QWidget, objectName)
            if widget is not None:
                return widget
        return None

    def _findQmlItem(self, objectName: str) -> Optional[QQuickItem]:
        """Find a QML item by objectName."""
        # Handle dot notation for nested items
        if "." in objectName:
            parts = objectName.split(".")
            item = self._findQmlItem(parts[0])
            for part in parts[1:]:
                if item is None:
                    return None
                item = self._findQmlItemInChildren(item, part)
            return item

        for root in self._getQmlRoots():
            item = self._findQmlItemInChildren(root, objectName)
            if item is not None:
                return item
        return None

    def _findQmlItemInChildren(
        self, parent: QQuickItem, objectName: str
    ) -> Optional[QQuickItem]:
        """Recursively find a QML item."""
        if parent.objectName() == objectName:
            return parent

        for child in parent.childItems():
            result = self._findQmlItemInChildren(child, objectName)
            if result is not None:
                return result

        return None

    def _getQmlRoots(self) -> List[QQuickItem]:
        """Get all QML root items."""
        roots = []
        for window in self._app.topLevelWidgets():
            self._collectQmlRoots(window, roots)
        return roots

    def _collectQmlRoots(self, widget: QWidget, roots: List[QQuickItem]):
        """Collect QML roots from a widget tree."""
        if isinstance(widget, QQuickWidget):
            root = widget.rootObject()
            if root is not None and root not in roots:
                roots.append(root)

        for child in widget.findChildren(QQuickWidget):
            root = child.rootObject()
            if root is not None and root not in roots:
                roots.append(root)

    def _getGraphicsViews(self) -> List[QGraphicsView]:
        """Get all QGraphicsViews."""
        views = []
        for window in self._app.topLevelWidgets():
            views.extend(window.findChildren(QGraphicsView))
        return views

    def _collectWidgets(
        self,
        widget: QWidget,
        elements: List[Dict],
        depth: int,
        maxDepth: int,
        visibleOnly: bool = True,
        namedOnly: bool = True,
        verbose: bool = False,
    ):
        """Collect widgets recursively."""
        if depth > maxDepth:
            return

        if visibleOnly and not widget.isVisible():
            return

        objName = widget.objectName()
        if namedOnly and not objName:
            for child in widget.children():
                if isinstance(child, QWidget):
                    self._collectWidgets(
                        child,
                        elements,
                        depth + 1,
                        maxDepth,
                        visibleOnly,
                        namedOnly,
                        verbose,
                    )
            return

        info = self._getWidgetInfo(widget, verbose)
        if info:
            elements.append(info)

        for child in widget.children():
            if isinstance(child, QWidget):
                self._collectWidgets(
                    child,
                    elements,
                    depth + 1,
                    maxDepth,
                    visibleOnly,
                    namedOnly,
                    verbose,
                )

    def _collectQmlItems(
        self,
        item: QQuickItem,
        elements: List[Dict],
        depth: int,
        maxDepth: int,
        visibleOnly: bool = True,
        namedOnly: bool = True,
        verbose: bool = False,
    ):
        """Collect QML items recursively."""
        if depth > maxDepth:
            return

        if visibleOnly and not item.isVisible():
            return

        objName = item.objectName()
        if namedOnly and not objName:
            for child in item.childItems():
                self._collectQmlItems(
                    child,
                    elements,
                    depth + 1,
                    maxDepth,
                    visibleOnly,
                    namedOnly,
                    verbose,
                )
            return

        info = self._getQmlItemInfo(item, verbose)
        if info:
            elements.append(info)

        for child in item.childItems():
            self._collectQmlItems(
                child, elements, depth + 1, maxDepth, visibleOnly, namedOnly, verbose
            )

    def _collectSceneItems(
        self,
        view: QGraphicsView,
        elements: List[Dict],
        visibleOnly: bool = True,
        verbose: bool = False,
    ):
        """Collect scene items from a QGraphicsView."""
        scene = view.scene()
        if scene is None:
            return

        for item in scene.items():
            if visibleOnly and not item.isVisible():
                continue
            info = self._getSceneItemInfo(item, view, verbose)
            if info:
                elements.append(info)

    # -------------------------------------------------------------------------
    # Element Info
    # -------------------------------------------------------------------------

    def _getWidgetInfo(self, widget: QWidget, verbose: bool = False) -> Dict[str, Any]:
        """Get info about a widget. Compact by default."""
        info = {
            "name": widget.objectName() or None,
            "type": "widget",
            "text": self._getTextProperty(widget),
        }
        if verbose:
            globalPos = widget.mapToGlobal(QPoint(0, 0))
            rect = widget.rect()
            info.update(
                {
                    "className": type(widget).__name__,
                    "visible": widget.isVisible(),
                    "enabled": widget.isEnabled(),
                    "focused": widget.hasFocus(),
                    "geometry": {
                        "x": globalPos.x(),
                        "y": globalPos.y(),
                        "width": rect.width(),
                        "height": rect.height(),
                    },
                    "checked": widget.property("checked"),
                }
            )
        return info

    def _getQmlItemInfo(
        self, item: QQuickItem, verbose: bool = False
    ) -> Dict[str, Any]:
        """Get info about a QML item. Compact by default."""
        info = {
            "name": item.objectName() or None,
            "type": "qml",
            "text": item.property("text"),
        }
        if verbose:
            quickWidget = self._findQuickWidgetForItem(item)
            if quickWidget is not None:
                scenePos = item.mapToScene(QPointF(0, 0))
                globalPos = quickWidget.mapToGlobal(scenePos.toPoint())
                x, y = globalPos.x(), globalPos.y()
            else:
                x, y = int(item.x()), int(item.y())
            info.update(
                {
                    "className": type(item).__name__,
                    "qmlType": (
                        item.metaObject().className() if item.metaObject() else None
                    ),
                    "visible": item.isVisible(),
                    "enabled": item.isEnabled(),
                    "focused": item.hasActiveFocus(),
                    "geometry": {
                        "x": x,
                        "y": y,
                        "width": int(item.width()),
                        "height": int(item.height()),
                    },
                    "checked": item.property("checked"),
                }
            )
        return info

    def _getSceneItemInfo(
        self, item: QGraphicsItem, view: QGraphicsView, verbose: bool = False
    ) -> Dict[str, Any]:
        """Get info about a scene item. Compact by default."""
        name = None
        if hasattr(item, "name"):
            name = getattr(item, "name", None)
            if callable(name):
                name = name()

        info = {
            "name": name,
            "type": "scene",
            "className": type(item).__name__,
        }
        if verbose:
            sceneRect = item.sceneBoundingRect()
            viewPos = view.mapFromScene(sceneRect.topLeft())
            globalPos = view.viewport().mapToGlobal(viewPos)
            itemId = getattr(item, "id", None) if hasattr(item, "id") else None
            info.update(
                {
                    "id": itemId,
                    "visible": item.isVisible(),
                    "geometry": {
                        "x": globalPos.x(),
                        "y": globalPos.y(),
                        "width": int(sceneRect.width()),
                        "height": int(sceneRect.height()),
                    },
                }
            )
        return info

    def _getTextProperty(self, obj: QObject) -> Optional[str]:
        """Get text property from various widget types."""
        for prop in ["text", "currentText", "title", "windowTitle", "placeholderText"]:
            value = obj.property(prop)
            if value is not None and isinstance(value, str) and value:
                return value
        return None

    def _findQuickWidgetForItem(self, item: QQuickItem) -> Optional[QQuickWidget]:
        """Find the QQuickWidget containing a QQuickItem."""
        window = item.window()
        if window is None:
            return None

        for topWidget in self._app.topLevelWidgets():
            for qw in topWidget.findChildren(QQuickWidget):
                if qw.quickWindow() == window:
                    return qw
        return None

    # -------------------------------------------------------------------------
    # Element Properties
    # -------------------------------------------------------------------------

    def getProperty(self, objectName: str, propertyName: str) -> Dict[str, Any]:
        """
        Get a property value from an element.

        Args:
            objectName: Element objectName
            propertyName: Property to get

        Returns:
            Dict with success and value
        """
        widget = self._findWidget(objectName)
        if widget is not None:
            value = widget.property(propertyName)
            return {"success": True, "value": self._convertValue(value)}

        item = self._findQmlItem(objectName)
        if item is not None:
            value = item.property(propertyName)
            return {"success": True, "value": self._convertValue(value)}

        return {"success": False, "error": f"Element not found: {objectName}"}

    def setProperty(
        self, objectName: str, propertyName: str, value: Any
    ) -> Dict[str, Any]:
        """
        Set a property value on an element.

        Args:
            objectName: Element objectName
            propertyName: Property to set
            value: New value

        Returns:
            Dict with success status
        """
        widget = self._findWidget(objectName)
        if widget is not None:
            success = widget.setProperty(propertyName, value)
            return {"success": success}

        item = self._findQmlItem(objectName)
        if item is not None:
            success = item.setProperty(propertyName, value)
            return {"success": success}

        return {"success": False, "error": f"Element not found: {objectName}"}

    def _convertValue(self, value: Any) -> Any:
        """Convert Qt types to JSON-serializable types."""
        if value is None:
            return None
        if isinstance(value, (int, float, str, bool)):
            return value
        if hasattr(value, "toString"):
            return value.toString()
        if isinstance(value, (QPoint, QPointF)):
            return {"x": value.x(), "y": value.y()}
        if isinstance(value, (QRect, QRectF)):
            return {
                "x": value.x(),
                "y": value.y(),
                "width": value.width(),
                "height": value.height(),
            }
        return str(value)

    # -------------------------------------------------------------------------
    # Element Interaction
    # -------------------------------------------------------------------------

    def click(
        self,
        objectName: str,
        button: int = Qt.LeftButton,
        pos: Optional[tuple] = None,
    ) -> Dict[str, Any]:
        """
        Click on an element.

        Args:
            objectName: Element objectName
            button: Mouse button
            pos: Optional (x, y) position within element

        Returns:
            Dict with success status
        """
        widget = self._findWidget(objectName)
        if widget is not None:
            return self._clickWidget(widget, button, pos)

        item = self._findQmlItem(objectName)
        if item is not None:
            return self._clickQmlItem(item, button, pos)

        return {"success": False, "error": f"Element not found: {objectName}"}

    def _clickWidget(
        self, widget: QWidget, button: int, pos: Optional[tuple]
    ) -> Dict[str, Any]:
        """Click on a widget."""
        if pos is None:
            clickPos = widget.rect().center()
        else:
            clickPos = QPoint(pos[0], pos[1])

        QTest.mouseClick(widget, button, Qt.NoModifier, clickPos)
        self._app.processEvents()
        return {"success": True}

    def _clickQmlItem(
        self, item: QQuickItem, button: int, pos: Optional[tuple]
    ) -> Dict[str, Any]:
        """Click on a QML item."""
        quickWidget = self._findQuickWidgetForItem(item)
        if quickWidget is None:
            return {"success": False, "error": "Could not find QQuickWidget"}

        if pos is None:
            localPos = QPointF(item.width() / 2, item.height() / 2)
        else:
            localPos = QPointF(pos[0], pos[1])

        scenePos = item.mapToScene(localPos)
        widgetPos = scenePos.toPoint()

        QTest.mouseClick(quickWidget, button, Qt.NoModifier, widgetPos)
        self._app.processEvents()
        return {"success": True}

    def doubleClick(
        self,
        objectName: str,
        button: int = Qt.LeftButton,
        pos: Optional[tuple] = None,
    ) -> Dict[str, Any]:
        """Double-click on an element."""
        widget = self._findWidget(objectName)
        if widget is not None:
            if pos is None:
                clickPos = widget.rect().center()
            else:
                clickPos = QPoint(pos[0], pos[1])
            QTest.mouseDClick(widget, button, Qt.NoModifier, clickPos)
            self._app.processEvents()
            return {"success": True}

        item = self._findQmlItem(objectName)
        if item is not None:
            quickWidget = self._findQuickWidgetForItem(item)
            if quickWidget is None:
                return {"success": False, "error": "Could not find QQuickWidget"}

            if pos is None:
                localPos = QPointF(item.width() / 2, item.height() / 2)
            else:
                localPos = QPointF(pos[0], pos[1])

            scenePos = item.mapToScene(localPos)
            QTest.mouseDClick(quickWidget, button, Qt.NoModifier, scenePos.toPoint())
            self._app.processEvents()
            return {"success": True}

        return {"success": False, "error": f"Element not found: {objectName}"}

    def typeText(
        self,
        text: str,
        objectName: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Type text, optionally into a specific element.

        Args:
            text: Text to type
            objectName: Optional element to focus first

        Returns:
            Dict with success status
        """
        target = None

        if objectName:
            widget = self._findWidget(objectName)
            if widget is not None:
                widget.setFocus()
                target = widget
            else:
                item = self._findQmlItem(objectName)
                if item is not None:
                    item.setFocus(True)
                    item.forceActiveFocus()
                    target = self._findQuickWidgetForItem(item)

            if target is None:
                return {"success": False, "error": f"Element not found: {objectName}"}
        else:
            target = self._app.focusWidget()
            if target is None:
                return {"success": False, "error": "No element has focus"}

        self._app.processEvents()
        QTest.keyClicks(target, text)
        self._app.processEvents()
        return {"success": True}

    def pressKey(
        self,
        key: str,
        objectName: Optional[str] = None,
        modifiers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Press a key.

        Args:
            key: Key name (e.g., "Return", "Tab", "a")
            objectName: Optional element to focus first
            modifiers: Optional list of modifiers

        Returns:
            Dict with success status
        """
        # Resolve key
        keyMap = {
            "enter": Qt.Key_Return,
            "return": Qt.Key_Return,
            "tab": Qt.Key_Tab,
            "escape": Qt.Key_Escape,
            "backspace": Qt.Key_Backspace,
            "delete": Qt.Key_Delete,
            "space": Qt.Key_Space,
            "up": Qt.Key_Up,
            "down": Qt.Key_Down,
            "left": Qt.Key_Left,
            "right": Qt.Key_Right,
        }

        if key.lower() in keyMap:
            qtKey = keyMap[key.lower()]
        elif len(key) == 1:
            qtKey = ord(key.upper())
        else:
            return {"success": False, "error": f"Unknown key: {key}"}

        # Resolve modifiers
        qtMods = Qt.NoModifier
        if modifiers:
            modMap = {
                "ctrl": Qt.ControlModifier,
                "shift": Qt.ShiftModifier,
                "alt": Qt.AltModifier,
                "meta": Qt.MetaModifier,
            }
            for mod in modifiers:
                if mod.lower() in modMap:
                    qtMods |= modMap[mod.lower()]

        # Get target
        target = None
        if objectName:
            widget = self._findWidget(objectName)
            if widget is not None:
                widget.setFocus()
                target = widget
            else:
                item = self._findQmlItem(objectName)
                if item is not None:
                    item.setFocus(True)
                    target = self._findQuickWidgetForItem(item)

            if target is None:
                return {"success": False, "error": f"Element not found: {objectName}"}
        else:
            target = self._app.focusWidget()
            if target is None:
                return {"success": False, "error": "No element has focus"}

        self._app.processEvents()
        QTest.keyClick(target, qtKey, qtMods)
        self._app.processEvents()
        return {"success": True}

    def focus(self, objectName: str) -> Dict[str, Any]:
        """
        Set focus to an element.

        Args:
            objectName: Element objectName

        Returns:
            Dict with success status
        """
        widget = self._findWidget(objectName)
        if widget is not None:
            widget.setFocus()
            widget.activateWindow()
            self._app.processEvents()
            return {"success": True}

        item = self._findQmlItem(objectName)
        if item is not None:
            item.setFocus(True)
            item.forceActiveFocus()
            self._app.processEvents()
            return {"success": True}

        return {"success": False, "error": f"Element not found: {objectName}"}

    # -------------------------------------------------------------------------
    # Scene Item Interaction
    # -------------------------------------------------------------------------

    def clickSceneItem(
        self,
        name: str,
        button: int = Qt.LeftButton,
    ) -> Dict[str, Any]:
        """
        Click on a scene item.

        Args:
            name: Scene item name
            button: Mouse button

        Returns:
            Dict with success status
        """
        for view in self._getGraphicsViews():
            scene = view.scene()
            if scene is None:
                continue

            # Find item by name
            item = None
            if hasattr(scene, "find"):
                item = scene.find(name=name)
            else:
                for sceneItem in scene.items():
                    itemName = getattr(sceneItem, "name", None)
                    if callable(itemName):
                        itemName = itemName()
                    if itemName == name:
                        item = sceneItem
                        break

            if item is not None:
                center = item.sceneBoundingRect().center()
                viewPos = view.mapFromScene(center)
                QTest.mouseClick(view.viewport(), button, Qt.NoModifier, viewPos)
                self._app.processEvents()
                return {"success": True}

        return {"success": False, "error": f"Scene item not found: {name}"}

    def getSceneItems(self, itemType: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all scene items.

        Args:
            itemType: Optional type filter

        Returns:
            Dict with list of items
        """
        items = []
        for view in self._getGraphicsViews():
            scene = view.scene()
            if scene is None:
                continue

            for item in scene.items():
                className = type(item).__name__
                if itemType is not None and className != itemType:
                    continue

                info = self._getSceneItemInfo(item, view)
                items.append(info)

        return {"success": True, "items": items}

    # -------------------------------------------------------------------------
    # Window Operations
    # -------------------------------------------------------------------------

    def getWindows(self) -> Dict[str, Any]:
        """Get all top-level windows."""
        windows = []
        for window in self._app.topLevelWidgets():
            if window.isVisible():
                windows.append(
                    {
                        "objectName": window.objectName() or None,
                        "className": type(window).__name__,
                        "title": window.windowTitle(),
                        "geometry": {
                            "x": window.x(),
                            "y": window.y(),
                            "width": window.width(),
                            "height": window.height(),
                        },
                    }
                )
        return {"success": True, "windows": windows}

    def openFile(self, filePath: str) -> Dict[str, Any]:
        """
        Open a file in the application.

        Uses QTimer.singleShot to schedule the open operation after the
        command response is sent, preventing the bridge from blocking.

        Args:
            filePath: Absolute path to the .fd file to open

        Returns:
            Dict with success status
        """
        import os

        try:
            # Find MainWindow
            mainWindow = None
            for window in self._app.topLevelWidgets():
                if type(window).__name__ == "MainWindow":
                    mainWindow = window
                    break

            if mainWindow is None:
                return {"success": False, "error": "MainWindow not found"}

            # Validate file path exists
            if not os.path.exists(filePath):
                return {"success": False, "error": f"File does not exist: {filePath}"}

            # Check if it's a valid .fd bundle (directory with .fd extension)
            if not os.path.isdir(filePath):
                return {
                    "success": False,
                    "error": f"Not a directory/bundle: {filePath}",
                }

            if not filePath.endswith(".fd"):
                return {"success": False, "error": f"Not a .fd file: {filePath}"}

            # Get initial state for verification
            initialTitle = mainWindow.windowTitle()
            initialScene = mainWindow.scene if hasattr(mainWindow, "scene") else None
            initialItemCount = len(initialScene.items()) if initialScene else 0

            # Schedule the open operation via QTimer so it runs after
            # the bridge response is sent. This prevents blocking.
            QTimer.singleShot(0, lambda: mainWindow.open(filePath=filePath))

            return {
                "success": True,
                "message": f"Open scheduled for: {filePath}",
                "note": "File load is async. Wait briefly, then use get_scene_items or get_windows to verify.",
                "initialState": {
                    "title": initialTitle,
                    "itemCount": initialItemCount,
                },
            }

        except Exception as e:
            log.exception(f"Error opening file: {e}")
            return {"success": False, "error": str(e)}

    def activateWindow(self, objectName: str) -> Dict[str, Any]:
        """Activate a window."""
        for window in self._app.topLevelWidgets():
            if window.objectName() == objectName:
                window.activateWindow()
                window.raise_()
                self._app.processEvents()
                return {"success": True}
        return {"success": False, "error": f"Window not found: {objectName}"}

    def takeScreenshot(self, objectName: Optional[str] = None) -> Dict[str, Any]:
        """
        Take a screenshot of a widget or the main window.

        Args:
            objectName: Optional widget to screenshot, defaults to main window

        Returns:
            Dict with success status and base64-encoded PNG data
        """
        import base64

        widget = None
        if objectName:
            widget = self._findWidget(objectName)
            if widget is None:
                return {"success": False, "error": f"Widget not found: {objectName}"}
        else:
            # Default to main window
            for window in self._app.topLevelWidgets():
                if window.isVisible() and window.objectName() == "MainWindow":
                    widget = window
                    break

            if widget is None:
                # Fallback to any visible top-level widget
                for window in self._app.topLevelWidgets():
                    if window.isVisible():
                        widget = window
                        break

        if widget is None:
            return {"success": False, "error": "No visible widget found"}

        # Ensure widget is fully rendered
        self._app.processEvents()

        # Grab the widget
        pixmap = widget.grab()

        # Convert to PNG bytes
        byteArray = QByteArray()
        buffer = QBuffer(byteArray)
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        buffer.close()

        # Encode to base64
        imageData = base64.b64encode(bytes(byteArray)).decode("utf-8")

        return {
            "success": True,
            "width": pixmap.width(),
            "height": pixmap.height(),
            "format": "png",
            "data": imageData,
        }
