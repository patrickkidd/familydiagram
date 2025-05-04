import logging

from pkdiagram.pyqt import pyqtSlot, pyqtSignal, QObject, QNetworkRequest
from pkdiagram import util


_log = logging.getLogger(__name__)


class Therapist(QObject):
    """
    Simply translates the UI into a REST request.
    """

    requestSent = pyqtSignal(str)
    responseReceived = pyqtSignal(str, arguments=["response"])
    serverError = pyqtSignal(str)
    serverDown = pyqtSignal()

    def __init__(self, session):
        super().__init__()
        self._session = session

    def setScene(self, scene):
        self._scene = scene

    @pyqtSlot(str, bool)
    def sendMessage(self, message: str):
        self._sendMessage(message)

    def _sendMessage(self, message: str):
        """
        Mockable because qml latches on to slots at init time.
        """

        def onSuccess(data):
            # added_data_points = data["added_data_points"]
            self.responseReceived.emit(data["message"])

        def onError():
            if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 0:
                self.serverDown.emit()
            else:
                self.serverError.emit(reply.errorString())

        args = {
            "message": message,
        }
        reply = self._session.server().nonBlockingRequest(
            "POST", "/copilot/chat", data=args, error=onError, success=onSuccess
        )
        self._session.track(f"therapist.Engine.sendMessage: {message}")
        self.requestSent.emit(message)
