import logging

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
from pkdiagram.personal.api import JSON_HEADERS
from pkdiagram.personal.commands import HandlePDPItem, PDPAction
from pkdiagram.personal.discussioncontroller import DiscussionController
from pkdiagram.personal.saveguard import SaveGuard
from pkdiagram.pyqt import (
    QObject,
    QUndoStack,
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
    extractCompleted = pyqtSignal(QVariant, arguments=["summary"])
    extractFailed = pyqtSignal(str, arguments=["error"])
    rebuildProgress = pyqtSignal(int, str, arguments=["percent", "message"])
    rebuildCancelled = pyqtSignal()

    def __init__(
        self,
        session: Session,
        saveGuard: SaveGuard,
        undoStack: QUndoStack,
        parent=None,
    ):
        super().__init__(parent)
        self.session = session
        self._saveGuard = saveGuard
        self._undoStack = undoStack
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
    def acceptPDPItem(self, id: int, undo=True):
        if id > 0:
            return self._saveGuard(
                lambda: self._doHandleCommittedItem(id, accept=True, undo=undo)
            )
        if id == 0:
            _log.error(f"acceptPDPItem called with id 0, ignoring")
            return False

        def _do():
            prev_data = self._diagram.getDiagramData() if undo else None
            success = self._doAcceptPDPItem(id)
            if success:
                self.committed.emit()
                if undo:
                    cmd = HandlePDPItem(PDPAction.Accept, self, id, prev_data)
                    self._undoStack.push(cmd)
            return success

        return self._saveGuard(_do)

    @pyqtSlot(int, result=bool)
    def rejectPDPItem(self, id: int, undo=True):
        if id > 0:
            return self._saveGuard(
                lambda: self._doHandleCommittedItem(id, accept=False, undo=undo)
            )
        if id == 0:
            _log.error(f"rejectPDPItem called with id 0, ignoring")
            return False

        def _do():
            prev_data = self._diagram.getDiagramData() if undo else None
            success = self._doRejectPDPItem(id)
            if success and undo:
                cmd = HandlePDPItem(PDPAction.Reject, self, id, prev_data)
                self._undoStack.push(cmd)
            return success

        return self._saveGuard(_do)

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

    def _doAcceptPDPItem(self, id: int) -> bool:
        _log.info(f"Accepting PDP item with id: {id}")

        committedItems = {"people": [], "events": [], "pair_bonds": [], "emotions": []}
        drained = {}

        def applyChange(diagramData: DiagramData):
            _log.info(f"Applying accept PDP item change for id: {id}")
            if not diagramData.pdp:
                _log.warning("No PDP data available")
                return diagramData
            if self.scene is not None:
                diagramData.lastItemId = max(
                    diagramData.lastItemId, self.scene.lastItemId()
                )
            # Capture IDs before commit to identify what was added
            prevPeopleIds = {p["id"] for p in diagramData.people}
            prevEventIds = {e["id"] for e in diagramData.events}
            prevPairBondIds = {pb["id"] for pb in diagramData.pair_bonds}

            diagramData.commit_pdp_items([id])

            # Find newly committed items
            committedItems["people"] = [
                p for p in diagramData.people if p["id"] not in prevPeopleIds
            ]
            committedItems["events"] = [
                e for e in diagramData.events if e["id"] not in prevEventIds
            ]
            committedItems["pair_bonds"] = [
                pb for pb in diagramData.pair_bonds if pb["id"] not in prevPairBondIds
            ]
            drained["v"] = self._pdpDrained(diagramData)

            return diagramData

        def stillValidAfterRefresh(diagramData: DiagramData):
            return True

        success = self._diagram.save(
            self.session.server(), applyChange, stillValidAfterRefresh, useJson=True
        )

        if success:
            self._addCommittedItemsToScene(committedItems)
            self.pdpChanged.emit()
            self._postCommitPdp([id], drained.get("v", False))
        else:
            _log.warning(f"Failed to accept PDP item after retries")

        return success

    def _addCommittedItemsToScene(self, committedItems: dict):
        if self.scene is None:
            return
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

        # Phase 3: Add all items to scene.
        # isInitializing: suppress cross-reference validation (FR-4)
        # batch mode: defer signals and geometry updates
        self.scene.isInitializing = True
        self.scene.setBatchAddingRemovingItems(True)
        try:
            for item, chunk in itemChunks:
                self.scene.addItem(item)
        finally:
            self.scene.isInitializing = False
            self.scene.setBatchAddingRemovingItems(False)

    def _doHandleCommittedItem(self, id: int, accept: bool, undo: bool = True) -> bool:
        """Accept or reject a committed item (positive id in pdp.people or pdp.delete)."""
        prev_data = self._diagram.getDiagramData() if undo else None
        result: dict = {"is_delete": False, "edit_fields": {}, "drained": False}

        def applyChange(diagramData: DiagramData):
            if not diagramData.pdp:
                return diagramData
            is_delete = id in (diagramData.pdp.delete or [])
            result["is_delete"] = is_delete
            if accept:
                if is_delete:
                    diagramData.accept_committed_delete(id)
                else:
                    pdp_person = next(
                        (p for p in diagramData.pdp.people if p.id == id), None
                    )
                    if pdp_person is not None:
                        if pdp_person.name is not None:
                            result["edit_fields"]["name"] = pdp_person.name
                        if pdp_person.gender is not None:
                            result["edit_fields"]["gender"] = pdp_person.gender
                    diagramData.accept_committed_edit(id)
            else:
                if is_delete:
                    diagramData.reject_committed_delete(id)
                else:
                    diagramData.reject_committed_edit(id)
            result["drained"] = self._pdpDrained(diagramData)
            return diagramData

        success = self._diagram.save(
            self.session.server(), applyChange, lambda d: True, useJson=True
        )

        if success:
            if self.scene is not None and accept:
                if result["is_delete"]:
                    person = self.scene.find(id=id)
                    if person is not None:
                        self.scene.removeItem(person)
                elif result["edit_fields"]:
                    person = self.scene.find(id=id)
                    if person is not None:
                        if "name" in result["edit_fields"]:
                            person.setName(result["edit_fields"]["name"])
                        if "gender" in result["edit_fields"]:
                            person.setGender(result["edit_fields"]["gender"])
            self.pdpChanged.emit()
            if accept:
                # The route acknowledges echoed positive ids as no-ops; the
                # flag is what advances the cursor when this was the last card.
                self._postCommitPdp([id], result["drained"])
            if undo and prev_data:
                action = PDPAction.Accept if accept else PDPAction.Reject
                self._undoStack.push(HandlePDPItem(action, self, id, prev_data))
        else:
            _log.warning(f"Failed to handle committed item {id}")

        return success

    @pyqtSlot(int, result=bool)
    def acceptCommittedEdit(self, id: int) -> bool:
        return bool(
            self._saveGuard(lambda: self._doHandleCommittedItem(id, accept=True))
        )

    @pyqtSlot(int, result=bool)
    def rejectCommittedEdit(self, id: int) -> bool:
        return bool(
            self._saveGuard(lambda: self._doHandleCommittedItem(id, accept=False))
        )

    @pyqtSlot(int, result=bool)
    def acceptCommittedDelete(self, id: int) -> bool:
        return bool(
            self._saveGuard(lambda: self._doHandleCommittedItem(id, accept=True))
        )

    @pyqtSlot(int, result=bool)
    def rejectCommittedDelete(self, id: int) -> bool:
        return bool(
            self._saveGuard(lambda: self._doHandleCommittedItem(id, accept=False))
        )

    def _doRejectPDPItem(self, id: int) -> bool:
        _log.info(f"Rejecting PDP item with id: {id}")

        def applyChange(diagramData: DiagramData):
            if not diagramData.pdp:
                _log.warning("No PDP data available")
                return diagramData
            diagramData.reject_pdp_item(id)
            return diagramData

        def stillValidAfterRefresh(diagramData: DiagramData):
            return True

        success = self._diagram.save(
            self.session.server(), applyChange, stillValidAfterRefresh, useJson=True
        )

        if success:
            self.pdpChanged.emit()
        else:
            _log.warning(f"Failed to reject PDP item after retries")

        return success

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

        def _do():
            diagramData = self._diagram.getDiagramData()
            if not diagramData.pdp:
                return

            newIds = []
            for person in diagramData.pdp.people:
                if person.id is not None and person.id < 0:
                    newIds.append(person.id)
            for event in diagramData.pdp.events:
                if event.id < 0:
                    newIds.append(event.id)
            for pair_bond in diagramData.pdp.pair_bonds:
                if pair_bond.id is not None and pair_bond.id < 0:
                    newIds.append(pair_bond.id)

            committedEdits = [
                p
                for p in diagramData.pdp.people
                if p.id is not None and p.id > 0 and not is_parents_edit(p)
            ]
            deleteIds = list(diagramData.pdp.delete or [])

            if not newIds and not committedEdits and not deleteIds:
                self._postCommitPdp([], True)
                return

            _log.info(
                f"Accepting all PDP items: new={newIds}, edits={[p.id for p in committedEdits]}, deletes={deleteIds}"
            )

            newItems = {"people": [], "events": [], "pair_bonds": [], "emotions": []}
            editFields: dict[int, dict] = {}
            drained = {}

            def applyChange(diagramData: DiagramData):
                if not diagramData.pdp:
                    _log.warning("No PDP data available")
                    return diagramData
                if self.scene is not None:
                    diagramData.lastItemId = max(
                        diagramData.lastItemId, self.scene.lastItemId()
                    )

                if newIds:
                    prevPeopleIds = {p["id"] for p in diagramData.people}
                    prevEventIds = {e["id"] for e in diagramData.events}
                    prevPairBondIds = {pb["id"] for pb in diagramData.pair_bonds}
                    diagramData.commit_pdp_items(newIds)
                    newItems["people"] = [
                        p for p in diagramData.people if p["id"] not in prevPeopleIds
                    ]
                    newItems["events"] = [
                        e for e in diagramData.events if e["id"] not in prevEventIds
                    ]
                    newItems["pair_bonds"] = [
                        pb
                        for pb in diagramData.pair_bonds
                        if pb["id"] not in prevPairBondIds
                    ]

                for pdp_person in committedEdits:
                    if pdp_person.name is not None:
                        editFields.setdefault(pdp_person.id, {})[
                            "name"
                        ] = pdp_person.name
                    if pdp_person.gender is not None:
                        editFields.setdefault(pdp_person.id, {})[
                            "gender"
                        ] = pdp_person.gender
                    diagramData.accept_committed_edit(pdp_person.id)

                for del_id in deleteIds:
                    diagramData.accept_committed_delete(del_id)

                drained["v"] = self._pdpDrained(diagramData)
                return diagramData

            success = self._diagram.save(
                self.session.server(), applyChange, lambda d: True, useJson=True
            )

            if success:
                self._addCommittedItemsToScene(newItems)
                if self.scene is not None:
                    for person_id, fields in editFields.items():
                        person = self.scene.find(id=person_id)
                        if person is not None:
                            if "name" in fields:
                                person.setName(fields["name"])
                            if "gender" in fields:
                                person.setGender(fields["gender"])
                    for del_id in deleteIds:
                        person = self.scene.find(id=del_id)
                        if person is not None:
                            self.scene.removeItem(person)
                self.pdpChanged.emit()
                self.committed.emit()
                allIds = newIds + [p.id for p in committedEdits] + deleteIds
                self._postCommitPdp(allIds, drained.get("v", True))
            else:
                _log.warning("Failed to accept all PDP items after retries")

        self._saveGuard(_do)

    @pyqtSlot(int, str, "QVariant")
    def updatePDPItem(self, id: int, field: str, value):
        if not self._diagram:
            return

        def _do():
            _log.info(f"Updating PDP item {id}: {field} = {value}")

            def applyChange(diagramData: DiagramData):
                if not diagramData.pdp:
                    return diagramData

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

            success = self._diagram.save(
                self.session.server(), applyChange, lambda d: True, useJson=True
            )

            if success:
                self.pdpChanged.emit()
            else:
                _log.warning(f"Failed to update PDP item {id} after retries")

        self._saveGuard(_do)

    ## Clear Diagram Data

    @pyqtSlot(bool)
    def clearDiagramData(self, clearPeople: bool):
        if not self._diagram:
            return

        def _do():
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

            def applyChange(diagramData: DiagramData):
                diagramData.events = []
                diagramData.pdp = None
                if clearPeople:
                    diagramData.people = [
                        p for p in diagramData.people if p.get("id") in (1, 2)
                    ]
                    diagramData.pair_bonds = []
                    diagramData.emotions = []
                return diagramData

            success = self._diagram.save(
                self.session.server(), applyChange, lambda d: True, useJson=True
            )

            if success:
                self.pdpChanged.emit()
                _log.info("Diagram data cleared successfully")
            else:
                _log.warning("Failed to clear diagram data")

        self._saveGuard(_do)

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
                # Use the optimistic-locking save loop so a concurrent
                # Pro/Personal save during the import doesn't get clobbered
                # by a blind setDiagramData. The applyChange overwrites
                # only the pdp field; everything else passes through from
                # the server's current state.
                # Wrapped in the save guard so it serializes against any
                # in-flight saveDiagram (Personal auto-save during import).
                # Plan: doc/plans/2026-05-01--mvp-merge-fix/README.md
                imported_pdp = from_dict(PDP, data["pdp"])

                def _do():
                    def applyChange(diagramData: DiagramData):
                        diagramData.pdp = imported_pdp
                        return diagramData

                    diagram.save(
                        self.session.server(), applyChange, lambda d: True, useJson=True
                    )

                self._saveGuard(_do)
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

    @pyqtSlot()
    def extractFull(self):
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
        self._discussion.markExtracted()
        self.extractStarted.emit()

        def onSuccess(data):
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

                def _do():
                    def applyChange(diagramData: DiagramData):
                        diagramData.pdp = rebuilt_pdp
                        return diagramData

                    diagram.save(
                        self.session.server(),
                        applyChange,
                        lambda d: True,
                        useJson=True,
                    )

                self._saveGuard(_do)
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
