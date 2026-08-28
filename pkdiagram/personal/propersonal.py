import logging
import pickle

from btcopilot.schema import DiagramData
from pkdiagram.app import Session
from pkdiagram.models import ServerFileManagerModel
from pkdiagram.personal.api import JSON_HEADERS
from pkdiagram.personal.audio import VoiceRecorder
from pkdiagram.personal.clustermodel import ClusterModel
from pkdiagram.personal.discussioncontroller import DiscussionController
from pkdiagram.personal.models import Discussion
from pkdiagram.personal.pdpcontroller import PDPController
from pkdiagram.personal.sarfgraphmodel import SARFGraphModel
from pkdiagram.personal.savegate import SaveGate
from pkdiagram.personal.settings import Settings
from pkdiagram.personal.tts import TextToSpeech
from pkdiagram.pyqt import (
    QApplication,
    QObject,
    QQuickItem,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)
from pkdiagram.scene import Scene
from pkdiagram.server_types import Diagram
from pkdiagram.views import EventForm

_log = logging.getLogger(__name__)


class ProPersonal(QObject):
    """The Personal chat components composed against Pro's open case: Pro's
    Session, Pro's Scene, Pro's writer. Owns no session, no diagram loading and
    no second Scene, so everything the coach sees is the case Pro has open.

    Only the owner of a read-write server case may chat (FD-336 D3); anything
    else reports why through disabledReason instead of loading."""

    S_NO_SERVER_CASE = "Open a server case to chat."
    S_NOT_OWNER = "Chat is available on server cases you own."
    S_READ_ONLY = "This case is read-only."

    enabledChanged = pyqtSignal()
    eventFormDoneEditing = pyqtSignal()

    def __init__(
        self, session: Session, fileModel: ServerFileManagerModel, parent=None
    ):
        super().__init__(parent)
        self.session = session
        self.scene: Scene | None = None
        self.eventForm: EventForm | None = None
        self._diagram: Diagram | None = None
        self._settings = Settings(QApplication.instance().prefs(), self)

        self.saver = fileModel.saver
        self.gate = SaveGate(self)
        self.discussion = DiscussionController(self.session, self._settings, self)
        self.discussion.gate = self.gate
        self.pdpController = PDPController(self.session, fileModel.saver, self)
        self.pdpController.setDiscussion(self.discussion)
        self.pdpController.gate = self.gate
        self.sarfGraphModel = SARFGraphModel(self)
        self.clusterModel = ClusterModel(self.session, self)
        self.tts = TextToSpeech(self._settings, self)
        self.voice = VoiceRecorder(self.session, self)

        self.pdpController.pdpChanged.connect(self.sarfGraphModel.refresh)
        self.pdpController.committed.connect(self.clusterModel.detect)
        self.clusterModel.clustersDetected.connect(self._onClustersDetected)

    def contextProperties(self) -> dict:
        """What the Personal QML needs beyond what Pro's engine already
        registers. diagramLoader is null because Pro opens the case, not the
        Personal loader; the container only reads it for a label."""
        return {
            "personalApp": self,
            "discussion": self.discussion,
            "pdpController": self.pdpController,
            "diagramLoader": None,
            "tts": self.tts,
            "voice": self.voice,
            "sarfGraphModel": self.sarfGraphModel,
            "clusterModel": self.clusterModel,
        }

    def deinit(self):
        self.pdpController.pdpChanged.disconnect(self.sarfGraphModel.refresh)
        self.pdpController.committed.disconnect(self.clusterModel.detect)
        self.clusterModel.clustersDetected.disconnect(self._onClustersDetected)
        self.sarfGraphModel.deinit()
        self.clusterModel.deinit()

    def _onClustersDetected(self):
        """A detection result belongs on the row, not only in the local cache,
        or Learn re-detects on every reopen and the other client never sees it
        (FD-336 F-007). It is not a user edit, so a clean document stays clean."""
        if self._diagram is None or self.scene is None:
            return
        clusters = self.clusterModel.clusters
        cacheKey = self.clusterModel.cacheKey
        wasClean = self.scene.stack().isClean()

        def mutate(diagramData: DiagramData) -> DiagramData:
            diagramData.clusters = clusters
            diagramData.clusterCacheKey = cacheKey
            return diagramData

        saved = self.saver.save(
            self._diagram.id, pickle.dumps(self.scene.data()), mutate=mutate
        )
        if not saved:
            _log.warning(f"Could not persist clusters for diagram {self._diagram.id}")
        elif wasClean:
            self.scene.stack().setClean()

    # Enablement (D3)

    @pyqtProperty(str, notify=enabledChanged)
    def disabledReason(self) -> str:
        if self.scene is None or self._diagram is None:
            return self.S_NO_SERVER_CASE
        if self.scene.readOnly():
            return self.S_READ_ONLY
        user = self.session.user
        if user is None or self._diagram.user_id != user.id:
            return self.S_NOT_OWNER
        return ""

    @pyqtProperty(bool, notify=enabledChanged)
    def enabled(self) -> bool:
        return not self.disabledReason

    def _onEnablementChanged(self):
        if not self.enabled:
            # Disabled unloads the container, and the QML event form and its
            # models go with it, so the wrapper must not outlive them.
            self.eventForm = None
        self.enabledChanged.emit()

    # Case

    def setScene(self, scene: Scene | None):
        self.scene = scene
        self.gate.scene = scene
        self.sarfGraphModel.scene = scene
        self.clusterModel.scene = scene
        self.pdpController.setScene(scene)
        if self.eventForm:
            self.eventForm.setScene(scene)
        self._onEnablementChanged()

    def setDiagram(self, diagram: Diagram | None, discussions: list | None = None):
        """Bind to an open server case. Discussions arrive from the server
        unless the caller already has them."""
        self._diagram = diagram
        self.pdpController.setDiagram(diagram)
        self.clusterModel.diagramId = diagram.id if diagram else None
        self.discussion.setDiagram(diagram, discussions if discussions else [])
        if diagram:
            diagramData = diagram.getDiagramData()
            if diagramData.clusters:
                self.clusterModel.setClustersData(
                    diagramData.clusters, diagramData.clusterCacheKey
                )
            if discussions is None:
                self._fetchDiscussions(diagram)
        self._onEnablementChanged()

    def diagram(self) -> Diagram | None:
        return self._diagram

    def clear(self):
        self.setScene(None)
        self.setDiagram(None, [])

    def _fetchDiscussions(self, diagram: Diagram):
        def onSuccess(data):
            if diagram is not self._diagram:
                return
            self.discussion.setDiagram(diagram, [Discussion.create(x) for x in data])

        def onError():
            _log.error(
                f"Could not load discussions for diagram {diagram.id}: {reply.errorString()}"
            )

        reply = self.session.server().nonBlockingRequest(
            "GET",
            f"/personal/diagrams/{diagram.id}/discussions",
            data={},
            error=onError,
            success=onSuccess,
            headers=JSON_HEADERS,
            from_root=True,
        )

    # Event form (the container's bottom sheet, editing Pro's Scene)

    @pyqtSlot(QQuickItem)
    def initEventForm(self, eventFormItem: QQuickItem):
        self.eventForm = EventForm(eventFormItem, self)
        self.eventForm.saved.connect(self.gate.save)
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
            self.gate.save()
