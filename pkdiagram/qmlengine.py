from .pyqt import pyqtSlot, QQmlEngine, QQmlError, QObject, QApplication
from . import util, commands, qmlutil, qmlvedana

from pkdiagram.models import (
    SceneModel,
    SearchModel,
    TimelineModel,
    PeopleModel,
    AccessRightsModel,
)


class CommandsWrapper(QObject):

    @pyqtSlot(str)
    def trackView(self, s):
        commands.trackView(s)


class QmlEngine(QQmlEngine):
    """
    Contains the basic context properties available to every view.

    A new instance of this is managed along with every new DocumentView instance.
    """

    def __init__(self, parent, session):
        super().__init__(parent)
        for path in util.QML_IMPORT_PATHS:
            self.addImportPath(path)
        self.commands = CommandsWrapper(self)
        self.util = QApplication.instance().qmlUtil()  # should be local, not global
        self.vedana = qmlvedana.QmlVedana(self)
        self._errors = []

        # Models

        self.session = session

        self.sceneModel = SceneModel(self)
        self.sceneModel.session = session

        self.searchModel = SearchModel(self)

        self.timelineModel = TimelineModel(self)
        self.timelineModel.searchModel = self.searchModel

        self.peopleModel = PeopleModel(self)

        self.accessRightsModel = AccessRightsModel(self)
        self.accessRightsModel.setSession(self.session)

        self.rootContext().setContextProperty("engine", self)
        self.rootContext().setContextProperty("util", self.util)
        self.rootContext().setContextProperty("commands", self.commands)
        self.rootContext().setContextProperty("vedana", self.vedana)
        self.rootContext().setContextProperty("session", self.session)
        self.rootContext().setContextProperty("sceneModel", self.sceneModel)
        self.rootContext().setContextProperty("searchModel", self.searchModel)
        self.rootContext().setContextProperty("timelineModel", self.timelineModel)
        self.rootContext().setContextProperty("peopleModel", self.peopleModel)
        self.rootContext().setContextProperty(
            "accessRightsModel", self.accessRightsModel
        )

    def deinit(self):
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

    def setServerDiagram(self, diagram):
        self.sceneModel.setServerDiagram(diagram)
        self.accessRightsModel.setServerDiagram(diagram)

    def onWarnings(self, qmlErrors: list[QQmlError]):
        self._errors.extend(qmlErrors)
