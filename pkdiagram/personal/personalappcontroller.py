import logging
from typing import Callable

from _pkdiagram import CUtil
from pkdiagram import pepper
from pkdiagram.app import AppConfig
from pkdiagram.pyqt import (
    QObject,
    QApplication,
    QQmlEngine,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
    QNetworkReply,
    QNetworkRequest,
)
from pkdiagram.app import Session, Analytics
from pkdiagram.personal.models import Diagram, Discussion
from pkdiagram.scene import Scene
from pkdiagram.models import SceneModel, PeopleModel
from pkdiagram.views import EventForm

_log = logging.getLogger(__name__)


class PersonalAppController(QObject):
    """
    App controller for the personal app.

    Contains the user's one free diagram.
    """

    requestSent = pyqtSignal(str)
    responseReceived = pyqtSignal(str, dict, arguments=["statement", "pdp"])
    serverError = pyqtSignal(str)
    serverDown = pyqtSignal()

    discussionsChanged = pyqtSignal()
    pdpChanged = pyqtSignal()
    diagramChanged = pyqtSignal()
    statementsChanged = pyqtSignal()

    def __init__(self, app: QApplication, parent=None):
        super().__init__(parent)

        self.app = app
        self._diagram: Diagram | None = None
        self._discussions = []
        self._currentDiscussion: Discussion | None = None
        self._pdp: dict | None = None
        self.scene = None

        self.util = QApplication.instance().qmlUtil()  # should be local, not global

        self.analytics = Analytics(datadog_api_key=pepper.DATADOG_API_KEY)
        self.session = Session(self.analytics)
        self.session.changed.connect(self.onSessionChanged)

        self.appConfig = AppConfig(self, prefsName="personal.alaskafamilysystems.com")
        self.sceneModel = SceneModel(self)
        self.sceneModel.session = self.session
        self.peopleModel = PeopleModel(self)
        self.eventForm = None

    def init(self, engine: QQmlEngine):
        engine.rootContext().setContextProperty("CUtil", CUtil.instance())
        engine.rootContext().setContextProperty("util", self.util)
        engine.rootContext().setContextProperty("session", self.session)
        engine.rootContext().setContextProperty("personalApp", self)
        engine.rootContext().setContextProperty("sceneModel", self.sceneModel)
        engine.rootContext().setContextProperty("peopleModel", self.peopleModel)
        self.eventForm = EventForm(self.rootObject(), self)
        self.analytics.init()
        self.appConfig.init()
        self.session.setQmlEngine(engine)
        lastSessionData = self.appConfig.get("lastSessionData", pickled=True)
        if lastSessionData and not self.appConfig.wasTamperedWith:
            self.session.init(sessionData=lastSessionData)
            self._refreshDiagram()
            self._refreshPDP()
        else:
            self.session.init()

    def deinit(self):
        self.analytics.init()
        self.session.deinit()
        self.eventView

    def setScene(self, scene: Scene):
        self.scene = scene
        self.peopleModel.scene = scene
        self.sceneModel.scene = scene
        self.eventForm.setScene(scene)

    def rootObject(self) -> QObject:
        return self.rootObjects()[0]

    def exec(self, mw):
        """
        Stuff that happens once per app load on the first MainWindow.
        At this point the MainWindow is fully initialized with a session
        and ready for app-level verbs.
        """
        self.app.exec()

    def onError(self, reply: QNetworkReply):
        if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 0:
            self.serverDown.emit()
        else:
            self.serverError.emit(reply.errorString())

    def onSessionChanged(self, oldFeatures, newFeatures):
        """Called on login, logout, invalidated token."""

        if self.session.isLoggedIn():
            self.appConfig.set("lastSessionData", self.session.data(), pickled=True)
        else:
            self.appConfig.delete("lastSessionData")
        self.appConfig.write()

        #

        if not self.session.user:
            self._diagram = None
            self._discussions = []
            self._pdp = {}
            self._currentDiscussion = None
        else:
            self._refreshDiagram()
            self._refreshPDP()
        self.discussionsChanged.emit()
        self.statementsChanged.emit()
        self.pdpChanged.emit()
        self.diagramChanged.emit()

    # Diagram

    @pyqtProperty("QVariantMap", notify=diagramChanged)
    def diagram(self):
        return self._diagram if self._diagram is not None else {}

    def _refreshDiagram(self):
        if not self.session.user:
            return

        def onSuccess(data):
            if "diagram_data" in data:
                data.pop("diagram_data")
            self._diagram = Diagram(**data)
            self._discussions = [Discussion.create(x) for x in data["discussions"]]
            self.discussionsChanged.emit()
            self.statementsChanged.emit()
            self.pdpChanged.emit()

        reply = self.session.server().nonBlockingRequest(
            "GET",
            f"/personal/diagrams/{self.session.user.free_diagram_id}",
            data={},
            error=lambda: self.onError(reply),
            success=onSuccess,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            from_root=True,
        )

    # Discussions

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

        reply = self.session.server().nonBlockingRequest(
            "POST",
            "/personal/discussions/",
            data={"diagram_id": self._diagram.id},
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
            url = f"/personal/discussions/{self._currentDiscussion.id}/statements"
        else:
            url = "/personal/discussions/"
        args = {"statement": statement}
        reply = self.session.server().nonBlockingRequest(
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
        self.session.track(f"personal.Engine.sendStatement: {statement}")
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

        reply = self.session.server().nonBlockingRequest(
            "GET",
            "/personal/pdp",
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
        reply = self.session.server().nonBlockingRequest(
            "POST",
            f"/personal/diagrams/{self._diagram.id}/pdp/{-id}/accept",
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
        reply = self.session.server().nonBlockingRequest(
            "POST",
            f"/personal/diagrams/{self._diagram.id}/pdp/{-id}/reject",
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
