import base64
import logging
import pickle
from typing import Callable

from btcopilot.schema import EventKind, DiagramData, asdict
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
    QUndoStack,
)
from pkdiagram.app import Session, Analytics
from pkdiagram.personal.models import Discussion
from pkdiagram.server_types import Diagram
from pkdiagram.scene import Scene, Person, Event, Marriage, Emotion
from pkdiagram.models import SceneModel, PeopleModel
from pkdiagram.views import EventForm
from pkdiagram.personal.sarfgraphmodel import SARFGraphModel

_log = logging.getLogger(__name__)


class PersonalAppController(QObject):
    requestSent = pyqtSignal(str)
    responseReceived = pyqtSignal(str, dict, arguments=["statement", "pdp"])
    serverError = pyqtSignal(str)
    serverDown = pyqtSignal()

    discussionsChanged = pyqtSignal()
    pdpChanged = pyqtSignal()
    diagramChanged = pyqtSignal()
    statementsChanged = pyqtSignal()

    def __init__(self, undoStack=None, parent=None):
        super().__init__(parent)

        self.app = QApplication.instance()
        self._diagram: Diagram | None = None
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
        self.eventForm = None
        self._pendingScene: Scene | None = None

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
        self.pdpChanged.disconnect(self.sarfGraphModel.refresh)
        self.sarfGraphModel.deinit()
        self.analytics.init()
        self.session.deinit()
        if self.eventForm:
            self.eventForm.deinit()
        self._engine = None

    def onQmlObjectCreated(self, rootObject: QQuickItem, url: QUrl):
        if not self.eventForm:
            self.eventForm = EventForm(
                rootObject.property("personalView")
                .property("discussView")
                .property("eventForm"),
                self,
            )
            self.eventForm.saved.connect(self.onEventFormSaved)
            if self._pendingScene:
                self.setScene(self._pendingScene)
                self._pendingScene = None
            else:
                self.eventForm.setScene(self.scene)

    def onEventFormSaved(self):
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
        """
        Stuff that happens once per app load on the first MainWindow.
        At this point the MainWindow is fully initialized with a session
        and ready for app-level verbs.
        """
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
        else:
            self.appConfig.delete("lastSessionData")
        self.appConfig.write()

        if not self.session.user:
            self._diagram = None
            self._discussions = []
            self._pdp = {}
            self._currentDiscussion = None
        else:
            self._refreshDiagram()
        self.discussionsChanged.emit()
        self.statementsChanged.emit()
        self.pdpChanged.emit()
        self.diagramChanged.emit()

    # Diagram

    @pyqtProperty("QVariantMap", notify=diagramChanged)
    def diagram(self):
        return self._diagram if self._diagram is not None else {}

    def _refreshDiagram(self):
        if not self.session.user:
            return

        def onSuccess(data):
            raw_data = base64.b64decode(data["data"])
            data["data"] = raw_data
            self._diagram = Diagram(**data)
            self._discussions = [Discussion.create(x) for x in data["discussions"]]
            self.discussionsChanged.emit()
            self.statementsChanged.emit()
            self.pdpChanged.emit()
            _log.info(
                f"Loaded personal diagram: {self._diagram.id}, version: {self._diagram.version}"
            )
            assert self.scene is None
            scene_data = pickle.loads(raw_data)
            scene = Scene()
            scene.read(scene_data)
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
        """
        Mockable because qml latches on to slots at init time.
        """

        def _doSendStatement():
            if not self._currentDiscussion:
                QMessageBox.information(
                    self, "Cannot send statement without current discussion"
                )
                return

            def onSuccess(data):
                self.responseReceived.emit(data["statement"], data["pdp"])

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
            prevEventsIds = {e["id"] for e in diagramData.events}
            prevPairBondsIds = {pb["id"] for pb in diagramData.pair_bonds}

            diagramData.commit_pdp_items([id])

            # Find newly committed items
            committedItems["people"] = [
                p for p in diagramData.people if p["id"] not in prevPeopleIds
            ]
            committedItems["events"] = [
                e for e in diagramData.events if e["id"] not in prevEventsIds
            ]
            committedItems["pair_bonds"] = [
                pb for pb in diagramData.pair_bonds if pb["id"] not in prevPairBondsIds
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

            ids_to_remove = {id}

            for event in diagramData.pdp.events:
                if (
                    event.person == id
                    or event.spouse == id
                    or event.child == id
                    or id in event.relationshipTargets
                    or id in event.relationshipTriangles
                ):
                    ids_to_remove.add(event.id)

            for pair_bond in diagramData.pdp.pair_bonds:
                if pair_bond.person_a == id or pair_bond.person_b == id:
                    ids_to_remove.add(pair_bond.id)

            for person in diagramData.pdp.people:
                if person.parents == id:
                    ids_to_remove.add(person.id)

            diagramData.pdp.people = [
                p for p in diagramData.pdp.people if p.id not in ids_to_remove
            ]
            diagramData.pdp.events = [
                e for e in diagramData.pdp.events if e.id not in ids_to_remove
            ]
            diagramData.pdp.pair_bonds = [
                pb for pb in diagramData.pdp.pair_bonds if pb.id not in ids_to_remove
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
                return asdict(diagramData.pdp)
        return {}

    @pyqtSlot()
    def acceptAllPDPItems(self):
        if not self._diagram:
            return

        diagramData = self._diagram.getDiagramData()
        if not diagramData.pdp:
            return

        all_ids = []
        for person in diagramData.pdp.people:
            if person.id is not None:
                all_ids.append(person.id)
        for event in diagramData.pdp.events:
            all_ids.append(event.id)
        for pair_bond in diagramData.pdp.pair_bonds:
            if pair_bond.id is not None:
                all_ids.append(pair_bond.id)

        if not all_ids:
            return

        _log.info(f"Accepting all PDP items: {all_ids}")

        def applyChange(diagramData: DiagramData):
            diagramData.commit_pdp_items(all_ids)
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
