from ..pyqt import (
    Qt,
    QAbstractListModel,
    qmlRegisterUncreatableType,
    QObject,
    QModelIndex,
    QVariant,
    pyqtSlot,
    QMessageBox,
    QApplication,
    qmlRegisterType,
    QMessageBox,
)
from .. import util, objects, commands
from ..objects import Item, Property, Layer
from ..scene import Scene
from .modelhelper import ModelHelper
from pkdiagram.models import SearchModel


class TagsModel(QAbstractListModel, ModelHelper):
    """
    Manages a list of tags from the scene and their active state in either a
    list of items or a searchModel.
    """

    # Mutually exclusive with items
    ModelHelper.registerQtProperties(
        [{"attr": "searchModel", "type": QObject, "default": None}]
    )

    NEW_NAME_TMPL = "New Tag %i"

    IdRole = Qt.UserRole + 1
    NameRole = IdRole + 1
    ActiveRole = NameRole + 1
    FlagsRole = ActiveRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sceneTags = []
        self._settingTags = False
        self._searchModel = None
        self.initModelHelper()

    def get(self, attr):
        if attr == "searchModel":
            return self._searchModel
        else:
            return super().get(attr)

    def set(self, attr, value):
        if attr == "scene":
            # Manage the list of tags from the scene
            super().set(attr, value)
            if self._scene:
                self._sceneTags = sorted(self._scene.tags())
            else:
                self._sceneTags = []
            self.modelReset.emit()
        elif attr == "searchModel":
            if self._items:
                raise ValueError(
                    "Cannot set TagsModel.searchModel when TagsModel.items is set"
                )
            # mutually exclusive with `tags`; just to manage active states
            if self._searchModel:
                self._searchModel.tagsChanged.disconnect(self.onSearchTagsChanged)
            self._searchModel = value
            super().set(attr, value)
            if self._searchModel:
                self._searchModel.tagsChanged.connect(self.onSearchTagsChanged)
            self.modelReset.emit()
        elif attr == "items":
            if self._searchModel:
                raise ValueError(
                    "Cannot set TagsModel.items when TagsModel.searchModel is set"
                )
            # mutually exclusive with `searchModel`; just to manage active states
            super().set(attr, value)
            self.modelReset.emit()
        else:
            super().set(attr, value)

    ## Reactive data

    def onSceneProperty(self, prop):
        """For the list of tags"""
        if prop.name() == "tags":
            self._sceneTags = sorted(self._scene.tags())
            self._blocked = True
            self.modelReset.emit()
            self._blocked = False

    def onItemProperty(self, prop):
        """For the active states"""
        if self._settingTags:
            return
        if prop.name() == "tags":
            startIndex = self.index(0, 0)
            endIndex = self.index(self.rowCount() - 1, 0)
            self.dataChanged.emit(startIndex, endIndex, [self.ActiveRole])

    def onSearchTagsChanged(self):
        """For the active states"""
        startIndex = self.index(0, 0)
        endIndex = self.index(self.rowCount() - 1, 0)
        self.dataChanged.emit(startIndex, endIndex, [self.ActiveRole])

    # Scene tags: Manage the list

    def tagAtRow(self, row):
        if row < 0 or row >= len(self._sceneTags):
            raise KeyError("No tag at row: %s" % row)
        return self._sceneTags[row]

    @pyqtSlot()
    def addTag(self):
        tag = util.newNameOf(self._sceneTags, tmpl=self.NEW_NAME_TMPL, key=lambda x: x)
        commands.createTag(self._scene, tag)

    @pyqtSlot(int)
    def removeTag(self, row):
        tag = self.data(self.index(row, 0))
        items = self._scene.find(tags=tag)
        ok = QMessageBox.Yes
        if items:
            ok = QMessageBox.question(
                QApplication.activeWindow(),
                "Are you sure?",
                "Deleting this tag will also remove it from the %i items that use it. Are you sure you want to do this?"
                % len(items),
            )
        else:
            ok = QMessageBox.question(
                QApplication.activeWindow(),
                "Are you sure?",
                "Are you sure you want to remove this tag?",
            )
        if ok == QMessageBox.Yes:
            self._blocked = True
            commands.deleteTag(self._scene, tag)
            self._blocked = False

    def roleNames(self):
        return {
            self.NameRole: b"name",
            self.ActiveRole: b"active",
            self.IdRole: b"id",
            self.FlagsRole: b"flags",
        }

    @pyqtSlot(result=int)
    def rowCount(self, index=QModelIndex()):
        if not self._scene:
            return 0
        return len(self._sceneTags)

    @pyqtSlot(result=int)
    def columnCount(self, index=QModelIndex()):
        return 1

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsEditable

    def data(self, index, role=NameRole):
        ret = None
        if role == self.NameRole:
            ret = self.tagAtRow(index.row())
        elif role == self.ActiveRole:
            tag = self.tagAtRow(index.row())
            if self._searchModel:
                itemTags = self._searchModel.tags
                if tag in self._searchModel.tags:
                    numChecked = 1
            else:
                numChecked = 0
                for item in self._items:
                    if isinstance(item, SearchModel):
                        itemTags = item.tags
                    else:
                        itemTags = item.tags()
                    if tag in itemTags:
                        numChecked += 1
            if numChecked == 0:
                return Qt.Unchecked
            elif numChecked == len(self._items):
                return Qt.Checked
            else:
                return Qt.PartiallyChecked
        elif role == self.FlagsRole:
            ret = self.flags(index)
        else:
            ret = super().data(index, role)
        return ret

    def setData(self, index, value, role=NameRole):
        success = False
        emit = True
        tag = self.tagAtRow(index.row())
        if role == self.NameRole:
            if value and value not in self._scene.tags():  # must be valid + unique
                commands.renameTag(self._scene, tag, value)
                emit = False
                success = True
            else:  # trigger a cancel
                self.dataChanged.emit(index, index)
        elif role == self.ActiveRole:
            if self._searchModel:
                newTags = list(self._searchModel.tags)
                if value:
                    if not tag in newTags:
                        newTags.append(tag)
                else:
                    if tag in newTags:
                        newTags.remove(tag)
                if newTags != self._searchModel.tags:
                    self._searchModel.tags = newTags
                    success = True
            elif self._items and value != self.data(index, role):
                # Emotions and their events are bound to the same tags.
                # Added here to include prop changes in undo
                todo = set(self._items)
                for item in self._items:
                    if item.isEvent and item.parent and item.parent.isEmotion:
                        todo.add(item.parent)
                    elif item.isEmotion:
                        todo.add(item.startEvent)
                        todo.add(item.endEvent)
                # Do the value set
                id = commands.nextId()
                self._settingTags = True
                for item in todo:
                    if value == Qt.Checked or value:
                        if not tag in item.tags():
                            item.setTag(tag, undo=id)
                            success = True
                    else:
                        if tag in item.tags():
                            item.unsetTag(tag, undo=id)
                            success = True
                self._settingTags = False
        if success and emit:
            self.dataChanged.emit(index, index, [role])
        return success


qmlRegisterType(TagsModel, "PK.Models", 1, 0, "TagsModel")
