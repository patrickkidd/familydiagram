"""
Qt Inspector - Inspects Qt widgets and QML items.

This module provides deep inspection of the Qt object hierarchy,
including widgets, QML items, and QGraphicsView scene items.
"""

import logging
from typing import Optional, Dict, Any, List, Union

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
        maxDepth: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        List all elements in the UI.

        Args:
            elementType: Filter by type ("widget", "qml", "scene", or None for all)
            maxDepth: Maximum depth to traverse

        Returns:
            List of element info dicts
        """
        elements = []

        # Collect widgets
        if elementType is None or elementType == "widget":
            for window in self._app.topLevelWidgets():
                self._collectWidgets(window, elements, 0, maxDepth)

        # Collect QML items
        if elementType is None or elementType == "qml":
            for root in self._getQmlRoots():
                self._collectQmlItems(root, elements, 0, maxDepth)

        # Collect scene items
        if elementType is None or elementType == "scene":
            for view in self._getGraphicsViews():
                self._collectSceneItems(view, elements)

        return elements

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
    ):
        """Collect widgets recursively."""
        if depth > maxDepth:
            return

        info = self._getWidgetInfo(widget)
        if info:
            elements.append(info)

        for child in widget.children():
            if isinstance(child, QWidget):
                self._collectWidgets(child, elements, depth + 1, maxDepth)

    def _collectQmlItems(
        self,
        item: QQuickItem,
        elements: List[Dict],
        depth: int,
        maxDepth: int,
    ):
        """Collect QML items recursively."""
        if depth > maxDepth:
            return

        info = self._getQmlItemInfo(item)
        if info:
            elements.append(info)

        for child in item.childItems():
            self._collectQmlItems(child, elements, depth + 1, maxDepth)

    def _collectSceneItems(self, view: QGraphicsView, elements: List[Dict]):
        """Collect scene items from a QGraphicsView."""
        scene = view.scene()
        if scene is None:
            return

        for item in scene.items():
            info = self._getSceneItemInfo(item, view)
            if info:
                elements.append(info)

    # -------------------------------------------------------------------------
    # Element Info
    # -------------------------------------------------------------------------

    def _getWidgetInfo(self, widget: QWidget) -> Dict[str, Any]:
        """Get info about a widget."""
        globalPos = widget.mapToGlobal(QPoint(0, 0))
        rect = widget.rect()

        return {
            "type": "widget",
            "objectName": widget.objectName() or None,
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
            "text": self._getTextProperty(widget),
            "checked": widget.property("checked"),
        }

    def _getQmlItemInfo(self, item: QQuickItem) -> Dict[str, Any]:
        """Get info about a QML item."""
        # Get screen position
        window = item.window()
        quickWidget = self._findQuickWidgetForItem(item)

        if quickWidget is not None:
            # Map to widget coordinates then to global
            scenePos = item.mapToScene(QPointF(0, 0))
            globalPos = quickWidget.mapToGlobal(scenePos.toPoint())
            x, y = globalPos.x(), globalPos.y()
        else:
            x, y = int(item.x()), int(item.y())

        return {
            "type": "qml",
            "objectName": item.objectName() or None,
            "className": type(item).__name__,
            "qmlType": item.metaObject().className() if item.metaObject() else None,
            "visible": item.isVisible(),
            "enabled": item.isEnabled(),
            "focused": item.hasActiveFocus(),
            "geometry": {
                "x": x,
                "y": y,
                "width": int(item.width()),
                "height": int(item.height()),
            },
            "text": item.property("text"),
            "checked": item.property("checked"),
        }

    def _getSceneItemInfo(
        self, item: QGraphicsItem, view: QGraphicsView
    ) -> Dict[str, Any]:
        """Get info about a scene item."""
        # Get screen position
        sceneRect = item.sceneBoundingRect()
        viewPos = view.mapFromScene(sceneRect.topLeft())
        globalPos = view.viewport().mapToGlobal(viewPos)

        # Try to get name from item
        name = None
        if hasattr(item, "name"):
            name = getattr(item, "name", None)
            if callable(name):
                name = name()

        itemId = None
        if hasattr(item, "id"):
            itemId = getattr(item, "id", None)

        return {
            "type": "scene",
            "objectName": name,
            "id": itemId,
            "className": type(item).__name__,
            "visible": item.isVisible(),
            "geometry": {
                "x": globalPos.x(),
                "y": globalPos.y(),
                "width": int(sceneRect.width()),
                "height": int(sceneRect.height()),
            },
        }

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

    def getProperty(
        self, objectName: str, propertyName: str
    ) -> Dict[str, Any]:
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

    def getSceneItems(
        self, itemType: Optional[str] = None
    ) -> Dict[str, Any]:
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
                windows.append({
                    "objectName": window.objectName() or None,
                    "className": type(window).__name__,
                    "title": window.windowTitle(),
                    "geometry": {
                        "x": window.x(),
                        "y": window.y(),
                        "width": window.width(),
                        "height": window.height(),
                    },
                })
        return {"success": True, "windows": windows}

    def activateWindow(self, objectName: str) -> Dict[str, Any]:
        """Activate a window."""
        for window in self._app.topLevelWidgets():
            if window.objectName() == objectName:
                window.activateWindow()
                window.raise_()
                self._app.processEvents()
                return {"success": True}
        return {"success": False, "error": f"Window not found: {objectName}"}
