import logging

from pkdiagram.pyqt import (
    pyqtSignal,
    Qt,
    QVBoxLayout,
    QSize,
)
from pkdiagram.widgets import Dialog
from pkdiagram.qmlwidgethelper import QmlWidgetHelper

_log = logging.getLogger(__name__)


class SearchDialog(Dialog, QmlWidgetHelper):

    quit = pyqtSignal()

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._sizeHint = QSize()
        self.initQmlWidgetHelper(engine, "qml/SearchForm.qml")
        self.checkInitQml()
        self.qml.rootObject().done.connect(self.onDone)
        Layout = QVBoxLayout(self)
        Layout.setContentsMargins(0, 0, 0, 0)
        Layout.addWidget(self.qml)
        width = int(self.qml.rootObject().property("width"))
        height = int(self.qml.rootObject().property("height"))
        self._sizeHint = QSize(width, height)

        self.setMaximumSize(self.sizeHint())
        self.resize(self.sizeHint())

    def sizeHint(self):
        return self._sizeHint

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Q and (e.modifiers() & Qt.ControlModifier):
            self.quit.emit()
            e.ignore()
        super().keyPressEvent(e)

    def onActiveFocusItemChanged(self):
        super().onActiveFocusItemChanged()
        # item = self.qml.rootObject().window().activeFocusItem()
        # if item:
        #     nextItem = item.nextItemInFocusChain()
        #     while not nextItem.isVisible() or not nextItem.isEnabled():
        #         nextItem = item.nextItemInFocusChain()
        #     nextItemParent = nextItem.parent()
        #     while not nextItemParent.objectName():
        #         nextItemParent = nextItemParent.parent()
        #     itemName = nextItem.objectName()
        #     parentName = nextItemParent.objectName()
        # else:
        #     itemName = ""
        #     parentName = ""
        # _log.info(
        #     f"AddAnythingDialog.onActiveFocusItemChanged: {parentName}.{itemName}"
        # )
        # className = item.metaObject().className() if item else ""
        # _log.info(
        #     f"AddAnythingDialog.onActiveFocusItemChanged: {className}[{item.objectName() if item else ''}]"
        # )
