"""
Qt Inspector - Inspects Qt widgets and QML items.

This module provides deep inspection of the Qt object hierarchy,
including widgets, QML items, and QGraphicsView scene items.
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any, List, Union


class AppState(str, Enum):
    Initializing = "initializing"
    Running = "running"
    Stopped = "stopped"
    Error = "error"


class AppLoginState(str, Enum):
    AccountDialogVisible = "account_dialog_visible"
    NotLoggedIn = "not_logged_in"
    LoggedIn = "logged_in"


class AppView(str, Enum):
    FileManager = "file_manager"
    DocumentView = "document_view"
    AccountView = "account_view"
    WelcomeView = "welcome_view"
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
    QQuickWindow,
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
        # Try Pro app first (MainWindow widget)
        mainWindow = None
        for window in self._app.topLevelWidgets():
            if type(window).__name__ == "MainWindow":
                mainWindow = window
                break

        if mainWindow is not None:
            return self._getProAppState(mainWindow)

        # Try Personal app (QQuickWindow from QQmlApplicationEngine)
        personalWindow = self._findPersonalAppWindow()
        if personalWindow is not None:
            return self._getPersonalAppState(personalWindow)

        # Neither app type found - still initializing
        return {
            "success": True,
            "state": {
                "appState": AppState.Initializing.value,
                "loginState": None,
                "currentView": None,
            },
        }

    def _findPersonalAppWindow(self) -> Optional[QQuickWindow]:
        for window in self._app.topLevelWindows():
            if isinstance(window, QQuickWindow):
                rootItem = window.contentItem()
                if rootItem:
                    for child in rootItem.childItems():
                        if child.objectName() == "personalView" or "PersonalContainer" in type(child).__name__:
                            return window
                    # Check if window has personalApp context property
                    if window.property("personalView") is not None:
                        return window
                return window
        return None

    def _getProAppState(self, mainWindow) -> Dict[str, Any]:
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

        session = mainWindow.session
        if any(d["className"] == "AccountDialog" for d in visibleDialogs):
            loginState = AppLoginState.AccountDialogVisible.value
        elif session.isLoggedIn():
            loginState = AppLoginState.LoggedIn.value
        else:
            loginState = AppLoginState.NotLoggedIn.value

        currentView = None
        loadedFileName = None

        if any(d["className"] == "AccountDialog" for d in visibleDialogs):
            currentView = AppView.AccountView.value
        elif any(d["className"] == "WelcomeDialog" for d in visibleDialogs):
            currentView = AppView.WelcomeView.value
        else:
            fileManager = mainWindow.fileManager
            documentView = mainWindow.documentView

            if fileManager.isVisible() and documentView.isVisible():
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
                "appType": "pro",
                "loginState": loginState,
                "currentView": currentView,
                "loadedFileName": loadedFileName,
                "visibleDialogs": visibleDialogs,
            },
        }

    def _getPersonalAppState(self, window: QQuickWindow) -> Dict[str, Any]:
        rootItem = window.contentItem()

        personalContainer = self._findQmlItemByType(rootItem, "PersonalContainer")

        session = None
        personalApp = None

        for child in rootItem.childItems():
            if "ApplicationWindow" in type(child).__name__ or child.property("personalView") is not None:
                engine = child.property("__engine")
                if engine:
                    ctx = engine.rootContext()
                    session = ctx.contextProperty("session")
                    personalApp = ctx.contextProperty("personalApp")
                break

        loginState = None
        currentView = None

        accountDialog = self._findQmlItemInChildren(rootItem, "AccountDialog")
        if accountDialog and accountDialog.isVisible():
            loginState = AppLoginState.AccountDialogVisible.value
            currentView = AppView.AccountView.value
        elif personalContainer:
            tabBar = personalContainer.property("tabBar")

            if tabBar is not None and tabBar.property("visible"):
                loginState = AppLoginState.LoggedIn.value
                tabIndex = tabBar.property("currentIndex")
                if tabIndex == 0:
                    currentView = AppView.DiscussView.value
                elif tabIndex == 1:
                    currentView = AppView.LearnView.value
                elif tabIndex == 2:
                    currentView = AppView.PlanView.value
            else:
                loginState = AppLoginState.NotLoggedIn.value
        else:
            loginState = AppLoginState.NotLoggedIn.value

        return {
            "success": True,
            "state": {
                "appState": AppState.Running.value,
                "appType": "personal",
                "loginState": loginState,
                "currentView": currentView,
                "loadedFileName": None,
                "visibleDialogs": [],
            },
        }

    def _findQmlItemByType(self, parent: QQuickItem, typeName: str) -> Optional[QQuickItem]:
        if parent is None:
            return None

        className = type(parent).__name__
        if typeName in className:
            return parent

        for child in parent.childItems():
            result = self._findQmlItemByType(child, typeName)
            if result is not None:
                return result

        return None

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
        """Get all QML root items from both widgets and windows."""
        roots = []

        # Collect from QQuickWidgets embedded in widgets
        for window in self._app.topLevelWidgets():
            self._collectQmlRoots(window, roots)

        # Collect from QQuickWindows (Personal app uses QQmlApplicationEngine)
        for window in self._app.topLevelWindows():
            if isinstance(window, QQuickWindow):
                contentItem = window.contentItem()
                if contentItem is not None:
                    # Add all direct children of contentItem as roots
                    for child in contentItem.childItems():
                        if child not in roots:
                            roots.append(child)

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

    def _findWindowForQmlItem(self, item: QQuickItem) -> Optional[Union[QQuickWidget, QQuickWindow]]:
        """Find the QQuickWidget or QQuickWindow containing a QQuickItem."""
        window = item.window()
        if window is None:
            return None

        # First try to find a QQuickWidget (Pro app embeds QML in widgets)
        for topWidget in self._app.topLevelWidgets():
            for qw in topWidget.findChildren(QQuickWidget):
                if qw.quickWindow() == window:
                    return qw

        # Fall back to returning the QQuickWindow directly (Personal app)
        if isinstance(window, QQuickWindow):
            return window

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
        target = self._findWindowForQmlItem(item)
        if target is None:
            return {"success": False, "error": "Could not find QQuickWidget or QQuickWindow"}

        if pos is None:
            localPos = QPointF(item.width() / 2, item.height() / 2)
        else:
            localPos = QPointF(pos[0], pos[1])

        scenePos = item.mapToScene(localPos)
        clickPos = scenePos.toPoint()

        # QQuickWindow needs QTest.mouseClick on the window directly
        # QQuickWidget can be clicked as a QWidget
        if isinstance(target, QQuickWidget):
            QTest.mouseClick(target, button, Qt.NoModifier, clickPos)
        else:
            # For QQuickWindow, use QTest with the window
            QTest.mouseClick(target, button, Qt.NoModifier, clickPos)

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
            target = self._findWindowForQmlItem(item)
            if target is None:
                return {"success": False, "error": "Could not find QQuickWidget or QQuickWindow"}

            if pos is None:
                localPos = QPointF(item.width() / 2, item.height() / 2)
            else:
                localPos = QPointF(pos[0], pos[1])

            scenePos = item.mapToScene(localPos)
            QTest.mouseDClick(target, button, Qt.NoModifier, scenePos.toPoint())
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
                    target = self._findWindowForQmlItem(item)

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
                    target = self._findWindowForQmlItem(item)

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
        """Get all top-level windows (both widgets and QQuickWindows)."""
        windows = []

        # Collect QWidget windows
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
                        "type": "widget",
                    }
                )

        # Collect QQuickWindow windows (Personal app)
        for window in self._app.topLevelWindows():
            if isinstance(window, QQuickWindow) and window.isVisible():
                windows.append(
                    {
                        "objectName": window.objectName() or None,
                        "className": type(window).__name__,
                        "title": window.title(),
                        "geometry": {
                            "x": window.x(),
                            "y": window.y(),
                            "width": window.width(),
                            "height": window.height(),
                        },
                        "type": "quick",
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
        Take a screenshot of a widget, QQuickWindow, or the main window.

        Args:
            objectName: Optional widget to screenshot, defaults to main window

        Returns:
            Dict with success status and base64-encoded PNG data
        """
        import base64

        target = None
        isQuickWindow = False

        if objectName:
            target = self._findWidget(objectName)
            if target is None:
                return {"success": False, "error": f"Widget not found: {objectName}"}
        else:
            # Default to main window - first try MainWindow widget (Pro app)
            for window in self._app.topLevelWidgets():
                if window.isVisible() and window.objectName() == "MainWindow":
                    target = window
                    break

            # If no MainWindow, try QQuickWindow (Personal app)
            if target is None:
                for window in self._app.topLevelWindows():
                    if isinstance(window, QQuickWindow) and window.isVisible():
                        target = window
                        isQuickWindow = True
                        break

            # Fallback to any visible top-level widget
            if target is None:
                for window in self._app.topLevelWidgets():
                    if window.isVisible():
                        target = window
                        break

        if target is None:
            return {"success": False, "error": "No visible window found"}

        # Ensure fully rendered
        self._app.processEvents()

        # Grab the screenshot
        if isQuickWindow:
            # QQuickWindow uses grabWindow() which returns a QImage
            image = target.grabWindow()
            if image.isNull():
                # Fallback: try to render the content item
                contentItem = target.contentItem()
                if contentItem:
                    from pkdiagram.pyqt import QQuickItemGrabResult
                    # Use QQuickItem.grabToImage() for offscreen rendering
                    # This is async, but we need sync - fall back to empty pixmap
                    return {
                        "success": False,
                        "error": "QQuickWindow screenshot not available in offscreen mode",
                    }
            pixmap = QPixmap.fromImage(image)
        else:
            # QWidget uses grab() which returns a QPixmap
            pixmap = target.grab()

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

    # -------------------------------------------------------------------------
    # Personal App State Introspection
    # -------------------------------------------------------------------------

    def getPersonalState(self, component: str = "all") -> Dict[str, Any]:
        """
        Get state from the Personal app.

        Args:
            component: Which component to inspect:
                - "all": Overview of all components
                - "learn": Learn tab (sarfGraphModel + QML state)
                - "discuss": Discuss tab (chat state + QML state)
                - "plan": Plan tab (diagram view state)
                - "pdp": PDP import state

        Returns:
            Dict with model data and QML UI state for the component
        """
        # Find PersonalAppController
        controller = self._findPersonalAppController()
        if controller is None:
            return {"success": False, "error": "PersonalAppController not found"}

        # Find Personal app window for QML state
        personalWindow = self._findPersonalAppWindow()
        rootItem = personalWindow.contentItem() if personalWindow else None

        if component == "all":
            return self._getPersonalOverview(controller, rootItem)
        elif component == "learn":
            return self._getLearnState(controller, rootItem)
        elif component == "discuss":
            return self._getDiscussState(controller, rootItem)
        elif component == "plan":
            return self._getPlanState(controller, rootItem)
        elif component == "pdp":
            return self._getPdpState(controller, rootItem)
        else:
            return {"success": False, "error": f"Unknown component: {component}"}

    def _findPersonalAppController(self):
        """Find the PersonalAppController instance."""
        # Try app.personalController attribute (set in main.py)
        controller = getattr(self._app, "personalController", None)
        if controller:
            return controller

        # Fallback: try QApplication children
        from pkdiagram.personal import PersonalAppController

        for child in self._app.children():
            if isinstance(child, PersonalAppController):
                return child

        return None

    def _getPersonalOverview(self, controller, rootItem) -> Dict[str, Any]:
        """Get overview of all Personal app state."""
        result = {"success": True, "component": "all"}

        # Session info
        session = controller.session
        result["session"] = {
            "isLoggedIn": session.isLoggedIn() if session else False,
            "hasActiveChat": hasattr(session, "activeChat") and session.activeChat is not None,
        }

        # Scene info
        scene = controller.scene
        result["scene"] = {
            "personCount": len(list(scene.people())) if scene else 0,
            "eventCount": len(list(scene.events())) if scene else 0,
        }

        # Current tab from QML
        if rootItem:
            container = self._findQmlItemByType(rootItem, "PersonalContainer")
            if container:
                tabBar = container.property("tabBar")
                if tabBar:
                    result["currentTab"] = tabBar.property("currentIndex")

        # Model summaries
        result["sarfGraphModel"] = {
            "hasData": controller.sarfGraphModel.hasData,
            "eventCount": len(controller.sarfGraphModel.events),
        }

        return result

    def _getLearnState(self, controller, rootItem) -> Dict[str, Any]:
        """Get Learn tab state (sarfGraphModel + QML)."""
        model = controller.sarfGraphModel

        result = {
            "success": True,
            "component": "learn",
            "model": {
                "hasData": model.hasData,
                "yearStart": model.yearStart,
                "yearEnd": model.yearEnd,
                "yearSpan": model.yearSpan,
                "eventCount": len(model.events),
                "events": model.events,
                "cumulative": model.cumulative,
            },
        }

        # QML UI state
        if rootItem:
            learnView = self._findQmlItemInChildren(rootItem, "learnView")
            if learnView:
                result["ui"] = {
                    "visible": learnView.isVisible(),
                    "selectedEvent": learnView.property("selectedEvent"),
                    "highlightedEvent": learnView.property("highlightedEvent"),
                }

                # Get storyList state
                storyList = self._findQmlItemInChildren(learnView, "storyList")
                if storyList:
                    result["ui"]["storyList"] = {
                        "count": storyList.property("count"),
                        "contentY": storyList.property("contentY"),
                        "currentIndex": storyList.property("currentIndex"),
                    }

        return result

    def _getDiscussState(self, controller, rootItem) -> Dict[str, Any]:
        """Get Discuss tab state (chat + QML)."""
        result = {
            "success": True,
            "component": "discuss",
            "model": {},
        }

        # Chat state from session if available
        session = controller.session
        if session and hasattr(session, "messages"):
            result["model"]["messageCount"] = len(session.messages) if session.messages else 0

        # QML UI state
        if rootItem:
            discussView = self._findQmlItemInChildren(rootItem, "discussView")
            if discussView:
                result["ui"] = {
                    "visible": discussView.isVisible(),
                }

        return result

    def _getPlanState(self, controller, rootItem) -> Dict[str, Any]:
        """Get Plan tab state (diagram view)."""
        result = {
            "success": True,
            "component": "plan",
            "model": {},
        }

        # Scene data
        scene = controller.scene
        if scene:
            result["model"]["personCount"] = len(list(scene.people()))
            result["model"]["eventCount"] = len(list(scene.events()))

        # QML UI state
        if rootItem:
            planView = self._findQmlItemInChildren(rootItem, "planView")
            if planView:
                result["ui"] = {
                    "visible": planView.isVisible(),
                }

        return result

    def _getPdpState(self, controller, rootItem) -> Dict[str, Any]:
        """Get PDP import state."""
        result = {
            "success": True,
            "component": "pdp",
            "model": {},
        }

        # PDP data from session if available
        session = controller.session
        if session:
            pdp = getattr(session, "pdp", None)
            if pdp:
                result["model"]["hasPdp"] = True
            else:
                result["model"]["hasPdp"] = False

        return result
