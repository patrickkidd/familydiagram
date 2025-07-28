import time
import logging
from typing import Union

from pkdiagram.pyqt import (
    pyqtSignal,
    Q_ARG,
    Q_RETURN_ARG,
    Qt,
    QObject,
    QApplication,
    QQuickWidget,
    QQuickItem,
    QQmlComponent,
    QUrl,
    QRectF,
    QMetaObject,
    QAbstractItemModel,
    QVariant,
    QApplication,
    QPointF,
)
from pkdiagram import util


from PyQt5.QtTest import QTest


_log = logging.getLogger(__name__)


def __quickWidget(item: QQuickItem) -> QQuickWidget:
    # Get the window containing the QQuickItem
    window = item.window()

    if not window:
        return None

    # Iterate through all top-level widgets to find the QQuickWidget
    from PyQt5.QtWidgets import QApplication

    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, QQuickWidget):
            if widget.quickWindow() == window:
                return widget
    return None


def itemString(item: QQuickItem) -> str:
    if item:
        return f'{item.metaObject().className()}["{item.objectName()}"], parent: {item.parent().metaObject().className() if item.parent() else "None"}'
    else:
        return "None"


class QmlHelper:
    def __init__(self, quickWidget: QQuickWidget):
        self.quickWidget = quickWidget

    def focus(self, item: Union[QQuickItem, str]):
        if not self.quickWidget.isActiveWindow():
            # self.here('Setting active window to %s, currently %s' % (self, QApplication.activeWindow()))
            QApplication.setActiveWindow(self.quickWidget)
            _log.debug(f'focus("{item.objectName()}")')
            QTest.qWaitForWindowActive(self, 5000)
            if not self.quickWidget.isActiveWindow():
                raise RuntimeError(
                    "Could not set activeWindow to %s, currently is %s"
                    % (self.quickWidget, QApplication.activeWindow())
                )
            # else:
            #     Debug('Success setting active window to', self)
        assert (
            item.property("enabled") == True
        ), f"The item {item.objectName()} cannot be focused if it is not enabled."
        _log.debug(f'QmlWidgetHelper.focusItem("{item.objectName()}")')

        self.mouseClick(item)

        if not item.hasActiveFocus():
            item.forceActiveFocus()  # in case mouse doesn't work if item out of self.quickWidget
            util.waitUntil(lambda: item.hasActiveFocus())
        if not item.hasFocus():
            item.setFocus(True)
            util.waitUntil(lambda: item.hasFocus())
        if not item.hasActiveFocus():
            msg = "Could not set active focus on `%s`" % item.objectName()
            if not self.quickWidget.isActiveWindow():
                raise RuntimeError(msg + ", window is not active.")
            elif not item.isEnabled():
                raise RuntimeError(msg + ", item is not enabled.")
            elif not item.isVisible():
                raise RuntimeError(msg + ", item is not visible.")
            else:
                if False and util.IS_TEST:
                    pngPath = util.dumpWidget(self)
                else:
                    pngPath = None
                itemRect = QRectF(
                    item.property("x"),
                    item.property("y"),
                    item.property("width"),
                    item.property("height"),
                )
                msg += ", reason unknown (item rect: %s)" % itemRect
                if pngPath:
                    msg += "\n    - Widget dumped to: %s" % pngPath
                msg += "\n    - self.qml                  : %s" % self.qml
                msg += (
                    "\n    - QApplication.focusWidget(): %s"
                    % QApplication.focusWidget()
                )
                msg += "\n    - root item size: %s, %s" % (
                    self.quickWidget.rootObject().property("width"),
                    self.quickWidget.rootObject().property("height"),
                )
                raise RuntimeError(msg)
        return item

    def resetFocus(self, item: QQuickItem):
        _log.debug(f"QmlWidgetHelper.resetFocus({itemString(item)})")
        item.setProperty("focus", False)
        if item.hasActiveFocus():
            self.rootObject().forceActiveFocus()  # TextField?
            if item.hasActiveFocus():
                raise RuntimeError("Could not re-set active focus.")

    def mouseClick(self, item: QQuickItem, button=Qt.MouseButton.LeftButton, pos=None):
        if pos is None:
            rect = item.mapRectToScene(
                QRectF(0, 0, item.property("width"), item.property("height"))
            ).toRect()
            pos = rect.center()

        # validation checks
        if not item.property("visible"):
            _log.warning(f"Cannot click '{item.objectName()}' since it is not visible")
        if not item.property("enabled"):
            _log.warning(f"Cannot click '{item.objectName()}' since it is not enabled")
        _log.debug(
            f"QmlWidgetHelper.mouseClickItem('{itemString(item)}', {button}, {pos}) (rect: {rect})"
        )
        QTest.mouseClick(self.quickWidget, button, Qt.KeyboardModifier.NoModifier, pos)

    def keyClicks(self, item: QQuickItem, s: str, resetFocus=True, returnToFinish=True):
        self.focus(item)
        _log.debug(
            f'QmlWidgetHelper.keyClicks("{item.objectName()}", "{s}", resetFocus={resetFocus}, returnToFinish={returnToFinish})'
        )
        QTest.keyClicks(self.quickWidget, s)
        if returnToFinish:
            _log.debug(
                f'QmlWidgetHelper.keyClicks[returnToFinish]("{item.objectName()}", {s})'
            )
            QTest.keyClick(self.quickWidget, Qt.Key_Return)  # only for TextInput?
        if resetFocus:
            self.resetFocus(item)
        QApplication.processEvents()


