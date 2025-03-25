from pkdiagram.pyqt import (
    QWidget,
    QVBoxLayout,
    pyqtSignal,
)
from pkdiagram.widgets import QmlWidgetHelper
from pkdiagram.server_types import Diagram


class FileManager(QWidget, QmlWidgetHelper):

    QmlWidgetHelper.registerQmlMethods(
        [{"name": "clearSelection"}, {"name": "showLocalFiles"}]
    )

    localFileClicked = pyqtSignal(str)
    serverFileClicked = pyqtSignal(str, Diagram)
    newButtonClicked = pyqtSignal()
    localFilesShownChanged = pyqtSignal(bool)

    def __init__(self, engine, parent=None):
        QWidget.__init__(self, parent)
        self.initQmlWidgetHelper(engine, "qml/FileManager.qml")
        self.checkInitQml()

    def onInitQml(self):
        super().onInitQml()
        self.qml.rootObject().localFileClicked.connect(self.localFileClicked)
        self.qml.rootObject().serverFileClicked.connect(self.onServerFileClicked)
        self.qml.rootObject().newButtonClicked.connect(self.newButtonClicked)
        self.qml.rootObject().localFilesShownChanged.connect(
            self.onLocalFilesShownChanged
        )
        self.clearSelection()
        self.serverFileModel = self.rootProp("serverFileModel")
        self.localFileModel = self.rootProp("localFileModel")
        Layout = QVBoxLayout(self)
        Layout.setContentsMargins(0, 0, 0, 0)
        Layout.addWidget(self.qml)

    def init(self):
        self.serverFileModel.init()
        self.serverFileModel.setSession(self.qmlEngine().session)

    def deinit(self):
        self.serverFileModel.deinit()
        QmlWidgetHelper.deinit(self)

    def showEvent(self, e):
        super().showEvent(e)

    def onLocalFilesShownChanged(self):
        on = self.rootProp("localFilesShown")
        self.localFilesShownChanged.emit(on)

    def onServerFileClicked(self, fpath):
        serverFileManagerModel = self.rootProp("serverFileModel")
        diagram = serverFileManagerModel.serverDiagramForPath(fpath)
        updatedDiagram = serverFileManagerModel.syncDiagramFromServer(diagram.id)
        if updatedDiagram:
            self.serverFileClicked.emit(fpath, updatedDiagram)
        else:
            self.serverFileClicked.emit(fpath, diagram)

    def updateModTimes(self):
        self.localFileModel.updateModTimes()

    def onLocalUUIDUpdated(self, url, uuid):
        self.here("TODO:", url, uuid)

    def onFileClosed(self):
        self.clearSelection()
