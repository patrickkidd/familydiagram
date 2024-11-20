import os, os.path, pickle, shutil, datetime, logging
from pkdiagram.pyqt import (
    Qt,
    QTimer,
    pyqtSignal,
    pyqtSlot,
    qmlRegisterType,
    QMessageBox,
    QApplication,
    QDateTime,
    QMessageBox,
)
from pkdiagram import CUtil, util
from pkdiagram.models import FileManagerModel
from pkdiagram.app import Diagram, HTTPError


log = logging.getLogger(__name__)


class ServerFileManagerModel(FileManagerModel):
    """
    Provide access to files on the server.
    - Cache files locally for offline use.
    - Encrypts files on disk to prevent user tampering.
    - Can syncronously pull files when they are about be opened.
    - Can be periodically queried to detect and emit changes to files.
        - Overwrites local version with server version if server version is newer
        - Can be used to automatically update the currently opened file.
    - Allows permission-bound provisioning:
        - Upload (Owner)
        - Share diagram with various users (owner, admin)
        - Delete (owner, admin)
    - Allow sort by `owner` field.
    """

    SERVER_SYNC_MS = 1000 * 60 * 30  # 30 minutes
    S_CONFIRM_DELETE_SERVER_FILE = (
        "Are you sure you want to delete this file? This cannot be undone."
    )

    DiagramDataRole = FileManagerModel.OwnerRole + 1

    serverError = pyqtSignal(int)
    updateFinished = pyqtSignal()

    # for testing
    indexGETResponse = pyqtSignal(object)
    diagramGETResponse = pyqtSignal(object)

    def __init__(self, parent=None, dataPath=None, metadataPath=None):
        super().__init__(parent)
        self.initialized = False
        self.diagramCache = {}
        self._indexReplies = []
        self.prefs = util.prefs()
        self.session = None
        self.dataPath = dataPath
        if dataPath is None:
            localRoot = util.appDataDir()
            self.dataPath = os.path.join(localRoot, "Server")
        self.metadataPath = metadataPath
        if self.metadataPath is None:
            self.metadataPath = os.path.join(self.dataPath, "index.pickle")
        self.updateTimer = QTimer(self)
        self.updateTimer.timeout.connect(self.onUpdateTimer)
        self.updateTimer.start(self.SERVER_SYNC_MS)
        self.initFileManagerModel()

    ## Init

    def init(self):
        """Read the index and sync with what files are on disk in case some deleted."""
        if not os.path.isdir(self.dataPath):
            # log.info("Creating folder:", self.dataPath)
            os.makedirs(self.dataPath)
        if not os.path.isfile(self.metadataPath):
            with open(self.metadataPath, "wb") as f:
                bdata = pickle.dumps(self.diagramCache)
                f.write(bdata)
        self.initialized = True
        self.read()

    def deinit(self):
        self.prefs = None
        self.setSession(None)
        super().clear()
        self.write()
        self.initialized = False

    def pendingUrls(self):
        return [reply.request().url().toString() for reply in self._indexReplies]

    def summarizePendingRequests(self):
        return "\n".join(util.summarizeReplyShort(x) for x in self._indexReplies)

    def setSession(self, session):
        if self.session:
            self.session.changed.disconnect(self.update)
        self.session = session
        if self.session:
            self.session.changed.connect(self.update)
            if self.session.isLoggedIn():
                self.update()

    ## Verbs

    def clear(self):
        for fname in os.listdir(self.dataPath):
            if not fname.startswith("."):
                id = fname.replace(util.DOT_EXTENSION, "")
                self._deleteLocalFileByID(id)
        self.diagramCache = {}
        self.write()
        super().clear()

    def reload(self):
        self.clear()
        self.update()

    def read(self):
        try:
            self._do_read()
        except Exception as e:
            import traceback

            print(traceback.format_exc())

    def _do_read(self):
        with open(self.metadataPath, "rb") as f:
            bdata = f.read()
            try:
                index = self._demarshal(pickle.loads(bdata))
            except (
                Exception
            ) as e:  # usually ModuleNotFoundError on _cutil for 1.0.x branch
                log.error(
                    f"Exception caught loading cached server index, resetting...",
                    exc_info=True,
                )
                index = []
        cacheIds = [x.id for x in index]
        # sync with disk first (i.e. manually cleared cache)
        diskIds = []
        for fname in os.listdir(self.dataPath):
            if fname.startswith(".") or util.suffix(fname) != util.EXTENSION:
                continue
            diagramId = int(fname.replace(util.DOT_EXTENSION, "").replace("~", ""))
            diskIds.append(diagramId)
        # delete cache entries without disk file to match
        newIndex = [x for x in index if x.id in diskIds]
        # delete disk file entries without cache entry to match
        for diagram_id in diskIds:
            if not diagram_id in cacheIds:
                self._deleteLocalFileByID(id)
        # load up resulting data
        # log.info("READ:")
        for diagram in newIndex:
            # log.info(f"    Diagram[{diagram.id}].updated_at: {diagram.updated_at}")
            self._addOrUpdateDiagram(diagram, _batch=True)
        self._resort()

    def write(self):
        os.makedirs(self.dataPath, exist_ok=True)
        with open(self.metadataPath, "wb") as f:
            # log.info("self.write():")
            # for diagram_id, diagram in self.diagramCache.items():
            #     log.info(f"    ID: {diagram_id}, updated_at: {diagram.updated_at}")
            data = self._marshal(self.diagramCache)
            bdata = pickle.dumps(data)
            f.write(bdata)

    def onUpdateTimer(self):
        self.update()

    def update(self):
        """Sync local from server retaining whatever hasn't changed."""
        if not self.session.isLoggedIn():
            self.clear()
            return

        def checkIndexRequestsComplete(reply):
            """Called after index but also after get single file."""
            self._indexReplies.remove(reply)
            if not self._indexReplies:
                self.updateFinished.emit()
                self.modelReset.emit()

        def onIndexFinished(reply):
            self.indexGETResponse.emit(reply)
            checkIndexRequestsComplete(reply)

        def onIndexSuccess(data):
            """Sync local from server retaining whatever hasn't changed."""

            def onSingleGETSuccess(data):
                """Called for each file needing updating."""
                # log.debug(f"GET /diagrams/{reply.request().url().toString()} SUCCESS.")
                self._addOrUpdateDiagram(Diagram.create(data))

            def onSingleGETFinished(reply):
                # log.debug(f"GET /diagrams/{reply.request().url().toString()} FINISHED.")
                self.diagramGETResponse.emit(reply)
                checkIndexRequestsComplete(reply)

            if not self.session:
                # Race condition after this deinitialized
                return

            try:
                reply.property("pk_server").checkHTTPReply(reply, quiet=True)
            except HTTPError as e:
                pass
            else:

                # Delete stale files on disk
                newById = {x["id"]: x for x in data}
                for diagram_id, diagram in dict(self.diagramCache).items():
                    if not diagram.id in newById:
                        fpath = self.localPathForID(diagram.id)
                        self._deleteLocalFileByID(diagram.id)
                        del self.diagramCache[diagram.id]
                        self.removeFileEntry(fpath)

                # Pull new entries asyncronously
                for entry in data:
                    if (
                        not self.diagramCache.get(entry["id"])
                        or entry["saved_at"]
                        > self.diagramCache.get(entry["id"]).saved_at()
                    ):
                        url = self._serverDiagramUrl(entry["id"])
                        getReply = self.session.server().nonBlockingRequest(
                            "GET",
                            url,
                            b"",
                            success=onSingleGETSuccess,
                            finished=onSingleGETFinished,
                        )
                        self._indexReplies.append(getReply)

        reply = self.session.server().nonBlockingRequest(
            "GET", "/diagrams", b"", success=onIndexSuccess, finished=onIndexFinished
        )
        self._indexReplies.append(reply)

    def isUpdating(self):
        return len(self._indexReplies) > 0

    def syncDiagramFromServer(self, diagram_id):
        try:
            response = self.session.server().blockingRequest(
                "GET", f"/diagrams/{diagram_id}", statuses=[200, None]
            )
        except HTTPError as e:
            log.error(
                f"Status code {e.status_code} syncing diagram from server {e.url}."
            )
            return
        if response.status_code == None:
            return
        elif response.status_code == 204:
            return  # No Content. Shouldn't get this, but it's ok if we do.
        elif response.status_code == 200:
            bdata = response.body
            if len(bdata) == 0:
                log.info("Zero-length data from server")
                return
            serverDiagram = Diagram(**pickle.loads(response.body))
            self._addOrUpdateDiagram(serverDiagram)
            return serverDiagram

    ## Helpers

    def _serverDiagramUrl(self, id):
        return f"/diagrams/{id}"

    def localPathForID(self, id):
        return os.path.join(self.dataPath, f"{id}{util.DOT_EXTENSION}")

    def pathForDiagram(self, diagram):
        return self.localPathForID(diagram.id)

    def serverDiagramForPath(self, fpath):
        for id, diagram in self.diagramCache.items():
            diagram_fpath = self.localPathForID(id)
            if fpath == diagram_fpath:
                return diagram

    def findDiagram(self, id):
        return self.diagramCache.get(id)

    def diagramForRow(self, row):
        diagram_id = self.index(row, 0).data(self.IDRole)
        return self.findDiagram(diagram_id)

    def rowForDiagramId(self, diagram_id):
        for row in range(self.rowCount()):
            if diagram_id == self.index(row, 0).data(self.IDRole):
                return row

    def findMyFreeDiagram(self):
        if self.session.isLoggedIn():
            return self.findDiagram(self.session.user.free_diagram_id)

    def _addOrUpdateDiagram(self, newDiagram, _batch=False):
        """Add or update a diagram and update the underlying FileManagerModel."""

        ## FileManagerModel
        if newDiagram.isFreeDiagram():
            name = "Free Diagram"
        elif (
            newDiagram.use_real_names and not newDiagram.require_password_for_real_names
        ):
            name = newDiagram.name
        # elif newDiagram.alias:
        #     name = '[%s]' % newDiagram.alias
        elif newDiagram.name:
            name = newDiagram.name
        else:
            name = "<not set>"

        if newDiagram.updated_at:
            modified = newDiagram.updated_at.timestamp()
        else:
            modified = newDiagram.created_at.timestamp()
        self.addFileEntry(
            self.localPathForID(newDiagram.id),
            name=name,
            status=CUtil.FileIsCurrent,
            id=newDiagram.id,
            owner=newDiagram.user.username,
            modified=modified,
            shown=True,
            _batch=_batch,
        )

        ## ServerFileManagerModel

        # Ensure encrypted fd file exists on disk
        packagePath = os.path.join(
            self.dataPath, f"{newDiagram.id}{util.DOT_EXTENSION}"
        )
        picklePath = os.path.join(packagePath, "diagram.pickle")
        os.makedirs(packagePath, exist_ok=True)
        util.writeWithHash(picklePath, newDiagram.data)

        # Update diagram and emit
        existingDiagram = self.diagramCache.get(newDiagram.id)
        if existingDiagram:
            newMTime = QDateTime(
                newDiagram.updated_at
                if newDiagram.updated_at
                else newDiagram.created_at
            )
            existingMTime = QDateTime(
                existingDiagram.updated_at
                if existingDiagram.updated_at
                else existingDiagram.created_at
            )
            if newMTime > existingMTime:
                self.diagramCache[newDiagram.id] = newDiagram
                if not _batch:
                    row = self.rowForDiagramId(newDiagram.id)
                    self.dataChanged.emit(
                        self.index(row, 0), self.index(row, 0), [self.DiagramDataRole]
                    )
        else:
            self.diagramCache[newDiagram.id] = newDiagram

    def _deleteLocalFileByID(self, id):
        fpath = self.localPathForID(id)
        isValid = os.path.isfile(fpath) or os.path.isdir(fpath)
        if os.path.isfile(fpath):
            try:
                os.unlink(fpath)
            except:
                log.info(f"Could not delete file: {fpath}")
                return
            # log.info('Deleted file', fpath)
        elif os.path.isdir(fpath):
            try:
                shutil.rmtree(fpath)
            except:
                log.info(f"Could not delete dir: {fpath}")
            # log.info('Deleted dir', fpath)

    @pyqtSlot(int)
    def deleteFileAtRow(self, row):
        diagram_id = self.data(self.index(row, 0), self.IDRole)
        if diagram_id:
            btn = QMessageBox.question(
                QApplication.activeWindow(),
                "Are you sure?",
                self.S_CONFIRM_DELETE_SERVER_FILE,
            )
            if btn != QMessageBox.Yes:
                return
        url = self._serverDiagramUrl(diagram_id)
        self.session.server().blockingRequest("DELETE", url)
        # entry = self.findDiagram(diagram_id)
        del self.diagramCache[diagram_id]
        fpath = self.localPathForID(diagram_id)
        self.removeFileEntry(fpath)
        shutil.rmtree(fpath)

    def _demarshal(self, data):
        return [Diagram.create(entry) for entry in data]

    def _marshal(self, data):
        return [diagram.dict() for diagram_id, diagram in data.items()]

    ## Model Virtuals

    def get(self, attr):
        if attr == "sortBy":
            ret = self.prefs.value("FileManager/serverSortBy", defaultValue="name")
            if isinstance(ret, bytes):
                ret = ret.decode()
            return ret

    def set(self, attr, x):
        if attr == "sortBy":
            self.sortByRoleName(x)
            self.prefs.setValue("FileManager/serverSortBy", x.encode())
        else:
            super().set(attr, x)

    def data(self, index, role=Qt.DisplayRole):
        if role == self.DiagramDataRole:
            entry = self._entries[index.row()]
            diagram = self.findDiagram(entry[self.IDRole])
            return diagram.data
        else:
            return super().data(index, role)

    def setData(self, index, value, role=Qt.DisplayRole):
        if role == self.ShownRole:
            log.warning(
                f"ServerFileManagerModel.ShownRole is deprecated (value: {value})"
            )
            entry = self._entries[index.row()]
            if value != entry[role]:
                entry[role] = value

                def undoShown(on):
                    entry[role] = on
                    self.dataChanged.emit(index, index, [role])

                self.sendShownOnServer(entry[self.IDRole], value, undoShown)
                self.dataChanged.emit(index, index, [role])
        elif role == self.DiagramDataRole:
            diagram = self.diagramForRow(index.row())
            diagram.updated_at = datetime.datetime.utcnow()
            diagram.updated_at.isoformat()
            diagram.data = value
            self.session.server().blockingRequest(
                "PUT",
                f"/diagrams/{diagram.id}",
                bdata=pickle.dumps(
                    {"data": diagram.data, "updated_at": diagram.updated_at}
                ),
                statuses=[200],
            )
            log.info(
                f"Pushed diagram {diagram.id} to server, bytes: {len(diagram.data)}, updated_at: {diagram.updated_at}"
            )
            self.dataChanged.emit(index, index, [role])
        elif role == self.ModifiedRole:
            diagram = self.diagramForRow(index.row())
            self.diagram.updated_at = value
            self.dataChanged.emit(index, index, [role])
        return False

    def sendShownOnServer(self, id, on, callback):
        # TODO: Make syncronous
        def onFinished(reply):
            try:
                reply.property("pk_server").checkHTTPReply(reply)
            except HTTPError as e:
                reply.property("pk_callback")(reply.was)
                return
            entry = self.findDiagram(reply.propery("pk_id"))
            entry["shown"] = reply.property("pk_shown")
            bdata = encryption.decryptBytes(reply.readAll())
            data = pickle.loads(bdata)
            reply.callback(data["shown"])
            self.updateFileEntry(self.localPathForID(data["id"]), shown=data["shown"])

        url = self._serverDiagramUrl(id) + "?shown=" + str(on)
        bdata = pickle.dumps({})
        reply = self.session.server().nonBlockingRequest(
            "PATCH", url, bdata, finished=onFinished
        )
        reply.setProperty("pk_id", id)
        reply.setProperty("pk_shown", on)
        reply.setProperty("pk_callback", callback)
        reply.setProperty("pk_was", self.findDiagram(id)["shown"])


qmlRegisterType(ServerFileManagerModel, "PK.Models", 1, 0, "ServerFileManagerModel")
