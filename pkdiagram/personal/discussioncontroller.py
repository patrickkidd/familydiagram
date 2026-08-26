import logging
from typing import Callable

from pkdiagram.app import Session
from pkdiagram.personal.api import JSON_HEADERS
from pkdiagram.personal.models import Discussion
from pkdiagram.personal.settings import Settings
from pkdiagram.pyqt import (
    QMessageBox,
    QNetworkReply,
    QNetworkRequest,
    QObject,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)
from pkdiagram.server_types import Diagram

_log = logging.getLogger(__name__)


class DiscussionController(QObject):
    """The chat with the coach for one Diagram: its discussions, the current
    one, and the statements sent to it. Bound to a Diagram by setDiagram()."""

    requestSent = pyqtSignal(str)
    responseReceived = pyqtSignal(str, arguments=["statement"])
    serverError = pyqtSignal(str)
    serverDown = pyqtSignal()

    discussionsChanged = pyqtSignal()
    statementsChanged = pyqtSignal()
    currentDiscussionChanged = pyqtSignal()
    responseModelChanged = pyqtSignal()

    AVAILABLE_MODELS = [
        {
            "id": "opus-4.6",
            "name": "Premium",
            "description": "Deeper observations and more nuanced coaching. Makes connections between family patterns. Takes a moment longer to respond.",
        },
        {
            "id": "gemini-2.5-flash",
            "name": "Standard",
            "description": "Quick, focused responses. Efficient at collecting family facts and keeping the conversation moving.",
        },
    ]
    DEFAULT_MODEL = "opus-4.6"

    def __init__(self, session: Session, settings: Settings, parent=None):
        super().__init__(parent)
        self.session = session
        self._settings = settings
        # Consulted before a send reaches the server (FD-336 D6). Standalone
        # Personal leaves it None; only the Pro embedding has a document that
        # can be dirty.
        self.gate: Callable[[], bool] | None = None
        self._diagram: Diagram | None = None
        self._discussions: list[Discussion] = []
        self._currentDiscussion: Discussion | None = None
        self._dirty: bool = False  # conversation past last accepted extraction
        self._sentSinceExtract: bool = False

    def setDiagram(self, diagram: Diagram | None, discussions: list[Discussion]):
        self._diagram = diagram
        self._discussions = discussions
        self._currentDiscussion = None
        self._dirty = False
        self._sentSinceExtract = False
        self.discussionsChanged.emit()
        self.statementsChanged.emit()
        self.currentDiscussionChanged.emit()

    def _isCurrent(self, diagram: Diagram | None) -> bool:
        return self._diagram is diagram

    def onError(self, reply: QNetworkReply):
        if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 0:
            self.serverDown.emit()
        else:
            self.serverError.emit(reply.errorString())

    # Model selection

    @pyqtProperty("QVariantList", constant=True)
    def availableModels(self):
        return self.AVAILABLE_MODELS

    @pyqtProperty(str, notify=responseModelChanged)
    def responseModel(self):
        return (
            self._settings.value("responseModel", self.DEFAULT_MODEL)
            or self.DEFAULT_MODEL
        )

    @pyqtSlot(str)
    def setResponseModel(self, modelId: str):
        if modelId == self.responseModel:
            return
        self._settings.setValue("responseModel", modelId)
        self.responseModelChanged.emit()

    # Discussions

    @pyqtProperty("QVariantList", notify=discussionsChanged)
    def discussions(self):
        return list(self._discussions)

    def currentDiscussion(self) -> Discussion | None:
        return self._currentDiscussion

    @pyqtProperty(int, notify=statementsChanged)
    def currentDiscussionId(self):
        return self._currentDiscussion.id if self._currentDiscussion else -1

    @pyqtProperty(bool, notify=statementsChanged)
    def canExtract(self) -> bool:
        """Extract button visibility. Dirty = there is conversation past the
        last accepted extraction. Transitions (no model resync needed):
        - discussion load: computed from server order vs cursor;
        - send: dirty (a new statement is always past the cursor);
        - full accept: clean, unless chat happened since the extract that
          produced the accepted PDP (then still dirty);
        - partial accept / extract-without-accept: unchanged."""
        return bool(self._currentDiscussion) and self._dirty

    @pyqtSlot()
    def createDiscussion(self):
        self._createDiscussion()

    def _createDiscussion(self, callback: Callable | None = None):
        if not self._diagram:
            _log.warning("Cannot create discussion without diagram")
            return

        diagram = self._diagram

        def onSuccess(data):
            if not self._isCurrent(diagram):
                return
            discussion = Discussion.create(data)
            self._discussions.append(discussion)
            self.discussionsChanged.emit()
            self._setCurrentDiscussion(discussion.id)
            if callback:
                callback()

        reply = self.session.server().nonBlockingRequest(
            "POST",
            "/personal/discussions/",
            data={"diagram_id": diagram.id},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers=JSON_HEADERS,
            from_root=True,
        )

    def _setCurrentDiscussion(self, discussion_id: int):
        self._currentDiscussion = next(
            x for x in self._discussions if x.id == discussion_id
        )
        self._recomputeDirtyFromModel()
        self.statementsChanged.emit()
        self.currentDiscussionChanged.emit()

    def _recomputeDirtyFromModel(self):
        """At discussion load the model is server-fresh (statements carry
        order, cursor = extracted_through_order), so compute dirty directly."""
        self._sentSinceExtract = False
        d = self._currentDiscussion
        if not d:
            self._dirty = False
            return
        self._dirty = any(
            (s.order or 0) > d.extracted_through_order for s in d.statements()
        )

    @pyqtSlot(int)
    def setCurrentDiscussion(self, discussion_id: int):
        self._setCurrentDiscussion(discussion_id)

    def markExtracted(self):
        """An extraction was just issued: chat sent from here on is what makes
        a later full accept still dirty."""
        self._sentSinceExtract = False

    def markAccepted(self):
        """The server confirmed a full accept: clean unless chat was sent after
        the extract that produced the accepted PDP."""
        self._dirty = self._sentSinceExtract
        self.statementsChanged.emit()

    # Statements

    @pyqtProperty("QVariantList", notify=statementsChanged)
    def statements(self):
        if self._currentDiscussion:
            return list(self._currentDiscussion.statements())
        else:
            return []

    @pyqtSlot(str)
    def sendStatement(self, statement: str):
        if self.gate and not self.gate():
            return
        self._sendStatement(statement)

    def _sendStatement(self, statement: str):
        def _doSendStatement():
            if not self._currentDiscussion:
                QMessageBox.information(
                    self, "Cannot send statement without current discussion"
                )
                return

            diagram = self._diagram

            def onSuccess(data):
                if not self._isCurrent(diagram):
                    return
                self.responseReceived.emit(data["statement"])

            args = {
                "statement": statement,
                "model": self.responseModel,
            }
            reply = self.session.server().nonBlockingRequest(
                "POST",
                f"/personal/discussions/{self._currentDiscussion.id}/statements",
                data=args,
                error=lambda: self.onError(reply),
                success=onSuccess,
                headers=JSON_HEADERS,
                from_root=True,
            )
            self.session.track(f"personal.Engine.sendStatement: {statement}")
            # A new statement is always past the cursor -> dirty. No model
            # resync needed; the flag is the source of truth between loads.
            self._dirty = True
            self._sentSinceExtract = True
            self.statementsChanged.emit()
            self.requestSent.emit(statement)

        if self._currentDiscussion:
            _doSendStatement()
        else:
            self._createDiscussion(callback=_doSendStatement)
