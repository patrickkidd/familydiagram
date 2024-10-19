import logging


from ..pyqt import (
    Qt,
    pyqtSlot,
    QAbstractListModel,
    QModelIndex,
    QVariant,
    QObject,
    qmlRegisterType,
    QQmlEngine,
)
from .. import objects, scene, util
from .modelhelper import ModelHelper

_log = logging.getLogger(__name__)


class PeopleModel(QAbstractListModel, ModelHelper):
    """Something for the people drop-downs."""

    ModelHelper.registerQtProperties([{"attr": "autocompleteNames", "type": list}])

    IdRole = Qt.UserRole + 1
    NameRole = IdRole + 1
    PersonIdRole = NameRole + 1
    FullNameOrAlias = PersonIdRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._people = []
        self._sortedIds = []  # same order
        self._sortedNames = []  # same order
        self.initModelHelper()

    ## Data

    def _sort(self):
        self._sortedIds = []
        self._sortedNames = []
        for person in sorted(self._people, key=lambda x: x.fullNameOrAlias()):
            if person.fullNameOrAlias():
                self._sortedIds.append(person.id)
                self._sortedNames.append(person.fullNameOrAlias())

    def updateData(self):
        if self._scene:
            self._people = self._scene.people()
        else:
            self._people = []
            self._sortedIds = []
            self._sortedNames = []
        self._sort()
        self.modelReset.emit()

    def onSceneProperty(self, prop):
        if prop.name() == "showAliases":
            self.updateData()
        super().onSceneProperty(prop)

    def cleanupBatchAddingRemovingItems(self, added, removed):
        """Just reset the model."""
        self.updateData()

    def onPersonAdded(self, person):
        if self._scene.isBatchAddingRemovingItems():
            return
        # withNames = [p for p in (self._people + [person]) if p.fullNameOrAlias()]
        # sortedPeople = sorted(withNames, key=lambda x: x.fullNameOrAlias())
        # newRow = sortedPeople.index(person)
        if not person in self._people:
            self._people.append(person)
        self._sort()
        newRow = self.rowForId(person.id)
        if newRow >= 0:
            self.beginInsertRows(QModelIndex(), newRow, newRow)
            self.endInsertRows()

    def personNewRow(self, people, person):
        withNames = [p for p in (self._people) if p.fullNameOrAlias()]
        sortedPeople = sorted(withNames, key=lambda x: x.fullNameOrAlias())

    def onPersonChanged(self, prop):
        if self._scene.isBatchAddingRemovingItems():
            return
        person = prop.item
        if prop.name() in ("name", "lastName", "alias"):
            oldRow = self.rowForId(person.id)
            if oldRow == -1 and prop.get():  # null name set to non-null
                self.onPersonAdded(prop.item)
                # newRow = self.rowForId(person.id)
                # self.beginInsertRows(QModelIndex(), newRow, newRow)
                # self.endInsertRows()
            elif oldRow > -1 and not prop.get():  # non-null name set to null
                self.beginRemoveRows(QModelIndex(), oldRow, oldRow)
                self._sort()
                self.endRemoveRows()
            elif (
                oldRow == -1 and not prop.get()
            ):  # non-null name still set to null (e.g. when called recursively)
                pass
            elif self._sortedNames[oldRow] != person.fullNameOrAlias():  # Re-ordered
                self._sort()
                newRow = self.rowForId(person.id)
                if newRow != oldRow:
                    if newRow >= oldRow:
                        # I really don't understand the documentation for beginMoveRows when sourceParent and destinationParent are the same
                        # https://forum.qt.io/topic/95879/endmoverows-in-model-crashes-my-app/6
                        newRow += 1
                    self.beginMoveRows(
                        QModelIndex(), oldRow, oldRow, QModelIndex(), newRow
                    )
                    self.endMoveRows()
                    index = self.index(newRow, 0)
                    self.dataChanged.emit(index, index)

    def onPersonRemoved(self, person):
        if self._scene.isBatchAddingRemovingItems():
            return
        row = self.rowForId(person.id)
        if row > -1:
            self.beginRemoveRows(QModelIndex(), row, row)
            self._people.remove(person)
            self._sort()
            self.endRemoveRows()

    ## Properties

    def get(self, attr):
        if attr == "autoCompleteNames":
            return list(self._sortedNames)
        else:
            return super().get(attr)

    def set(self, attr, value):
        if attr == "scene":
            if self._scene:
                self.scene.personAdded.disconnect(self.onPersonAdded)
                self.scene.personChanged.disconnect(self.onPersonChanged)
                self.scene.personRemoved.disconnect(self.onPersonRemoved)
        super().set(attr, value)
        if attr == "scene":
            if value:
                value.personAdded.connect(self.onPersonAdded)
                value.personChanged.connect(self.onPersonChanged)
                value.personRemoved.connect(self.onPersonRemoved)
            self.updateData()

    @pyqtSlot(int, result=int)
    def idForRow(self, row):
        if row >= 0 and row < len(self._sortedIds):
            return self._sortedIds[row]
        return -1

    @pyqtSlot(int, result=int)
    def rowForId(self, id):
        ret = None
        if not id in self._sortedIds:  # could be blank
            ret = -1
        else:
            ret = self._sortedIds.index(id)
        return ret

    @pyqtSlot(int, result=QObject)
    def personForRow(self, row):
        if row < 0 or row >= len(self._sortedIds):
            return None
        personId = self._sortedIds[row]
        ret = next(x for x in self._people if x.id == personId)
        QQmlEngine.setObjectOwnership(ret, QQmlEngine.CppOwnership)
        return ret

    ## Qt Virtuals

    def roleNames(self):
        return {
            self.IdRole: b"id",
            self.NameRole: b"name",
            self.PersonIdRole: b"personId",
            self.FullNameOrAlias: b"fullNameOrAlias",
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._sortedNames)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.DisplayRole):
        ret = None
        if role in (Qt.DisplayRole, self.NameRole):
            ret = self._sortedNames[index.row()]
        elif role == self.IdRole:
            ret = self._sortedIds[index.row()]
        elif role == self.PersonIdRole:
            ret = self._sortedIds[index.row()]
        elif role == self.FullNameOrAlias:
            personId = self._sortedIds[index.row()]
            ret = next(x for x in self._people if x.id == personId).fullNameOrAlias()
        return ret


qmlRegisterType(PeopleModel, "PK.Models", 1, 0, "PeopleModel")
