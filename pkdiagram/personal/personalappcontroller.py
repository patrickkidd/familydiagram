import logging
import pickle

from btcopilot.schema import DiagramData, EventKind, asdict

from _pkdiagram import CUtil
from pkdiagram import pepper, util
from pkdiagram.app import AppConfig, Analytics, Session
from pkdiagram.models import SceneModel, PeopleModel
from pkdiagram.personal.audio import VoiceRecorder
from pkdiagram.personal.clustermodel import ClusterModel
from pkdiagram.personal.diagramloader import DiagramLoader
from pkdiagram.personal.discussioncontroller import DiscussionController
from pkdiagram.personal.pdpcontroller import PDPController
from pkdiagram.personal.sarfgraphmodel import SARFGraphModel
from pkdiagram.personal.saveguard import SaveGuard
from pkdiagram.personal.settings import Settings
from pkdiagram.personal.shakedetector import ShakeDetector
from pkdiagram.personal.tts import TextToSpeech
from pkdiagram.pyqt import (
    QObject,
    QApplication,
    QQmlEngine,
    QQuickItem,
    QUndoStack,
    QUrl,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)
from pkdiagram.scene import Event, Person, Scene
from pkdiagram.server_types import Diagram
from pkdiagram.views import EventForm

_log = logging.getLogger(__name__)


