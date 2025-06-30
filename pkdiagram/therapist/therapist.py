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


class ChatMessage(QObject):

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


class ChatThread(QObject):
    """
    For clean exposure to Qml
    """

    def __init__(
        self,
        id: int,
        user_id: int,
        summary: str | None = None,
        messages: list[ChatMessage] = [],
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._id = id
        self._user_id = user_id
        self._summary = summary
        self._messages = messages

    def as_dict(self) -> dict:
        return {
            "id": self._id,
            "user_id": self._user_id,
            "summary": self._summary,
            "messages": [x.as_dict() for x in self._messages],
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

    def messages(self) -> list[ChatMessage]:
        return list(self._messages)


def make_thread(data: dict) -> ChatThread:
    return ChatThread(
        id=data["id"],
        user_id=data["user_id"],
        summary=data["summary"],
        messages=data.get("messages", []),
    )


def make_message(data: dict) -> ChatMessage:
    return ChatMessage(
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
        arguments=["message", "pdp"],
    )
    serverError = pyqtSignal(str)
    serverDown = pyqtSignal()

    threadsChanged = pyqtSignal()
    pdpChanged = pyqtSignal()
    messagesChanged = pyqtSignal()

    def __init__(self, session):
        super().__init__()
        self._session = session
        self._session.changed.connect(self.onSessionChanged)
        self._threads = []
        self._pdp = None  # type: dict | None
        self._currentThread: ChatThread | None = None
        self._messages: list[ChatMessage] = []

    def init(self):
        self.refreshThreads()
        self.refreshPDP()

    def onSessionChanged(self):
        self._threads = [make_thread(x) for x in self._session.user.chat_threads]
        self._pdp = self._session.user.pdp
        self.threadsChanged.emit()
        self.messagesChanged.emit()
        self.pdpChanged.emit()

    def onError(self, reply: QNetworkReply):
        if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 0:
            self.serverDown.emit()
        else:
            self.serverError.emit(reply.errorString())

    ## Threads

    @pyqtProperty("QVariantList", notify=threadsChanged)
    def threads(self):
        return list(self._threads)

    @pyqtProperty("QVariantMap", notify=pdpChanged)
    def pdp(self):
        return self._pdp if self._pdp is not None else {}

    def setPDP(self, pdp: dict):
        self._pdp = pdp
        _log.debug(f"pdpChanged.emit(): {self._pdp}")
        self.pdpChanged.emit()

    def _setCurrentThread(self, thread_id: int):
        self._currentThread = next(x for x in self._threads if x.id == thread_id)
        self._refreshMessages()

    @pyqtSlot(int)
    def setCurrentThread(self, thread_id: int):
        self._setCurrentThread(thread_id)

    @pyqtSlot()
    def createThread(self):
        self._createThread()

    def _createThread(self):

        def onSuccess(data):
            thread = make_thread(data)
            self._threads.append(thread)
            self.threadsChanged.emit()
            self._setCurrentThread(thread.id)

        reply = self._session.server().nonBlockingRequest(
            "POST",
            "/therapist/threads",
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
            self._threads = [make_thread(x) for x in data]
            if not self._threads:
                self._createThread()
            else:
                self.threadsChanged.emit()

        reply = self._session.server().nonBlockingRequest(
            "GET",
            "/therapist/threads",
            data={},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    @pyqtSlot()
    def refreshPDP(self):
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

    ## Messages

    @pyqtProperty("QVariantList", notify=messagesChanged)
    def messages(self):
        return list(self._messages)

    def _refreshMessages(self):

        def onSuccess(data):
            self._messages = [make_message(x) for x in data]
            # _log.info(f"messagesChanged.emit(): {len(self._messages)} messages")
            self.messagesChanged.emit()

        reply = self._session.server().nonBlockingRequest(
            "GET",
            f"/therapist/threads/{self._currentThread.id}/messages",
            data={},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    @pyqtSlot(str)
    def sendMessage(self, message: str):
        self._sendMessage(message)

    def _sendMessage(self, message: str):
        """
        Mockable because qml latches on to slots at init time.
        """

        def onSuccess(data):
            # added_data_points = data["added_data_points"]
            # response = Response(
            #     message=data["message"],
            #     added_data_points=data["added_data_points"],
            #     removed_data_points=data["removed_data_points"],
            #     guidance=data["guidance"],
            # )
            self.setPDP(data["pdp"])
            self.responseReceived.emit(
                data["message"],
                data["pdp"],
            )

        args = {
            "thread_id": self._currentThread.id,
            "message": message,
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
        self._session.track(f"therapist.Engine.sendMessage: {message}")
        self.requestSent.emit(message)

    @pyqtSlot(int)
    def acceptPDPItem(self, id: int):
        _log.info(f"Accepting PDP item with id: {id}")
        reply = self._session.server().nonBlockingRequest(
            "POST",
            f"/therapist/pdp/accept/{id}",
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
            f"/therapist/pdp/reject/{id}",
            data={},
            error=lambda: self.onError(reply),
            success=lambda data: _log.info(f"Rejected PDP item: {data}"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )
