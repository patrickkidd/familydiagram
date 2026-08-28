import logging
import pickle
from copy import deepcopy
from typing import Callable

from btcopilot.schema import (
    DateCertainty,
    DiagramData,
    EventKind,
    PDP,
    Person as SchemaPerson,
    RelationshipKind,
    VariableShift,
    asdict,
    from_dict,
    is_parents_edit,
)
from PyQt5.QtCore import QDateTime, QTimer

from pkdiagram import util
from pkdiagram.app import Session
from pkdiagram.models.diagramsaver import DiagramSaver
from pkdiagram.personal.api import JSON_HEADERS
from pkdiagram.personal.commands import AcceptPDPItems
from pkdiagram.personal.discussioncontroller import DiscussionController
from pkdiagram.pyqt import (
    QLineF,
    QObject,
    QPointF,
    QUrl,
    QVariant,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)
from pkdiagram.scene import Event, Marriage, Person, Scene
from pkdiagram.server_types import Diagram

# Rebuild fails if no progress advance arrives within this window — catches a
# crashed/killed worker or a lost task, which otherwise poll a dead task forever.
REBUILD_STALL_MS = 180_000

# Committed items carry no position, so they cascade from the centre of the
# people already on the diagram instead of stacking on the origin (FD-336 D11).
PLACEMENT_OFFSET = 60

_log = logging.getLogger(__name__)


