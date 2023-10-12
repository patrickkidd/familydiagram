import os
from ..pyqt import Qt, QModelIndex, QVariant, pyqtSlot, pyqtSignal, QMessageBox, QApplication, QAbstractListModel
from .. import util
from .qobjecthelper import QObjectHelper


class FileManagerModel(QAbstractListModel, QObjectHelper):

    PathRole = Qt.UserRole + 1
    NameRole = PathRole + 1
    AliasRole = NameRole + 1
    ModifiedRole = NameRole + 1
    PinnedRole = ModifiedRole + 1
    IDRole = PinnedRole + 1
    StatusRole = IDRole + 1
    ShownRole = StatusRole + 1
    OwnerRole = ShownRole + 1
    
    QObjectHelper.registerQtProperties([
        { 'attr': 'sortBy' },
        { 'attr': 'searchText', 'type': str }
    ])

    cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = []
        self._unfilteredEntries = []
        self._sortRole = self.NameRole
        self._sortOrder = Qt.AscendingOrder
        self._searchText = None

    def initFileManagerModel(self):
        sortBy = self.get('sortBy')
        self.sortByRoleName(sortBy)
        self.initQObjectHelper()

    ## Data

    def set(self, attr, x):
        if attr == 'searchText':
            self.beginResetModel()
            self._searchText = x
            self._resort()
            self.refreshProperty('searchText')
            self.endResetModel()
        else:
            super().set(attr, x)

    def reset(self, attr):
        super().reset(attr)
        if attr == 'searchText':
            self.beginResetModel()
            self._searchText = None
            self._resort()
            self.endResetModel()

    def get(self, attr):
        if attr == 'searchText':
            ret = self._searchText
        else:
            ret = super().get(attr)
        return ret

    def rowForFilePath(self, filePath):
        for row, entry in enumerate(self._entries):
            if entry[self.PathRole] == filePath:
                return row
            
    def roleForName(self, name):
        for role, roleName in self.roleNames().items():
            if name == roleName.decode():
                return role

    @pyqtSlot(str)
    def sortByRoleName(self, name):
        self._sortRole = self.roleForName(name)
        self.sort(0)

    def _shouldShowEntry(self, entry):
        searchText = self._searchText.lower() if self._searchText else None
        if not searchText:
            return True
        elif entry[self.NameRole] and searchText in entry[self.NameRole].lower():
            return True
        elif entry[self.OwnerRole] and searchText in entry[self.OwnerRole].lower():
            return True
        else:
            return False

    def entryForRow(self, row):
        return self._entries[row]

    @pyqtSlot()

    def _sorted(self):
        def key(entry):
            if self._sortRole in entry and entry[self._sortRole]:
                return entry[self._sortRole]
            else:
                return 0
        entries = [x for x in self._unfilteredEntries if self._shouldShowEntry(x)]
        entries = sorted(entries, key=key)
        if self._sortOrder == Qt.DescendingOrder:
            entries.reverse()
        return entries
        
    def _resort(self):
        self._entries = self._sorted()

    def addFileEntry(self, path, _batch=False, **kwargs):
        # Create new entry
        newEntry = {}
        newEntry[self.PathRole] = path
        for role in self.roleNames():
            if not role in newEntry:
                newEntry[role] = None
        for k, v in kwargs.items():
            newEntry[self.roleForName(k)] = v
        # Update cached rows
        found = False
        for oldEntry in self._unfilteredEntries:
            if oldEntry[self.PathRole] == newEntry[self.PathRole]:
                found = True
                break
        if found:
            newEntry = oldEntry
        else:
            self._unfilteredEntries.append(newEntry)
        # Update shown rows
        if not self._shouldShowEntry(newEntry):
            return
        if _batch:
            return
        entries = self._sorted()
        newRow = entries.index(newEntry)
        if len(entries) > len(self._entries):
            self.beginInsertRows(QModelIndex(), newRow, newRow)
            self._entries = entries
            self.endInsertRows()
        elif len(entries) < len(self._entries):
            oldRow = None
            for row, oldEntry in enumerate(self._entries):
                if oldEntry[self.PathRole] == newEntry[self.PathRole]:
                    oldRow = row
                    break
            if oldRow != newRow:
                self.rowsAboutToBeMoved.emit(QModelIndex(), oldRow, oldRow, QModelIndex(), newRow)
                self._entries = entries
                self.rowsMoved.emit(QModelIndex(), oldRow, oldRow, QModelIndex(), newRow)
        else:
            pass # exists

    def removeFileEntry(self, path):
        entry = None
        for _entry in self._unfilteredEntries:
            if _entry[self.PathRole] == path:
                entry = _entry
        if not entry:
            return
        row = self._unfilteredEntries.remove(entry)
        row = self._entries.index(entry)
        if row > -1:
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._entries[row]
            self.endRemoveRows()

    def updateFileEntry(self, path, **kwargs):
        entry = None
        for _entry in self._unfilteredEntries:
            if _entry[self.PathRole] == path:
                entry = _entry
                break
        row = self._entries.index(entry) > -1
        for role, roleName in self.roleNames().items():
            name = roleName.decode()
            if name in kwargs and kwargs[name] != entry[role]:
                entry[role] = kwargs[name]
                if row != -1:
                    index = self.index(row, 0)
                    self.dataChanged.emit(index, index, [role])

    def clear(self):
        self.beginResetModel()
        self._unfilteredEntries = []
        self._entries = []
        self.endResetModel()
        self.cleared.emit()

    ## Qt Virtuals
    
    def rowCount(self, index=QModelIndex()):
        return len(self._entries)

    def roleNames(self):
        return {
            self.PathRole: b'path',
            self.NameRole: b'name',
            self.AliasRole: b'alias',
            self.ModifiedRole: b'modified',
            self.PinnedRole: b'pinned',
            self.IDRole: b'id',
            self.StatusRole: b'status',
            self.ShownRole: b'shown',
            self.OwnerRole: b'owner'
        }

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            _role = self.NameRole
        else:
            _role = role
        entry = self._entries[index.row()]
        return entry.get(_role)

    def sort(self, column, order=Qt.AscendingOrder):
        if self._sortRole == self.NameRole:
            order = Qt.AscendingOrder
        elif self._sortRole == self.ModifiedRole:
            order = Qt.DescendingOrder
        self._sortOrder = order
        self.beginResetModel()
        self._resort()
        self.endResetModel()

