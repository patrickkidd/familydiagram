from pkdiagram.pyqt import Qt, QStringListModel, qmlRegisterType, pyqtSlot
from pkdiagram import util
from .modelhelper import ModelHelper


class SceneVariablesModel(QStringListModel, ModelHelper):

    NEW_NAME_TMPL = "New Variable %i"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dataChanged.connect(self.onDataChanged)
        self.initModelHelper()

    ## Data

    def refreshAllProperties(self):
        if self._scene:
            self.onSceneProperty(self._scene.prop("eventProperties"))
        else:
            self.setStringList([])

    @util.blocked
    def onDataChanged(self, start, end, roles):
        """Called when variable renamed."""
        oldName = self._scene.eventProperties()[start.row()]["name"]
        newName = self.data(start, Qt.DisplayRole)
        self._scene.renameEventProperty(oldName, newName, undo=True)

    @util.blocked
    def onSceneProperty(self, prop):
        if prop.name() == "eventProperties":
            names = [x["name"] for x in self._scene.eventProperties()]
            self.setStringList(names)

    @pyqtSlot()
    def addRow(self):
        names = [x["name"] for x in self._scene.eventProperties()]
        name = util.newNameOf(names, tmpl=self.NEW_NAME_TMPL, key=lambda x: x)
        self._scene.addEventProperty(name, undo=True)

    @pyqtSlot(int)
    def removeRow(self, row):
        name = self.data(self.index(row, 0), Qt.DisplayRole)
        self._scene.removeEventPropertyByName(name, undo=True)


qmlRegisterType(SceneVariablesModel, "PK.Models", 1, 0, "SceneVariablesModel")
