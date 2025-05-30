import logging

from pkdiagram.pyqt import Qt, QVBoxLayout, QSize
from pkdiagram.widgets import Dialog, QmlWidgetHelper

_log = logging.getLogger(__name__)


class AccountDialog(Dialog, QmlWidgetHelper):

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.initQmlWidgetHelper(engine, "qml/AccountDialog.qml")
        self._sizeHint = QSize()

    def onInitQml(self):
        super().onInitQml()
        self.qml.rootObject().done.connect(self.onDone)
        Layout = QVBoxLayout(self)
        Layout.setContentsMargins(0, 0, 0, 0)
        Layout.addWidget(self.qml)
        width = int(self.qml.rootObject().property("width"))
        height = int(self.qml.rootObject().property("height"))
        self._sizeHint = QSize(width, height)
        self.setMaximumSize(self.sizeHint())
        self.resize(self.sizeHint())

    def show(self):
        self.checkInitQml()
        super().show()

    def sizeHint(self):
        return self._sizeHint

    def deinit(self):
        if self.qml:
            self.qml.rootObject().done.disconnect(self.onDone)
            QmlWidgetHelper.deinit(self)

    def canClose(self):
        return bool(self.qmlEngine().session.isLoggedIn())

    def hide(self):
        """Don't allow to close dialog from escape key unless logged in."""
        if not self.canClose():
            return
        super().hide()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Q and (e.modifiers() & Qt.ControlModifier):
            self.quit.emit()
            e.ignore()
        super().keyPressEvent(e)
