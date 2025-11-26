import enum
import logging
import base64
from dataclasses import dataclass
from typing import Callable

from pkdiagram.pyqt import (
    pyqtSlot,
    pyqtSignal,
    pyqtProperty,
    QObject,
    QNetworkRequest,
    qmlRegisterType,
    QNetworkReply,
    QMessageBox,
    QUndoStack,
)
from pkdiagram.server_types import Diagram
from pkdiagram.personal.commands import HandlePDPItem, PDPAction
from btcopilot.schema import DiagramData, asdict, Person, Event

# from pkdiagram import util
# from pkdiagram.models.qobjecthelper import qobject_dataclass


_log = logging.getLogger(__name__)


@dataclass
class Response:
    message: str
    pdp: dict


# qmlRegisterType(Response, "PK.Models", 1, 0, "Response")


class SpeakerType(enum.StrEnum):
    Expert = "expert"
    Subject = "subject"


class Speaker(QObject):
    def __init__(self, id: int, person_id: int, name: str, type: SpeakerType):
        super().__init__()
        self._id = id
        self._person_id = person_id
        self._name = name
        self._type = type

    def as_dict(self) -> dict:
        return {
            "person_id": self._person_id,
            "name": self._name,
            "type": self._type.value,
        }

    @pyqtProperty(int, constant=True)
    def id(self) -> int:
        return self._id

    @pyqtProperty(str, constant=True)
    def name(self) -> str:
        return self._name

    @pyqtProperty(str, constant=True)
    def type(self) -> str:
        return self._type


