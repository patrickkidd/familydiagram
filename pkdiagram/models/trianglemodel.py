import logging

from sortedcontainers import SortedList

from pkdiagram.pyqt import (
    Qt,
    qmlRegisterType,
    QAbstractListModel,
    QModelIndex,
)
from pkdiagram import util
from pkdiagram.scene import Item, Layer
from pkdiagram.models import ModelHelper

_log = logging.getLogger(__name__)


class TriangleModel(QAbstractListModel, ModelHelper):

    PROPERTIES = Item.adjustedClassProperties(
        Item,
        [
            {"attr": "noTriangles", "type": bool},
            {"attr": "anyActive", "type": bool},
        ],
    )

    ModelHelper.registerQtProperties(PROPERTIES)

    NameRole = Qt.ItemDataRole.DisplayRole
    ActiveRole = NameRole + 1
    FlagsRole = ActiveRole + 1
    DateRole = FlagsRole + 1
    DescriptionRole = DateRole + 1
    EventIdRole = DescriptionRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._triangles = SortedList()
        self._activeLayers = []
        self.initModelHelper()

    def refresh(self):
        self._triangles = SortedList()
        self._activeLayers = []
        if self._scene:
            for event in self._scene.events():
                triangle = event.triangle()
                if triangle:
                    self._triangles.add(triangle)
                    if triangle.layer() and triangle.layer().active():
                        self._activeLayers.append(triangle.layer())
        self.modelReset.emit()
        self.refreshProperty("noTriangles")
        self.refreshProperty("anyActive")

    def set(self, attr, value):
        if attr == "scene":
            if self._scene:
                self._scene.eventAdded.disconnect(self.onEventAddedOrRemoved)
                self._scene.eventRemoved.disconnect(self.onEventAddedOrRemoved)
                self._scene.layerChanged.disconnect(self.onLayerChanged)
        super().set(attr, value)
        if attr == "scene":
            if self._scene:
                self._scene.eventAdded.connect(self.onEventAddedOrRemoved)
                self._scene.eventRemoved.connect(self.onEventAddedOrRemoved)
                self._scene.layerChanged.connect(self.onLayerChanged)
            self.refresh()

    def get(self, attr):
        if attr == "noTriangles":
            return len(self._triangles) == 0
        elif attr == "anyActive":
            return bool(self._activeLayers)
        else:
            return super().get(attr)

    def layers(self) -> list[Layer]:
        return [x.layer() for x in self._triangles if x.layer()]

    def onEventAddedOrRemoved(self, event):
        self.refresh()

    @util.iblocked
    def onLayerChanged(self, prop):
        if prop.name() == "active":
            ourLayers = self.layers()
            if prop.get():
                if prop.item in ourLayers and self._scene:
                    for layer in self._scene.layers(includeInternal=False):
                        if layer.active():
                            layer.setActive(False)
                else:
                    for layer in ourLayers:
                        if layer.active():
                            layer.setActive(False)
                            self._activeLayers.remove(layer)
                            row = ourLayers.index(layer)
                            self.dataChanged.emit(
                                self.index(row, 0),
                                self.index(row, 0),
                                [self.ActiveRole],
                            )
            if prop.item in ourLayers:
                row = ourLayers.index(prop.item)
                if prop.get() and prop.item not in self._activeLayers:
                    self._activeLayers.append(prop.item)
                elif not prop.get() and prop.item in self._activeLayers:
                    self._activeLayers.remove(prop.item)
                self.dataChanged.emit(
                    self.index(row, 0),
                    self.index(row, 0),
                    [self.ActiveRole],
                )
                self.refreshProperty("anyActive")
        else:
            self.refresh()

    ## Qt Virtuals

    def roleNames(self):
        return {
            self.NameRole: b"name",
            self.ActiveRole: b"active",
            self.FlagsRole: b"flags",
            self.DateRole: b"date",
            self.DescriptionRole: b"description",
            self.EventIdRole: b"eventId",
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._triangles)

    def columnCount(self, parent=QModelIndex()):
        return 2

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.row() < 0 or index.row() >= len(self._triangles):
            return None
        ret = None
        triangle = self._triangles[index.row()]
        event = triangle.event()
        if role == self.NameRole:
            ret = triangle.name()
        elif role == self.ActiveRole:
            if triangle.layer() in self._activeLayers:
                ret = Qt.CheckState.Checked
            else:
                ret = Qt.CheckState.Unchecked
        elif role == self.FlagsRole:
            ret = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable
        elif role == self.DateRole:
            if event and event.dateTime():
                ret = event.dateTime().toString("yyyy-MM-dd")
            else:
                ret = ""
        elif role == self.DescriptionRole:
            ret = event.description() if event else ""
        elif role == self.EventIdRole:
            ret = event.id if event else None
        return ret

    def setData(self, index, value, role=Qt.EditRole):
        if index.row() < 0 or index.row() >= len(self._triangles):
            return False
        success = False
        triangle = self._triangles[index.row()]
        if role == self.ActiveRole:
            if value in (Qt.CheckState.Checked, Qt.CheckState.PartiallyChecked):
                value = True
            else:
                value = False
            if triangle.layer():
                if value:
                    self._scene.setExclusiveLayerActive(triangle.layer())
                else:
                    triangle.layer().setActive(False)
                if value and triangle.layer() not in self._activeLayers:
                    self._activeLayers.append(triangle.layer())
                elif not value and triangle.layer() in self._activeLayers:
                    self._activeLayers.remove(triangle.layer())
                self.refreshProperty("anyActive")
        if success:
            self.dataChanged.emit(index, index, [role])
        return success


qmlRegisterType(TriangleModel, "PK.Models", 1, 0, "TriangleModel")
