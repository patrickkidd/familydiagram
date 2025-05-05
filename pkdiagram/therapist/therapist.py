import logging
from dataclasses import dataclass

from pkdiagram.pyqt import (
    pyqtSlot,
    pyqtSignal,
    QObject,
    QNetworkRequest,
    qmlRegisterType,
)

from pkdiagram import util


_log = logging.getLogger(__name__)


@dataclass
class Response:
    message: str
    added_data_points: list
    removed_data_points: list
    guidance: list[str]  # comprehensive list


# qmlRegisterType(Response, "PK.Models", 1, 0, "Response")


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

    def __init__(self, session):
        super().__init__()
        self._session = session

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

        def onError():
            if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 0:
                self.serverDown.emit()
            else:
                self.serverError.emit(reply.errorString())

        args = {
            "message": message,
        }
        reply = self._session.server().nonBlockingRequest(
            "POST",
            "/therapist/chat",
            data=args,
            error=onError,
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )
        self._session.track(f"therapist.Engine.sendMessage: {message}")
        self.requestSent.emit(message)
