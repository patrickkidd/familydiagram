import logging

from pkdiagram.pyqt import (
    Qt,
    QAbstractListModel,
    QObject,
    QModelIndex,
    pyqtSlot,
    QMessageBox,
    QApplication,
    qmlRegisterType,
    QMessageBox,
)
from pkdiagram import util
from .modelhelper import ModelHelper
from pkdiagram.models import SearchModel


_log = logging.getLogger(__name__)


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
        self._settingItemTags = False
        self._searchModel = None
        self._settingSearchTags = False
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
        if self._settingItemTags:
            return
        if prop.name() == "tags":
            startIndex = self.index(0, 0)
            endIndex = self.index(self.rowCount() - 1, 0)
            self.dataChanged.emit(startIndex, endIndex, [self.ActiveRole])

    def onSearchTagsChanged(self):
        """For the active states"""
        if self._settingSearchTags:
            return
        startIndex = self.index(0, 0)
        endIndex = self.index(self.rowCount() - 1, 0)
        self.dataChanged.emit(startIndex, endIndex, [self.ActiveRole])

    # Scene tags: Manage the list

    def tagAtRow(self, row) -> str:
        if row < 0 or row >= len(self._sceneTags):
            raise KeyError("No tag at row: %s" % row)
        return self._sceneTags[row]

    def rowForTag(self, tag: str) -> int:
        return self._sceneTags.index(tag)

    @pyqtSlot()
    def addTag(self):
        tag = util.newNameOf(self._sceneTags, tmpl=self.NEW_NAME_TMPL, key=lambda x: x)
        self._scene.addTag(tag)

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
            self._scene.removeTag(tag)
            self._blocked = False

    def checkedTags(self) -> list[str]:
        tags = []
        for row in range(self.rowCount()):
            index = self.index(row, 0)
            if index.data(role=self.ActiveRole) == Qt.Checked:
                tag = index.data(role=self.NameRole)
                tags.append(tag)
        return tags

    def uncheckedTags(self) -> list[str]:
        tags = []
        for row in range(self.rowCount()):
            index = self.index(row, 0)
            if index.data(role=self.ActiveRole) == Qt.Unchecked:
                tag = index.data(role=self.NameRole)
                tags.append(tag)
        return tags

    @pyqtSlot()
    def resetToSceneTags(self):
        if self._items:
            self._settingItemTags = True
            for item in self._items:
                item.setTags([])
            self._settingItemTags = False
        self.modelReset.emit()

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
            if self._searchModel:
                itemTags = self._searchModel.tags
                if tag in self._searchModel.tags:
                    numChecked = 1
            else:
                for item in self._items:
                    if isinstance(item, SearchModel):
                        itemTags = item.tags
                    else:
                        itemTags = item.tags()
                    if tag in itemTags:
                        numChecked += 1
            if numChecked == 0:
                return Qt.Unchecked
            elif self._items and numChecked == len(self._items):
                return Qt.Checked
            elif self._searchModel:
                return Qt.Checked
            else:
                return Qt.PartiallyChecked
        elif role == self.FlagsRole:
            ret = self.flags(index)
        else:
            ret = super().data(index, role)
        return ret

    def setData(self, index, value, role=NameRole):
        _log.debug(f"TagsModel.setData: {index}, {value}, {role}")
        success = False
        emit = True
        tag = self.tagAtRow(index.row())
        if role == self.NameRole:
            if value and value not in self._scene.tags():  # must be valid + unique
                self._scene.renameTag(tag, value)
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
                    self._settingSearchTags = True
                    self._searchModel.tags = newTags
                    self._settingSearchTags = False
                    success = True
            elif self._items and value != self.data(index, role):
                # Emotions and their events are bound to the same tags.
                # Added here to include prop changes in undo
                todo = set(self._items)
                # Do the value set
                self._settingItemTags = True
                with self._scene.macro(f"Set tag '{tag}' on items to {value}"):
                    for item in todo:
                        if value == Qt.Checked or value:
                            if tag not in item.tags():
                                item.setTag(tag, undo=True)
                                success = True
                        else:
                            if tag in item.tags():
                                item.unsetTag(tag, undo=True)
                                success = True
                self._settingItemTags = False
            else:
                raise RuntimeError(
                    f"Setting TagsModel.ActiveRole requires either `items` or `searchModel`  to be set."
                )
        if success and emit:
            self.dataChanged.emit(index, index, [role])
        return success


qmlRegisterType(TagsModel, "PK.Models", 1, 0, "TagsModel")
