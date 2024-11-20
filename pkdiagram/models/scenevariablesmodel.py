from pkdiagram.pyqt import Qt, QStringListModel, qmlRegisterType, pyqtSlot
from pkdiagram import util
from pkdiagram.models import ModelHelper
from pkdiagram.app import commands


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
        commands.renameEventProperty(self._scene, oldName, newName)

    @util.blocked
    def onSceneProperty(self, prop):
        if prop.name() == "eventProperties":
            names = [x["name"] for x in self._scene.eventProperties()]
            self.setStringList(names)

    @pyqtSlot()
    def addRow(self):
        names = [x["name"] for x in self._scene.eventProperties()]
        name = util.newNameOf(names, tmpl=self.NEW_NAME_TMPL, key=lambda x: x)
        self._scene.addEventProperty(name)

    @pyqtSlot(int)
    def removeRow(self, row):
        name = self.data(self.index(row, 0), Qt.DisplayRole)
        self._scene.removeEventProperty(name)


qmlRegisterType(SceneVariablesModel, "PK.Models", 1, 0, "SceneVariablesModel")
