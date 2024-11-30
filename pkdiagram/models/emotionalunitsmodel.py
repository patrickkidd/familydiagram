import logging

from sortedcontainers import SortedList

from ..pyqt import (
    Qt,
    qmlRegisterType,
    QAbstractListModel,
    QModelIndex,
)
from .. import util
from pkdiagram.objects import Item
from pkdiagram.models import ModelHelper

_log = logging.getLogger(__name__)


class EmotionalUnitsModel(QAbstractListModel, ModelHelper):
    """
    Automatically generated list of emotional units from list of pair-bonds.
    Represents everyone attached to the reproductive-pair. Can set transient
    active list on the scene.
    """

    PROPERTIES = Item.adjustedClassProperties(
        Item,
        [
            {"attr": "noPairBondsWithNames", "type": bool},
        ],
    )

    ModelHelper.registerQtProperties(PROPERTIES)

    NameRole = Qt.ItemDataRole.DisplayRole
    ActiveRole = Qt.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._emotionalUnits = SortedList()
        self._activeLayers = []
        self.initModelHelper()

    def refresh(self):
        self._emotionalUnits = SortedList()
        self._activeLayers = []
        if self._scene:
            for marriage in self._scene.marriages():
                if not marriage.peopleNames():
                    continue
                name = marriage.emotionalUnit().name()
                if name:
                    self._emotionalUnits.add(marriage.emotionalUnit())
                if marriage.emotionalUnit().layer().active():
                    self._activeLayers.append(marriage.emotionalUnit().layer())
        self.modelReset.emit()
        self.refreshProperty("noPairBondsWithNames")

    def set(self, attr, value):
        if attr == "scene":
            if self._scene:
                self._scene.marriageAdded.disconnect(self.onMarriageAddedOrRemoved)
                self._scene.marriageRemoved.disconnect(self.onMarriageAddedOrRemoved)
                self._scene.layerChanged.disconnect(self.onLayerChanged)
                self._scene.propertyChanged.disconnect(self.onSceneProperty)
        super().set(attr, value)
        if attr == "scene":
            if self._scene:
                self._scene.marriageAdded.connect(self.onMarriageAddedOrRemoved)
                self._scene.marriageRemoved.connect(self.onMarriageAddedOrRemoved)
                self._scene.layerChanged.connect(self.onLayerChanged)
                self._scene.propertyChanged.connect(self.onSceneProperty)
            self.refresh()

    def get(self, attr):
        if attr == "noPairBondsWithNames":
            if self._scene:
                return not self._scene.marriages() or not self._emotionalUnits
            else:
                return True
        else:
            return super().get(attr)

    def onMarriageAddedOrRemoved(self):
        self.refresh()

    def onLayerChanged(self, prop):
        if prop.name() != "active":
            self.refresh()

    def onSceneProperty(self, prop):
        if prop.name() in ("hideNames", "showAliases"):
            self.refresh()

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
            ret = emotionalUnit.name()
        elif role == self.ActiveRole:
            if emotionalUnit.layer() in self._activeLayers:
                ret = Qt.CheckState.Checked
            else:
                ret = Qt.CheckState.Unchecked
        return ret

    def setData(self, index, value, role=Qt.EditRole):
        if index.row() < 0 or index.row() >= len(self._emotionalUnits):
            return False
        success = False
        emotionalUnit = self._emotionalUnits[index.row()]
        if role == self.ActiveRole:
            if value in (Qt.CheckState.Checked, Qt.CheckState.PartiallyChecked):
                value = True
            else:
                value = False
            emotionalUnit.layer().setActive(value)
            if value and emotionalUnit.layer() not in self._activeLayers:
                self._activeLayers.append(emotionalUnit.layer())
            elif not value and emotionalUnit.layer() in self._activeLayers:
                self._activeLayers.remove(emotionalUnit.layer())
        if success:
            self.dataChanged.emit(index, index, [role])
        return success


qmlRegisterType(EmotionalUnitsModel, "PK.Models", 1, 0, "EmotionalUnitsModel")
