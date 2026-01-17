import json
import logging
from pathlib import Path

from btcopilot.schema import (
    Event as SchemaEvent,
    Vignette,
    VignettePattern,
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


class VignetteModel(QObject):
    changed = pyqtSignal()
    detectingChanged = pyqtSignal()
    vignettesDetected = (
        pyqtSignal()
    )  # Emitted after successful detection (for persistence)
    errorOccurred = pyqtSignal(str, arguments=["error"])

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self._session = session
        self._scene: Scene | None = None
        self._diagramId: int | None = None
        self._vignettes: list[dict] = []
        self._eventToVignette: dict[int, str] = {}
        self._selectedVignetteId: str | None = None
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
        self._vignettes = []
        self._eventToVignette = {}
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
        return self._cacheDir / f"vignettes_{self._diagramId}.json"

    def _loadCache(self):
        path = self._cacheFilePath()
        if not path or not path.exists():
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            self._vignettes = data.get("vignettes", [])
            self._cacheKey = data.get("cacheKey")
            self._buildEventMapping()
            self.changed.emit()
            _log.info(f"Loaded {len(self._vignettes)} vignettes from cache")
        except Exception as e:
            _log.warning(f"Failed to load vignette cache: {e}")

    def _saveCache(self):
        path = self._cacheFilePath()
        if not path:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(
                    {"vignettes": self._vignettes, "cacheKey": self._cacheKey},
                    f,
                    indent=2,
                )
            _log.info(f"Saved {len(self._vignettes)} vignettes to cache")
        except Exception as e:
            _log.warning(f"Failed to save vignette cache: {e}")

    def _buildEventMapping(self):
        self._eventToVignette = {}
        for v in self._vignettes:
            for eventId in v.get("eventIds", []):
                self._eventToVignette[eventId] = v.get("id")

    def setCacheDir(self, path: Path):
        self._cacheDir = path
        self._loadCache()

    @pyqtSlot()
    def detect(self):
        if not self._scene or not self._diagramId or not self._session:
            _log.warning(
                "Cannot detect vignettes: missing scene, diagramId, or session"
            )
            return

        if self._detecting:
            _log.warning("Vignette detection already in progress")
            return

        events = self._scene.events(onlyDated=True)
        if not events:
            self._vignettes = []
            self._eventToVignette = {}
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

        _log.info(f"Requesting vignette detection for {len(events_data)} events")

        def onSuccess(data):
            self._detecting = False
            self.detectingChanged.emit()
            self._vignettes = data.get("vignettes", [])
            self._cacheKey = data.get("cacheKey")
            self._buildEventMapping()
            self._saveCache()
            self.changed.emit()
            self.vignettesDetected.emit()
            _log.info(f"Received {len(self._vignettes)} vignettes")

        def onError(reply: QNetworkReply):
            self._detecting = False
            self.detectingChanged.emit()
            error = reply.errorString() if reply else "Unknown error"
            _log.error(f"Vignette detection failed: {error}")
            self.errorOccurred.emit(error)

        reply = self._session.server().nonBlockingRequest(
            "POST",
            f"/personal/diagrams/{self._diagramId}/vignettes",
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
    def vignettes(self) -> list[dict]:
        return self._vignettes

    @pyqtProperty(int, notify=changed)
    def count(self) -> int:
        return len(self._vignettes)

    @pyqtProperty(bool, notify=changed)
    def hasVignettes(self) -> bool:
        return len(self._vignettes) > 0

    @pyqtProperty(bool, notify=detectingChanged)
    def detecting(self) -> bool:
        return self._detecting

    @pyqtProperty(str, notify=changed)
    def selectedVignetteId(self) -> str:
        return self._selectedVignetteId or ""

    @selectedVignetteId.setter
    def selectedVignetteId(self, value: str):
        if self._selectedVignetteId == value:
            return
        self._selectedVignetteId = value if value else None
        self.changed.emit()

    @pyqtSlot(str)
    def selectVignette(self, vignetteId: str):
        self.selectedVignetteId = vignetteId

    @pyqtSlot(int, result=str)
    def vignetteForEvent(self, eventId: int) -> str:
        return self._eventToVignette.get(eventId, "")

    @pyqtSlot(str, result="QVariantMap")
    def vignetteById(self, vignetteId: str) -> dict:
        for v in self._vignettes:
            if v.get("id") == vignetteId:
                return v
        return {}

    @pyqtSlot(int, result="QVariantMap")
    def vignetteAt(self, index: int) -> dict:
        if 0 <= index < len(self._vignettes):
            return self._vignettes[index]
        return {}

    @pyqtSlot(str, result="QVariantList")
    def eventsInVignette(self, vignetteId: str) -> list[int]:
        for v in self._vignettes:
            if v.get("id") == vignetteId:
                return v.get("eventIds", [])
        return []

    @property
    def cacheKey(self) -> str | None:
        return self._cacheKey

    def setVignettesData(self, vignettes: list[dict], cacheKey: str | None):
        self._vignettes = vignettes
        self._cacheKey = cacheKey
        self._buildEventMapping()
        self.changed.emit()
        _log.info(f"Loaded {len(self._vignettes)} vignettes from diagram data")
