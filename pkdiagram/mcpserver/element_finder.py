"""
Element finder utilities for locating UI elements.
"""

import logging
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING

from pkdiagram.pyqt import (
    Qt,
    QWidget,
    QQuickItem,
    QQuickWidget,
    QApplication,
    QObject,
    QPoint,
    QRectF,
)

if TYPE_CHECKING:
    from .app_controller import AppTestController

log = logging.getLogger(__name__)


class ElementFinder:
    """
    Finds and queries UI elements in the application.

    Supports finding:
    - QWidgets by objectName or type
    - QQuickItems by objectName
    - Scene items by name or type
    - Elements by text content
    """

    def __init__(self, controller: "AppTestController"):
        self._controller = controller

    # -------------------------------------------------------------------------
    # Widget Finding
    # -------------------------------------------------------------------------

    def findWidget(
        self,
        objectName: str,
        parent: Optional[QWidget] = None,
    ) -> Optional[QWidget]:
        """
        Find a widget by object name.

        Args:
            objectName: The objectName to search for
            parent: Optional parent widget to search within

        Returns:
            The widget if found, None otherwise
        """
        if parent is None:
            parent = self._controller.mainWindow

        if parent is None:
            # Search all top-level widgets
            for widget in QApplication.topLevelWidgets():
                result = widget.findChild(QWidget, objectName)
                if result is not None:
                    return result
            return None

        return parent.findChild(QWidget, objectName)

    def findWidgetByType(
        self,
        typeName: str,
        parent: Optional[QWidget] = None,
    ) -> List[QWidget]:
        """
        Find all widgets of a specific type.

        Args:
            typeName: The class name to search for (e.g., "QPushButton")
            parent: Optional parent widget

        Returns:
            List of matching widgets
        """
        if parent is None:
            parent = self._controller.mainWindow

        if parent is None:
            return []

        results = []
        for child in parent.findChildren(QWidget):
            if type(child).__name__ == typeName:
                results.append(child)

        return results

    def findWidgetByText(
        self,
        text: str,
        parent: Optional[QWidget] = None,
        exact: bool = False,
    ) -> List[QWidget]:
        """
        Find widgets containing specific text.

        Args:
            text: Text to search for
            parent: Optional parent widget
            exact: If True, require exact match

        Returns:
            List of matching widgets
        """
        if parent is None:
            parent = self._controller.mainWindow

        if parent is None:
            return []

        results = []
        for child in parent.findChildren(QWidget):
            # Try common text properties
            for prop in ["text", "title", "windowTitle", "toolTip", "placeholderText"]:
                value = child.property(prop)
                if value is not None:
                    if exact:
                        if str(value) == text:
                            results.append(child)
                            break
                    else:
                        if text.lower() in str(value).lower():
                            results.append(child)
                            break

        return results

    # -------------------------------------------------------------------------
    # QML Item Finding
    # -------------------------------------------------------------------------

    def findQmlItem(
        self,
        objectName: str,
        root: Optional[QQuickItem] = None,
    ) -> Optional[QQuickItem]:
        """
        Find a QML item by object name.

        Args:
            objectName: The objectName to search for (supports dot notation)
            root: Optional root item to search from

        Returns:
            The QQuickItem if found, None otherwise
        """
        # Handle dot notation for nested items
        if "." in objectName:
            parts = objectName.split(".")
            item = self.findQmlItem(parts[0], root)
            for part in parts[1:]:
                if item is None:
                    return None
                item = self.findQmlItem(part, item)
            return item

        # Get all QML roots if none specified
        if root is None:
            roots = self._getAllQmlRoots()
            for r in roots:
                result = self._findItemRecursive(r, objectName)
                if result is not None:
                    return result
            return None

        return self._findItemRecursive(root, objectName)

    def _findItemRecursive(
        self, item: QQuickItem, objectName: str
    ) -> Optional[QQuickItem]:
        """Recursively search for a QML item by objectName."""
        if item.objectName() == objectName:
            return item

        for child in item.childItems():
            result = self._findItemRecursive(child, objectName)
            if result is not None:
                return result

        return None

    def _getAllQmlRoots(self) -> List[QQuickItem]:
        """Get all QML root items in the application."""
        roots = []

        # Get from DocumentView's QML components
        dv = self._controller.documentView
        if dv is not None:
            # Check for QML drawers/property sheets
            for attr in dir(dv):
                obj = getattr(dv, attr, None)
                if isinstance(obj, QQuickWidget):
                    root = obj.rootObject()
                    if root is not None:
                        roots.append(root)
                elif hasattr(obj, "qml") and isinstance(
                    getattr(obj, "qml", None), QQuickWidget
                ):
                    root = obj.qml.rootObject()
                    if root is not None:
                        roots.append(root)

        # Search all top-level widgets for QQuickWidgets
        for widget in QApplication.topLevelWidgets():
            self._collectQmlRoots(widget, roots)

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

    def findQmlItemByType(
        self,
        typeName: str,
        root: Optional[QQuickItem] = None,
    ) -> List[QQuickItem]:
        """
        Find all QML items of a specific type.

        Args:
            typeName: The QML type name (e.g., "Button", "ListView")
            root: Optional root item

        Returns:
            List of matching items
        """
        results = []

        if root is None:
            roots = self._getAllQmlRoots()
        else:
            roots = [root]

        for r in roots:
            self._findItemsByType(r, typeName, results)

        return results

    def _findItemsByType(
        self,
        item: QQuickItem,
        typeName: str,
        results: List[QQuickItem],
    ):
        """Recursively find items by type."""
        # Check class name and metaobject class name
        className = type(item).__name__
        metaClassName = item.metaObject().className() if item.metaObject() else ""

        if typeName in className or typeName in metaClassName:
            results.append(item)

        for child in item.childItems():
            self._findItemsByType(child, typeName, results)

    def findQmlItemByProperty(
        self,
        propertyName: str,
        propertyValue: Any,
        root: Optional[QQuickItem] = None,
    ) -> List[QQuickItem]:
        """
        Find QML items with a specific property value.

        Args:
            propertyName: Property name to check
            propertyValue: Expected value
            root: Optional root item

        Returns:
            List of matching items
        """
        results = []

        if root is None:
            roots = self._getAllQmlRoots()
        else:
            roots = [root]

        for r in roots:
            self._findItemsByProperty(r, propertyName, propertyValue, results)

        return results

    def _findItemsByProperty(
        self,
        item: QQuickItem,
        propertyName: str,
        propertyValue: Any,
        results: List[QQuickItem],
    ):
        """Recursively find items by property."""
        value = item.property(propertyName)
        if value == propertyValue:
            results.append(item)

        for child in item.childItems():
            self._findItemsByProperty(child, propertyName, propertyValue, results)

    def findContainingQuickWidget(self, item: QQuickItem) -> Optional[QQuickWidget]:
        """
        Find the QQuickWidget that contains a QQuickItem.

        Args:
            item: The QQuickItem to find the container for

        Returns:
            The QQuickWidget, or None if not found
        """
        # Get the window (QQuickWindow) containing this item
        window = item.window()
        if window is None:
            return None

        # Search for the QQuickWidget with this window
        for widget in QApplication.topLevelWidgets():
            result = self._findQuickWidgetWithWindow(widget, window)
            if result is not None:
                return result

        return None

    def _findQuickWidgetWithWindow(
        self, widget: QWidget, window
    ) -> Optional[QQuickWidget]:
        """Find a QQuickWidget with a specific window."""
        if isinstance(widget, QQuickWidget):
            if widget.quickWindow() == window:
                return widget

        for child in widget.findChildren(QQuickWidget):
            if child.quickWindow() == window:
                return child

        return None

    # -------------------------------------------------------------------------
    # Scene Item Finding
    # -------------------------------------------------------------------------

    def findSceneItem(
        self,
        name: Optional[str] = None,
        itemType: Optional[str] = None,
        **kwargs,
    ) -> Optional[Any]:
        """
        Find an item in the Scene.

        Args:
            name: Item name to search for
            itemType: Item type (e.g., "Person", "Marriage")
            **kwargs: Additional property filters

        Returns:
            The scene item if found, None otherwise
        """
        scene = self._controller.scene
        if scene is None:
            return None

        # Use Scene.find() if available
        if hasattr(scene, "find"):
            return scene.find(name=name, **kwargs)

        # Manual search
        for item in scene.items():
            if name is not None:
                itemName = getattr(item, "name", None)
                if itemName != name:
                    continue

            if itemType is not None:
                if type(item).__name__ != itemType:
                    continue

            # Check additional properties
            match = True
            for key, value in kwargs.items():
                if getattr(item, key, None) != value:
                    match = False
                    break

            if match:
                return item

        return None

    def findAllSceneItems(
        self,
        itemType: Optional[str] = None,
        **kwargs,
    ) -> List[Any]:
        """
        Find all scene items matching criteria.

        Args:
            itemType: Item type filter
            **kwargs: Additional property filters

        Returns:
            List of matching scene items
        """
        scene = self._controller.scene
        if scene is None:
            return []

        results = []
        for item in scene.items():
            if itemType is not None:
                if type(item).__name__ != itemType:
                    continue

            match = True
            for key, value in kwargs.items():
                if getattr(item, key, None) != value:
                    match = False
                    break

            if match:
                results.append(item)

        return results

    # -------------------------------------------------------------------------
    # Element Information
    # -------------------------------------------------------------------------

    def getElementInfo(
        self,
        element: Union[str, QWidget, QQuickItem],
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about an element.

        Args:
            element: Object name, QWidget, or QQuickItem

        Returns:
            Dict with element information
        """
        if isinstance(element, str):
            # Try to find by name
            widget = self.findWidget(element)
            if widget is not None:
                element = widget
            else:
                qmlItem = self.findQmlItem(element)
                if qmlItem is not None:
                    element = qmlItem
                else:
                    return None

        if isinstance(element, QQuickItem):
            return self._getQmlItemInfo(element)
        else:
            return self._getWidgetInfo(element)

    def _getWidgetInfo(self, widget: QWidget) -> Dict[str, Any]:
        """Get information about a QWidget."""
        rect = widget.geometry()
        return {
            "type": "widget",
            "className": type(widget).__name__,
            "objectName": widget.objectName(),
            "visible": widget.isVisible(),
            "enabled": widget.isEnabled(),
            "focused": widget.hasFocus(),
            "geometry": {
                "x": rect.x(),
                "y": rect.y(),
                "width": rect.width(),
                "height": rect.height(),
            },
            "properties": self._getCommonProperties(widget),
        }

    def _getQmlItemInfo(self, item: QQuickItem) -> Dict[str, Any]:
        """Get information about a QQuickItem."""
        return {
            "type": "qml",
            "className": type(item).__name__,
            "metaClassName": item.metaObject().className() if item.metaObject() else "",
            "objectName": item.objectName(),
            "visible": item.isVisible(),
            "enabled": item.isEnabled(),
            "focused": item.hasActiveFocus(),
            "geometry": {
                "x": item.x(),
                "y": item.y(),
                "width": item.width(),
                "height": item.height(),
            },
            "properties": self._getQmlProperties(item),
        }

    def _getCommonProperties(self, obj: QObject) -> Dict[str, Any]:
        """Get common properties from a QObject."""
        props = {}
        commonProps = [
            "text",
            "title",
            "checked",
            "checkState",
            "currentIndex",
            "currentText",
            "value",
            "minimum",
            "maximum",
            "count",
            "toolTip",
            "placeholder",
        ]

        for prop in commonProps:
            value = obj.property(prop)
            if value is not None:
                props[prop] = self._convertValue(value)

        return props

    def _getQmlProperties(self, item: QQuickItem) -> Dict[str, Any]:
        """Get QML-specific properties."""
        props = self._getCommonProperties(item)

        # Add QML-specific properties
        qmlProps = [
            "opacity",
            "scale",
            "rotation",
            "clip",
            "smooth",
            "antialiasing",
        ]

        for prop in qmlProps:
            value = item.property(prop)
            if value is not None:
                props[prop] = self._convertValue(value)

        return props

    def _convertValue(self, value: Any) -> Any:
        """Convert Qt types to JSON-serializable types."""
        if hasattr(value, "toString"):
            return value.toString()
        elif hasattr(value, "__iter__") and not isinstance(value, str):
            return list(value)
        elif isinstance(value, (int, float, str, bool, type(None))):
            return value
        else:
            return str(value)

    # -------------------------------------------------------------------------
    # Tree Inspection
    # -------------------------------------------------------------------------

    def getWidgetTree(
        self,
        root: Optional[QWidget] = None,
        maxDepth: int = 10,
    ) -> Dict[str, Any]:
        """
        Get the widget tree structure.

        Args:
            root: Root widget (defaults to main window)
            maxDepth: Maximum depth to traverse

        Returns:
            Tree structure as nested dicts
        """
        if root is None:
            root = self._controller.mainWindow

        if root is None:
            return {}

        return self._buildWidgetTree(root, 0, maxDepth)

    def _buildWidgetTree(
        self, widget: QWidget, depth: int, maxDepth: int
    ) -> Dict[str, Any]:
        """Build widget tree recursively."""
        node = {
            "className": type(widget).__name__,
            "objectName": widget.objectName(),
            "visible": widget.isVisible(),
        }

        if depth < maxDepth:
            children = []
            for child in widget.children():
                if isinstance(child, QWidget):
                    children.append(self._buildWidgetTree(child, depth + 1, maxDepth))

            if children:
                node["children"] = children

        return node

    def getQmlTree(
        self,
        root: Optional[QQuickItem] = None,
        maxDepth: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get the QML item tree structure.

        Args:
            root: Root item (defaults to all roots)
            maxDepth: Maximum depth to traverse

        Returns:
            List of tree structures
        """
        if root is None:
            roots = self._getAllQmlRoots()
            return [self._buildQmlTree(r, 0, maxDepth) for r in roots]

        return [self._buildQmlTree(root, 0, maxDepth)]

    def _buildQmlTree(
        self, item: QQuickItem, depth: int, maxDepth: int
    ) -> Dict[str, Any]:
        """Build QML tree recursively."""
        node = {
            "className": type(item).__name__,
            "objectName": item.objectName(),
            "visible": item.isVisible(),
        }

        if depth < maxDepth:
            children = []
            for child in item.childItems():
                children.append(self._buildQmlTree(child, depth + 1, maxDepth))

            if children:
                node["children"] = children

        return node

    # -------------------------------------------------------------------------
    # Wait Utilities
    # -------------------------------------------------------------------------

    def waitForElement(
        self,
        objectName: str,
        timeout: int = 5000,
        checkVisible: bool = True,
    ) -> Optional[Union[QWidget, QQuickItem]]:
        """
        Wait for an element to appear.

        Args:
            objectName: Element objectName to wait for
            timeout: Maximum wait time in ms
            checkVisible: If True, also wait for visibility

        Returns:
            The element if found, None if timeout
        """

        def check():
            widget = self.findWidget(objectName)
            if widget is not None:
                if not checkVisible or widget.isVisible():
                    return widget

            item = self.findQmlItem(objectName)
            if item is not None:
                if not checkVisible or item.isVisible():
                    return item

            return None

        result = None
        elapsed = 0
        interval = 50

        while elapsed < timeout:
            self._controller.processEvents(interval)
            result = check()
            if result is not None:
                return result
            elapsed += interval

        return None

    def waitForElementGone(
        self,
        objectName: str,
        timeout: int = 5000,
    ) -> bool:
        """
        Wait for an element to disappear.

        Args:
            objectName: Element objectName
            timeout: Maximum wait time in ms

        Returns:
            True if element is gone, False if timeout
        """
        elapsed = 0
        interval = 50

        while elapsed < timeout:
            self._controller.processEvents(interval)

            widget = self.findWidget(objectName)
            item = self.findQmlItem(objectName)

            if widget is None and item is None:
                return True

            # Also check visibility
            if widget is not None and not widget.isVisible():
                return True
            if item is not None and not item.isVisible():
                return True

            elapsed += interval

        return False

    def waitForProperty(
        self,
        objectName: str,
        propertyName: str,
        expectedValue: Any,
        timeout: int = 5000,
    ) -> bool:
        """
        Wait for an element's property to reach a specific value.

        Args:
            objectName: Element objectName
            propertyName: Property to check
            expectedValue: Expected value
            timeout: Maximum wait time in ms

        Returns:
            True if property matches, False if timeout
        """
        elapsed = 0
        interval = 50

        while elapsed < timeout:
            self._controller.processEvents(interval)

            value = self._controller.getProperty(objectName, propertyName)
            if value == expectedValue:
                return True

            elapsed += interval

        return False