import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtQuick import QQuickItem


def waitForListViewDelegates(listView: QQuickItem, numDelegates: int):
    assert listView.property("enabled"), "ListView must be enabled"
    assert listView.property("visible"), "ListView must be visible"

    QApplication.processEvents()
    model_count = listView.property("count")
    _log.info(f"Waiting for ListView to populate (model count: {model_count})")

    if model_count == 0:
        return []

    # Store original properties to restore later
    original_clip = listView.property("clip")
    original_cache_buffer = listView.property("cacheBuffer")

    try:
        # Disable clipping and increase cache buffer to force all delegates to be created
        listView.setProperty("clip", False)
        listView.setProperty("cacheBuffer", 10000)  # Large buffer to keep all items

        QApplication.processEvents()

        # Force ListView to create all delegates by positioning at each index
        for i in range(model_count):
            listView.positionViewAtIndex(i, 0)  # ListView.Contain = 0
            QApplication.processEvents()

        # Collect all instantiated delegates
        delegates = []
        all_delegates_ready = True

        for i in range(model_count):
            delegate = listView.itemAtIndex(i)
            if delegate is None:
                all_delegates_ready = False
                break

            # Check if delegate is clickable (enabled, visible, and has geometry)
            if not delegate.property("enabled"):
                all_delegates_ready = False
                break

            if not delegate.property("visible"):
                all_delegates_ready = False
                break

            # Check if delegate has valid geometry (width > 0, height > 0)
            width = delegate.property("width")
            height = delegate.property("height")
            if not width or width <= 0 or not height or height <= 0:
                all_delegates_ready = False
                break

            delegates.append(delegate)

        if all_delegates_ready and len(delegates) == model_count:
            # Final check: ensure all delegates are actually clickable by testing mouse areas
            all_clickable = True
            for delegate in delegates:
                # Force one more event processing to ensure mouse areas are ready
                QApplication.processEvents()

                # Verify the delegate is still valid and has proper geometry
                if (
                    delegate.property("width") <= 0
                    or delegate.property("height") <= 0
                    or not delegate.property("enabled")
                    or not delegate.property("visible")
                ):
                    all_clickable = False
                    break

            if all_clickable:
                return delegates

    finally:
        # Restore original properties
        listView.setProperty("clip", original_clip)
        listView.setProperty("cacheBuffer", original_cache_buffer)
        QApplication.processEvents()

    raise TimeoutError(
        f"ListView delegates were not ready within {timeout_ms}ms. "
        f"Expected {model_count} delegates, got {len(delegates) if 'delegates' in locals() else 0}"
    )
