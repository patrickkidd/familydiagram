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
    added_data_points: list
    removed_data_points: list
    guidance: list[str]  # comprehensive list


# qmlRegisterType(Response, "PK.Models", 1, 0, "Response")


class ChatMessage(QObject):

    def __init__(
        self, id: int, user_id: int, message: str, parent: QObject | None = None
    ):
        super().__init__(parent)
        self._id = id
        self._user_id = user_id
        self._message = message

    def as_dict(self) -> dict:
        return {
            "id": self._id,
            "user_id": self._user_id,
            "message": self._message,
        }


class ChatThread(QObject):
    """
    For clean exposure to Qml
    """

    # idChanged = pyqtSignal()
    # userIdChanged = pyqtSignal()
    # summaryChanged = pyqtSignal()

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

    # def setMessages(self, messages: list[ChatMessage]):


def make_thread(data: dict) -> ChatThread:
    return ChatThread(
        id=data["id"],
        user_id=data["user_id"],
        summary=data["summary"],
        messages=data.get("messages", []),
    )


class Therapist(QObject):
    """
    Simply translates the UI into a REST request.
    """

    requestSent = pyqtSignal(str)
    responseReceived = pyqtSignal(
        str,
        list,
        list,
        list,
        arguments=["message", "added", "removed", "guidance"],
    )
    serverError = pyqtSignal(str)
    serverDown = pyqtSignal()

    threadsChanged = pyqtSignal()

    def __init__(self, session):
        super().__init__()
        self._session = session
        self._session.changed.connect(self.onSessionChanged)
        self._threads = []

    def init(self):
        self.refreshThreads()

    def onSessionChanged(self):
        self._threads = [make_thread(x) for x in self._session.user.chat_threads]
        self.threadsChanged.emit()

    @pyqtProperty("QVariantList", notify=threadsChanged)
    def threads(self):
        return self._threads

    def onError(self, reply: QNetworkReply):
        if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 0:
            self.serverDown.emit()
        else:
            self.serverError.emit(reply.errorString())

    @pyqtSlot()
    def refreshThreads(self):

        def onSuccess(data):
            self._threads = [make_thread(x) for x in data]
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
            self.responseReceived.emit(
                data["message"],
                data["added_data_points"],
                data["removed_data_points"],
                data["guidance"],
            )

        args = {
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
