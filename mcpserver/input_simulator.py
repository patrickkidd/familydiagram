"""
Input event simulation for PyQt+QML applications.
"""

import logging
from typing import Optional, Union, Tuple, TYPE_CHECKING

from pkdiagram.pyqt import (
    Qt,
    QWidget,
    QQuickItem,
    QQuickWidget,
    QPoint,
    QPointF,
    QTest,
    QApplication,
    QMouseEvent,
    QKeyEvent,
    QEvent,
    QCoreApplication,
    QGraphicsView,
    QGraphicsItem,
)

if TYPE_CHECKING:
    from .app_controller import AppTestController

log = logging.getLogger(__name__)


# Key name to Qt.Key mapping
KEY_MAP = {
    "enter": Qt.Key_Return,
    "return": Qt.Key_Return,
    "tab": Qt.Key_Tab,
    "escape": Qt.Key_Escape,
    "esc": Qt.Key_Escape,
    "backspace": Qt.Key_Backspace,
    "delete": Qt.Key_Delete,
    "space": Qt.Key_Space,
    "up": Qt.Key_Up,
    "down": Qt.Key_Down,
    "left": Qt.Key_Left,
    "right": Qt.Key_Right,
    "home": Qt.Key_Home,
    "end": Qt.Key_End,
    "pageup": Qt.Key_PageUp,
    "pagedown": Qt.Key_PageDown,
    "f1": Qt.Key_F1,
    "f2": Qt.Key_F2,
    "f3": Qt.Key_F3,
    "f4": Qt.Key_F4,
    "f5": Qt.Key_F5,
    "f6": Qt.Key_F6,
    "f7": Qt.Key_F7,
    "f8": Qt.Key_F8,
    "f9": Qt.Key_F9,
    "f10": Qt.Key_F10,
    "f11": Qt.Key_F11,
    "f12": Qt.Key_F12,
    "ctrl": Qt.Key_Control,
    "shift": Qt.Key_Shift,
    "alt": Qt.Key_Alt,
    "meta": Qt.Key_Meta,
}


