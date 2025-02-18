import pickle
import logging

from pkdiagram.pyqt import pyqtSlot, pyqtSignal, QObject, QNetworkRequest, QNetworkReply
from pkdiagram.server_types import HTTPError


_log = logging.getLogger(__name__)


def formatSources(sources: list) -> str:
    return "\n---------\n".join(
        f"{x['fd_title']}, {x['fd_authors']}:\n\n{x['passage']}" for x in sources
    )


class CopilotEngine(QObject):

    requestSent = pyqtSignal(str)
    responseReceived = pyqtSignal(
        str, str, int, arguments=["response", "sources", "numSources"]
    )
    serverError = pyqtSignal(str)
    serverDown = pyqtSignal()

    def __init__(self, session):
        super().__init__()
        self._session = session
        self._scene = None

    def setScene(self, scene):
        self._scene = scene

    @pyqtSlot(str, bool)
    def ask(self, question: str, includeTags: bool = None):
        self._ask(question, includeTags)

    def _ask(self, question: str, includeTags: bool = None):
        """
        Mockable because qml latches on to slots at init time.
        """

        def onFinished(data):
            if isinstance(data, str):
                data = pickle.loads(data)
                sourcesText = formatSources(data["sources"])
                self.responseReceived.emit(
                    data["response"], sourcesText, len(data["sources"])
                )

        def onError():
            if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 0:
                self.serverDown.emit()
            else:
                self.serverError.emit(reply.errorString())

        if includeTags:
            timelineData = ""
            eventProperties = self._scene.eventProperties()

            def _vars(event):
                return ", ".join(f"{x['attr']}: {x.get()}" for x in eventProperties)

            for event in self._scene.events(tags=includeTags):
                timelineData += (
                    f"Timestamp: {event.dateTime}\t"
                    f"Description: {event.description}\t"
                    f"People: {', '.join(event.people)}\t"
                    f"Variables: {', '.join(_vars(event))}\n"
                )

        args = {
            "question": question,
            "session": self._session.token,
        }
        reply = self._session.server().nonBlockingRequest(
            "POST", "/copilot/chat", data=args, error=onError, finished=onFinished
        )
        onFinished._reply = reply
        self.requestSent.emit(question)
