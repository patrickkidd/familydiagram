import logging
from .pyqt import (
    pyqtSignal,
    pyqtProperty,
    QObject,
    Qt,
    QQuickWidget,
    QUrl,
    QVBoxLayout,
    QEvent,
    QQuickItem,
    QQmlEngine,
)
from . import util
from .widgets import Drawer
from .qmlwidgethelper import QmlWidgetHelper


_log = logging.getLogger(__name__)


class QmlDrawer(Drawer, QmlWidgetHelper):

    QmlWidgetHelper.registerQmlMethods(
        [
            {"name": "onInspect"},
            {"name": "removeSelection"},
            {"name": "setCurrentTab"},
            {"name": "currentTab", "return": True},
        ]
    )

    canInspectChanged = pyqtSignal()
    qmlFocusItemChanged = pyqtSignal(QQuickItem)

    def __init__(
        self,
        engine: QQmlEngine,
        source: str,
        parent=None,
        resizable=True,
        propSheetModel=None,
        objectName=None,
    ):
        super().__init__(parent=parent, resizable=resizable)
        if objectName is not None:
            self.setObjectName(objectName)
        if util.isInstance(parent, "DocumentView"):
            self._documentView = parent
        else:
            self._documentView = None
        self.propSheetModel = propSheetModel
        self.initQmlWidgetHelper(engine, source)
        self.checkInitQml()
        self.layout().addWidget(self.qml)

    def documentView(self):
        return self._documentView

    def onInitQml(self):
        super().onInitQml()
        self.qml.rootObject().done.connect(self.onDone)
        if hasattr(self.qml.rootObject(), "resize"):
            self.qml.rootObject().resize.connect(self.onResize)
        if hasattr(self.qml.rootObject(), "canInspectChanged"):
            self.qml.rootObject().canInspectChanged.connect(self.canInspectChanged)
        if hasattr(self.qml.rootObject(), "isDrawerOpenChanged"):
            self.qml.rootObject().isDrawerOpenChanged.connect(
                self.onIsDrawerOpenChanged
            )
        self.qml.rootObject().setProperty("expanded", self.expanded)
        self.qml.rootObject().window().activeFocusItemChanged.connect(
            self.onActiveFocusItemChanged
        )

    def deinit(self):
        self.qml.rootObject().done.disconnect(self.onDone)
        self.qml.rootObject().window().activeFocusItemChanged.disconnect(
            self.onActiveFocusItemChanged
        )
        if hasattr(self, "qml"):
            model = self.rootModel()
            if model and model.items:
                model.resetItems()
            if model and model.scene:
                model.resetScene()
        Drawer.deinit(self)
        QmlWidgetHelper.deinit(self)

    def rootModel(self):
        return self.rootProp(self.propSheetModel)

    def onActiveFocusItemChanged(self):
        """Allow to avoid prev/next layer shortcut for cmd-left|right"""
        item = self.qml.rootObject().window().activeFocusItem()
        self.qmlFocusItemChanged.emit(item)

    def canClose(self):
        """Virtual"""
        return True

    def show(self, items=[], tab=None, **kwargs):
        if not type(items) == list:
            items = [items]
        self.checkInitQml()
        super().show(**kwargs)
        if self.propSheetModel:
            if not self.isQmlReady():
                raise RuntimeError("QmlWidgetHelper not initialized for", self)
            self.rootProp(self.propSheetModel).items = items
            for item in items:
                item.isInspecting = True
        self.qml.setFocus()
        self.setCurrentTab(tab)

    def hide(self, **kwargs):
        passedCB = kwargs.get("callback")

        def onHidden():
            if self.isQmlReady():
                self.qml.rootObject().forceActiveFocus()
                focusResetter = self.qml.rootObject().property("focusResetter")
                if focusResetter:
                    focusResetter.forceActiveFocus()
                if self.propSheetModel:
                    self.rootProp(self.propSheetModel).reset("items")
                if hasattr(self.qml.rootObject(), "hidden"):
                    self.qml.rootObject().hidden.emit()
            if passedCB:
                passedCB()

        if self.propSheetModel:
            for item in self.rootProp(self.propSheetModel).items:
                item.isInspecting = False
        _kwargs = dict(kwargs)
        _kwargs["callback"] = onHidden
        super().hide(**_kwargs)

    def onDone(self):
        self.hide()

    def onExpandAnimationFinished(self):
        super().onExpandAnimationFinished()
        if hasattr(self, "qml"):
            self.qml.rootObject().setProperty("expanded", self.expanded)

    def setCurrentTabIndex(self, x):
        self.checkInitQml()
        if self.hasItem("stack"):
            self.setItemProp("stack", "currentIndex", x)

    def nextTab(self):
        if self.hasItem("tabBar"):
            x = self.itemProp("tabBar", "currentIndex")
            count = self.itemProp("tabBar", "count")
            currentIndex = min(x + 1, count - 1)
            self.setCurrentTabIndex(currentIndex)

    def prevTab(self):
        if self.hasItem("tabBar"):
            x = self.itemProp("tabBar", "currentIndex")
            count = self.itemProp("tabBar", "count")
            currentIndex = max(x - 1, 0)
            self.setCurrentTabIndex(currentIndex)

    def onIsDrawerOpenChanged(self):
        x = self.qml.rootObject().property("isDrawerOpen")
        self.setLockResizeHandle(x)
