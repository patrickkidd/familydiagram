from pkdiagram.pyqt import QQmlEngine, QQmlError, QApplication, QItemSelectionModel
from pkdiagram import util
from pkdiagram.models import (
    SceneModel,
    SearchModel,
    TimelineModel,
    PeopleModel,
    AccessRightsModel,
)
from pkdiagram.views import QmlVedana
from pkdiagram.models import CopilotEngine


class QmlEngine(QQmlEngine):
    """
    Contains the basic context properties available to every view. Each model
    type is only instantiated once, and then the properties are updated as the
    underlying scene data changes. This allows qml bindings to be set once since
    they are fragile, a pain to debug, and not terribly fast to init & deinit.

    A new instance of this is managed along with every new DocumentView
    instance.
    """

    def __init__(self, session, parent=None):
        super().__init__(parent)
        for path in util.QML_IMPORT_PATHS:
            self.addImportPath(path)
        self.util = QApplication.instance().qmlUtil()  # should be local, not global
        self.vedana = QmlVedana(self)
        self._errors = []

        # Models

        self.session = session
        self.session.setQmlEngine(self)

        self.sceneModel = SceneModel(self)
        self.sceneModel.session = session

        self.searchModel = SearchModel(self)
        self.copilot = CopilotEngine(self.session, self.searchModel)

        self.timelineModel = TimelineModel(self)
        self.timelineModel.searchModel = self.searchModel
        self.eventSelectionModel = QItemSelectionModel(self.timelineModel)

        self.peopleModel = PeopleModel(self)

        self.accessRightsModel = AccessRightsModel(self)
        self.accessRightsModel.setSession(self.session)

        self.rootContext().setContextProperty("engine", self)
        self.rootContext().setContextProperty("util", self.util)
        self.rootContext().setContextProperty("copilot", self.copilot)
        self.rootContext().setContextProperty("vedana", self.vedana)
        self.rootContext().setContextProperty("session", self.session)
        self.rootContext().setContextProperty("sceneModel", self.sceneModel)
        self.rootContext().setContextProperty("searchModel", self.searchModel)
        self.rootContext().setContextProperty("timelineModel", self.timelineModel)
        self.rootContext().setContextProperty(
            "eventSelectionModel", self.eventSelectionModel
        )
        self.rootContext().setContextProperty("peopleModel", self.peopleModel)
        self.rootContext().setContextProperty(
            "accessRightsModel", self.accessRightsModel
        )

    def deinit(self):
        self.util.deinit()
        self.session.deinit()

    def setScene(self, scene):
        self.sceneModel.scene = scene
        self.timelineModel.scene = scene
        if scene:
            self.timelineModel.items = [scene]
        else:
            self.timelineModel.items = []
        self.peopleModel.scene = scene
        self.accessRightsModel.scene = scene
        self.searchModel.scene = scene
        self.copilot.setScene(scene)

    def setServerDiagram(self, diagram):
        self.sceneModel.setServerDiagram(diagram)
        self.accessRightsModel.setServerDiagram(diagram)

    def onWarnings(self, qmlErrors: list[QQmlError]):
        self._errors.extend(qmlErrors)
