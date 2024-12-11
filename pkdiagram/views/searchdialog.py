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
