from pkdiagram.pyqt import (
    Qt,
    QAbstractListModel,
    QModelIndex,
    pyqtSlot,
    qmlRegisterType,
    QVariant,
    QMessageBox,
    QApplication,
)
from pkdiagram import util
from ..scene import Layer, LayerItem, Property
from .modelhelper import ModelHelper


class SceneLayerModel(QAbstractListModel, ModelHelper):

    NEW_NAME_TMPL = "View %i"

    IdRole = Qt.UserRole + 1
    NameRole = IdRole + 1
    DescriptionRole = NameRole + 1
    NotesRole = DescriptionRole + 1
    ActiveRole = NotesRole + 1
    DataRole = ActiveRole + 1
    TagsRole = DataRole + 1
    StoreGeometryRole = TagsRole + 1
    ItemPropertiesRole = StoreGeometryRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layers = []
        self._reorderingLayers = False
        self._isResettingModel = False
        self.initModelHelper()

    def set(self, attr, value):
        if attr == "scene":
            if self._scene:
                self._scene.layerAdded[Layer].disconnect(self.onLayerAdded)
                self._scene.layerChanged[Property].disconnect(self.onLayerChanged)
                self._scene.layerRemoved[Layer].disconnect(self.onLayerRemoved)
                self._scene.diagramReset.disconnect(self.onDiagramReset)
                self._layers = []
            if value:
                value.layerAdded[Layer].connect(self.onLayerAdded)
                value.layerChanged[Property].connect(self.onLayerChanged)
                value.layerRemoved[Layer].connect(self.onLayerRemoved)
                value.diagramReset.connect(self.onDiagramReset)
                self._layers = [x for x in value.layers(includeInternal=False)]
            self._isResettingModel = True
            self.modelReset.emit()
            self._isResettingModel = False
        super().set(attr, value)

    @util.blocked
    def onLayerAdded(self, layer):
        if layer.internal():
            return
        # expects it to already have `order` set
        self.beginInsertRows(QModelIndex(), layer.order(), layer.order())
        self._layers = self.scene.layers(includeInternal=False)
        self.endInsertRows()

    @util.blocked
    def onLayerChanged(self, prop):
        if prop.item.internal():
            return
        role = None
        if prop.name() == "id":
            role = self.IdRole
        elif prop.name() == "active":
            role = self.ActiveRole
        elif prop.name() == "name":
            role = self.NameRole
        elif prop.name() == "description":
            role = self.DescriptionRole
        elif prop.name() == "notes":
            role = self.NotesRole
        elif prop.name() == "storeGeometry":
            role = self.StoreGeometryRole
        elif prop.name() == "order":
            if self._reorderingLayers:
                return
            self._layers = self._scene.layers(includeInternal=False)
            self.modelReset.emit()
        if role is not None:
            row = self._layers.index(prop.item)
            self.dataChanged.emit(self.index(row, 0), self.index(row, 0), [role])

    @util.blocked
    def onLayerRemoved(self, layer):
        if layer.internal():
            return
        row = self._layers.index(layer)
        self.beginRemoveRows(QModelIndex(), row, row)
        self._layers.remove(layer)
        self.endRemoveRows()

    def onDiagramReset(self):
        self.modelReset.emit()

    @pyqtSlot()
    def addRow(self):
        name = util.newNameOf(
            self._layers, tmpl=self.NEW_NAME_TMPL, key=lambda x: x.name()
        )
        layer = Layer(name=name)
        self._scene.addItem(layer, undo=True)

    @pyqtSlot(int)
    def duplicateRow(self, row):
        oldLayer = self._layers[row]
        newLayer = oldLayer.clone(self._scene)
        tmpl = oldLayer.name() + " %i"
        name = util.newNameOf(self._layers, tmpl=tmpl, key=lambda x: x.name())
        newLayer.setName(name)
        self._scene.addItem(newLayer, undo=True)
        self._scene.tidyLayerOrder()

    @pyqtSlot(int)
    def removeRow(self, row):
        layer = self._layers[row]
        nItems = 0
        for item in self.scene.find(types=LayerItem):
            if item.layers() == [layer.id]:
                nItems += 1
        if nItems:
            btn = QMessageBox.question(
                QApplication.activeWindow(),
                "Are you sure?",
                "Are you sure you want to delete this view and the %i items within it?"
                % nItems,
            )
        else:
            btn = QMessageBox.question(
                QApplication.activeWindow(),
                "Are you sure?",
                "Are you sure you want to delete this view?",
            )
        if btn == QMessageBox.No:
            return
        self._scene.removeItem(layer, undo=True)

    def layerForIndex(self, index):
        if index.row() >= 0 and index.row() < len(self._layers):
            return self._layers[index.row()]

    @pyqtSlot(int, result=QVariant)
    def layerForRow(self, row):
        return self.layerForIndex(self.createIndex(row, 0))

    def indexForLayer(self, layer):
        """Just first column"""
        if layer in self._layers:
            row = self._layers.index(layer)
            return self.index(row, 0)

    @pyqtSlot(int, int)
    def moveLayer(self, oldRow, newRow):
        self._reorderingLayers = True
        self._layers.insert(newRow, self._layers.pop(oldRow))
        self._scene.setLayerOrder(self._layers, undo=True)
        self.modelReset.emit()
        self._reorderingLayers = False

    ## Qt Virtuals

    def roleNames(self):
        return {
            self.IdRole: b"id",
            self.NameRole: b"name",
            self.DescriptionRole: b"description",
            self.NotesRole: b"notes",
            self.ActiveRole: b"active",
            self.StoreGeometryRole: b"storeGeometry",
            self.ItemPropertiesRole: b"itemProperties",
        }

    def rowCount(self, index=QModelIndex()):
        return len(self._layers)

    def data(self, index, role=NameRole):
        layer = self._layers[index.row()]
        ret = None
        if role == self.IdRole:
            ret = layer.id
        elif role == self.NameRole:
            ret = layer.name()
        elif role == self.ActiveRole:
            if layer.active():
                ret = Qt.Checked
            else:
                ret = Qt.Unchecked
        elif role == self.DescriptionRole:
            ret = layer.description()
        elif role == self.NotesRole:
            ret = layer.notes()
        elif role == self.StoreGeometryRole:
            ret = layer.storeGeometry()
        elif role == self.ItemPropertiesRole:
            layer = self._layers[index.row()]
            ret = layer.itemProperties()
        else:
            return super().data(index, role)
        return ret

    def setData(self, index, value, role=NameRole):
        if self._isResettingModel:
            return False
        success = True
        layer = self._layers[index.row()]
        if role == self.NameRole:
            success = layer.setName(value, undo=True)
        elif role == self.ActiveRole:
            if value == Qt.Unchecked or not value:
                value = False
            else:
                value = True
            if value != layer.active():
                success = layer.setActive(value, undo=True)
        elif role == self.DescriptionRole:
            if value != layer.description():
                success = layer.setDescription(value, undo=True)
        elif role == self.NotesRole:
            if value != layer.notes():
                success = layer.setNotes(value, undo=True)
        elif role == self.StoreGeometryRole:
            if value != layer.storeGeometry():
                success = layer.setStoreGeometry(value, undo=True)
        elif role == self.ItemPropertiesRole:
            success = layer.setItemProperties(value)
        else:
            success = False
        if success:
            self.dataChanged.emit(index, index, [role])
        return success

    @pyqtSlot(int)
    def setActiveExclusively(self, row):
        for _row in range(self.rowCount()):
            if _row == row:
                self.setData(self.index(_row, 0), True, self.ActiveRole)
            else:
                self.setData(self.index(_row, 0), False, self.ActiveRole)


qmlRegisterType(SceneLayerModel, "PK.Models", 1, 0, "SceneLayerModel")