class PDPController(QObject):
    """The staged extraction (PDP) for one Diagram: producing it (extract,
    rebuild, journal import) and resolving it (accept/reject onto the Scene).

    Every server callback is issued against a specific Diagram and returns
    without side effects if setDiagram() has since moved on, so an extraction
    in flight can't land on the wrong case."""

    pdpChanged = pyqtSignal()
    committed = pyqtSignal()

    journalImportStarted = pyqtSignal()
    journalImportCompleted = pyqtSignal(QVariant, arguments=["summary"])
    journalImportFailed = pyqtSignal(str, arguments=["error"])

    extractStarted = pyqtSignal()
    extractingChanged = pyqtSignal()
    extractCompleted = pyqtSignal(QVariant, arguments=["summary"])
    extractFailed = pyqtSignal(str, arguments=["error"])
    rebuildProgress = pyqtSignal(int, str, arguments=["percent", "message"])
    rebuildCancelled = pyqtSignal()

    ITEM_FIELDS = ("people", "events", "pair_bonds")

    def __init__(self, session: Session, saver: DiagramSaver, parent=None):
        super().__init__(parent)
        self.session = session
        self.saver = saver
        # Consulted before an extract reaches the server (FD-336 D6).
        # Standalone Personal leaves it None.
        self.gate: Callable[[], bool] | None = None
        self._diagram: Diagram | None = None
        self._discussion: DiscussionController | None = None
        self.scene: Scene | None = None
        # Highest Statement.order the last extract covered, as reported by the
        # server. Echoed back on commit-pdp so the cursor advances to the
        # exact extraction being accepted, not whatever the server's pending
        # value happens to hold after a concurrent re-extract (FD-331).
        self._pendingExtractedThroughOrder: int | None = None
        self._rebuildActive = False
        self._rebuildCancelled = False
        self._rebuildTaskId = ""
        self._rebuildPrevCurrent = -1
        self._rebuildLastProgressMs = 0
        self._rebuildPoll: tuple[int, str] | None = None
        self._rebuildTimer = QTimer(self)
        self._rebuildTimer.setSingleShot(True)
        self._rebuildTimer.setInterval(1000)
        self._rebuildTimer.timeout.connect(self._onRebuildTimeout)

    def setDiagram(self, diagram: Diagram | None):
        if self._rebuildActive:
            self.cancelRebuild()
        self._diagram = diagram
        self._pendingExtractedThroughOrder = None
        self._extracting = False
        self.pdpChanged.emit()

    def setScene(self, scene: Scene | None):
        if scene is None and self._rebuildActive:
            self.cancelRebuild()
        self.scene = scene
        # committedPeople on the pdp map comes from the scene, so it is stale
        # until this lands.
        self.pdpChanged.emit()

    def setDiscussion(self, discussion: DiscussionController):
        self._discussion = discussion
        discussion.currentDiscussionChanged.connect(self.pdpChanged)

    def _isCurrent(self, diagram: Diagram | None) -> bool:
        return self._diagram is diagram

    def _currentDiscussion(self):
        return self._discussion.currentDiscussion() if self._discussion else None

    @pyqtProperty(bool, notify=pdpChanged)
    def canRebuild(self) -> bool:
        """Rebuild button visibility. True when there is a current discussion
        AND the diagram already has at least one person (something to rebuild
        from). Independent of canExtract — a rebuild is valid even when the
        conversation is fully extracted."""
        if not self._currentDiscussion() or not self._diagram:
            return False
        if self.scene and self.scene.people():
            return True
        diagramData = self._diagram.getDiagramData()
        return bool(diagramData.people)

    @pyqtSlot(int, result=bool)
    def acceptPDPItem(self, id: int, undo=True) -> bool:
        if id == 0:
            _log.error(f"acceptPDPItem called with id 0, ignoring")
            return False
        result = self._acceptIds([id])
        if result and undo and self.scene:
            self.scene.push(AcceptPDPItems(self, [id], *result))
        return result is not None

    @pyqtSlot(int, result=bool)
    def rejectPDPItem(self, id: int) -> bool:
        """Not undoable: nothing lands on the Scene, and the next extraction
        re-proposes the item."""
        if id == 0:
            _log.error(f"rejectPDPItem called with id 0, ignoring")
            return False

        def mutate(diagramData: DiagramData) -> DiagramData:
            if id < 0:
                diagramData.reject_pdp_item(id)
            elif id in (diagramData.pdp.delete or []):
                diagramData.reject_committed_delete(id)
            else:
                diagramData.reject_committed_edit(id)
            return diagramData

        success = self.saver.save(self._diagram.id, self._sceneBytes(), mutate=mutate)
        if success:
            self.pdpChanged.emit()
        else:
            _log.warning(f"Failed to reject PDP item {id} after retries")
        return success

    def _postCommitPdp(self, itemIds: list[int], fullAccept: bool):
        """Tell the backend which staged items were accepted so the
        re-extraction cursor advances on a full accept. Best-effort: a failure
        only means the cursor doesn't advance (next extract re-windows; the
        server-side committed-duplicate guard absorbs the repeat)."""
        # Empty itemIds is valid only as an explicit full accept of an empty
        # PDP (advance the cursor, nothing to commit).
        discussion = self._currentDiscussion()
        if not discussion or (not itemIds and not fullAccept):
            return

        diagram = self._diagram

        def onError():
            _log.warning(f"commit-pdp cursor advance failed: {reply.errorString()}")

        def onSuccess(data):
            if not self._isCurrent(diagram):
                return
            # Server confirmed the accept. Clean unless chat was sent after the
            # extract that produced this PDP (then still dirty).
            if isinstance(data, dict) and data.get("full_accept"):
                self._discussion.markAccepted()

        data = {"item_ids": itemIds, "full_accept": fullAccept}
        if self._pendingExtractedThroughOrder is not None:
            data["accepted_through_order"] = self._pendingExtractedThroughOrder

        reply = self.session.server().nonBlockingRequest(
            "POST",
            f"/personal/discussions/{discussion.id}/commit-pdp",
            data=data,
            error=onError,
            success=onSuccess,
            headers=JSON_HEADERS,
            from_root=True,
        )

    @staticmethod
    def _pdpDrained(diagramData: DiagramData) -> bool:
        """Parents-only edit rows are the server-applied channel (applied by
        commit-pdp on full accept), so they never block a full accept."""
        return not (
            any(not is_parents_edit(p) for p in diagramData.pdp.people)
            or diagramData.pdp.events
            or diagramData.pdp.pair_bonds
        )

    def _sceneBytes(self) -> bytes:
        """This client's view of the row. With no Scene loaded — the blob was
        corrupt enough that Scene.read raised — the row stands in for it, so
        the merge is a no-op and only the mutation lands."""
        return pickle.dumps(self.scene.data()) if self.scene else self._diagram.data

    @classmethod
    def _itemFields(cls, diagramData: DiagramData) -> dict:
        fields = {
            name: deepcopy(getattr(diagramData, name)) for name in cls.ITEM_FIELDS
        }
        fields["pdp"] = deepcopy(diagramData.pdp)
        return fields

    def _acceptIds(self, ids: list[int]) -> tuple[dict, dict] | None:
        """Commit staged items onto the row and mirror the result onto the
        Scene. Returns the row's committed collections either side of the
        accept, or None if the save failed."""
        _log.info(f"Accepting PDP items: {ids}")
        prev, post, drained = {}, {}, {}

        def mutate(diagramData: DiagramData) -> DiagramData:
            prev.update(self._itemFields(diagramData))
            newIds = [x for x in ids if x < 0]
            if newIds:
                diagramData.commit_pdp_items(newIds)
            for id in (x for x in ids if x > 0):
                if id in (diagramData.pdp.delete or []):
                    diagramData.accept_committed_delete(id)
                else:
                    diagramData.accept_committed_edit(id)
            drained["v"] = self._pdpDrained(diagramData)
            post.update(self._itemFields(diagramData))
            return diagramData

        if not self.saver.save(self._diagram.id, self._sceneBytes(), mutate=mutate):
            _log.warning(f"Failed to accept PDP items {ids} after retries")
            return None

        self._syncSceneTo(post)
        self.pdpChanged.emit()
        self.committed.emit()
        self._postCommitPdp(ids, drained["v"])
        return prev, post

    def _revertTo(self, prev: dict) -> bool:
        """Undo half of AcceptPDPItems: the cards and the committed
        collections go back on the row, and the Scene follows."""

        def mutate(diagramData: DiagramData) -> DiagramData:
            for name in self.ITEM_FIELDS:
                setattr(diagramData, name, deepcopy(prev[name]))
            diagramData.pdp = deepcopy(prev["pdp"])
            return diagramData

        self._syncSceneTo(prev)
        success = self.saver.save(self._diagram.id, self._sceneBytes(), mutate=mutate)
        if success:
            self.pdpChanged.emit()
        else:
            _log.warning("Failed to undo an accept after retries")
        return success

    def _syncSceneTo(self, fields: dict):
        """Match the Scene to the row's committed collections: add what it
        lacks, drop what the row no longer carries, take name/gender edits."""
        if self.scene is None:
            return
        adds = {name: [] for name in self.ITEM_FIELDS}
        keep = set()
        for name in self.ITEM_FIELDS:
            for chunk in fields[name]:
                keep.add(chunk["id"])
                item = self.scene.itemRegistry.get(chunk["id"])
                if item is None:
                    adds[name].append(chunk)
                elif name == "people":
                    if chunk.get("name") is not None:
                        item.setName(chunk["name"])
                    if chunk.get("gender") is not None:
                        item.setGender(chunk["gender"])
        stale = [
            item
            for item in list(self.scene.events())
            + list(self.scene.marriages())
            + list(self.scene.people())
            if item.id not in keep
        ]
        if stale:
            self.scene.setBatchAddingRemovingItems(True)
            try:
                for item in stale:
                    self.scene.removeItem(item)
            finally:
                self.scene.setBatchAddingRemovingItems(False)
        self._addCommittedItemsToScene(adds)

    def _place(self, people: list):
        """Committed chunks carry no position (D11). Cascade each new person off
        the centre of the people already on the diagram, stepping until it
        clears every one of them, so nothing lands on top of anything — within
        this batch or across separate accepts. Reads stored positions, not
        scene bounding rects, which lag a person placed moments ago."""
        placed = [person.itemPos() for person in self.scene.people()]
        if placed:
            xs = [pos.x() for pos in placed]
            ys = [pos.y() for pos in placed]
            anchor = QPointF((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        else:
            anchor = QPointF()

        def candidate(step):
            return anchor + QPointF(PLACEMENT_OFFSET * step, PLACEMENT_OFFSET * step)

        step = 1
        for person in people:
            pos = candidate(step)
            while any(
                QLineF(pos, other).length() < PLACEMENT_OFFSET for other in placed
            ):
                step += 1
                pos = candidate(step)
            person.setItemPosNow(pos)
            placed.append(pos)
            step += 1

    def _addCommittedItemsToScene(self, committedItems: dict):
        _log.debug(
            f"committing to scene: {len(committedItems['people'])} people, "
            f"{len(committedItems['pair_bonds'])} pair bonds, "
            f"{len(committedItems['events'])} events\n"
            f"  people:     {committedItems['people']}\n"
            f"  pair_bonds: {committedItems['pair_bonds']}\n"
            f"  events:     {committedItems['events']}"
        )
        if (
            not committedItems["people"]
            and not committedItems["events"]
            and not committedItems["pair_bonds"]
        ):
            return

        # Phase 1: Create items and build local map (two-phase approach like Scene.read())
        itemChunks = []
        localMap = {}

        for chunk in committedItems["people"]:
            item = Person()
            item.id = chunk["id"]
            localMap[item.id] = item
            itemChunks.append((item, chunk))

        for chunk in committedItems["pair_bonds"]:
            item = Marriage()
            _log.debug(
                f"constructing Marriage {chunk['id']}: "
                f"person_a={chunk.get('person_a')} person_b={chunk.get('person_b')} "
                f"married={chunk.get('married')} chunk={chunk}"
            )
            item.id = chunk["id"]
            localMap[item.id] = item
            itemChunks.append((item, chunk))

        for chunk in committedItems["events"]:
            kind = EventKind(chunk["kind"])
            if kind.isPairBond() and not chunk.get("spouse"):
                _log.error(
                    f"Skipping invalid pair bond event {chunk['id']} (kind={kind.value}): missing spouse"
                )
                continue
            item = Event(kind=EventKind.Shift, person=None)
            item.id = chunk["id"]
            localMap[item.id] = item
            itemChunks.append((item, chunk))

        # Phase 2: Read all chunks before adding to scene
        def byId(id):
            return localMap.get(id) or self.scene.itemRegistry.get(id)

        for item, chunk in itemChunks:
            item.read(chunk, byId)

        # Accept is a probabilistic-origin ingress (LLM extraction). Per the
        # provenance-normalized ingress rule (scene/CLAUDE.md), it must pass
        # through the SAME shared resilience step as load (Scene.read), not a
        # per-ingress patch. Drop events whose primary refs didn't resolve
        # (full chunk logged, recoverable) so addItem can't crash on a None
        # person. FMEA 2026-05-02 L2 recurred here because only load was wired.
        dropped = self.scene._dropIrrecoverableEvents(itemChunks)
        if dropped:
            droppedSet = set(dropped)
            itemChunks = [(i, c) for (i, c) in itemChunks if i not in droppedSet]

        self._place([item for item, chunk in itemChunks if isinstance(item, Person)])

        # Phase 3: Add all items to scene.
        # isInitializing: suppress cross-reference validation (FR-4)
        # batch mode: defer signals and geometry updates
        self.scene.isInitializing = True
        self.scene.setBatchAddingRemovingItems(True)
        try:
            for item, chunk in itemChunks:
                _log.debug(
                    f"scene.addItem {type(item).__name__} {item.id}: "
                    f"{getattr(item, 'name', lambda: None)() if callable(getattr(item, 'name', None)) else ''}"
                )
                self.scene.addItem(item)
        finally:
            self.scene.isInitializing = False
            self.scene.setBatchAddingRemovingItems(False)

    @pyqtProperty("QVariantMap", notify=pdpChanged)
    def pdp(self):
        if self._diagram:
            diagramData = self._diagram.getDiagramData()
            if diagramData.pdp:
                result = asdict(diagramData.pdp)
                # Include committed people from scene so QML can resolve relationshipTargets/Triangles
                committedPeople = []
                if self.scene:
                    for person in self.scene.people():
                        committedPeople.append(
                            {"id": person.id, "name": person.fullNameOrAlias()}
                        )
                result["committedPeople"] = committedPeople
                return result
        return {}

    # PDP helper slots - model lookups and enum mappings

    @pyqtSlot("QVariantMap", result=bool)
    def isParentsEdit(self, person: dict) -> bool:
        """Parents-only rows render no card; PDPSheet and the badge count both
        filter through this so they can't disagree."""
        return is_parents_edit(from_dict(SchemaPerson, person))

    @pyqtSlot(int, result=str)
    @pyqtSlot("QVariant", result=str)
    def resolvePersonName(self, personId: int | None) -> str:
        if personId is None:
            return ""
        if not self._diagram:
            return f"Person #{personId}"
        diagramData = self._diagram.getDiagramData()
        if diagramData.pdp:
            for p in diagramData.pdp.people:
                if p.id == personId:
                    return p.name or p.last_name or ""
        if self.scene:
            for person in self.scene.people():
                if person.id == personId:
                    return person.fullNameOrAlias()
        return f"Person #{personId}"

    @pyqtSlot("QVariantList", result=str)
    def resolvePersonNames(self, personIds: list[int]) -> str:
        if not personIds:
            return ""
        names = [self.resolvePersonName(pid) for pid in personIds if pid is not None]
        return ", ".join(n for n in names if n)

    @pyqtSlot(int, result=str)
    @pyqtSlot("QVariant", result=str)
    def resolvePairBondChildren(self, pairBondId) -> str:
        if pairBondId is None:
            return ""
        if not self._diagram:
            return ""
        diagramData = self._diagram.getDiagramData()
        if not diagramData.pdp:
            return ""
        names = [
            p.name or ""
            for p in diagramData.pdp.people
            if p.parents == pairBondId and p.name
        ]
        return ", ".join(names)

    @pyqtSlot(int, result=str)
    @pyqtSlot("QVariant", result=str)
    def scenePersonKind(self, personId: int | None) -> str:
        if personId is None:
            return ""
        if self._diagram:
            for p in self._diagram.getDiagramData().people:
                if p.get("id") == personId:
                    kind = p.get("gender")
                    return util.personKindNameFromKind(kind) or "" if kind else ""
        if self.scene:
            for person in self.scene.people():
                if person.id == personId:
                    return util.personKindNameFromKind(person.gender()) or ""
        return ""

    @pyqtSlot(str, result=str)
    def kindLabel(self, kind: str) -> str:
        return util.personKindNameFromKind(kind) or ""

    @pyqtSlot(int, result=str)
    @pyqtSlot("QVariant", result=str)
    def resolveParentNames(self, parentsId: int | None) -> str:
        if parentsId is None:
            return ""
        if not self._diagram:
            return ""
        diagramData = self._diagram.getDiagramData()
        if not diagramData.pdp:
            return ""
        for pb in diagramData.pdp.pair_bonds:
            if pb.id == parentsId:
                nameA = self.resolvePersonName(pb.person_a) if pb.person_a else ""
                nameB = self.resolvePersonName(pb.person_b) if pb.person_b else ""
                if nameA and nameB:
                    return f"{nameA} & {nameB}"
                return nameA or nameB
        return ""

    @pyqtSlot(str, result=str)
    @pyqtSlot("QVariant", result=str)
    def eventKindLabel(self, kind: str | None) -> str:
        if not kind:
            return "Event"
        labels = {
            EventKind.Bonded.value: "Bonded",
            EventKind.Married.value: "Married",
            EventKind.Birth.value: "Birth",
            EventKind.Adopted.value: "Adopted",
            EventKind.Moved.value: "Moved",
            EventKind.Separated.value: "Separated",
            EventKind.Divorced.value: "Divorced",
            EventKind.Shift.value: "Shift",
            EventKind.Death.value: "Death",
        }
        return labels.get(kind, "Event")

    @pyqtSlot(str, result=str)
    @pyqtSlot("QVariant", result=str)
    def variableLabel(self, val: str | None) -> str:
        if not val:
            return ""
        labels = {
            VariableShift.Up.value: "Up",
            VariableShift.Down.value: "Down",
            VariableShift.Same.value: "Same",
        }
        return labels.get(val, "")

    @pyqtSlot(str, result=str)
    @pyqtSlot("QVariant", result=str)
    def relationshipLabel(self, val: str | None) -> str:
        if not val:
            return ""
        try:
            kind = RelationshipKind(val)
            return kind.menuLabel()
        except ValueError:
            return ""

    @pyqtSlot(str, result=str)
    @pyqtSlot("QVariant", result=str)
    def dateCertaintyLabel(self, val: str | None) -> str:
        if not val:
            return ""
        labels = {
            DateCertainty.Unknown.value: "Unknown",
            DateCertainty.Approximate.value: "Approximate",
            DateCertainty.Certain.value: "Certain",
        }
        return labels.get(val, "")

    @pyqtSlot()
    def dismissEmptyExtraction(self) -> None:
        self._postCommitPdp([], True)

    @pyqtSlot()
    def acceptAllPDPItems(self):
        if not self._diagram:
            return

        pdp = self._diagram.getDiagramData().pdp
        newIds = [
            item.id
            for item in list(pdp.people) + list(pdp.events) + list(pdp.pair_bonds)
            if item.id is not None and item.id < 0
        ]
        editIds = [
            p.id
            for p in pdp.people
            if p.id is not None and p.id > 0 and not is_parents_edit(p)
        ]
        deleteIds = list(pdp.delete or [])

        if not newIds and not editIds and not deleteIds:
            self._postCommitPdp([], True)
            return

        ids = newIds + editIds + deleteIds
        result = self._acceptIds(ids)
        if result and self.scene:
            self.scene.push(AcceptPDPItems(self, ids, *result))

    @pyqtSlot(int, str, "QVariant")
    def updatePDPItem(self, id: int, field: str, value):
        if not self._diagram:
            return

        _log.info(f"Updating PDP item {id}: {field} = {value}")

        def mutate(diagramData: DiagramData) -> DiagramData:
            for event in diagramData.pdp.events:
                if event.id == id:
                    if hasattr(event, field):
                        setattr(event, field, value)
                    break

            for person in diagramData.pdp.people:
                if person.id == id:
                    if hasattr(person, field):
                        setattr(person, field, value)
                    break

            return diagramData

        if self.saver.save(self._diagram.id, self._sceneBytes(), mutate=mutate):
            self.pdpChanged.emit()
        else:
            _log.warning(f"Failed to update PDP item {id} after retries")

    ## Clear Diagram Data

    @pyqtSlot(bool)
    def clearDiagramData(self, clearPeople: bool):
        if not self._diagram:
            return

        _log.info(
            f"Clearing diagram data (clearPeople={clearPeople}, "
            f"scene-loaded={self.scene is not None})"
        )

        if self.scene is not None:
            self.scene.setBatchAddingRemovingItems(True)
            try:
                for event in list(self.scene.events()):
                    self.scene.removeItem(event)

                if clearPeople:
                    for emotion in list(self.scene.emotions()):
                        self.scene.removeItem(emotion)
                    for marriage in list(self.scene.marriages()):
                        self.scene.removeItem(marriage)
                    for person in list(self.scene.people()):
                        if person.id not in (1, 2):
                            self.scene.removeItem(person)
            finally:
                self.scene.setBatchAddingRemovingItems(False)

        def mutate(diagramData: DiagramData) -> DiagramData:
            diagramData.events = []
            diagramData.pdp = PDP()
            if clearPeople:
                diagramData.people = [
                    p for p in diagramData.people if p.get("id") in (1, 2)
                ]
                diagramData.pair_bonds = []
                diagramData.emotions = []
            return diagramData

        if self.saver.save(self._diagram.id, self._sceneBytes(), mutate=mutate):
            self.pdpChanged.emit()
            _log.info("Diagram data cleared successfully")
        else:
            _log.warning("Failed to clear diagram data")

    ## Journal Import

    @pyqtSlot(str)
    def importJournalNotes(self, text: str):
        if not self._diagram:
            self.journalImportFailed.emit("No diagram loaded")
            return

        diagram = self._diagram
        self.journalImportStarted.emit()

        def onSuccess(data):
            if not self._isCurrent(diagram):
                return
            if data.get("pdp"):
                # Through the saver so a concurrent Pro/Personal save during
                # the import isn't clobbered by a blind setDiagramData, and so
                # this serializes against any in-flight save.
                # Plan: doc/plans/2026-05-01--mvp-merge-fix/README.md
                imported_pdp = from_dict(PDP, data["pdp"])

                def mutate(diagramData: DiagramData) -> DiagramData:
                    diagramData.pdp = imported_pdp
                    return diagramData

                self.saver.save(diagram.id, self._sceneBytes(), mutate=mutate)
            self.pdpChanged.emit()
            self.journalImportCompleted.emit(data.get("summary", {}))
            self.committed.emit()

        def onError():
            if not self._isCurrent(diagram):
                return
            self.journalImportFailed.emit(reply.errorString())

        reply = self.session.server().nonBlockingRequest(
            "POST",
            f"/personal/diagrams/{diagram.id}/import-text",
            data={"text": text},
            error=onError,
            success=onSuccess,
            headers=JSON_HEADERS,
            from_root=True,
        )

    @pyqtSlot(QUrl)
    def importFromFile(self, file_url: QUrl):
        self._onFilePicked(file_url.toLocalFile())

    def _onFilePicked(self, path: str):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError) as e:
            self.journalImportFailed.emit(str(e))
            return
        self.importJournalNotes(text)

    ## Extract Full

    @pyqtProperty(bool, notify=extractingChanged)
    def extracting(self) -> bool:
        """An extraction is in flight. The server admits one at a time, so a
        second request is refused; the button must not offer one."""
        return self._extracting

    def _setExtracting(self, on: bool):
        if on == self._extracting:
            return
        self._extracting = on
        self.extractingChanged.emit()

    @pyqtSlot()
    def extractFull(self):
        if self.gate and not self.gate():
            return
        discussion = self._currentDiscussion()
        if not discussion:
            self.extractFailed.emit("No discussion selected")
            return
        if not self._diagram:
            self.extractFailed.emit("No diagram loaded")
            return

        diagram = self._diagram
        # Baseline for "chat since this extract": a later full accept is clean
        # only if no statement was sent after this extract.
        _log.debug(
            f"extract requested for discussion {discussion.id} on diagram {diagram.id}"
        )
        self._discussion.markExtracted()
        self._setExtracting(True)
        self.extractStarted.emit()

        def onSuccess(data):
            self._setExtracting(False)
            _log.debug(
                f"extract returned: people={data.get('people_count')} "
                f"events={data.get('events_count')} "
                f"pairBonds={data.get('pair_bonds_count')} "
                f"pdp={data.get('pdp')}"
            )
            if not self._isCurrent(diagram):
                return
            self._pendingExtractedThroughOrder = data.get(
                "pending_extracted_through_order"
            )
            diagramData = diagram.getDiagramData()
            diagramData.pdp = from_dict(PDP, data["pdp"])
            diagram.setDiagramData(diagramData)
            self.pdpChanged.emit()
            self.extractCompleted.emit(
                {
                    "people": data.get("people_count", 0),
                    "events": data.get("events_count", 0),
                    "pairBonds": data.get("pair_bonds_count", 0),
                }
            )

        def onError():
            self._setExtracting(False)
            _log.debug(f"extract failed: {reply.errorString()}")
            if not self._isCurrent(diagram):
                return
            self.extractFailed.emit(reply.errorString())

        reply = self.session.server().nonBlockingRequest(
            "POST",
            f"/personal/discussions/{discussion.id}/extract",
            data={},
            error=onError,
            success=onSuccess,
            headers=JSON_HEADERS,
            from_root=True,
        )

    ## Rebuild (deep re-extraction)

    @pyqtSlot(int)
    def rebuildDiagram(self, k: int):
        discussion = self._currentDiscussion()
        if not discussion:
            self.extractFailed.emit("No discussion selected")
            return
        if not self._diagram:
            self.extractFailed.emit("No diagram loaded")
            return

        diagram = self._diagram
        discussionId = discussion.id

        # Watchdog / cancel state for this run. A frozen task never advances,
        # so the poller fails it after REBUILD_STALL_MS instead of spinning
        # forever; cancel stops the poll loop and tells the server to abort.
        self._rebuildActive = True
        self._rebuildLastProgressMs = QDateTime.currentMSecsSinceEpoch()
        self._rebuildPrevCurrent = -1
        self._rebuildCancelled = False
        self._rebuildTaskId = ""

        # Set overlay to determinate mode at 0 before showing
        self.rebuildProgress.emit(0, "Starting rebuild...")
        self.extractStarted.emit()

        def onSuccess(data):
            if not self._isCurrent(diagram):
                return
            taskId = data.get("task_id", "")
            if not taskId:
                self._rebuildActive = False
                self.extractFailed.emit("Server did not return a task ID")
                return
            self._rebuildTaskId = taskId
            self._pollRebuild(discussionId, taskId)

        def onError():
            if not self._isCurrent(diagram):
                return
            self._rebuildActive = False
            self.extractFailed.emit(reply.errorString())

        reply = self.session.server().nonBlockingRequest(
            "POST",
            f"/personal/discussions/{discussionId}/deep-reextract",
            data={"k": k},
            error=onError,
            success=onSuccess,
            headers=JSON_HEADERS,
            from_root=True,
        )

    def _onRebuildTimeout(self):
        self._pollRebuild(*self._rebuildPoll)

    def _pollRebuild(self, discussionId: int, taskId: str):
        self._rebuildPoll = (discussionId, taskId)
        diagram = self._diagram

        def onSuccess(data):
            if self._rebuildCancelled or not self._isCurrent(diagram):
                return
            status = data.get("status", "")
            now = QDateTime.currentMSecsSinceEpoch()
            if status == "progress":
                current = data.get("current", 0)
                total = data.get("total", 1)
                label = data.get("label", "Rebuilding...")
                percent = round(current / total * 100) if total else 0
                if current > self._rebuildPrevCurrent:
                    self._rebuildPrevCurrent = current
                    self._rebuildLastProgressMs = now
                self.rebuildProgress.emit(percent, label)
                if self._rebuildStalled(now):
                    return
                self._rebuildTimer.start()
            elif status == "complete":
                self._rebuildActive = False
                rebuilt_pdp = from_dict(PDP, data["pdp"])

                def mutate(diagramData: DiagramData) -> DiagramData:
                    diagramData.pdp = rebuilt_pdp
                    return diagramData

                self.saver.save(diagram.id, self._sceneBytes(), mutate=mutate)
                self.pdpChanged.emit()
                self.extractCompleted.emit(
                    {
                        "people": data.get("people_count", 0),
                        "events": data.get("events_count", 0),
                        "pairBonds": data.get("pair_bonds_count", 0),
                    }
                )
            elif status == "error":
                self._rebuildActive = False
                self.extractFailed.emit(data.get("error", "Rebuild failed"))
            else:
                # pending or unknown — keep polling unless it has gone stale
                if self._rebuildStalled(now):
                    return
                self._rebuildTimer.start()

        def onError():
            if not self._isCurrent(diagram):
                return
            self._rebuildActive = False
            self.extractFailed.emit(pollReply.errorString())

        pollReply = self.session.server().nonBlockingRequest(
            "GET",
            f"/personal/discussions/{discussionId}/deep-reextract-status/{taskId}",
            data={},
            error=onError,
            success=onSuccess,
            headers=JSON_HEADERS,
            from_root=True,
        )

    def _rebuildStalled(self, now_ms: int) -> bool:
        """True (and emits the failure) if no progress has advanced within
        REBUILD_STALL_MS — i.e. the worker crashed/was killed or the task was
        lost. Stops the poll loop so the overlay can't spin on a dead task."""
        if self._rebuildLastProgressMs <= 0:
            return False  # no rebuild active
        if now_ms - self._rebuildLastProgressMs <= REBUILD_STALL_MS:
            return False
        self._rebuildActive = False
        self.extractFailed.emit(
            "The rebuild stopped responding — the server may have crashed. "
            "Please try again."
        )
        return True

    @pyqtSlot()
    def cancelRebuild(self):
        """Stop polling, tell the server to abort the background task and release
        the lock, and dismiss the overlay. Quitting the app has the same
        server-side effect: polling stops, the heartbeat expires, and the worker
        aborts the run on its own — so no orphaned rebuild keeps running."""
        self._rebuildCancelled = True
        self._rebuildActive = False
        self._rebuildTimer.stop()
        taskId = self._rebuildTaskId
        discussion = self._currentDiscussion()
        discussionId = discussion.id if discussion else None
        if taskId and discussionId:
            self.session.server().nonBlockingRequest(
                "POST",
                f"/personal/discussions/{discussionId}/deep-reextract/{taskId}/cancel",
                data={},
                error=lambda: None,
                success=lambda d: None,
                headers=JSON_HEADERS,
                from_root=True,
            )
        self._rebuildTaskId = ""
        self.rebuildCancelled.emit()