class PersonalAppController(QObject):
    """Composition root for the standalone Personal app: owns the session, the
    app-wide models and the loaded Diagram/Scene, and wires the discussion, PDP
    and diagram-loading components to them."""

    eventFormDoneEditing = pyqtSignal()
    userProfileChanged = pyqtSignal()

    def __init__(self, undoStack=None, parent=None):
        super().__init__(parent)

        self.app = QApplication.instance()
        self._diagram: Diagram | None = None
        self._engine: QQmlEngine | None = None
        self.scene = None
        self._undoStack = undoStack if undoStack else QUndoStack(self)
        self._saveGuard = SaveGuard()

        self.util = self.app.qmlUtil()  # should be local, not global

        self.analytics = Analytics(datadog_api_key=pepper.DATADOG_API_KEY)
        self.session = Session(self.analytics)
        self.session.changed.connect(self.onSessionChanged)

        self.appConfig = AppConfig(self, prefsName="personal.alaskafamilysystems.com")
        self._settings = Settings(self.app.prefs(), self)
        self.sceneModel = SceneModel(self)
        self.sceneModel.session = self.session
        self.peopleModel = PeopleModel(self)
        self.sarfGraphModel = SARFGraphModel(self)
        self.clusterModel = ClusterModel(self.session, self)

        self.discussion = DiscussionController(self.session, self._settings, self)
        self.pdpController = PDPController(
            self.session, self._saveGuard, self._undoStack, self
        )
        self.pdpController.setDiscussion(self.discussion)
        self.diagramLoader = DiagramLoader(self.session, self.appConfig, self)
        self.tts = TextToSpeech(self._settings, self)
        self.voice = VoiceRecorder(self.session, self)

        self.diagramLoader.diagramLoaded.connect(self._onDiagramLoaded)
        self.pdpController.pdpChanged.connect(self.sarfGraphModel.refresh)
        self.pdpController.committed.connect(self._onPDPCommitted)
        self.clusterModel.clustersDetected.connect(self._onClustersDetected)
        self.eventForm = None  # EventForm (from PersonalContainer drawer)
        self.shakeDetector = ShakeDetector(self)
        self.shakeDetector.shakeDetected.connect(self.undo)

    def contextProperties(self) -> dict:
        return {
            "CUtil": CUtil.instance(),
            "util": self.util,
            "session": self.session,
            "personalApp": self,
            "discussion": self.discussion,
            "pdpController": self.pdpController,
            "diagramLoader": self.diagramLoader,
            "tts": self.tts,
            "voice": self.voice,
            "sceneModel": self.sceneModel,
            "peopleModel": self.peopleModel,
            "sarfGraphModel": self.sarfGraphModel,
            "clusterModel": self.clusterModel,
        }

    def init(self, engine: QQmlEngine):
        for name, value in self.contextProperties().items():
            engine.rootContext().setContextProperty(name, value)
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
        self.diagramLoader.diagramLoaded.disconnect(self._onDiagramLoaded)
        self.pdpController.pdpChanged.disconnect(self.sarfGraphModel.refresh)
        self.pdpController.committed.disconnect(self._onPDPCommitted)
        self.clusterModel.clustersDetected.disconnect(self._onClustersDetected)
        self.sarfGraphModel.deinit()
        self.clusterModel.deinit()
        self.analytics.init()
        self.session.deinit()
        if self.eventForm:
            self.eventForm.deinit()
        self._engine = None

    def exec(self, mw):
        self.app.exec()

    @pyqtProperty(QObject, constant=True)
    def settings(self):
        return self._settings

    # Diagram / Scene

    def setDiagram(self, diagram: Diagram | None, discussions: list | None = None):
        self.pdpController.setDiagram(diagram)
        self.discussion.setDiagram(diagram, discussions if discussions else [])
        self._diagram = diagram
        self.clusterModel.diagramId = diagram.id if diagram else None

    def _onDiagramLoaded(self, diagram: Diagram, scene: Scene | None, discussions):
        self.setDiagram(diagram, discussions)
        if scene is not None:
            self.setScene(scene)

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
        # Emits pdpChanged, so committedPeople gets populated from the scene.
        self.pdpController.setScene(scene)
        # New scene -> the wizard gate and profile values depend on its primary
        # node, so re-evaluate them (FD-321).
        self.userProfileChanged.emit()

    def onSessionChanged(self, oldFeatures, newFeatures):
        if self.session.isLoggedIn():
            self.appConfig.set("lastSessionData", self.session.data(), pickled=True)
            self.shakeDetector.start()
        else:
            self.appConfig.delete("lastSessionData")
            self.shakeDetector.stop()
        self.appConfig.write()

        if not self.session.user:
            self.setDiagram(None)
            self.diagramLoader.clear()
        else:
            self.diagramLoader.refreshDiagrams()
            self.diagramLoader.refreshDiagram()

    # Save

    def saveDiagram(self):
        if not self._diagram or not self.scene:
            return

        # Snapshot baseline for the merge: Personal's Scene view at the
        # last successful save (or, on first save, what was loaded at
        # open). NOT the canonical server state, NOT the post-merge bytes
        # — those may contain other-client items Personal's Scene never
        # loaded, which would get interpreted as deletes on the next save.
        # Plan: doc/plans/2026-05-01--mvp-merge-fix/README.md
        snapshotBytes = (
            getattr(self._diagram, "_lastSavedSnapshot", None) or self._diagram.data
        )
        openSnapshot = pickle.loads(snapshotBytes) if snapshotBytes else {}

        # Capture Scene state NOW (caller-side) so we can stash it as the
        # next-save snapshot after Diagram.save returns success.
        currentSceneBytes = pickle.dumps(asdict(self.scene.diagramData()))

        def _do():
            def applyChange(diagramData: DiagramData):
                sceneDiagramData = self.scene.diagramData()
                # Scene collections — snapshot-diff merge. For each field,
                # take server's copy unless the user actually edited the
                # item (snapshot vs local differ), preventing a stale
                # snapshot from clobbering concurrent edits.
                for fname in DiagramData.SCENE_COLLECTION_FIELDS:
                    snapshot_field = openSnapshot.get(fname, [])
                    local_field = getattr(sceneDiagramData, fname)
                    setattr(
                        diagramData,
                        fname,
                        DiagramData.apply_local_changes(
                            getattr(diagramData, fname),
                            snapshot_field,
                            local_field,
                        ),
                    )
                diagramData.version = sceneDiagramData.version
                diagramData.versionCompat = sceneDiagramData.versionCompat
                diagramData.name = sceneDiagramData.name
                diagramData.lastItemId = max(
                    diagramData.lastItemId, sceneDiagramData.lastItemId
                )
                diagramData.clusters = self.clusterModel.clusters
                diagramData.clusterCacheKey = self.clusterModel.cacheKey
                return diagramData

            success = self._diagram.save(
                self.session.server(), applyChange, lambda d: True, useJson=True
            )
            if success:
                # Capture Personal's Scene view as the merge baseline for
                # the next save. NOT the post-merge bytes (other-client
                # items would leak in and get treated as deletes later).
                self._diagram._lastSavedSnapshot = currentSceneBytes

        self._saveGuard(_do)

    def _onPDPCommitted(self):
        self.clusterModel.detect()

    def _onClustersDetected(self):
        self.saveDiagram()

    # Event form

    def onQmlObjectCreated(self, rootObject: QQuickItem, url: QUrl):
        if self.eventForm and self.scene:
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

    # User profile (FD-321)

    def _primaryPerson(self) -> Person | None:
        """The user's own node. The one marked primary, else a deterministic
        fallback (lowest id) so a pre-existing diagram with no primary marked is
        still editable. None only when the scene has no people."""
        if not self.scene:
            return None
        primary = self.scene.query1(primary=True)
        if primary is not None:
            return primary
        people = sorted(self.scene.people(), key=lambda p: p.id)
        return people[0] if people else None

    @pyqtProperty(bool, notify=userProfileChanged)
    def shouldPromptProfile(self) -> bool:
        """First-launch wizard gate: the prompt pref is unset AND the primary
        node has no name. Either a completed save or an explicit skip sets the
        pref, so the wizard never reappears."""
        if self.appConfig.get("personalProfilePrompted"):
            return False
        person = self._primaryPerson()
        return not (person and person.name())

    @pyqtSlot()
    def markProfilePrompted(self):
        self.appConfig.set("personalProfilePrompted", True)
        if self.appConfig.filePath:
            self.appConfig.write()
        self.userProfileChanged.emit()

    def _isOwnDiagram(self) -> bool:
        """True iff the active scene is the user's own (free) diagram, where the
        primary node IS the account holder. The account name is linked only here.
        A loaded client file (other owned/shared diagram, e.g. a clinician's
        client) is NOT own; nothing-loaded is the fresh Personal default scene,
        which IS the user's own (their free diagram is created on first save)."""
        user = self.session.user if self.session else None
        if user is None or user.free_diagram_id is None:
            return False
        if self._diagram is None:
            return True
        return self._diagram.id == user.free_diagram_id

    @pyqtProperty("QVariantMap", notify=userProfileChanged)
    def userProfile(self) -> dict:
        person = self._primaryPerson()
        name = person.name() if person else None
        if not name and self._isOwnDiagram():
            # On the user's own diagram, pre-fill from the account name (set at
            # signup) so the average self-user just confirms it and adds a birth date.
            user = self.session.user
            year, month, day = "", "", ""
            if person:
                birth = person.birthDateTime()
                if birth and birth.isValid():
                    d = birth.date()
                    year, month, day = str(d.year()), str(d.month()), str(d.day())
            return {"firstName": user.first_name or "", "lastName": user.last_name or "",
                    "birthYear": year, "birthMonth": month, "birthDay": day}
        if not person:
            return {"firstName": "", "lastName": "", "birthYear": "", "birthMonth": "", "birthDay": ""}
        birth = person.birthDateTime()
        if birth and birth.isValid():
            d = birth.date()
            year, month, day = str(d.year()), str(d.month()), str(d.day())
        else:
            year, month, day = "", "", ""
        return {
            "firstName": person.name() or "",
            "lastName": person.lastName() or "",
            "birthYear": year,
            "birthMonth": month,
            "birthDay": day,
        }

    @pyqtSlot(str, str, int, int, int, result=bool)
    def saveUserProfile(
        self, firstName: str, lastName: str, year: int, month: int, day: int
    ) -> bool:
        """Land name on the primary Person and birth date as a Birth event on
        it, then persist via the normal save path. A primary person is created
        if the diagram has none. Returns False if there is no scene to write to.
        year<=0 means no birth date (the event is removed if one exists)."""
        if not self.scene:
            _log.warning("saveUserProfile called with no scene")
            return False

        person = self._primaryPerson()
        if person is None:
            person = Person(primary=True)
            self.scene.addItem(person)
        elif not person.primary():
            person.setPrimary(True)

        person.setName(firstName.strip() or None)
        person.setLastName(lastName.strip() or None)

        birthEvent = person.birthEvent()
        if year > 0:
            dateTime = util.Date(year, month, day)
            if birthEvent is None:
                # A person's own birth event keys on child(), so the subject is
                # the child of the event (parents unknown -> no person/spouse).
                birthEvent = Event(EventKind.Birth, person=person, child=person, dateTime=dateTime)
                self.scene.addItem(birthEvent)
            else:
                birthEvent.setDateTime(dateTime)
        elif birthEvent is not None:
            self.scene.removeItem(birthEvent)

        self.saveDiagram()

        # On the user's OWN (free) diagram the primary node is the account holder,
        # so keep the account name in sync. Never touch the account from a client
        # file (other owned/shared diagrams), whose node is a different person.
        if self._isOwnDiagram():
            self.session.updateName(firstName.strip(), lastName.strip())

        self.markProfilePrompted()
        self.userProfileChanged.emit()
        return True
