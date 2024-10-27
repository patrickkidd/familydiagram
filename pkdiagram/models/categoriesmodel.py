from ..pyqt import (
    Qt,
    QAbstractListModel,
    QModelIndex,
    pyqtSlot,
    qmlRegisterType,
    QVariant,
    QMessageBox,
    QApplication,
)
from .. import util, commands
from ..scene import Scene
from ..objects import Layer, LayerItem, Property, Person, Event
from .modelhelper import ModelHelper


class CategoriesModel(QAbstractListModel, ModelHelper):
    """
    Combines like-named layers and tags into a single list. Setting a category
    active sets the underlying later and tag active exclusively.

    A "category" is an overlay on top of layers and tags in the simplified UI.
    """

    NEW_NAME_TMPL = "Category %i"

    NameRole = Qt.UserRole + 1
    ActiveRole = NameRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._categories = []
        self._reorderingLayers = False
        self.initModelHelper()

    def regenerate(self):
        wasCategories = list(self._categories)
        layers = set(x.name() for x in self.scene.layers())
        tags = set(x.name() for x in self.scene.tags())
        categories = layers.union(tags)
        if categories != wasCategories:
            return
        # added = [x for x in categories if x not in wasCategories]
        # removed = [x for x in wasCategories if x in categories]
        self.modelReset.emit()

    def set(self, attr, value):
        if attr == "scene":
            if self._scene:
                self._scene.layerAdded[Layer].disconnect(self.regenerate)
                self._scene.layerChanged[Property].disconnect(self.regenerate)
                self._scene.layerRemoved[Layer].disconnect(self.regenerate)
                self._scene.diagramReset.disconnect(self.regenerate)
            if value:
                value.layerAdded[Layer].connect(self.regenerate)
                value.layerChanged[Property].connect(self.regenerate)
                value.layerRemoved[Layer].connect(self.regenerate)
                value.diagramReset.connect(self.regenerate)
        super().set(attr, value)

    def onItemProperty(self, prop):
        if prop.name == "scene":
            self.regenerate()

    @pyqtSlot()
    def addRow(self):
        allLayersAndTags = set(self.scene.tags()) | set(self.scene.layers())
        name = util.newNameOf(
            allLayersAndTags, tmpl=self.NEW_NAME_TMPL, key=lambda x: x.name()
        )
        layer = Layer(name=name, storeGeometry=True)
        id = commands.nextId()
        commands.addLayer(self.scene, layer, id=id)
        commands.createTag(name, id=id)
        self._scene.tidyLayerOrder()

    @pyqtSlot(int)
    def duplicateRow(self, row):
        oldCategory = self._categories[row]
        tmpl = oldCategory.name() + " %i"
        allLayersAndTags = set(self.scene.tags()) + set(self.scene.layers())
        name = util.newNameOf(allLayersAndTags, tmpl=tmpl, key=lambda x: x.name())
        layer = Layer(name=name, storeGeometry=True)
        id = commands.nextId()
        commands.addLayer(self.scene, layer, id=id)
        commands.createTag(name, id=id)
        self._scene.tidyLayerOrder()

    @pyqtSlot(int)
    def removeRow(self, row):
        category = self._categories[row]
        layer = self.scene.layers(name=category)[0]
        nItems = len(
            x for x in self.scene.find(types=LayerItem) if x.layers() == [layer.id]
        )
        nEvents = len(x for x in self.scene.find(types=Event) if category in x.tags())
        if nItems:
            btn = QMessageBox.question(
                QApplication.activeWindow(),
                "Are you sure?",
                "Are you sure you want to delete this category? "
                f"This will also delete the {nItems} view items like text callouts and drawings, and remove it from {nEvents}.",
            )
        else:
            btn = QMessageBox.question(
                QApplication.activeWindow(),
                "Are you sure?",
                "Are you sure you want to delete this view?",
            )
        if btn == QMessageBox.No:
            return
        id = commands.nextId()
        commands.removeItems(self.scene, layer, id=id)
        commands.deleteTag(self.scene, id=id)

    def categoryForIndex(self, index):
        if index.row() >= 0 and index.row() < len(self._categories):
            return self._categories[index.row()]

    @pyqtSlot(int, result=QVariant)
    def categoryForRow(self, row):
        return self.categoryForIndex(self.createIndex(row, 0))

    @pyqtSlot(int, int)
    def moveCategory(self, oldRow, newRow):
        self._reorderingLayers = True
        self._categories.insert(newRow, self._categories.pop(oldRow))
        commands.setLayerOrder(self._scene, self._categories)
        self.modelReset.emit()
        self._reorderingLayers = False

    ## Qt Virtuals

    def roleNames(self):
        return {
            self.NameRole: b"name",
            self.ActiveRole: b"active",
        }

    def rowCount(self, index=QModelIndex()):
        return len(self._categories)

    def data(self, index, role=NameRole):
        category = self._categories[index.row()]
        ret = None
        if role == self.NameRole:
            ret = category
        elif role == self.ActiveRole:
            activeCategories = set(self.scene.tags()).union(
                x for x in self.scene.layers() if x.active()
            )
            if category in activeCategories:
                ret = Qt.Checked
            else:
                ret = Qt.Unchecked
        else:
            return super().data(index, role)
        return ret

    def setData(self, index, value, role=NameRole):
        success = True
        layer = self._layers[index.row()]
        if role == self.NameRole:
            success = layer.setName(value, undo=True)
        elif role == self.ActiveRole:
            if value == Qt.Unchecked or not value:
                value = False
            else:
                value = True
            iLayer = self._scene.layers().index(layer)
            id = commands.nextId()
            self._scene.setExclusiveActiveLayerIndex(iLayer, id=id)
            self._scene.searchModel.setTags([layer.name()])
            success = True
        else:
            success = False
        if success:
            self.dataChanged.emit(index, index, [role])
        return success


qmlRegisterType(CategoriesModel, "PK.Models", 1, 0, "CategoriesModel")
