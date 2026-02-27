import base64
import logging
import pickle
from typing import Callable

from btcopilot.schema import (
    EventKind,
    DiagramData,
    PDP,
    asdict,
    from_dict,
    VariableShift,
    RelationshipKind,
    DateCertainty,
)
from PyQt5.QtTextToSpeech import QTextToSpeech, QVoice
from pkdiagram.personal.commands import HandlePDPItem, PDPAction
from pkdiagram.personal.settings import Settings
from _pkdiagram import CUtil
from pkdiagram import pepper, util
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
from PyQt5.QtCore import QLocale
from pkdiagram.app import Session, Analytics
from pkdiagram.personal.models import Discussion
from pkdiagram.server_types import Diagram
from pkdiagram.scene import Scene, Person, Event, Marriage, Emotion
from pkdiagram.models import SceneModel, PeopleModel
from pkdiagram.views import EventForm
from pkdiagram.personal.sarfgraphmodel import SARFGraphModel
from pkdiagram.personal.shakedetector import ShakeDetector
from pkdiagram.personal.clustermodel import ClusterModel

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

    journalImportStarted = pyqtSignal()
    journalImportCompleted = pyqtSignal(QVariant, arguments=["summary"])
    journalImportFailed = pyqtSignal(str, arguments=["error"])

    ttsPlayingIndexChanged = pyqtSignal()
    ttsFinished = pyqtSignal()
    ttsVoiceChanged = pyqtSignal()

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
        self.clusterModel = ClusterModel(self.session, self)
        self.pdpChanged.connect(self.sarfGraphModel.refresh)
        self.diagramChanged.connect(self._onDiagramChanged)
        self.clusterModel.clustersDetected.connect(self._onClustersDetected)
        self.eventForm = None  # EventForm (from PersonalContainer drawer)
        self._pendingScene: Scene | None = None
        self.shakeDetector = ShakeDetector(self)
        self.shakeDetector.shakeDetected.connect(self.undo)
        self._saving = False
        self._saveQueue = []
        self._settings = Settings(self.app.prefs(), self)
        self._tts = QTextToSpeech(self)
        self._ttsPlayingIndex = -1
        self._tts.stateChanged.connect(self._onTtsStateChanged)
        self._initTtsVoice()

    def _initTtsVoice(self):
        saved = self._settings.value("ttsVoiceName")
        if saved:
            voice, locale = self._findVoice(saved)
            if voice:
                self._tts.setLocale(locale)
                self._tts.setVoice(voice)
                _log.debug(f"TTS voice restored: {voice.name()}")
                return
        for voice in self._tts.availableVoices():
            if voice.gender() == QVoice.Female:
                self._tts.setVoice(voice)
                _log.debug(f"TTS voice: {voice.name()}")
                return
        _log.debug("No female voice found, using default")

    def _findVoice(self, name):
        for locale in self._tts.availableLocales():
            if locale.language() != QLocale.English:
                continue
            self._tts.setLocale(locale)
            for voice in self._tts.availableVoices():
                if voice.name() == name:
                    return voice, locale
        return None, None

    def _collectVoices(self):
        origLocale = self._tts.locale()
        origVoice = self._tts.voice()
        voices = []
        seen = set()
        for locale in self._tts.availableLocales():
            if locale.language() != QLocale.English:
                continue
            self._tts.setLocale(locale)
            country = QLocale.countryToString(locale.country())
            localeLabel = f"English ({country})"
            for voice in self._tts.availableVoices():
                if voice.name() not in seen:
                    seen.add(voice.name())
                    voices.append({"name": voice.name(), "locale": localeLabel})
        self._tts.setLocale(origLocale)
        if origVoice.name():
            self._tts.setVoice(origVoice)
        return voices

    def _onTtsStateChanged(self, state):
        if state in (QTextToSpeech.Ready, QTextToSpeech.BackendError):
            wasPlaying = self._ttsPlayingIndex >= 0
            self._ttsPlayingIndex = -1
            self.ttsPlayingIndexChanged.emit()
            if wasPlaying and state == QTextToSpeech.Ready:
                self.ttsFinished.emit()

    def init(self, engine: QQmlEngine):
        engine.rootContext().setContextProperty("CUtil", CUtil.instance())
        engine.rootContext().setContextProperty("util", self.util)
        engine.rootContext().setContextProperty("session", self.session)
        engine.rootContext().setContextProperty("personalApp", self)
        engine.rootContext().setContextProperty("sceneModel", self.sceneModel)
        engine.rootContext().setContextProperty("peopleModel", self.peopleModel)
        engine.rootContext().setContextProperty("sarfGraphModel", self.sarfGraphModel)
        engine.rootContext().setContextProperty("clusterModel", self.clusterModel)
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
        self.diagramChanged.disconnect(self._onDiagramChanged)
        self.clusterModel.clustersDetected.disconnect(self._onClustersDetected)
        self.sarfGraphModel.deinit()
        self.clusterModel.deinit()
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

    def _withSaveGuard(self, fn):
        if self._saving:
            self._saveQueue.append(fn)
            return None
        self._saving = True
        try:
            return fn()
        finally:
            self._saving = False
            if self._saveQueue:
                self._withSaveGuard(self._saveQueue.pop(0))

    def saveDiagram(self):
        if not self._diagram or not self.scene:
            return

        def _do():
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
                diagramData.lastItemId = sceneDiagramData.lastItemId
                diagramData.clusters = self.clusterModel.clusters
                diagramData.clusterCacheKey = self.clusterModel.cacheKey
                return diagramData

            self._diagram.save(
                self.session.server(), applyChange, lambda d: True, useJson=True
            )

        self._withSaveGuard(_do)

    def setScene(self, scene: Scene):
        self.scene = scene
        self.peopleModel.scene = scene
        self.sceneModel.scene = scene
        self.sarfGraphModel.scene = scene
        self.clusterModel.scene = scene
        # Load persisted clusters AFTER scene is set (scene setter clears clusters)
        if self._diagram:
            diagramData = self._diagram.getDiagramData()
            if diagramData.clusters:
                self.clusterModel.setClustersData(
                    diagramData.clusters, diagramData.clusterCacheKey
                )
        if self.eventForm:
            self.eventForm.setScene(scene)
        # Re-emit pdpChanged so committedPeople gets populated from the scene
        self.pdpChanged.emit()

    def exec(self, mw):
        self.app.exec()

    def onError(self, reply: QNetworkReply):
        if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 0:
            self.serverDown.emit()
        else:
            self.serverError.emit(reply.errorString())

    def _onDiagramChanged(self):
        if self._diagram:
            self.clusterModel.diagramId = self._diagram.id
        else:
            self.clusterModel.diagramId = None

    def _onClustersDetected(self):
        self.saveDiagram()

    def onSessionChanged(self, oldFeatures, newFeatures):
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

    @pyqtProperty(QObject, constant=True)
    def settings(self):
        return self._settings

    # TTS

    @pyqtProperty(int, notify=ttsPlayingIndexChanged)
    def ttsPlayingIndex(self):
        return self._ttsPlayingIndex

    @pyqtSlot(str, int)
    def sayAtIndex(self, text, index):
        self._tts.stop()
        self._ttsPlayingIndex = index
        self.ttsPlayingIndexChanged.emit()
        self._tts.say(text)

    @pyqtSlot()
    def stopSpeaking(self):
        self._tts.stop()

    @pyqtProperty("QVariantList", constant=True)
    def ttsVoices(self):
        return self._collectVoices()

    @pyqtProperty(str, notify=ttsVoiceChanged)
    def ttsVoiceName(self):
        return self._tts.voice().name()

    @pyqtSlot(str)
    def setTtsVoice(self, name):
        voice, locale = self._findVoice(name)
        if voice:
            self._tts.setLocale(locale)
            self._tts.setVoice(voice)
            self._settings.setValue("ttsVoiceName", name)
            self.ttsVoiceChanged.emit()
            _log.debug(f"TTS voice set to: {name}")

    @pyqtSlot(str)
    def previewVoice(self, name):
        self.setTtsVoice(name)
        self._tts.say("Hello, this is a preview of my voice.")

    @pyqtSlot()
    def openSystemVoiceSettings(self):
        import subprocess

        if util.IS_IOS:
            CUtil.openNativeUrl("App-Prefs:root=ACCESSIBILITY&path=SPEECH")
        else:
            subprocess.Popen(
                [
                    "open",
                    "x-apple.systempreferences:com.apple.preference.universalaccess?SpokenContent",
                ]
            )

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
        if id >= 0:
            _log.error(f"acceptPDPItem called with non-PDP id {id}, ignoring")
            return False

        def _do():
            prev_data = self._diagram.getDiagramData() if undo else None
            success = self._doAcceptPDPItem(id)
            if success and undo:
                cmd = HandlePDPItem(PDPAction.Accept, self, id, prev_data)
                self._undoStack.push(cmd)
            return success

        return self._withSaveGuard(_do)

    @pyqtSlot(int, result=bool)
    def rejectPDPItem(self, id: int, undo=True):
        if id >= 0:
            _log.error(f"rejectPDPItem called with non-PDP id {id}, ignoring")
            return False

        def _do():
            prev_data = self._diagram.getDiagramData() if undo else None
            success = self._doRejectPDPItem(id)
            if success and undo:
                cmd = HandlePDPItem(PDPAction.Reject, self, id, prev_data)
                self._undoStack.push(cmd)
            return success

        return self._withSaveGuard(_do)

    def _doAcceptPDPItem(self, id: int) -> bool:
        _log.info(f"Accepting PDP item with id: {id}")

        committedItems = {"people": [], "events": [], "pair_bonds": [], "emotions": []}

        def applyChange(diagramData: DiagramData):
            _log.info(f"Applying accept PDP item change for id: {id}")
            # Scene's lastItemId includes internal layers; server's may not
            diagramData.lastItemId = max(diagramData.lastItemId, self.scene.lastItemId())
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
            self.clusterModel.detect()
        else:
            _log.warning(f"Failed to accept PDP item after retries")

        return success

    def _addCommittedItemsToScene(self, committedItems: dict):
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
    def acceptAllPDPItems(self):
        if not self._diagram:
            return

        def _do():
            diagramData = self._diagram.getDiagramData()
            if not diagramData.pdp:
                return

            allIds = []
            for person in diagramData.pdp.people:
                if person.id is not None and person.id < 0:
                    allIds.append(person.id)
            for event in diagramData.pdp.events:
                if event.id < 0:
                    allIds.append(event.id)
            for pair_bond in diagramData.pdp.pair_bonds:
                if pair_bond.id is not None and pair_bond.id < 0:
                    allIds.append(pair_bond.id)

            if not allIds:
                return

            _log.info(f"Accepting all PDP items: {allIds}")

            committedItems = {
                "people": [],
                "events": [],
                "pair_bonds": [],
                "emotions": [],
            }

            def applyChange(diagramData: DiagramData):
                # Scene's lastItemId includes internal layers; server's may not
                diagramData.lastItemId = max(diagramData.lastItemId, self.scene.lastItemId())
                prevPeopleIds = {p["id"] for p in diagramData.people}
                prevEventIds = {e["id"] for e in diagramData.events}
                prevPairBondIds = {pb["id"] for pb in diagramData.pair_bonds}

                diagramData.commit_pdp_items(allIds)

                committedItems["people"] = [
                    p for p in diagramData.people if p["id"] not in prevPeopleIds
                ]
                committedItems["events"] = [
                    e for e in diagramData.events if e["id"] not in prevEventIds
                ]
                committedItems["pair_bonds"] = [
                    pb
                    for pb in diagramData.pair_bonds
                    if pb["id"] not in prevPairBondIds
                ]

                return diagramData

            success = self._diagram.save(
                self.session.server(), applyChange, lambda d: True, useJson=True
            )

            if success:
                self._addCommittedItemsToScene(committedItems)
                self.pdpChanged.emit()
                self.clusterModel.detect()
            else:
                _log.warning("Failed to accept all PDP items after retries")

        self._withSaveGuard(_do)

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

        self._withSaveGuard(_do)

    ## Clear Diagram Data

    @pyqtSlot(bool)
    def clearDiagramData(self, clearPeople: bool):
        if not self._diagram or not self.scene:
            return

        def _do():
            _log.info(f"Clearing diagram data (clearPeople={clearPeople})")

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

        self._withSaveGuard(_do)

    ## Journal Import

    @pyqtSlot(str)
    def importJournalNotes(self, text: str):
        if not self._diagram:
            self.journalImportFailed.emit("No diagram loaded")
            return

        self.journalImportStarted.emit()

        def onSuccess(data):
            if data.get("pdp") and self._diagram:
                diagramData = self._diagram.getDiagramData()
                diagramData.pdp = from_dict(PDP, data["pdp"])
                self._diagram.setDiagramData(diagramData)
            self.pdpChanged.emit()
            self.journalImportCompleted.emit(data.get("summary", {}))
            self.clusterModel.detect()

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
