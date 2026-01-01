import base64
import logging
import pickle
from typing import Callable

from btcopilot.schema import EventKind, DiagramData, PDP, asdict, from_dict
from pkdiagram.personal.commands import HandlePDPItem, PDPAction
from _pkdiagram import CUtil
from pkdiagram import pepper
from pkdiagram.app import AppConfig
from pkdiagram.pyqt import (
    QObject,
    QApplication,
    QQmlEngine,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
    QNetworkReply,
    QNetworkRequest,
    QQuickItem,
    QUrl,
    QMessageBox,
    QInputDialog,
    QUndoStack,
    QVariant,
)
from pkdiagram.app import Session, Analytics
from pkdiagram.personal.models import Discussion
from pkdiagram.server_types import Diagram
from pkdiagram.scene import Scene, Person, Event, Marriage, Emotion
from pkdiagram.models import SceneModel, PeopleModel
from pkdiagram.views import EventForm
from pkdiagram.personal.sarfgraphmodel import SARFGraphModel
from pkdiagram.personal.shakedetector import ShakeDetector

_log = logging.getLogger(__name__)


class PersonalAppController(QObject):
    requestSent = pyqtSignal(str)
    responseReceived = pyqtSignal(str, dict, arguments=["statement", "pdp"])
    serverError = pyqtSignal(str)
    serverDown = pyqtSignal()

    discussionsChanged = pyqtSignal()
    pdpChanged = pyqtSignal()
    diagramChanged = pyqtSignal()
    diagramsChanged = pyqtSignal()
    statementsChanged = pyqtSignal()
    eventFormDoneEditing = pyqtSignal()

    journalImportCompleted = pyqtSignal(QVariant, arguments=["summary"])
    journalImportFailed = pyqtSignal(str, arguments=["error"])

    def __init__(self, undoStack=None, parent=None):
        super().__init__(parent)

        self.app = QApplication.instance()
        self._diagram: Diagram | None = None
        self._diagrams: list[dict] = []
        self._discussions = []
        self._currentDiscussion: Discussion | None = None
        self._pdp: dict | None = None
        self._rootObject = None
        self._engine: QQmlEngine | None = None
        self.scene = None
        self._undoStack = undoStack if undoStack else QUndoStack(self)

        self.util = self.app.qmlUtil()  # should be local, not global

        self.analytics = Analytics(datadog_api_key=pepper.DATADOG_API_KEY)
        self.session = Session(self.analytics)
        self.session.changed.connect(self.onSessionChanged)

        self.appConfig = AppConfig(self, prefsName="personal.alaskafamilysystems.com")
        self.sceneModel = SceneModel(self)
        self.sceneModel.session = self.session
        self.peopleModel = PeopleModel(self)
        self.sarfGraphModel = SARFGraphModel(self)
        self.pdpChanged.connect(self.sarfGraphModel.refresh)
        self.eventForm = None  # EventForm (from PersonalContainer drawer)
        self._pendingScene: Scene | None = None
        self.shakeDetector = ShakeDetector(self)
        self.shakeDetector.shakeDetected.connect(self.undo)

    def init(self, engine: QQmlEngine):
        engine.rootContext().setContextProperty("CUtil", CUtil.instance())
        engine.rootContext().setContextProperty("util", self.util)
        engine.rootContext().setContextProperty("session", self.session)
        engine.rootContext().setContextProperty("personalApp", self)
        engine.rootContext().setContextProperty("sceneModel", self.sceneModel)
        engine.rootContext().setContextProperty("peopleModel", self.peopleModel)
        engine.rootContext().setContextProperty("sarfGraphModel", self.sarfGraphModel)
        engine.objectCreated[QObject, QUrl].connect(self.onQmlObjectCreated)
        self._engine = engine
        self.analytics.init()
        self.appConfig.init()
        self.session.setQmlEngine(engine)
        lastSessionData = self.appConfig.get("lastSessionData", pickled=True)
        if lastSessionData and not self.appConfig.wasTamperedWith:
            self.session.init(sessionData=lastSessionData)
        else:
            self.session.init()

    def deinit(self):
        self.shakeDetector.stop()
        self.pdpChanged.disconnect(self.sarfGraphModel.refresh)
        self.sarfGraphModel.deinit()
        self.analytics.init()
        self.session.deinit()
        if self.eventForm:
            self.eventForm.deinit()
        self._engine = None

    def onQmlObjectCreated(self, rootObject: QQuickItem, url: QUrl):
        if self._pendingScene:
            self.setScene(self._pendingScene)
            self._pendingScene = None
        elif self.eventForm and self.scene:
            self.eventForm.setScene(self.scene)

    def onEventFormSaved(self):
        self.saveDiagram()

    @pyqtSlot(QQuickItem)
    def initEventForm(self, eventFormItem: QQuickItem):
        if self.eventForm is None:
            self.eventForm = EventForm(eventFormItem, self)
            self.eventForm.saved.connect(self.onEventFormSaved)
            self.eventForm.doneEditing.connect(self.eventFormDoneEditing)
            if self.scene:
                self.eventForm.setScene(self.scene)

    @pyqtSlot(int)
    def editEvent(self, eventId: int):
        if not self.eventForm or not self.scene:
            return
        event = self.scene.find(id=eventId)
        if event:
            self.eventForm.editEvents([event])

    @pyqtSlot(int)
    def deleteEvent(self, eventId: int):
        if not self.scene:
            return
        event = self.scene.find(id=eventId)
        if event:
            self.scene.removeItem(event, undo=True)
            self.saveDiagram()

    @pyqtSlot()
    def undo(self):
        if self.scene:
            self.scene.undo()
            self.saveDiagram()

    def saveDiagram(self):
        if not self._diagram or not self.scene:
            return False

        def applyChange(diagramData: DiagramData):
            sceneDiagramData = self.scene.diagramData()
            diagramData.people = sceneDiagramData.people
            diagramData.events = sceneDiagramData.events
            diagramData.pair_bonds = sceneDiagramData.pair_bonds
            diagramData.emotions = sceneDiagramData.emotions
            diagramData.multipleBirths = sceneDiagramData.multipleBirths
            diagramData.layers = sceneDiagramData.layers
            diagramData.layerItems = sceneDiagramData.layerItems
            diagramData.items = sceneDiagramData.items
            diagramData.pruned = sceneDiagramData.pruned
            diagramData.version = sceneDiagramData.version
            diagramData.versionCompat = sceneDiagramData.versionCompat
            diagramData.name = sceneDiagramData.name
            return diagramData

        def stillValidAfterRefresh(diagramData: DiagramData):
            return True

        return self._diagram.save(
            self.session.server(), applyChange, stillValidAfterRefresh, useJson=True
        )

    def setScene(self, scene: Scene):
        self.scene = scene
        self.peopleModel.scene = scene
        self.sceneModel.scene = scene
        self.sarfGraphModel.scene = scene
        if self.eventForm:
            self.eventForm.setScene(scene)

    def exec(self, mw):
        self.app.exec()

    def onError(self, reply: QNetworkReply):
        if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 0:
            self.serverDown.emit()
        else:
            self.serverError.emit(reply.errorString())

    def onSessionChanged(self, oldFeatures, newFeatures):
        """Called on login, logout, invalidated token."""

        if self.session.isLoggedIn():
            self.appConfig.set("lastSessionData", self.session.data(), pickled=True)
            self.shakeDetector.start()
        else:
            self.appConfig.delete("lastSessionData")
            self.shakeDetector.stop()
        self.appConfig.write()

        if not self.session.user:
            self._diagram = None
            self._diagrams = []
            self._discussions = []
            self._pdp = {}
            self._currentDiscussion = None
        else:
            self._refreshDiagrams()
            self._refreshDiagram()
        self.discussionsChanged.emit()
        self.statementsChanged.emit()
        self.pdpChanged.emit()
        self.diagramChanged.emit()
        self.diagramsChanged.emit()

    # Diagram

    @pyqtProperty("QVariantList", notify=diagramsChanged)
    def diagrams(self):
        return list(self._diagrams)

    def _refreshDiagrams(self):
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
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    @pyqtProperty("QVariantMap", notify=diagramChanged)
    def diagram(self):
        if self._diagram is not None:
            return self._diagram.__dict__
        return {}

    def _refreshDiagram(self):
        if not self.session.user:
            return

        def onSuccess(data):
            rawData = base64.b64decode(data["data"])
            data["data"] = rawData
            self._diagram = Diagram(**data)
            self._discussions = [Discussion.create(x) for x in data["discussions"]]
            self.discussionsChanged.emit()
            self.statementsChanged.emit()
            self.pdpChanged.emit()
            self.diagramChanged.emit()
            _log.info(
                f"Loaded personal diagram: {self._diagram.id}, version: {self._diagram.version}"
            )
            assert self.scene is None
            sceneData = pickle.loads(rawData)
            scene = Scene()
            scene.read(sceneData)
            if self.eventForm:
                self.setScene(scene)
            else:
                self._pendingScene = scene

        reply = self.session.server().nonBlockingRequest(
            "GET",
            f"/personal/diagrams/{self.session.user.free_diagram_id}",
            data={},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    @pyqtSlot(int)
    def loadDiagram(self, diagramId: int):
        if not self.session.user:
            return

        def onSuccess(data):
            rawData = base64.b64decode(data["data"])
            data["data"] = rawData
            self._diagram = Diagram(**data)
            self._discussions = [Discussion.create(x) for x in data["discussions"]]
            self._currentDiscussion = None
            self.discussionsChanged.emit()
            self.statementsChanged.emit()
            self.pdpChanged.emit()
            self.diagramChanged.emit()
            _log.info(
                f"Loaded diagram: {self._diagram.id}, version: {self._diagram.version}"
            )
            sceneData = pickle.loads(rawData)
            scene = Scene()
            try:
                scene.read(sceneData)
            except (pickle.UnpicklingError, KeyError, ValueError, TypeError):
                _log.exception(f"Failed to load diagram {diagramId}")
                QMessageBox.critical(
                    None,
                    "Error",
                    "The diagram file is corrupted and cannot be opened.",
                )
            else:
                self.setScene(scene)

        reply = self.session.server().nonBlockingRequest(
            "GET",
            f"/personal/diagrams/{diagramId}",
            data={},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
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
            self._refreshDiagrams()
            if diagramId:
                self.loadDiagram(diagramId)

        reply = self.session.server().nonBlockingRequest(
            "POST",
            "/personal/diagrams/",
            data={"name": name.strip()},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    # Discussions

    @pyqtProperty("QVariantList", notify=discussionsChanged)
    def discussions(self):
        return list(self._discussions)

    @pyqtProperty(int, notify=statementsChanged)
    def currentDiscussionId(self):
        return self._currentDiscussion.id if self._currentDiscussion else -1

    @pyqtSlot()
    def createDiscussion(self):
        self._createDiscussion()

    def _createDiscussion(self, callback: Callable | None = None):
        if not self._diagram:
            _log.warning("Cannot create discussion without diagram")
            return

        def onSuccess(data):
            discussion = Discussion.create(data)
            self._discussions.append(discussion)
            self.discussionsChanged.emit()
            self._setCurrentDiscussion(discussion.id)
            if callback:
                callback()

        reply = self.session.server().nonBlockingRequest(
            "POST",
            "/personal/discussions/",
            data={"diagram_id": self._diagram.id},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    def _setCurrentDiscussion(self, discussion_id: int):
        self._currentDiscussion = next(
            x for x in self._discussions if x.id == discussion_id
        )
        self.statementsChanged.emit()
        self.pdpChanged.emit()

    @pyqtSlot(int)
    def setCurrentDiscussion(self, discussion_id: int):
        self._setCurrentDiscussion(discussion_id)

    ## Statements

    @pyqtProperty("QVariantList", notify=statementsChanged)
    def statements(self):
        if self._currentDiscussion:
            return list(self._currentDiscussion.statements())
        else:
            return []

    @pyqtSlot(str)
    def sendStatement(self, statement: str):
        self._sendStatement(statement)

    def _sendStatement(self, statement: str):
        def _doSendStatement():
            if not self._currentDiscussion:
                QMessageBox.information(
                    self, "Cannot send statement without current discussion"
                )
                return

            def onSuccess(data):
                # Update local diagram with PDP from response
                if data.get("pdp") and self._diagram:
                    diagramData = self._diagram.getDiagramData()
                    diagramData.pdp = from_dict(PDP, data["pdp"])
                    self._diagram.setDiagramData(diagramData)
                self.responseReceived.emit(data["statement"], data["pdp"])
                self.pdpChanged.emit()

            args = {
                "statement": statement,
            }
            reply = self.session.server().nonBlockingRequest(
                "POST",
                f"/personal/discussions/{self._currentDiscussion.id}/statements",
                data=args,
                error=lambda: self.onError(reply),
                success=onSuccess,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                from_root=True,
            )
            self.session.track(f"personal.Engine.sendStatement: {statement}")
            self.requestSent.emit(statement)

        if self._currentDiscussion:
            _doSendStatement()
        else:
            self._createDiscussion(callback=_doSendStatement)

    ## PDP

    def _pdpItem(self, id: int) -> Person | Event | None:
        if self._diagram:
            diagramData = self._diagram.getDiagramData()
            if diagramData.pdp:
                for item in diagramData.pdp.people + diagramData.pdp.events:
                    if item.id == id:
                        return item
        return None

    @pyqtSlot(int, result=bool)
    def acceptPDPItem(self, id: int, undo=True):
        prev_data = self._diagram.getDiagramData() if undo else None

        success = self._doAcceptPDPItem(id)

        if not success:
            return False

        if undo:
            cmd = HandlePDPItem(PDPAction.Accept, self, id, prev_data)
            self._undoStack.push(cmd)

        return True

    @pyqtSlot(int, result=bool)
    def rejectPDPItem(self, id: int, undo=True):
        prev_data = self._diagram.getDiagramData() if undo else None

        success = self._doRejectPDPItem(id)

        if not success:
            return False

        if undo:
            cmd = HandlePDPItem(PDPAction.Reject, self, id, prev_data)
            self._undoStack.push(cmd)

        return True

    def _doAcceptPDPItem(self, id: int) -> bool:
        _log.info(f"Accepting PDP item with id: {id}")

        committedItems = {"people": [], "events": [], "pair_bonds": [], "emotions": []}

        def applyChange(diagramData: DiagramData):
            _log.info(f"Applying accept PDP item change for id: {id}")
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

            return diagramData

        def stillValidAfterRefresh(diagramData: DiagramData):
            return True

        success = self._diagram.save(
            self.session.server(), applyChange, stillValidAfterRefresh, useJson=True
        )

        if success:
            self._addCommittedItemsToScene(committedItems)
            self.pdpChanged.emit()
        else:
            _log.warning(f"Failed to accept PDP item after retries")

        return success

    def _addCommittedItemsToScene(self, committedItems: dict):
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
            item = Event(kind=EventKind.Shift, person=None)
            item.id = chunk["id"]
            localMap[item.id] = item
            itemChunks.append((item, chunk))

        # Phase 2: Read all chunks before adding to scene
        def byId(id):
            return localMap.get(id) or self.scene.itemRegistry.get(id)

        for item, chunk in itemChunks:
            item.read(chunk, byId)

        # Phase 3: Add all items to scene (triggers side effects)
        for item, chunk in itemChunks:
            self.scene.addItem(item)

    def _doRejectPDPItem(self, id: int) -> bool:
        _log.info(f"Rejecting PDP item with id: {id}")

        def applyChange(diagramData: DiagramData):
            if not diagramData.pdp:
                _log.warning("No PDP data available")
                return diagramData

            idsToRemove = {id}

            for event in diagramData.pdp.events:
                if (
                    event.person == id
                    or event.spouse == id
                    or event.child == id
                    or id in event.relationshipTargets
                    or id in event.relationshipTriangles
                ):
                    idsToRemove.add(event.id)

            for pair_bond in diagramData.pdp.pair_bonds:
                if pair_bond.person_a == id or pair_bond.person_b == id:
                    idsToRemove.add(pair_bond.id)

            for person in diagramData.pdp.people:
                if person.parents == id:
                    idsToRemove.add(person.id)

            diagramData.pdp.people = [
                p for p in diagramData.pdp.people if p.id not in idsToRemove
            ]
            diagramData.pdp.events = [
                e for e in diagramData.pdp.events if e.id not in idsToRemove
            ]
            diagramData.pdp.pair_bonds = [
                pb for pb in diagramData.pdp.pair_bonds if pb.id not in idsToRemove
            ]

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

    @pyqtSlot()
    def acceptAllPDPItems(self):
        if not self._diagram:
            return

        diagramData = self._diagram.getDiagramData()
        if not diagramData.pdp:
            return

        allIds = []
        for person in diagramData.pdp.people:
            if person.id is not None:
                allIds.append(person.id)
        for event in diagramData.pdp.events:
            allIds.append(event.id)
        for pair_bond in diagramData.pdp.pair_bonds:
            if pair_bond.id is not None:
                allIds.append(pair_bond.id)

        if not allIds:
            return

        _log.info(f"Accepting all PDP items: {allIds}")

        def applyChange(diagramData: DiagramData):
            diagramData.commit_pdp_items(allIds)
            return diagramData

        def stillValidAfterRefresh(diagramData: DiagramData):
            return True

        success = self._diagram.save(
            self.session.server(), applyChange, stillValidAfterRefresh, useJson=True
        )

        if success:
            self.pdpChanged.emit()
        else:
            _log.warning("Failed to accept all PDP items after retries")

    @pyqtSlot(int, str, "QVariant")
    def updatePDPItem(self, id: int, field: str, value):
        if not self._diagram:
            return

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

        def stillValidAfterRefresh(diagramData: DiagramData):
            return True

        success = self._diagram.save(
            self.session.server(), applyChange, stillValidAfterRefresh, useJson=True
        )

        if success:
            self.pdpChanged.emit()
        else:
            _log.warning(f"Failed to update PDP item {id} after retries")

    ## Journal Import

    @pyqtSlot(str)
    def importJournalNotes(self, text: str):
        if not self._diagram:
            self.journalImportFailed.emit("No diagram loaded")
            return

        def onSuccess(data):
            if data.get("pdp") and self._diagram:
                diagramData = self._diagram.getDiagramData()
                diagramData.pdp = from_dict(PDP, data["pdp"])
                self._diagram.setDiagramData(diagramData)
            self.pdpChanged.emit()
            self.journalImportCompleted.emit(data.get("summary", {}))

        def onError():
            self.journalImportFailed.emit(reply.errorString())

        reply = self.session.server().nonBlockingRequest(
            "POST",
            f"/personal/diagrams/{self._diagram.id}/import-text",
            data={"text": text},
            error=onError,
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )
