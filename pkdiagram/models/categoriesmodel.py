import contextlib

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
    S_CATEGORY_EXISTS_WITH_NAME = "A category with the name '{name}' already exists."
    S_LAYER_EXISTS_WITH_NAME = "A layer with the name '{name}' already exists."
    S_TAG_EXISTS_WITH_NAME = "A tag with the name '{name}' already exists."
    S_CONFIRM_DELETE_CATEGORY = (
        "Are you sure you want to delete this category? "
        "This will also delete the {nItems} view items like text callouts and drawings, and remove it from {nEvents}."
    )
    S_CONFIRM_DELETE_VIEW = "Are you sure you want to delete this view?"

    ActiveRole = Qt.UserRole + 1
    FlagsRole = ActiveRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._categories = []
        self._reorderingLayers = False
        self._updatingData = False
        self.initModelHelper()

    @contextlib.contextmanager
    def updatingData(self):
        was = self._updatingData
        self._updatingData = True

        yield

        self._updatingData = was

    def updateData(self):
        if self._updatingData:
            return

        wasCategories = list(self._categories)
        layers = set(x.name() for x in self.scene.layers())
        tags = set(x for x in self.scene.tags())
        categories = layers.intersection(tags)
        if list(categories) == wasCategories:
            return
        self._categories = sorted(categories)
        # added = [x for x in categories if x not in wasCategories]
        # removed = [x for x in wasCategories if x in categories]
        self.modelReset.emit()

    def set(self, attr, value):
        if attr == "scene":
            if self._scene:
                self._scene.layerAdded[Layer].disconnect(self.updateData)
                self._scene.layerChanged[Property].disconnect(self.updateData)
                self._scene.layerRemoved[Layer].disconnect(self.updateData)
                self._scene.diagramReset.disconnect(self.updateData)
                self._scene.propertyChanged[Property].disconnect(self.onSceneProperty)
            if value:
                value.layerAdded[Layer].connect(self.updateData)
                value.layerChanged[Property].connect(self.updateData)
                value.layerRemoved[Layer].connect(self.updateData)
                value.diagramReset.connect(self.updateData)
                value.propertyChanged[Property].connect(self.onSceneProperty)
        super().set(attr, value)

    def onItemProperty(self, prop):
        if prop.name() == "scene":
            self.updateData()

    def onSceneProperty(self, prop):
        if prop.name() == "tags":
            self.updateData()

    def indexForCategory(self, category) -> int:
        try:
            return self._categories.index(category)
        except ValueError:
            return -1

    @pyqtSlot()
    def addRow(self):
        allLayersAndTags = set(self.scene.tags()) | set(
            x.name() for x in self.scene.layers()
        )
        name = util.newNameOf(allLayersAndTags, tmpl=self.NEW_NAME_TMPL)
        with self.updatingData():
            layer = Layer(name=name, storeGeometry=True)
            with commands.macro("Add Category"):
                commands.addLayer(self._scene, layer)
                commands.createTag(self._scene, name)
            self._scene.tidyLayerOrder()
        self.updateData()

    @pyqtSlot(int)
    def duplicateRow(self, row):
        oldCategory = self._categories[row]
        tmpl = oldCategory.name() + " %i"
        allLayersAndTags = set(self.scene.tags()) + set(self.scene.layers())
        name = util.newNameOf(allLayersAndTags, tmpl=tmpl)
        layer = Layer(name=name, storeGeometry=True)
        with commands.macro("Duplicate Category"):
            commands.addLayer(self.scene, layer)
            commands.createTag(name)
        self._scene.tidyLayerOrder()

    @pyqtSlot(int)
    def removeRow(self, row):
        category = self._categories[row]
        layer = self.scene.layers(name=category)[0]
        nItems = sum(
            1 for x in self.scene.find(types=LayerItem) if x.layers() == [layer.id]
        )
        nEvents = sum(1 for x in self.scene.find(types=Event) if category in x.tags())
        if nItems or nEvents:
            btn = QMessageBox.question(
                QApplication.activeWindow(),
                "Are you sure?",
                self.S_CONFIRM_DELETE_CATEGORY.format(nItems=nItems, nEvents=nEvents),
            )
        else:
            btn = QMessageBox.question(
                QApplication.activeWindow(),
                "Are you sure?",
                self.S_CONFIRM_DELETE_VIEW,
            )
        if btn == QMessageBox.No:
            return
        with commands.macro("Remove Category"):
            commands.removeItems(self.scene, layer)
            commands.deleteTag(self.scene, category)

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
            Qt.ItemDataRole.DisplayRole: b"name",
            self.ActiveRole: b"active",
            self.FlagsRole: b"flags",
        }

    def rowCount(self, index=QModelIndex()):
        return len(self._categories)

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsEditable

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        category = self._categories[index.row()]
        ret = None
        if role == Qt.ItemDataRole.DisplayRole:
            ret = category
        elif role == self.ActiveRole:
            activeCategories = set(self.scene.tags()).union(
                x for x in self.scene.layers() if x.active()
            )
            if category in activeCategories:
                ret = Qt.Checked
            else:
                ret = Qt.Unchecked
        elif role == self.FlagsRole:
            ret = self.flags(index)
        else:
            return super().data(index, role)
        return ret

    def setData(self, index, value, role=Qt.ItemDataRole.DisplayRole):
        success = True
        category = self._categories[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            if value == category:
                success = False
            else:
                if value in self._categories:
                    QMessageBox.warning(
                        QApplication.activeWindow(),
                        "Category already exists",
                        self.S_CATEGORY_EXISTS_WITH_NAME.format(name=value),
                    )
                    success = False
                elif value in [x.name() for x in self._scene.layers()]:
                    QMessageBox.warning(
                        QApplication.activeWindow(),
                        "Layer exists",
                        self.S_LAYER_EXISTS_WITH_NAME.format(name=value),
                    )
                    success = False
                elif value in self._scene.tags():
                    QMessageBox.warning(
                        QApplication.activeWindow(),
                        "Tag exists",
                        self.S_TAG_EXISTS_WITH_NAME.format(name=value),
                    )
                    success = False
                else:
                    with self.updatingData():
                        layer = self.scene.layers(name=category)[0]
                        with commands.macro("Rename Category"):
                            layer.setName(value)
                            commands.renameTag(self._scene, category, value)
                    self.updateData()
                    success = True
            # elif role == self.ActiveRole:
            #     if value == Qt.Unchecked or not value:
            #         value = False
            #     else:
            #         value = True
            #     layer = self._scene.layers()[index.row()]
            #     iLayer = self._scene.layers().index(layer)
            #     with self.updatingData():
            #         with commands.macro("Set Category"):
            #             self._scene.setExclusiveActiveLayerIndex(iLayer)
            #             self._scene.searchModel.setTags([layer.name()])
            #     self.updateData()
            #     success = True
            # else:
            success = False
        if success:
            self.dataChanged.emit(index, index, [role])
        return success


qmlRegisterType(CategoriesModel, "PK.Models", 1, 0, "CategoriesModel")
