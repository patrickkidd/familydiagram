from PyQt5.QtCore import pyqtProperty, pyqtSignal, QObject, QVariant, QUrl
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtQml import *
from PyQt5.QtQuick import *
from PyQt5.QtQuickWidgets import *


class Yours(QObject):

    theirsChanged = pyqtSignal(int)

    def __init__(self, parent, theirs):
        super().__init__(parent)
        self._theirs = theirs

    @pyqtProperty(int, notify=theirsChanged)
    def theirs(self):
        return self._theirs


class Mine(QObject):

    yoursChanged = pyqtSignal(QVariant)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._yours = Yours(self, -1)

    @pyqtProperty(QVariant, notify=yoursChanged)
    def yours(self):
        return self._yours

    def setYours(self, x):
        self._yours = Yours(self, x)
        self.yoursChanged.emit(self._yours)


qmlRegisterType(Mine, "com.tester.stuff", 1, 0, "Mine")

app = QApplication([])
engine = QQmlEngine()
searchView = QQuickWidget()
searchView.setSource(QUrl.fromLocalFile("test_qml.qml"))
mine = searchView.rootObject().property("mine")

mine.setYours(1)
assert searchView.rootObject().property("theirs") == mine.yours.theirs

mine2 = Mine()
mine2.setYours(2)
searchView.rootObject().setProperty("mine", mine2)
assert searchView.rootObject().property("theirs") == mine2.yours.theirs
