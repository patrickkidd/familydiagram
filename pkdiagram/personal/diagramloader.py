import base64
import logging
import pickle

from pkdiagram.app import AppConfig, Session
from pkdiagram.personal.api import JSON_HEADERS
from pkdiagram.personal.models import Discussion
from pkdiagram.pyqt import (
    QInputDialog,
    QMessageBox,
    QNetworkReply,
    QNetworkRequest,
    QObject,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)
from pkdiagram.scene import Scene
from pkdiagram.server_types import Diagram

_log = logging.getLogger(__name__)


class DiagramLoader(QObject):
    """Personal's diagram list and the read side of one diagram: fetches it,
    builds its Scene, and hands both to whoever wired diagramLoaded."""

    diagramLoaded = pyqtSignal(object, object, object)
    diagramChanged = pyqtSignal()
    diagramsChanged = pyqtSignal()
    serverError = pyqtSignal(str)
    serverDown = pyqtSignal()

    def __init__(self, session: Session, appConfig: AppConfig, parent=None):
        super().__init__(parent)
        self.session = session
        self.appConfig = appConfig
        self._diagram: Diagram | None = None
        self._diagrams: list[dict] = []

    def clear(self):
        self._diagrams = []
        self.setDiagram(None)
        self.diagramsChanged.emit()

    def setDiagram(self, diagram: Diagram | None):
        if diagram is self._diagram:
            return
        self._diagram = diagram
        self.diagramChanged.emit()

    def findDiagram(self, diagramId: int) -> Diagram | None:
        """The lookup DiagramSaver resolves through, so a save always writes
        the Diagram object Personal currently has open."""
        return self._diagram if self._diagram and self._diagram.id == diagramId else None

    def onError(self, reply: QNetworkReply):
        if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 0:
            self.serverDown.emit()
        else:
            self.serverError.emit(reply.errorString())

    @pyqtProperty("QVariantList", notify=diagramsChanged)
    def diagrams(self):
        return list(self._diagrams)

    @pyqtProperty("QVariantMap", notify=diagramChanged)
    def diagram(self):
        if self._diagram is not None:
            return self._diagram.__dict__
        return {}

    def refreshDiagrams(self):
        if not self.session.user:
            return

        def onSuccess(data):
            self._diagrams = data.get("diagrams", [])
            self.diagramsChanged.emit()
            _log.info(f"Loaded {len(self._diagrams)} diagrams")

        reply = self.session.server().nonBlockingRequest(
            "GET",
            "/personal/diagrams",
            data={},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers=JSON_HEADERS,
            from_root=True,
        )

    def _saveLastDiagramId(self, diagramId: int):
        self.appConfig.set("lastDiagramId", diagramId)
        if self.appConfig.filePath:
            self.appConfig.write()

    def _readDiagram(self, data: dict, alertOnCorrupt: bool):
        """Adopt a diagram fetched from the server and rebuild its Scene. A
        corrupt blob yields a null scene; the diagram itself still loads."""
        rawData = base64.b64decode(data["data"])
        data["data"] = rawData
        self.setDiagram(Diagram(**data))
        discussions = [Discussion.create(x) for x in data["discussions"]]
        self._saveLastDiagramId(self._diagram.id)
        _log.info(
            f"Loaded personal diagram: {self._diagram.id}, version: {self._diagram.version}"
        )
        scene = Scene()
        try:
            scene.read(pickle.loads(rawData))
        except (
            pickle.UnpicklingError,
            KeyError,
            ValueError,
            TypeError,
            AttributeError,
        ):
            _log.exception(f"Failed to load scene for diagram {self._diagram.id}")
            if alertOnCorrupt:
                QMessageBox.critical(
                    None,
                    "Error",
                    "The diagram file is corrupted and cannot be opened.",
                )
            scene = None
        self.diagramLoaded.emit(self._diagram, scene, discussions)

    def refreshDiagram(self):
        if not self.session.user:
            return

        lastDiagramId = self.appConfig.get("lastDiagramId")
        diagramId = (
            lastDiagramId if lastDiagramId else self.session.user.free_diagram_id
        )

        def onSuccess(data):
            self._readDiagram(data, alertOnCorrupt=False)

        def onError():
            if lastDiagramId and lastDiagramId != self.session.user.free_diagram_id:
                _log.warning(
                    f"Last diagram {lastDiagramId} not found, falling back to free diagram"
                )
                self.appConfig.delete("lastDiagramId")
                if self.appConfig.filePath:
                    self.appConfig.write()
                self.refreshDiagram()
            else:
                self.onError(reply)

        reply = self.session.server().nonBlockingRequest(
            "GET",
            f"/personal/diagrams/{diagramId}",
            data={},
            error=onError,
            success=onSuccess,
            headers=JSON_HEADERS,
            from_root=True,
        )

    @pyqtSlot(int)
    def loadDiagram(self, diagramId: int):
        if not self.session.user:
            return

        def onSuccess(data):
            self._readDiagram(data, alertOnCorrupt=True)

        reply = self.session.server().nonBlockingRequest(
            "GET",
            f"/personal/diagrams/{diagramId}",
            data={},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers=JSON_HEADERS,
            from_root=True,
        )

    @pyqtSlot()
    def createDiagram(self):
        if not self.session.user:
            return

        name, ok = QInputDialog.getText(
            None, "New Diagram", "Enter a name for the new diagram:"
        )

        if not ok or not name.strip():
            return

        def onSuccess(data):
            diagramData = data.get("diagram", {})
            diagramId = diagramData.get("id")
            _log.info(f"Created diagram '{name}' (ID: {diagramId})")
            self.refreshDiagrams()
            if diagramId:
                self.loadDiagram(diagramId)

        reply = self.session.server().nonBlockingRequest(
            "POST",
            "/personal/diagrams/",
            data={"name": name.strip()},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers=JSON_HEADERS,
            from_root=True,
        )