class InputSimulator:
    """
    Simulates keyboard and mouse input for PyQt+QML applications.

    Provides methods for:
    - Mouse clicks, double clicks, moves, and drags
    - Keyboard typing and key presses
    - Focus management
    - Scroll events
    """

    def __init__(self, controller: "AppTestController"):
        self._controller = controller

    def _resolveTarget(
        self, target: Union[str, QWidget, QQuickItem]
    ) -> Optional[Union[QWidget, QQuickItem]]:
        """Resolve a target specification to an actual widget or QML item."""
        if isinstance(target, str):
            # Try to find by object name
            widget = self._controller.findWidget(target)
            if widget is not None:
                return widget
            return self._controller.findQmlItem(target)
        return target

    def _getWidgetForQmlItem(self, item: QQuickItem) -> Optional[QWidget]:
        """Get the QWidget that contains a QQuickItem."""
        window = item.window()
        if window is None:
            return None

        # Find the QQuickWidget that owns this item
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QQuickWidget):
                if widget.rootObject() == window.contentItem():
                    return widget
            # Check children
            for child in widget.findChildren(QQuickWidget):
                root = child.rootObject()
                if root is not None:
                    # Check if item is a descendant
                    parent = item
                    while parent is not None:
                        if parent == root:
                            return child
                        parent = parent.parentItem()
        return None

    def _getItemCenter(self, item: QQuickItem) -> QPointF:
        """Get the center point of a QQuickItem in its local coordinates."""
        return QPointF(item.width() / 2, item.height() / 2)

    def _mapToWidget(
        self, item: QQuickItem, localPos: QPointF, widget: QWidget
    ) -> QPoint:
        """Map a local position in a QQuickItem to widget coordinates."""
        # Map to scene coordinates
        scenePos = item.mapToScene(localPos)
        # For QQuickWidget, scene coords are widget coords
        return scenePos.toPoint()

    # -------------------------------------------------------------------------
    # Mouse Events
    # -------------------------------------------------------------------------

    def click(
        self,
        target: Union[str, QWidget, QQuickItem],
        button: int = Qt.LeftButton,
        pos: Optional[Tuple[int, int]] = None,
        modifiers: int = Qt.NoModifier,
    ) -> bool:
        """
        Click on a target widget or QML item.

        Args:
            target: Object name, QWidget, or QQuickItem to click
            button: Mouse button (Qt.LeftButton, Qt.RightButton, etc.)
            pos: Optional (x, y) position relative to target. Defaults to center.
            modifiers: Keyboard modifiers (Qt.ControlModifier, etc.)

        Returns:
            True if click was performed successfully
        """
        resolved = self._resolveTarget(target)
        if resolved is None:
            log.error(f"Could not find target: {target}")
            return False

        if isinstance(resolved, QQuickItem):
            return self._clickQmlItem(resolved, button, pos, modifiers)
        else:
            return self._clickWidget(resolved, button, pos, modifiers)

    def _clickWidget(
        self,
        widget: QWidget,
        button: int,
        pos: Optional[Tuple[int, int]],
        modifiers: int,
    ) -> bool:
        """Click on a QWidget."""
        if pos is None:
            clickPos = widget.rect().center()
        else:
            clickPos = QPoint(pos[0], pos[1])

        QTest.mouseClick(widget, button, modifiers, clickPos)
        self._controller.processEvents()
        return True

    def _clickQmlItem(
        self,
        item: QQuickItem,
        button: int,
        pos: Optional[Tuple[int, int]],
        modifiers: int,
    ) -> bool:
        """Click on a QQuickItem."""
        widget = self._getWidgetForQmlItem(item)
        if widget is None:
            log.error("Could not find widget for QML item")
            return False

        if pos is None:
            localPos = self._getItemCenter(item)
        else:
            localPos = QPointF(pos[0], pos[1])

        widgetPos = self._mapToWidget(item, localPos, widget)
        QTest.mouseClick(widget, button, modifiers, widgetPos)
        self._controller.processEvents()
        return True

    def doubleClick(
        self,
        target: Union[str, QWidget, QQuickItem],
        button: int = Qt.LeftButton,
        pos: Optional[Tuple[int, int]] = None,
        modifiers: int = Qt.NoModifier,
    ) -> bool:
        """
        Double-click on a target widget or QML item.

        Args:
            target: Object name, QWidget, or QQuickItem to double-click
            button: Mouse button
            pos: Optional (x, y) position relative to target
            modifiers: Keyboard modifiers

        Returns:
            True if double-click was performed successfully
        """
        resolved = self._resolveTarget(target)
        if resolved is None:
            log.error(f"Could not find target: {target}")
            return False

        if isinstance(resolved, QQuickItem):
            widget = self._getWidgetForQmlItem(resolved)
            if widget is None:
                return False
            if pos is None:
                localPos = self._getItemCenter(resolved)
            else:
                localPos = QPointF(pos[0], pos[1])
            widgetPos = self._mapToWidget(resolved, localPos, widget)
            QTest.mouseDClick(widget, button, modifiers, widgetPos)
        else:
            if pos is None:
                clickPos = resolved.rect().center()
            else:
                clickPos = QPoint(pos[0], pos[1])
            QTest.mouseDClick(resolved, button, modifiers, clickPos)

        self._controller.processEvents()
        return True

    def mouseMove(
        self,
        target: Union[str, QWidget, QQuickItem],
        pos: Tuple[int, int],
        modifiers: int = Qt.NoModifier,
    ) -> bool:
        """
        Move mouse to a position within a target.

        Args:
            target: Object name, QWidget, or QQuickItem
            pos: (x, y) position relative to target
            modifiers: Keyboard modifiers

        Returns:
            True if move was performed successfully
        """
        resolved = self._resolveTarget(target)
        if resolved is None:
            log.error(f"Could not find target: {target}")
            return False

        if isinstance(resolved, QQuickItem):
            widget = self._getWidgetForQmlItem(resolved)
            if widget is None:
                return False
            localPos = QPointF(pos[0], pos[1])
            widgetPos = self._mapToWidget(resolved, localPos, widget)
            QTest.mouseMove(widget, widgetPos)
        else:
            QTest.mouseMove(resolved, QPoint(pos[0], pos[1]))

        self._controller.processEvents()
        return True

    def drag(
        self,
        target: Union[str, QWidget, QQuickItem],
        startPos: Tuple[int, int],
        endPos: Tuple[int, int],
        button: int = Qt.LeftButton,
        modifiers: int = Qt.NoModifier,
        steps: int = 10,
    ) -> bool:
        """
        Perform a drag operation.

        Args:
            target: Object name, QWidget, or QQuickItem
            startPos: (x, y) start position relative to target
            endPos: (x, y) end position relative to target
            button: Mouse button to hold during drag
            modifiers: Keyboard modifiers
            steps: Number of intermediate move steps

        Returns:
            True if drag was performed successfully
        """
        resolved = self._resolveTarget(target)
        if resolved is None:
            log.error(f"Could not find target: {target}")
            return False

        # Get the widget to send events to
        if isinstance(resolved, QQuickItem):
            widget = self._getWidgetForQmlItem(resolved)
            if widget is None:
                return False
            startPoint = self._mapToWidget(
                resolved, QPointF(startPos[0], startPos[1]), widget
            )
            endPoint = self._mapToWidget(
                resolved, QPointF(endPos[0], endPos[1]), widget
            )
        else:
            widget = resolved
            startPoint = QPoint(startPos[0], startPos[1])
            endPoint = QPoint(endPos[0], endPos[1])

        # Press at start position
        QTest.mousePress(widget, button, modifiers, startPoint)
        self._controller.processEvents()

        # Move through intermediate positions
        for i in range(1, steps + 1):
            t = i / steps
            x = int(startPoint.x() + (endPoint.x() - startPoint.x()) * t)
            y = int(startPoint.y() + (endPoint.y() - startPoint.y()) * t)
            QTest.mouseMove(widget, QPoint(x, y))
            self._controller.processEvents(10)

        # Release at end position
        QTest.mouseRelease(widget, button, modifiers, endPoint)
        self._controller.processEvents()
        return True

    def scroll(
        self,
        target: Union[str, QWidget, QQuickItem],
        delta: int,
        orientation: int = Qt.Vertical,
        pos: Optional[Tuple[int, int]] = None,
    ) -> bool:
        """
        Perform a scroll operation.

        Args:
            target: Object name, QWidget, or QQuickItem
            delta: Scroll amount (positive = up/left, negative = down/right)
            orientation: Qt.Vertical or Qt.Horizontal
            pos: Optional position to scroll at

        Returns:
            True if scroll was performed successfully
        """
        resolved = self._resolveTarget(target)
        if resolved is None:
            log.error(f"Could not find target: {target}")
            return False

        from pkdiagram.pyqt import QWheelEvent

        # Determine widget and position
        if isinstance(resolved, QQuickItem):
            widget = self._getWidgetForQmlItem(resolved)
            if widget is None:
                return False
            if pos is None:
                localPos = self._getItemCenter(resolved)
            else:
                localPos = QPointF(pos[0], pos[1])
            eventPos = self._mapToWidget(resolved, localPos, widget)
        else:
            widget = resolved
            if pos is None:
                eventPos = resolved.rect().center()
            else:
                eventPos = QPoint(pos[0], pos[1])

        # Create angle delta based on orientation
        if orientation == Qt.Vertical:
            angleDelta = QPoint(0, delta)
        else:
            angleDelta = QPoint(delta, 0)

        # Create and send wheel event
        event = QWheelEvent(
            QPointF(eventPos),
            widget.mapToGlobal(eventPos),
            QPoint(0, 0),  # pixelDelta
            angleDelta,
            Qt.NoButton,
            Qt.NoModifier,
            Qt.NoScrollPhase,
            False,  # inverted
        )
        QCoreApplication.sendEvent(widget, event)
        self._controller.processEvents()
        return True

    # -------------------------------------------------------------------------
    # Keyboard Events
    # -------------------------------------------------------------------------

    def type(
        self,
        text: str,
        target: Optional[Union[str, QWidget, QQuickItem]] = None,
        modifiers: int = Qt.NoModifier,
    ) -> bool:
        """
        Type text into a target or the currently focused widget.

        Args:
            text: Text to type
            target: Optional target to focus first
            modifiers: Keyboard modifiers to apply

        Returns:
            True if typing was performed successfully
        """
        widget = None

        if target is not None:
            resolved = self._resolveTarget(target)
            if resolved is None:
                log.error(f"Could not find target: {target}")
                return False

            if isinstance(resolved, QQuickItem):
                widget = self._getWidgetForQmlItem(resolved)
                if widget is None:
                    return False
                # Focus the QML item
                resolved.setFocus(True)
            else:
                widget = resolved
                widget.setFocus()
        else:
            widget = QApplication.focusWidget()
            if widget is None:
                log.error("No widget has focus and no target specified")
                return False

        self._controller.processEvents()
        QTest.keyClicks(widget, text, modifiers)
        self._controller.processEvents()
        return True

    def keyPress(
        self,
        key: Union[str, int],
        target: Optional[Union[str, QWidget, QQuickItem]] = None,
        modifiers: int = Qt.NoModifier,
    ) -> bool:
        """
        Press a single key.

        Args:
            key: Key name (e.g., "enter", "escape", "a") or Qt.Key value
            target: Optional target to focus first
            modifiers: Keyboard modifiers

        Returns:
            True if key press was performed successfully
        """
        # Resolve key
        if isinstance(key, str):
            if len(key) == 1:
                # Single character
                qtKey = ord(key.upper())
            else:
                # Named key
                qtKey = KEY_MAP.get(key.lower())
                if qtKey is None:
                    log.error(f"Unknown key name: {key}")
                    return False
        else:
            qtKey = key

        widget = None

        if target is not None:
            resolved = self._resolveTarget(target)
            if resolved is None:
                log.error(f"Could not find target: {target}")
                return False

            if isinstance(resolved, QQuickItem):
                widget = self._getWidgetForQmlItem(resolved)
                if widget is None:
                    return False
                resolved.setFocus(True)
            else:
                widget = resolved
                widget.setFocus()
        else:
            widget = QApplication.focusWidget()
            if widget is None:
                log.error("No widget has focus and no target specified")
                return False

        self._controller.processEvents()
        QTest.keyClick(widget, qtKey, modifiers)
        self._controller.processEvents()
        return True

    def keySequence(
        self,
        keys: list,
        target: Optional[Union[str, QWidget, QQuickItem]] = None,
    ) -> bool:
        """
        Press a sequence of keys.

        Args:
            keys: List of key specifications. Each can be:
                  - A string like "a", "enter", "ctrl+s"
                  - A dict with "key" and optional "modifiers"
            target: Optional target to focus first

        Returns:
            True if all key presses were successful
        """
        for keySpec in keys:
            if isinstance(keySpec, dict):
                key = keySpec.get("key")
                modifiers = keySpec.get("modifiers", Qt.NoModifier)
            elif isinstance(keySpec, str) and "+" in keySpec:
                # Parse modifier+key format like "ctrl+s"
                parts = keySpec.lower().split("+")
                key = parts[-1]
                modifiers = Qt.NoModifier
                for mod in parts[:-1]:
                    if mod == "ctrl":
                        modifiers |= Qt.ControlModifier
                    elif mod == "shift":
                        modifiers |= Qt.ShiftModifier
                    elif mod == "alt":
                        modifiers |= Qt.AltModifier
                    elif mod == "meta":
                        modifiers |= Qt.MetaModifier
            else:
                key = keySpec
                modifiers = Qt.NoModifier

            if not self.keyPress(key, target, modifiers):
                return False
            target = None  # Only set focus on first key

        return True

    # -------------------------------------------------------------------------
    # Focus Management
    # -------------------------------------------------------------------------

    def focus(self, target: Union[str, QWidget, QQuickItem]) -> bool:
        """
        Set focus to a target.

        Args:
            target: Object name, QWidget, or QQuickItem to focus

        Returns:
            True if focus was set successfully
        """
        resolved = self._resolveTarget(target)
        if resolved is None:
            log.error(f"Could not find target: {target}")
            return False

        if isinstance(resolved, QQuickItem):
            resolved.setFocus(True)
            resolved.forceActiveFocus()
        else:
            resolved.setFocus()
            resolved.activateWindow()

        self._controller.processEvents()
        return True

    # -------------------------------------------------------------------------
    # Graphics View Support
    # -------------------------------------------------------------------------

    def clickGraphicsItem(
        self,
        itemOrName: Union[str, QGraphicsItem],
        button: int = Qt.LeftButton,
        modifiers: int = Qt.NoModifier,
    ) -> bool:
        """
        Click on a QGraphicsItem in a QGraphicsView.

        Args:
            itemOrName: The graphics item or scene item name/id
            button: Mouse button
            modifiers: Keyboard modifiers

        Returns:
            True if click was performed successfully
        """
        # Get the view
        dv = self._controller.documentView
        if dv is None:
            log.error("DocumentView not available")
            return False

        view = getattr(dv, "view", None)
        if view is None or not isinstance(view, QGraphicsView):
            log.error("View not available or not a QGraphicsView")
            return False

        # Resolve item
        if isinstance(itemOrName, str):
            scene = self._controller.scene
            if scene is None:
                return False
            item = scene.find(name=itemOrName)
            if item is None:
                log.error(f"Could not find scene item: {itemOrName}")
                return False
        else:
            item = itemOrName

        # Get item center in view coordinates
        scenePosCenter = item.sceneBoundingRect().center()
        viewPos = view.mapFromScene(scenePosCenter)

        QTest.mouseClick(view.viewport(), button, modifiers, viewPos)
        self._controller.processEvents()
        return True

    def doubleClickGraphicsItem(
        self,
        itemOrName: Union[str, QGraphicsItem],
        button: int = Qt.LeftButton,
        modifiers: int = Qt.NoModifier,
    ) -> bool:
        """
        Double-click on a QGraphicsItem.

        Args:
            itemOrName: The graphics item or scene item name/id
            button: Mouse button
            modifiers: Keyboard modifiers

        Returns:
            True if double-click was performed successfully
        """
        dv = self._controller.documentView
        if dv is None:
            return False

        view = getattr(dv, "view", None)
        if view is None:
            return False

        if isinstance(itemOrName, str):
            scene = self._controller.scene
            if scene is None:
                return False
            item = scene.find(name=itemOrName)
            if item is None:
                return False
        else:
            item = itemOrName

        scenePosCenter = item.sceneBoundingRect().center()
        viewPos = view.mapFromScene(scenePosCenter)

        QTest.mouseDClick(view.viewport(), button, modifiers, viewPos)
        self._controller.processEvents()
        return True

    def dragGraphicsItem(
        self,
        itemOrName: Union[str, QGraphicsItem],
        deltaX: int,
        deltaY: int,
        button: int = Qt.LeftButton,
        modifiers: int = Qt.NoModifier,
    ) -> bool:
        """
        Drag a QGraphicsItem by a delta.

        Args:
            itemOrName: The graphics item or scene item name/id
            deltaX: X distance to drag
            deltaY: Y distance to drag
            button: Mouse button
            modifiers: Keyboard modifiers

        Returns:
            True if drag was performed successfully
        """
        dv = self._controller.documentView
        if dv is None:
            return False

        view = getattr(dv, "view", None)
        if view is None:
            return False

        if isinstance(itemOrName, str):
            scene = self._controller.scene
            if scene is None:
                return False
            item = scene.find(name=itemOrName)
            if item is None:
                return False
        else:
            item = itemOrName

        scenePosCenter = item.sceneBoundingRect().center()
        startPos = view.mapFromScene(scenePosCenter)
        endPos = QPoint(startPos.x() + deltaX, startPos.y() + deltaY)

        viewport = view.viewport()
        QTest.mousePress(viewport, button, modifiers, startPos)
        self._controller.processEvents()

        # Move in steps
        steps = 10
        for i in range(1, steps + 1):
            t = i / steps
            x = int(startPos.x() + deltaX * t)
            y = int(startPos.y() + deltaY * t)
            QTest.mouseMove(viewport, QPoint(x, y))
            self._controller.processEvents(10)

        QTest.mouseRelease(viewport, button, modifiers, endPos)
        self._controller.processEvents()
        return True
