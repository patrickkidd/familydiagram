import os.path
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
    QEventLoop,
    QCoreApplication,
    QEvent,
    QTimer,
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


import inspect


def get_caller_info():
    """
    Retrieves the filename and line number of the function that called
    the current function.
    """
    # inspect.stack() returns a list of frame info objects.
    # The first element (index 0) is the current frame.
    # The second element (index 1) is the caller's frame.
    caller_frame = inspect.stack()[1]

    # Extract the filename and line number from the caller's frame info.
    filename = caller_frame.filename
    lineno = caller_frame.lineno
    function_name = caller_frame.function

    # return filename, lineno, function_name
    return f"{os.path.basename(filename)}:{lineno}:{function_name}"


def waitForListViewDelegates(
    listView: QQuickItem, numDelegates: int, timeout_ms: int = 5000
):
    """
    Wait for ListView delegates to be created and ready.
    Uses QEventLoop with QTimer for deterministic waiting.
    """
    assert listView.property("enabled"), "ListView must be enabled"
    assert listView.property("visible"), "ListView must be visible"

    # Store original properties
    original_clip = listView.property("clip")
    original_cache_buffer = listView.property("cacheBuffer")

    # Force all delegates to be created
    listView.setProperty("clip", False)
    listView.setProperty("cacheBuffer", 10000)

    def _isDelegateReady(delegate):
        """Check if a delegate is ready for interaction"""
        if delegate is None:
            return False
        if not delegate.property("enabled") or not delegate.property("visible"):
            return False
        width = delegate.property("width")
        height = delegate.property("height")
        return width and width > 0 and height and height > 0

    def _checkDelegates():
        """Check if all expected delegates are ready"""
        model_count = listView.property("count")
        if model_count == 0:
            return [] if numDelegates == 0 else None

        # Force ListView to update by positioning at each index
        for i in range(model_count):
            listView.positionViewAtIndex(i, 0)

        # Force Qt to process all pending events
        QApplication.sendPostedEvents()
        QApplication.processEvents(QEventLoop.AllEvents)
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

        # Use Qt's invokeMethod to force layout completion
        try:
            QMetaObject.invokeMethod(listView, "forceLayout", Qt.DirectConnection)
        except RuntimeError:
            pass  # forceLayout may not exist on all ListView versions

        QApplication.processEvents()

        # Collect ready delegates
        ready_delegates = []
        for i in range(model_count):
            delegate = listView.itemAtIndex(i)
            if _isDelegateReady(delegate):
                ready_delegates.append(delegate)

        # Debug logging
        _log.debug(
            f"waitForListViewDelegates: model_count={model_count}, "
            f"ready_delegates={len(ready_delegates)}, expected={numDelegates}"
        )

        # Return delegates if we have the expected number
        if len(ready_delegates) == numDelegates:
            return ready_delegates
        return None

    # Try immediate check first
    delegates = _checkDelegates()
    if delegates is not None:
        listView.setProperty("clip", original_clip)
        listView.setProperty("cacheBuffer", original_cache_buffer)
        return delegates

    # Set up event loop with timer for polling
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(10)  # Check every 10ms

    delegates_result = []

    def onTimeout():
        nonlocal delegates_result
        result = _checkDelegates()
        if result is not None:
            delegates_result = result
            loop.quit()

    timer.timeout.connect(onTimeout)

    # Set up timeout timer
    timeout_timer = QTimer()
    timeout_timer.setSingleShot(True)
    timeout_timer.timeout.connect(loop.quit)
    timeout_timer.start(timeout_ms)

    # Start polling timer
    timer.start()

    # Run event loop
    try:
        loop.exec()
    finally:
        timer.stop()
        timeout_timer.stop()
        # Restore original properties
        listView.setProperty("clip", original_clip)
        listView.setProperty("cacheBuffer", original_cache_buffer)

    if delegates_result:
        return delegates_result

    # Timeout - provide detailed error
    model_count = listView.property("count")
    actual_delegates = []
    for i in range(model_count):
        delegate = listView.itemAtIndex(i)
        if delegate:
            actual_delegates.append(delegate)

    raise TimeoutError(
        f"Expected {numDelegates} ListView delegates, got {len(actual_delegates)} "
        f"(model count: {model_count})"
    )

    # raise TimeoutError(
    #     f"ListView delegates were not ready within {TIMEOUT_S}s. "
    #     f"Expected {model_count} delegates, got {len(delegates) if 'delegates' in locals() else 0}"
    # )
