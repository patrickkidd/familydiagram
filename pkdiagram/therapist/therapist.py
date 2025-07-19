import logging
from dataclasses import dataclass

from pkdiagram.pyqt import (
    pyqtSlot,
    pyqtSignal,
    pyqtProperty,
    QObject,
    QNetworkRequest,
    qmlRegisterType,
    QNetworkReply,
)

# from pkdiagram import util
# from pkdiagram.models.qobjecthelper import qobject_dataclass


_log = logging.getLogger(__name__)


@dataclass
class Response:
    message: str
    pdp: dict


# qmlRegisterType(Response, "PK.Models", 1, 0, "Response")


class Statement(QObject):

    def __init__(
        self,
        id: int,
        text: str,
        origin: str,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._id = id
        self._text = text
        self._origin = origin

    def as_dict(self) -> dict:
        return {
            "id": self._id,
            "text": self._text,
            "origin": self._origin,
        }

    @pyqtProperty(int, constant=True)
    def id(self) -> int:
        return self._id

    @pyqtProperty(str, constant=True)
    def text(self) -> str:
        return self._text

    @pyqtProperty(str, constant=True)
    def origin(self) -> str:
        return self._origin


class Discussion(QObject):
    """
    For clean exposure to Qml
    """

    def __init__(
        self,
        id: int,
        user_id: int,
        summary: str | None = None,
        statements: list[Statement] = [],
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._id = id
        self._user_id = user_id
        self._summary = summary
        self._statements = statements

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


def make_discussion(data: dict) -> Discussion:
    return Discussion(
        id=data["id"],
        user_id=data["user_id"],
        summary=data["summary"],
        statements=data.get("statements", []),
    )


def make_statement(data: dict) -> Statement:
    return Statement(
        id=data["id"],
        text=data["text"],
        origin=data["origin"],
    )


class Therapist(QObject):
    """
    Simply translates the UI into a REST request.
    """

    requestSent = pyqtSignal(str)
    responseReceived = pyqtSignal(
        str,
        dict,
        arguments=["statement", "pdp"],
    )
    serverError = pyqtSignal(str)
    serverDown = pyqtSignal()

    discussionsChanged = pyqtSignal()
    pdpChanged = pyqtSignal()
    statementsChanged = pyqtSignal()

    def __init__(self, session):
        super().__init__()
        self._session = session
        self._session.changed.connect(self.onSessionChanged)
        self._discussions = []
        self._pdp = None  # type: dict | None
        self._currentThread: Discussion | None = None
        self._statements: list[Statement] = []

    def init(self):
        self.refreshThreads()
        self.refreshPDP()

    def onSessionChanged(self):
        self._discussions = [x for x in self._session.user.discussions]
        self._pdp = self._session.user.pdp
        self.discussionsChanged.emit()
        self.statementsChanged.emit()
        self.pdpChanged.emit()

    def onError(self, reply: QNetworkReply):
        if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 0:
            self.serverDown.emit()
        else:
            self.serverError.emit(reply.errorString())

    ## Threads

    @pyqtProperty("QVariantList", notify=discussionsChanged)
    def threads(self):
        return list(self._discussions)

    @pyqtProperty("QVariantMap", notify=pdpChanged)
    def pdp(self):
        return self._pdp if self._pdp is not None else {}

    def setPDP(self, pdp: dict):
        self._pdp = pdp
        _log.debug(f"pdpChanged.emit(): {self._pdp}")
        self.pdpChanged.emit()

    def _setCurrentThread(self, thread_id: int):
        self._currentThread = next(x for x in self._discussions if x.id == thread_id)
        self._refreshStatements()

    @pyqtSlot(int)
    def setCurrentThread(self, thread_id: int):
        self._setCurrentThread(thread_id)

    @pyqtSlot()
    def createThread(self):
        self._createThread()

    def _createThread(self):

        def onSuccess(data):
            thread = make_discussion(data)
            self._discussions.append(thread)
            self.discussionsChanged.emit()
            self._setCurrentThread(thread.id)

        reply = self._session.server().nonBlockingRequest(
            "POST",
            "/therapist/discussions",
            data={},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    @pyqtSlot()
    def refreshThreads(self):
        self._refreshThreads()

    def _refreshThreads(self):
        def onSuccess(data):
            self._discussions = [make_discussion(x) for x in data]
            if not self._discussions:
                self._createThread()
            else:
                self.discussionsChanged.emit()

        reply = self._session.server().nonBlockingRequest(
            "GET",
            "/therapist/discussions",
            data={},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

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

    ## Statements

    @pyqtProperty("QVariantList", notify=statementsChanged)
    def statements(self):
        return list(self._statements)

    def _refreshStatements(self):

        def onSuccess(data):
            self._statements = [make_statement(x) for x in data]
            # _log.info(f"statementsChanged.emit(): {len(self._statements)} statements")
            self.statementsChanged.emit()

        reply = self._session.server().nonBlockingRequest(
            "GET",
            f"/therapist/discussions/{self._currentThread.id}/statements",
            data={},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    @pyqtSlot(str)
    def sendStatement(self, statement: str):
        self._sendStatement(statement)

    def _sendStatement(self, statement: str):
        """
        Mockable because qml latches on to slots at init time.
        """

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
            "thread_id": self._currentThread.id,
            "statement": statement,
        }
        reply = self._session.server().nonBlockingRequest(
            "POST",
            "/therapist/chat",
            data=args,
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )
        self._session.track(f"therapist.Engine.sendStatement: {statement}")
        self.requestSent.emit(statement)

    @pyqtSlot(int)
    def acceptPDPItem(self, id: int):
        _log.info(f"Accepting PDP item with id: {id}")
        reply = self._session.server().nonBlockingRequest(
            "POST",
            f"/therapist/pdp/accept/{-id}",
            data={},
            error=lambda: self.onError(reply),
            success=lambda data: _log.info(f"Accepted PDP item: {data}"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    @pyqtSlot(int)
    def rejectPDPItem(self, id: int):
        _log.info(f"Rejecting PDP item with id: {id}")
        reply = self._session.server().nonBlockingRequest(
            "POST",
            f"/therapist/pdp/reject/{-id}",
            data={},
            error=lambda: self.onError(reply),
            success=lambda data: _log.info(f"Rejected PDP item: {data}"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )
