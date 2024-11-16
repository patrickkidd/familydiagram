from sortedcontainers import SortedList

from ..pyqt import (
    Qt,
    qmlRegisterType,
    QAbstractListModel,
    QModelIndex,
)
from .. import util
from pkdiagram.models import ModelHelper


class EmotionalUnitsModel(QAbstractListModel, ModelHelper):
    """
    Automatically generated list of emotional units from list of pair-bonds.
    Represents everyone attached to the reproductive-pair. Can set transient
    active list on the scene.
    """

    NameRole = Qt.UserRole + 1
    ActiveRole = Qt.UserRole + 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._emotionalUnits = SortedList()
        self._activeLayers = []

    def _refresh(self):
        self._emotionalUnits = {}
        for emotionalUnit in self.scene.emotionalUnits():
            itemName = emotionalUnit.itemName()
            if itemName:
                self._emotionalUnits.append(emotionalUnit)
        # stale marriages
        for id in self._activeLayers:
            if id not in self._emotionalUnits:
                self._emotionalUnits.remove(id)
        self.modelReset.emit()

    def set(self, attr, value):
        if attr == "scene":
            if self._scene:
                self._scene.marriageAdded.disconnect(self._refresh)
                self._scene.marriageRemoved.disconnect(self._refresh)
                self._scene.layerChanged.disconnect(self._refresh)
        super().set(attr, value)
        if attr == "scene":
            if self._scene:
                self._scene.marriageAdded.connect(self._refresh)
                self._scene.marriageRemoved.connect(self._refresh)
                self._scene.layerChanged.connect(self._refresh)
            self._refresh()

    ## Qt Virtuals

    def roleNames(self):
        return {self.NameRole: b"name", self.ActiveRole: b"active"}

    def rowCount(self, parent=QModelIndex()):
        return len(self._emotionalUnits)

    def columnCount(self, parent=QModelIndex()):
        return 2

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.row() < 0 or index.row() >= len(self._emotionalUnits):
            return None
        ret = None
        emotionalUnit = self._emotionalUnits[index.row()]
        if role == self.NameRole:
            ret = emotionalUnit.marriage().itemName()
        elif role == self.ActiveRole:
            ret = emotionalUnit.layer() in self._activeLayers
        return ret

    def setData(self, index, value, role=Qt.EditRole):
        if index.row() < 0 or index.row() >= len(self._emotionalUnits):
            return False
        success = False
        emotionalUnit = self._emotionalUnits[index.row()]
        if role == self.ActiveRole:
            self.layer.setActive(value)
            if not emotionalUnit.layer() in self._activeLayers:
                self._activeLayers.append(emotionalUnit.layer())
        if success:
            self.dataChanged.emit(index, index, [role])
        return success


qmlRegisterType(EmotionalUnitsModel, "PK.Models", 1, 0, "EmotionalUnitsModel")