class Statement(QObject):

    def __init__(
        self,
        id: int,
        text: str,
        speaker: Speaker,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._id = id
        self._text = text
        self._speaker = speaker

    def as_dict(self) -> dict:
        return {
            "id": self._id,
            "text": self._text,
            "speaker": self._speaker.as_dict() if self._speaker else None,
        }

    @pyqtProperty(int, constant=True)
    def id(self) -> int:
        return self._id

    @pyqtProperty(str, constant=True)
    def text(self) -> str:
        return self._text

    @pyqtProperty(Speaker, constant=True)
    def speaker(self) -> Speaker:
        return self._speaker


class Discussion(QObject):
    def __init__(
        self,
        id: int,
        user_id: int,
        diagram_id: int,
        summary: str | None = None,
        statements: list[Statement] | None = None,
        speakers: list[Speaker] | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._id = id
        self._user_id = user_id
        self._summary = summary
        self._statements = statements if statements is not None else []
        self._diagram_id = diagram_id
        self._speakers = speakers if speakers is not None else []

    def as_dict(self) -> dict:
        return {
            "id": self._id,
            "user_id": self._user_id,
            "summary": self._summary,
            "statements": [x.as_dict() for x in self._statements],
        }

    @pyqtProperty(int, constant=True)
    def id(self) -> int:
        return self._id

    @pyqtProperty(int, constant=True)
    def user_id(self) -> int:
        return self._user_id

    @pyqtProperty(str, constant=True)
    def summary(self) -> str:
        return self._summary if self._summary else ""

    def statements(self) -> list[Statement]:
        return list(self._statements)

    @staticmethod
    def create(data: dict) -> "Discussion":
        speakers = [
            Speaker(
                id=x["id"],
                person_id=x["person_id"],
                name=x["name"],
                type=SpeakerType(x["type"]),
            )
            for x in data["speakers"]
        ]
        return Discussion(
            id=data["id"],
            diagram_id=data["diagram_id"],
            user_id=data["user_id"],
            summary=data["summary"],
            statements=[
                Statement(
                    id=x["id"],
                    text=x["text"],
                    speaker=next(y for y in speakers if y.id == x["speaker_id"]),
                )
                for x in data.get("statements", [])
            ],
            speakers=speakers,
        )


class Personal(QObject):
    requestSent = pyqtSignal(str)
    responseReceived = pyqtSignal(str, dict, arguments=["statement", "pdp"])
    serverError = pyqtSignal(str)
    serverDown = pyqtSignal()

    discussionsChanged = pyqtSignal()
    pdpChanged = pyqtSignal()
    pdpItemAdded = pyqtSignal(dict)
    pdpItemRemoved = pyqtSignal(dict)
    diagramChanged = pyqtSignal()
    statementsChanged = pyqtSignal()

    def __init__(self, session, undoStack=None):
        super().__init__()
        self._session = session
        self._session.changed.connect(self.onSessionChanged)
        self._diagram: Diagram | None = None
        self._discussions = []
        self._currentDiscussion: Discussion | None = None
        self._undoStack = undoStack if undoStack else QUndoStack(self)

    def init(self):
        if self._session.user:
            self._refreshDiagram()

    def onSessionChanged(self):
        if not self._session.user:
            self._diagram = None
            self._discussions = []
            self._currentDiscussion = None
        else:
            self._refreshDiagram()
        self.discussionsChanged.emit()
        self.statementsChanged.emit()
        self.pdpChanged.emit()
        self.diagramChanged.emit()

    def onError(self, reply: QNetworkReply):
        if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 0:
            self.serverDown.emit()
        else:
            self.serverError.emit(reply.errorString())

    ## Discussions

    @pyqtProperty("QVariantList", notify=discussionsChanged)
    def discussions(self):
        return list(self._discussions)

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

        server = self._session.server()
        reply = server.nonBlockingRequest(
            "POST",
            "/personal/discussions/",
            data={"diagram_id": self._diagram.id},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    # Diagram

    @pyqtProperty("QVariantMap", notify=diagramChanged)
    def diagram(self):
        return self._diagram if self._diagram is not None else {}

    def _refreshDiagram(self):
        if not self._session.user:
            return

        def onSuccess(data):
            data["data"] = base64.b64decode(data["data"])
            self._diagram = Diagram(**data)
            self._discussions = [Discussion.create(x) for x in data["discussions"]]
            self.discussionsChanged.emit()
            self.statementsChanged.emit()
            self.pdpChanged.emit()

        reply = self._session.server().nonBlockingRequest(
            "GET",
            f"/personal/diagrams/{self._session.user.free_diagram_id}",
            data={},
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
                    "Cannot send statement without current discussion"
                )
                return

            def onSuccess(data):
                self.responseReceived.emit(data["statement"], data["pdp"])

            args = {
                "statement": statement,
            }
            reply = self._session.server().nonBlockingRequest(
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
            self._session.track(f"personal.Engine.sendStatement: {statement}")
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
        item = self._pdpItem(id)
        prev_data = self._diagram.getDiagramData() if undo else None

        success = self._doAcceptPDPItem(id)

        if not success:
            return False

        if undo:
            cmd = HandlePDPItem(PDPAction.Accept, self, id, prev_data)
            self._undoStack.push(cmd)

        if item:
            if isinstance(item, Person):
                text = item.name or "<blank>"
            elif isinstance(item, Event):
                text = item.description or "<blank>"
            else:
                text = "<blank type>"
            # self.pdpItemAdded.emit(
            #     {
            #         "id": id,
            #         "text": text,
            #         "kind": "Person" if isinstance(item, Person) else "Event",
            #     }
            # )

        return True

    @pyqtSlot(int, result=bool)
    def rejectPDPItem(self, id: int, undo=True):
        item = self._pdpItem(id)
        prev_data = self._diagram.getDiagramData() if undo else None

        success = self._doRejectPDPItem(id)

        if not success:
            return False

        if undo:
            cmd = HandlePDPItem(PDPAction.Reject, self, id, prev_data)
            self._undoStack.push(cmd)

        if item:
            if isinstance(item, Person):
                text = item.name or "<blank>"
            elif isinstance(item, Event):
                text = item.description or "<blank>"
            else:
                text = "<blank type>"
            # self.pdpItemRemoved.emit(
            #     {
            #         "id": id,
            #         "text": text,
            #         "kind": "Person" if isinstance(item, Person) else "Event",
            #     }
            # )

        return True

    def _doAcceptPDPItem(self, id: int) -> bool:
        _log.info(f"Accepting PDP item with id: {id}")

        def applyChange(diagramData: DiagramData):
            diagramData.commit_pdp_items([id])
            return diagramData

        def stillValidAfterRefresh(diagramData: DiagramData):
            return True

        success = self._diagram.save(
            self._session.server(), applyChange, stillValidAfterRefresh, useJson=True
        )

        if success:
            self.pdpChanged.emit()
        else:
            _log.warning(f"Failed to accept PDP item after retries")

        return success

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
            self._session.server(), applyChange, stillValidAfterRefresh, useJson=True
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


qmlRegisterType(Discussion, "Personal", 1, 0, "Discussion")
qmlRegisterType(Statement, "Personal", 1, 0, "Statement")
qmlRegisterType(Speaker, "Personal", 1, 0, "Speaker")
