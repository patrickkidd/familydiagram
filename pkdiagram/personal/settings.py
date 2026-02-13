from pkdiagram.pyqt import QObject, pyqtSlot, pyqtSignal


class Settings(QObject):

    valueChanged = pyqtSignal(str, arguments=["key"])

    def __init__(self, qsettings, parent=None):
        super().__init__(parent)
        self._qsettings = qsettings

    @pyqtSlot(str, result="QVariant")
    @pyqtSlot(str, "QVariant", result="QVariant")
    def value(self, key, default=None):
        return self._qsettings.value(key, defaultValue=default)

    @pyqtSlot(str, "QVariant")
    def setValue(self, key, value):
        self._qsettings.setValue(key, value)
        self.valueChanged.emit(key)
