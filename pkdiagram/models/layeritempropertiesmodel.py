import logging

from pkdiagram.pyqt import Qt, QObject, QModelIndex, QAbstractListModel, qmlRegisterType
from pkdiagram import util, scene, commands
from ..scene import Scene
from .modelhelper import ModelHelper

_log = logging.getLogger(__name__)


class LayerItemLayersModel(QAbstractListModel, ModelHelper):
    """Something for the layers drop-downs."""

    IdRole = Qt.UserRole + 1
    NameRole = IdRole + 1
    ActiveRole = NameRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layers = []
        self._sortedIds = []  # same order
        self._sortedNames = []  # same order
        self.initModelHelper()

    ## QObjectHelper

    def set(self, attr, value):
        if attr == "scene":
            if self._scene:
                self._scene.layerAdded.disconnect(self.onLayerAdded)
                self._scene.layerChanged.disconnect(self.onLayerChanged)
                self._scene.layerRemoved.disconnect(self.onLayerRemoved)
                self._scene.layerOrderChanged.disconnect(self.onLayerOrderChanged)
                self._layers = []
                self._sortedIds = []
                self._sortedNames = []
            if value:
                value.layerAdded.connect(self.onLayerAdded)
                value.layerChanged.connect(self.onLayerChanged)
                value.layerRemoved.connect(self.onLayerRemoved)
                value.layerOrderChanged.connect(self.onLayerOrderChanged)
                self._layers = value.layers()
                self._sort()
            self.modelReset.emit()
        super().set(attr, value)
        if attr == "scene":
            self.modelReset.emit()
        elif attr == "items":
            self.modelReset.emit()

    ## ModelHelper

    def onItemProperty(self, prop):
        pass

    ## Layers

    def onLayerAdded(self, layer):
        newLayers = self._layers + [layer]
        sortedLayers = sorted(newLayers, key=lambda x: x.name() and x.name() or "")
        newRow = sortedLayers.index(layer)
        self.beginInsertRows(QModelIndex(), newRow, newRow)
        self._layers.append(layer)
        self._sort()
        self.endInsertRows()

    def onLayerChanged(self, prop):
        if prop.name() == "name":
            row = self.rowForId(prop.item.id)
            if self._sortedNames[row] != prop.item.name():
                self._sortedNames[row] = prop.item.name()
                self._sort()
                self.modelReset.emit()
                # newRow = self.rowForId(prop.item.id)
                # self.beginMoveRows(QModelIndex(), row, row, QModelIndex(), newRow)
                # index = self.index(newRow, 0)
                # self.dataChanged.emit(index, index)

    def onLayerRemoved(self, layer):
        row = self.rowForId(layer.id)
        self.beginRemoveRows(QModelIndex(), row, row)
        self._layers.remove(layer)
        self._sort()
        self.endRemoveRows()

    def onLayerOrderChanged(self):
        self._sort()

    # @pyqtSlot(int, result=int)
    # def idForRow(self, row):
    #     if row >= 0 and row < len(self._sortedIds):
    #         return self._sortedIds[row]
    #     return -1

    # @pyqtSlot(int, result=int)
    def rowForId(self, id):
        if not id in self._sortedIds:  # could be blank
            return -1
        else:
            return self._sortedIds.index(id)

    def layerForRow(self, row):
        return self._layers[row]

    def _sort(self):
        self._sortedIds = []
        self._sortedNames = []
        self._layers = sorted(self._layers, key=lambda x: x.order())
        for layer in self._layers:
            if layer.name():
                self._sortedIds.append(layer.id)
                self._sortedNames.append(layer.name())

    ## Qt Virtuals

    def roleNames(self):
        return {self.IdRole: b"id", self.NameRole: b"name", self.ActiveRole: b"active"}

    def rowCount(self, parent=QModelIndex()):
        return len(self._sortedNames)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.DisplayRole):
        ret = None
        if role == self.IdRole:
            ret = self._sortedIds[index.row()]
        elif role in (Qt.DisplayRole, self.NameRole):
            ret = self._sortedNames[index.row()]
        elif role == self.ActiveRole:
            layer = self.layerForRow(index.row())
            x = util.sameOf(self._items, lambda item: layer.id in item.layers())
            if x is False:
                ret = Qt.Unchecked
            elif x is True:
                ret = Qt.Checked
            elif x is None:
                ret = Qt.PartiallyChecked
        if ret is None:
            _log.warning(
                f"LayerItemLayersModel.data() is None: index: {index}, role: {role}"
            )
        return ret

    def setData(self, index, value, role):
        success = False
        if role == self.ActiveRole:
            if not isinstance(value, bool) and value == Qt.PartiallyChecked:
                pass  # never set on click right?
            else:
                layer = self.layerForRow(index.row())
                id = commands.nextId()
                for item in self._items:
                    if not value:
                        newLayers = [id for id in item.layers() if id != layer.id]
                        if not item.isPerson and len(newLayers) == 0:
                            success = True  # cancel
                            continue
                    else:
                        if layer.id in item.layers():
                            continue
                        newLayers = [l for l in item.layers()] + [layer.id]
                    if set(newLayers) != set(item.layers()):
                        item.setLayers(newLayers, undo=id)
                        success = True
        if success:
            self.dataChanged.emit(index, index, [role])
        return success


class LayerItemPropertiesModel(QObject, ModelHelper):

    PROPERTIES = scene.Item.adjustedClassProperties(
        scene.LayerItem,
        [
            {"attr": "active", "type": Qt.CheckState},
            {"attr": "parentId", "type": int, "default": -1},
        ],
    )

    ModelHelper.registerQtProperties(PROPERTIES)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initModelHelper()


qmlRegisterType(LayerItemPropertiesModel, "PK.Models", 1, 0, "LayerItemPropertiesModel")
qmlRegisterType(LayerItemLayersModel, "PK.Models", 1, 0, "LayerItemLayersModel")
