import json
import logging
from pathlib import Path

from btcopilot.schema import (
    Event as SchemaEvent,
    Cluster,
    ClusterPattern,
    asdict,
    from_dict,
)
from pkdiagram.pyqt import (
    QObject,
    QNetworkReply,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)
from pkdiagram.scene import Scene, Event
from pkdiagram.app import Session

_log = logging.getLogger(__name__)


def _enumValue(val):
    return val.value if hasattr(val, "value") else val


class ClusterModel(QObject):
    changed = pyqtSignal()
    detectingChanged = pyqtSignal()
    clustersDetected = (
        pyqtSignal()
    )  # Emitted after successful detection (for persistence)
    errorOccurred = pyqtSignal(str, arguments=["error"])

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self._session = session
        self._scene: Scene | None = None
        self._diagramId: int | None = None
        self._clusters: list[dict] = []
        self._eventToCluster: dict[int, str] = {}
        self._selectedClusterId: str | None = None
        self._cacheKey: str | None = None
        self._detecting = False
        self._cacheDir: Path | None = None

    @property
    def scene(self) -> Scene | None:
        return self._scene

    @scene.setter
    def scene(self, value: Scene | None):
        if self._scene == value:
            return
        if self._scene:
            self._scene.eventAdded.disconnect(self._onSceneChanged)
            self._scene.eventRemoved.disconnect(self._onSceneChanged)
            self._scene.eventChanged.disconnect(self._onSceneChanged)
        self._scene = value
        if self._scene:
            self._scene.eventAdded.connect(self._onSceneChanged)
            self._scene.eventRemoved.connect(self._onSceneChanged)
            self._scene.eventChanged.connect(self._onSceneChanged)
        self._clusters = []
        self._eventToCluster = {}
        self._cacheKey = None
        self.changed.emit()

    @property
    def diagramId(self) -> int | None:
        return self._diagramId

    @diagramId.setter
    def diagramId(self, value: int | None):
        if self._diagramId == value:
            return
        self._diagramId = value
        self._loadCache()

    def _onSceneChanged(self, *args):
        pass

    def deinit(self):
        self.scene = None

    def _cacheFilePath(self) -> Path | None:
        if not self._cacheDir or not self._diagramId:
            return None
        return self._cacheDir / f"clusters_{self._diagramId}.json"

    def _loadCache(self):
        path = self._cacheFilePath()
        if not path or not path.exists():
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            self._clusters = data.get("clusters", [])
            self._cacheKey = data.get("cacheKey")
            self._buildEventMapping()
            self.changed.emit()
            _log.info(f"Loaded {len(self._clusters)} clusters from cache")
        except Exception as e:
            _log.warning(f"Failed to load cluster cache: {e}")

    def _saveCache(self):
        path = self._cacheFilePath()
        if not path:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(
                    {"clusters": self._clusters, "cacheKey": self._cacheKey},
                    f,
                    indent=2,
                )
            _log.info(f"Saved {len(self._clusters)} clusters to cache")
        except Exception as e:
            _log.warning(f"Failed to save cluster cache: {e}")

    def _buildEventMapping(self):
        self._eventToCluster = {}
        for c in self._clusters:
            for eventId in c.get("eventIds", []):
                self._eventToCluster[eventId] = c.get("id")

    def setCacheDir(self, path: Path):
        self._cacheDir = path
        self._loadCache()

    @pyqtSlot()
    def detect(self):
        if not self._scene or not self._diagramId or not self._session:
            _log.warning(
                "Cannot detect clusters: missing scene, diagramId, or session"
            )
            return

        if self._detecting:
            _log.warning("Cluster detection already in progress")
            return

        events = self._scene.events(onlyDated=True)
        if not events:
            self._clusters = []
            self._eventToCluster = {}
            self._cacheKey = None
            self.changed.emit()
            return

        events_data = []
        for event in sorted(events, key=lambda e: e.dateTime().toMSecsSinceEpoch()):
            kind = event.kind()
            symptom = event.symptom()
            anxiety = event.anxiety()
            relationship = event.relationship()
            functioning = event.functioning()
            notes = event.notes()
            person = event.person()

            event_dict = {
                "id": event.id,
                "kind": kind.value if kind else "shift",
                "dateTime": event.dateTime().toString("yyyy-MM-dd"),
                "description": event.description() or "",
            }
            if symptom:
                event_dict["symptom"] = _enumValue(symptom)
            if anxiety:
                event_dict["anxiety"] = _enumValue(anxiety)
            if relationship:
                event_dict["relationship"] = _enumValue(relationship)
            if functioning:
                event_dict["functioning"] = _enumValue(functioning)
            if notes:
                event_dict["notes"] = notes
            if person:
                event_dict["person"] = person.id
            events_data.append(event_dict)

        self._detecting = True
        self.detectingChanged.emit()

        _log.info(f"Requesting cluster detection for {len(events_data)} events")

        def onSuccess(data):
            self._detecting = False
            self.detectingChanged.emit()
            self._clusters = data.get("clusters", [])
            self._cacheKey = data.get("cacheKey")
            self._buildEventMapping()
            self._saveCache()
            self.changed.emit()
            self.clustersDetected.emit()
            _log.info(f"Received {len(self._clusters)} clusters")

        def onError(reply: QNetworkReply):
            self._detecting = False
            self.detectingChanged.emit()
            error = reply.errorString() if reply else "Unknown error"
            _log.error(f"Cluster detection failed: {error}")
            self.errorOccurred.emit(error)

        reply = self._session.server().nonBlockingRequest(
            "POST",
            f"/personal/diagrams/{self._diagramId}/clusters",
            data={"events": events_data},
            error=lambda: onError(reply),
            success=onSuccess,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            from_root=True,
        )

    @pyqtProperty("QVariantList", notify=changed)
    def clusters(self) -> list[dict]:
        return self._clusters

    @pyqtProperty(int, notify=changed)
    def count(self) -> int:
        return len(self._clusters)

    @pyqtProperty(bool, notify=changed)
    def hasClusters(self) -> bool:
        return len(self._clusters) > 0

    @pyqtProperty(bool, notify=detectingChanged)
    def detecting(self) -> bool:
        return self._detecting

    @pyqtProperty(str, notify=changed)
    def selectedClusterId(self) -> str:
        return self._selectedClusterId or ""

    @selectedClusterId.setter
    def selectedClusterId(self, value: str):
        if self._selectedClusterId == value:
            return
        self._selectedClusterId = value if value else None
        self.changed.emit()

    @pyqtSlot(str)
    def selectCluster(self, clusterId: str):
        self.selectedClusterId = clusterId

    @pyqtSlot(int, result=str)
    def clusterForEvent(self, eventId: int) -> str:
        return self._eventToCluster.get(eventId, "")

    @pyqtSlot(str, result="QVariantMap")
    def clusterById(self, clusterId: str) -> dict:
        for c in self._clusters:
            if c.get("id") == clusterId:
                return c
        return {}

    @pyqtSlot(int, result="QVariantMap")
    def clusterAt(self, index: int) -> dict:
        if 0 <= index < len(self._clusters):
            return self._clusters[index]
        return {}

    @pyqtSlot(str, result="QVariantList")
    def eventsInCluster(self, clusterId: str) -> list[int]:
        for c in self._clusters:
            if c.get("id") == clusterId:
                return c.get("eventIds", [])
        return []

    @property
    def cacheKey(self) -> str | None:
        return self._cacheKey

    def setClustersData(self, clusters: list[dict], cacheKey: str | None):
        self._clusters = clusters
        self._cacheKey = cacheKey
        self._buildEventMapping()
        self.changed.emit()
        _log.info(f"Loaded {len(self._clusters)} clusters from diagram data")
