import logging
from btcopilot.schema import EventKind, RelationshipKind, VariableShift
from pkdiagram.pyqt import (
    QObject,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)
from pkdiagram.scene import Scene, Event

_log = logging.getLogger(__name__)


class SARFGraphModel(QObject):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene: Scene | None = None
        self._events: list[dict] = []
        self._cumulative: list[dict] = []
        self._yearRange: tuple[int, int] = (1920, 1980)

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
        self.refresh()

    def _onSceneChanged(self, *args):
        self.refresh()

    def deinit(self):
        self.scene = None

    def refresh(self):
        self._buildEventData()
        self._calculateCumulative()
        self._calculateYearRange()
        self.changed.emit()

    def _buildEventData(self):
        self._events = []
        if not self._scene:
            return

        events = self._scene.events(onlyDated=True)
        events = sorted(events, key=lambda e: e.dateTime().toMSecsSinceEpoch())

        for event in events:
            dt = event.dateTime()
            year = dt.date().year()
            dateStr = dt.toString("MMM d, yyyy")

            kind = event.kind()
            if isinstance(kind, str):
                kind = EventKind(kind)

            symptom = self._shiftValue(event.symptom())
            anxiety = self._shiftValue(event.anxiety())
            functioning = self._shiftValue(event.functioning())
            relationship = self._relationshipValue(event.relationship())

            person = event.person()
            who = person.name() if person else ""

            self._events.append(
                {
                    "id": event.id,
                    "year": year,
                    "date": dateStr,
                    "kind": kind.value,
                    "symptom": symptom,
                    "anxiety": anxiety,
                    "functioning": functioning,
                    "relationship": relationship,
                    "description": event.description() or "",
                    "who": who,
                    "notes": event.notes() or "",
                }
            )

    def _shiftValue(self, shift: VariableShift | None) -> str | None:
        if shift is None:
            return None
        if isinstance(shift, str):
            return shift
        return shift.value

    def _relationshipValue(self, rel: RelationshipKind | None) -> str | None:
        if rel is None:
            return None
        if isinstance(rel, str):
            return rel
        return rel.value

    def _calculateCumulative(self):
        self._cumulative = []
        cs, ca, cf = 0, 0, 0

        for event in self._events:
            s = event.get("symptom")
            a = event.get("anxiety")
            f = event.get("functioning")

            if s == "up":
                cs += 1
            elif s == "down":
                cs -= 1

            if a == "up":
                ca += 1
            elif a == "down":
                ca -= 1

            if f == "up":
                cf += 1
            elif f == "down":
                cf -= 1

            self._cumulative.append(
                {
                    "year": event["year"],
                    "symptom": cs,
                    "anxiety": ca,
                    "functioning": cf,
                    "relationship": event.get("relationship"),
                }
            )

    def _calculateYearRange(self):
        if not self._events:
            self._yearRange = (1920, 1980)
            return

        years = [e["year"] for e in self._events]
        minYear = min(years)
        maxYear = max(years)
        padding = max(5, (maxYear - minYear) // 10)
        self._yearRange = (minYear - padding, maxYear + padding)

    @pyqtProperty("QVariantList", notify=changed)
    def events(self) -> list[dict]:
        return self._events

    @pyqtProperty("QVariantList", notify=changed)
    def cumulative(self) -> list[dict]:
        return self._cumulative

    @pyqtProperty(int, notify=changed)
    def yearStart(self) -> int:
        return self._yearRange[0]

    @pyqtProperty(int, notify=changed)
    def yearEnd(self) -> int:
        return self._yearRange[1]

    @pyqtProperty(int, notify=changed)
    def yearSpan(self) -> int:
        return self._yearRange[1] - self._yearRange[0]

    @pyqtProperty(bool, notify=changed)
    def hasData(self) -> bool:
        return len(self._events) > 0

    @pyqtSlot(int, result="QVariantMap")
    def eventAt(self, index: int) -> dict:
        if 0 <= index < len(self._events):
            return self._events[index]
        return {}

    @pyqtSlot(int, result="QVariantMap")
    def cumulativeAt(self, index: int) -> dict:
        if 0 <= index < len(self._cumulative):
            return self._cumulative[index]
        return {}

    @pyqtSlot(int, result=str)
    def primaryColor(self, index: int) -> str:
        if index < 0 or index >= len(self._events):
            return "#ffffff"
        event = self._events[index]
        if event.get("relationship"):
            return "#5080d0"
        if event.get("symptom"):
            return "#e05555"
        if event.get("anxiety"):
            return "#40a060"
        if event.get("functioning"):
            return "#909090"
        return "#ffffff"

    @pyqtSlot(str, result=bool)
    def isLifeEvent(self, kind: str) -> bool:
        return kind in (
            EventKind.Birth.value,
            EventKind.Married.value,
            EventKind.Separated.value,
            EventKind.Divorced.value,
            EventKind.Moved.value,
            EventKind.Bonded.value,
            EventKind.Adopted.value,
        )
