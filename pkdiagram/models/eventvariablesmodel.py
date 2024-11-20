from pkdiagram.pyqt import Qt, QAbstractTableModel, QModelIndex, qmlRegisterType
from pkdiagram import util
from pkdiagram.app import commands
from pkdiagram.models import ModelHelper


class EventVariablesModel(QAbstractTableModel, ModelHelper):

    FlagsRole = Qt.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = []
        self.initModelHelper()

    ## Item

    def onItemProperty(self, prop):
        if prop.name() == "eventProperties":
            self._values = []
            for i, entry in prop.get():
                self._entries[entry["attr"]] = entry
            self.modelReset()

    ## Qt Virtuals

    def roleNames(self):
        ret = super().roleNames()
        ret[self.FlagsRole] = b"flags"
        return ret

    def rowCount(self, parent=QModelIndex()):
        if self._scene:
            return len(self._scene.eventProperties())
        else:
            return 0

    def set(self, attr, value):
        super().set(attr, value)
        if attr == "items":
            self.modelReset.emit()

    def columnCount(self, parent=QModelIndex()):
        return 2  # name, value

    def flags(self, index):
        if index.column() == 0:
            return super().flags(index)
        else:
            return super().flags(index) | Qt.ItemIsEditable

    def data(self, index, role=Qt.DisplayRole):
        ret = None
        if role == self.FlagsRole:
            return self.flags(index)
        elif index.column() == 0:
            entry = self._scene.eventProperties()[index.row()]
            ret = entry["name"]
        elif index.column() == 1:
            entry = self._scene.eventProperties()[index.row()]
            ret = util.sameOf(
                self.items, lambda item: item.dynamicProperty(entry["attr"]).get()
            )
        return ret

    def setData(self, index, value, role=Qt.EditRole):
        if index.column() == 1:
            eventProperties = self._scene.eventProperties()
            attr = eventProperties[index.row()]["attr"]
            if attr:
                id = commands.nextId()
                for item in self.items:
                    prop = item.dynamicProperty(attr)
                    if value:
                        prop.set(value, undo=id)
                    else:
                        prop.reset(undo=id)
            else:
                return False
        self.dataChanged.emit(index, index, [role])
        return True


qmlRegisterType(EventVariablesModel, "PK.Models", 1, 0, "EventVariablesModel")
