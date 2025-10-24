import pickle
import logging

from btcopilot.schema import EventKind
from pkdiagram.pyqt import pyqtSlot, pyqtSignal, QObject, QNetworkRequest, QNetworkReply
from pkdiagram import util
from pkdiagram.server_types import HTTPError
from pkdiagram.scene import Scene, Event


_log = logging.getLogger(__name__)


def formatSources(sources: list) -> str:
    return "\n---------\n".join(
        f"{x['fd_title']}, {x['fd_authors']}:\n\n{x['passage']}" for x in sources
    )


def _eventParentName(event: Event) -> str:
    if event.kind() == EventKind.Bonded and event.person() and event.spouse():
        return f"{event.person().name()} & {event.spouse().name()}"
    elif event.person():
        return event.person().name()
    elif event.relationship() and event.relationshipTargets():
        return f"{event.relationship().name()} with {', '.join(target.name() for target in event.relationshipTargets())}"
    else:
        return "Unknown"


class CopilotEngine(QObject):
    """
    Simply translates the UI into a REST request.
    """

    requestSent = pyqtSignal(str)
    responseReceived = pyqtSignal(
        str, str, int, arguments=["response", "sources", "numSources"]
    )
    serverError = pyqtSignal(str)
    serverDown = pyqtSignal()

    def __init__(self, session, searchModel):
        super().__init__()
        self._session = session
        self._scene: Scene = None
        self._searchModel = searchModel

    def setScene(self, scene):
        self._scene = scene

    @pyqtSlot(str, bool)
    def ask(self, question: str, includeTags: bool = None):
        self._ask(question, includeTags)

    def _ask(self, question: str, includeTags: bool = None):
        """
        Mockable because qml latches on to slots at init time.
        """

        def onSuccess(data):
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
            events = self._scene.events(tags=self._searchModel.tags, onlyDated=True)
        else:
            events = []

        args = {
            "question": question,
            "session": self._session.token,
            "events": [
                {
                    "dateTime": util.dateTimeString(event.dateTime()),
                    "description": event.description(),
                    "people": _eventParentName(event),
                    "variables": {
                        prop["attr"]: event.dynamicProperty(prop["attr"]).get()
                        for prop in self._scene.eventProperties()
                    },
                }
                for event in events
            ],
        }
        reply = self._session.server().nonBlockingRequest(
            "POST", "/copilot/chat", data=args, error=onError, success=onSuccess
        )
        self._session.track(f"CopilotEngine.ask: {question}")
        self.requestSent.emit(question)
