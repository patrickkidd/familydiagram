import os, shutil
from pkdiagram.pyqt import *
from pkdiagram.util import CUtil
from pkdiagram import util
from .filemanagermodel import FileManagerModel


class LocalFileManagerModel(FileManagerModel):

    loaded = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.isLoaded = False  # for smooth animation aesthetics during app init
        self.prefs = util.prefs()
        CUtil.instance().fileAdded.connect(self.onFileAdded)
        CUtil.instance().fileStatusChanged.connect(self.onFileStatusChanged)
        CUtil.instance().fileRemoved.connect(self.onFileRemoved)
        for url in CUtil.instance().fileList():
            status = CUtil.instance().fileStatusForUrl(url)
            self.onFileAdded(url, status)
        self.initFileManagerModel()
        self.loaded.emit()
        self.isLoaded = True

    def setData(self, index, value, role=Qt.DisplayRole):
        if role == self.NameRole:
            entry = self._entries[index.row()]
            oldFilePath = entry[self.PathRole]
            dirPath = os.path.dirname(oldFilePath)
            newFilePath = os.path.join(dirPath, value) + util.DOT_EXTENSION
            if oldFilePath != newFilePath:
                success = False
                try:
                    os.rename(oldFilePath, newFilePath)
                    success = True
                except:
                    pass
                if success:
                    entry[self.NameRole] = value
                    entry[self.PathRole] = newFilePath
                self.dataChanged.emit(index, index, [role])
                return success
        return False

    def onFileAdded(self, url, status):
        fileInfo = QFileInfo(url.toLocalFile())
        if fileInfo.exists(
            url.toLocalFile()
        ):  # files don't exist when not downloaded yet
            modified = os.stat(url.toLocalFile()).st_mtime
        else:
            modified = None
        self.addFileEntry(
            url.toLocalFile(),
            name=fileInfo.fileName().replace(util.DOT_EXTENSION, ""),
            status=status,
            id="",
            modified=modified,
            shown=True,
        )

    def onFileRemoved(self, url):
        self.removeFileEntry(path=url.toLocalFile())

    def onFileStatusChanged(self, url, status):
        fileInfo = QFileInfo(url.toLocalFile())
        if fileInfo.exists(
            url.toLocalFile()
        ):  # files don't exist when not downloaded yet
            modified = os.stat(url.toLocalFile()).st_mtime
        else:
            modified = None
        self.updateFileEntry(path=url.toLocalFile, status=status, modified=modified)

    def updateModTimes(self):
        docsPath = CUtil.instance().documentsFolderPath()
        for fileInfo in QDir(docsPath).entryInfoList():
            if fileInfo.suffix() == util.EXTENSION:
                row = self.rowForFilePath(fileInfo.filePath())
                if row is not None:
                    modified = os.stat(fileInfo.filePath()).st_mtime
                    self.updateFileEntry(path=fileInfo.filePath(), modified=modified)

    @pyqtSlot(int)
    def deleteFileAtRow(self, row):
        entry = self._entries[row]
        filePath = entry[self.PathRole]
        status = entry[self.StatusRole]
        peoplePath = os.path.join(filePath, "People")
        documentsPath = os.path.join(filePath, "Documents")
        count = 0
        for root, dirs, files in os.walk(filePath):
            for fname in files:
                if fname != "diagram.pickle":
                    count += 1
        if count:
            btn = QMessageBox.question(
                QApplication.activeWindow(),
                "Are you sure?",
                "This diagram contains %i files, are you sure you want to delete it? This will delete it from the hard drive and cannot be undone."
                % count,
            )
        else:
            btn = QMessageBox.question(
                QApplication.activeWindow(),
                "Are you sure?",
                "Are you sure you want to delete this case? This will delete it from the hard drive and cannot be undone.",
            )
        if btn != QMessageBox.Yes:
            return
        self.beginRemoveRows(QModelIndex(), row, row)
        if os.path.isdir(filePath):
            shutil.rmtree(filePath)
        else:  # prolly won't hit it, but what the hell....
            os.remove(filePath)
        del self._entries[row]
        self.endRemoveRows()

    def get(self, attr):
        if attr == "sortBy":
            return self.prefs.value("FileManager/localSortBy", defaultValue="name")
        else:
            return super().get(attr)

    def set(self, attr, x):
        if attr == "sortBy":
            self.sortByRoleName(x)
            self.prefs.setValue("FileManager/localSortBy", x)
        else:
            super().set(attr, x)


qmlRegisterType(LocalFileManagerModel, "PK.Models", 1, 0, "LocalFileManagerModel")
