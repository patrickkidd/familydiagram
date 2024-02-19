from ..pyqt import (
    Qt,
    QAbstractListModel,
    qmlRegisterUncreatableType,
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


class TagsModel(QAbstractListModel, ModelHelper):
    """Manages a list of tags from the scene and their active state pulled from the items."""

    NEW_NAME_TMPL = "New Tag %i"

    IdRole = Qt.UserRole + 1
    NameRole = IdRole + 1
    ActiveRole = NameRole + 1
    FlagsRole = ActiveRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sceneTags = []
        self._settingTags = False
        self.initModelHelper()

    def set(self, attr, value):
        if attr == "scene":
            if self._scene:
                self._scene.searchModel.tagsChanged.disconnect(self.onSearchTagsChanged)
            super().set(attr, value)
            if self._scene:
                self._sceneTags = sorted(self._scene.tags())
                self._scene.searchModel.tagsChanged.connect(self.onSearchTagsChanged)
            else:
                self._sceneTags = []
            self.modelReset.emit()
        elif attr == "items":
            super().set(attr, value)
            self.modelReset.emit()
        else:
            super().set(attr, value)

    ## Data

    def onItemProperty(self, prop):
        if self._settingTags:
            return
        if prop.name() == "tags":
            startIndex = self.index(0, 0)
            endIndex = self.index(self.rowCount() - 1, 0)
            self.dataChanged.emit(startIndex, endIndex, [self.ActiveRole])

    def onSceneProperty(self, prop):
        if prop.name() == "tags":
            self._sceneTags = sorted(self._scene.tags())
            self._blocked = True
            self.modelReset.emit()
            self._blocked = False

    def onSearchTagsChanged(self):
        startIndex = self.index(0, 0)
        endIndex = self.index(self.rowCount() - 1, 0)
        self.dataChanged.emit(startIndex, endIndex, [self.ActiveRole])

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

    ## Qt Virtuals

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
            numChecked = 0
            for item in self._items:
                if item.isScene:
                    itemTags = item.searchModel.tags
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
            if self._items and self._items[0] == self._scene:
                newTags = list(self._scene.searchModel.tags)
                if value:
                    if not tag in newTags:
                        newTags.append(tag)
                else:
                    if tag in newTags:
                        newTags.remove(tag)
                if newTags != self._scene.searchModel.tags:
                    self._scene.searchModel.tags = newTags
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
