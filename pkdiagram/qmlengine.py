from .pyqt import QQmlApplicationEngine, QObject, pyqtSlot
from . import util, commands, qmlutil, qmlvedana


class CommandsWrapper(QObject):

    @pyqtSlot(str)
    def trackView(self, s):
        commands.trackView(s)


class QmlEngine(QQmlApplicationEngine):
    """The global singleton; Manage global objects."""

    def __init__(self, parent=None):
        super().__init__(parent)
        for path in util.QML_IMPORT_PATHS:
            self.addImportPath(path)
        self.commands = CommandsWrapper(self)
        self.util = qmlutil.QmlUtil(self)
        self.vedana = qmlvedana.QmlVedana(self)
        self.rootContext().setContextProperty("util", self.util)
        self.rootContext().setContextProperty("commands", self.commands)
        self.rootContext().setContextProperty("vedana", self.vedana)
        self.util.initColors()
