from .pyqt import QVBoxLayout, QSize
from . import util
from .widgets import Dialog
from .qmlwidgethelper import QmlWidgetHelper


class AccountDialog(Dialog, QmlWidgetHelper):

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self._sizeHint = QSize()
        Layout = QVBoxLayout(self)
        Layout.setContentsMargins(0, 0, 0, 0)
        self.initQmlWidgetHelper('qml/AccountDialog.qml', session=session)

    def init(self):
        self.checkInitQml()
        self.qml.rootObject().done.connect(self.onDone)
        width = int(self.qml.rootObject().property('width'))
        height = int(self.qml.rootObject().property('height'))
        self._sizeHint = QSize(width, height)
        self.setMaximumSize(self.sizeHint())
        self.resize(self.sizeHint())
        super().init()

    def sizeHint(self):
        return self._sizeHint

    def deinit(self):
        self.qml.rootObject().done.disconnect(self.onDone)

    def canClose(self):
        return bool(self.session.isLoggedIn())

    def onDone(self):
        self.hide()

    def hide(self):
        """ Don't allow to close dialog from escape key unless logged in. """
        if not self.canClose():
            return
        super().hide()

        
