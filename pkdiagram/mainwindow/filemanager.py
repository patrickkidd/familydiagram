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

    qmlInitialized = pyqtSignal()
    localFileClicked = pyqtSignal(str)
    serverFileClicked = pyqtSignal(str, Diagram)
    newButtonClicked = pyqtSignal()
    localFilesShownChanged = pyqtSignal(bool)

    def __init__(self, engine, parent=None):
        QWidget.__init__(self, parent)
        self.initQmlWidgetHelper(engine, "qml/FileManager.qml")

    def onInitQml(self):
        super().onInitQml()
        self.qml.rootObject().localFileClicked.connect(self.localFileClicked)
        self.qml.rootObject().serverFileClicked.connect(self.onServerFileClicked)
        self.qml.rootObject().newButtonClicked.connect(self.newButtonClicked)
        self.qml.rootObject().localFilesShownChanged.connect(
            self.onLocalFilesShownChanged
        )
        self.clearSelection()
        Layout = QVBoxLayout(self)
        Layout.setContentsMargins(0, 0, 0, 0)
        Layout.addWidget(self.qml)

    def init(self):
        pass

    def showEvent(self, e):
        super().showEvent(e)
        self.checkInitQml()

    def onLocalFilesShownChanged(self):
        on = self.rootProp("localFilesShown")
        self.localFilesShownChanged.emit(on)

    def onServerFileClicked(self, fpath):
        diagram = self.qmlEngine().serverFileModel.serverDiagramForPath(fpath)
        updatedDiagram = self.qmlEngine().serverFileModel.syncDiagramFromServer(
            diagram.id
        )
        if updatedDiagram:
            self.serverFileClicked.emit(fpath, updatedDiagram)
        else:
            self.serverFileClicked.emit(fpath, diagram)

    def onLocalUUIDUpdated(self, url, uuid):
        self.here("TODO:", url, uuid)

    def onFileClosed(self):
        self.clearSelection()
