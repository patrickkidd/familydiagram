import enum
import logging
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
)
from pkdiagram.server_types import User, Diagram

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
    """
    For clean exposure to Qml
    """

    def __init__(
        self,
        id: int,
        user_id: int,
        diagram_id: int,
        summary: str | None = None,
        statements: list[Statement] = [],
        speakers: list[Speaker] = [],
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._id = id
        self._user_id = user_id
        self._summary = summary
        self._statements = statements
        self._diagram_id = diagram_id
        self._speakers = speakers

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


class Therapist(QObject):
    """
    Simply translates the UI into a REST request.
    """

    requestSent = pyqtSignal(str)
    responseReceived = pyqtSignal(str, dict, arguments=["statement", "pdp"])
    serverError = pyqtSignal(str)
    serverDown = pyqtSignal()

    discussionsChanged = pyqtSignal()
    pdpChanged = pyqtSignal()
    diagramChanged = pyqtSignal()
    statementsChanged = pyqtSignal()

    def __init__(self, session):
        super().__init__()
        self._session = session
        self._session.changed.connect(self.onSessionChanged)
        self._diagram: Diagram | None = None
        self._discussions = []
        self._currentDiscussion: Discussion | None = None
        self._pdp: dict | None = None

    def init(self):
        self._refreshDiagram()
        self.refreshPDP()

    def onSessionChanged(self):
        if not self._session.user:
            self._diagram = None
            self._discussions = []
            self._pdp = {}
            self._currentDiscussion = None
        else:
            self._refreshDiagram()
            self.refreshPDP()
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

    @pyqtProperty("QVariantMap", notify=diagramChanged)
    def diagram(self):
        return self._diagram if self._diagram is not None else {}

    # Discussions

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
            "/therapist/discussions/",
            data={"diagram_id": self._diagram.id},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    def _refreshDiagram(self):
        if not self._session.user:
            return

        def onSuccess(data):
            self._diagram = Diagram(**data)
            self._discussions = [Discussion.create(x) for x in data["discussions"]]
            self.discussionsChanged.emit()
            self.statementsChanged.emit()
            self.pdpChanged.emit()

        server = self._session.server()
        reply = server.nonBlockingRequest(
            "GET",
            f"/therapist/diagrams/{self._session.user.free_diagram_id}",
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
                # added_data_points = data["added_data_points"]
                # response = Response(
                #     statement=data["statement"],
                #     added_data_points=data["added_data_points"],
                #     removed_data_points=data["removed_data_points"],
                #     guidance=data["guidance"],
                # )
                self.setPDP(data["pdp"])
                self.responseReceived.emit(data["statement"], data["pdp"])

            args = {
                "statement": statement,
            }
            reply = self._session.server().nonBlockingRequest(
                "POST",
                f"/therapist/discussions/{self._currentDiscussion.id}/statements",
                data=args,
                error=lambda: self.onError(reply),
                success=onSuccess,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                from_root=True,
            )
            self._session.track(f"therapist.Engine.sendStatement: {statement}")
            self.requestSent.emit(statement)

        if self._currentDiscussion:
            _doSendStatement()
        else:
            self._createDiscussion(callback=_doSendStatement)

    ## PDP

    @pyqtSlot()
    def refreshPDP(self):
        self._refreshPDP()

    def _refreshPDP(self):
        def onSuccess(data):
            # added_data_points = data["added_data_points"]
            # response = Response(
            #     statement=data["statement"],
            #     added_data_points=data["added_data_points"],
            #     removed_data_points=data["removed_data_points"],
            #     guidance=data["guidance"],
            # )
            self.setPDP(data["pdp"])
            self.responseReceived.emit(data["statement"], data["pdp"])

        # Create a discussion with the statement if there is no current discussion
        if self._currentDiscussion:
            url = f"/therapist/discussions/{self._currentDiscussion.id}/statements"
        else:
            url = "/therapist/discussions/"
        args = {"statement": statement}
        reply = self._session.server().nonBlockingRequest(
            "POST",
            url,
            data=args,
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            from_root=True,
        )
        self._session.track(f"therapist.Engine.sendStatement: {statement}")
        self.requestSent.emit(statement)

    ## PDP

    @pyqtSlot()
    def refreshPDP(self):
        self._refreshPDP()

    def _refreshPDP(self):
        def onSuccess(data):
            self.setPDP(data)
            # _log.info(f"pdpChanged.emit(): {self._pdp}")
            self.pdpChanged.emit()

        reply = self._session.server().nonBlockingRequest(
            "GET",
            "/therapist/pdp",
            data={},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    @pyqtSlot(int)
    def acceptPDPItem(self, id: int):
        if not self._diagram:
            _log.warning("Cannot accept PDP item without diagram")
            return
        _log.info(f"Accepting PDP item with id: {id}")
        reply = self._session.server().nonBlockingRequest(
            "POST",
            f"/therapist/diagrams/{self._diagram.id}/pdp/{-id}/accept",
            data={},
            error=lambda: self.onError(reply),
            success=lambda data: _log.info(f"Accepted PDP item: {data}"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    @pyqtSlot(int)
    def rejectPDPItem(self, id: int):
        if not self._diagram:
            _log.warning("Cannot reject PDP item without diagram")
            return
        _log.info(f"Rejecting PDP item with id: {id}")
        reply = self._session.server().nonBlockingRequest(
            "POST",
            f"/therapist/diagrams/{self._diagram.id}/pdp/{-id}/reject",
            data={},
            error=lambda: self.onError(reply),
            success=lambda data: _log.info(f"Rejected PDP item: {data}"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    @pyqtProperty("QVariantMap", notify=diagramChanged)
    def pdp(self):
        return self._pdp if self._pdp is not None else {}

    def setPDP(self, pdp: dict):
        self._pdp = pdp
        _log.debug(f"diagramChanged.emit(): {self._pdp}")
        self.diagramChanged.emit()


qmlRegisterType(Discussion, "Therapist", 1, 0, "Discussion")
qmlRegisterType(Statement, "Therapist", 1, 0, "Statement")
qmlRegisterType(Speaker, "Therapist", 1, 0, "Speaker")
