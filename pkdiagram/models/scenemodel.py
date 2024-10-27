from ..pyqt import (
    QObject,
    QVariant,
    pyqtSlot,
    pyqtSignal,
    QItemSelectionModel,
    QMessageBox,
    QApplication,
    qmlRegisterType,
    QQmlEngine,
)
from .. import objects, util, commands
from ..scene import Scene
from .modelhelper import ModelHelper
from .peoplemodel import PeopleModel
from .timelinemodel import TimelineModel
from .searchmodel import SearchModel
from .categoriesmodel import CategoriesModel
from .accessrightsmodel import AccessRightsModel
from ..session import Session
from ..server_types import Diagram


class SceneModel(QObject, ModelHelper):

    NEW_VAR_TMPL = "Variable %i"

    addEvent = pyqtSignal([QVariant, QVariant])
    addEmotion = pyqtSignal([], [QVariant])
    selectionChanged = pyqtSignal()  # called from prop sheets (deprecated)
    searchChanged = pyqtSignal()
    trySetShowAliases = pyqtSignal(bool)
    inspectItem = pyqtSignal(int)
    flashItems = pyqtSignal(list)
    uploadToServer = pyqtSignal()

    PROPERTIES = objects.Item.adjustedClassProperties(
        Scene,
        [
            {"attr": "timelineModel", "type": QVariant, "default": None},
            {"attr": "searchModel", "type": QVariant, "default": None},
            {"attr": "peopleModel", "type": QVariant, "default": None},
            {"attr": "accessRightsModel", "type": QVariant, "default": None},
            {"attr": "categoriesModel", "type": QVariant, "default": None},
            {"attr": "hasActiveLayers", "type": bool},
            {"attr": "authenticated", "type": bool, "default": False},
            {"attr": "eventPropertiesTemplateIndex", "type": int, "default": -1},
            {"attr": "session", "type": QObject},
            {"attr": "isOnServer", "type": bool},
            {"attr": "isMyDiagram", "type": bool},
            {"attr": "isInEditorMode", "type": bool},
        ],
    )

    ModelHelper.registerQtProperties(PROPERTIES)

    def __init__(self, parent=None, session=None):
        super().__init__(parent)
        if session:
            self._session = session
        else:
            self._session = Session()
        # Not the singleton, one of the provisional placeholders
        self._nullTimelineModel = TimelineModel(self)
        self._nullTimelineModel.setObjectName("nullTimelineModel")
        self._nullSearchModel = SearchModel(self)
        self._nullSearchModel.setObjectName("nullSearchModel")
        self._nullPeopleModel = PeopleModel(self)
        self._nullPeopleModel.setObjectName("nullPeopleModel")
        self._nullAccessRightsModel = AccessRightsModel(self)
        self._nullAccessRightsModel.setObjectName("accessRightModel")
        self._nullCategoriesModel = CategoriesModel(self)
        self._nullCategoriesModel.setObjectName("categoriesModel")
        self._activeFeatures = []
        self._isInEditorMode = False
        self.initModelHelper(storage=True)

    def setServerDiagram(self, diagram):
        self._scene.setServerDiagram(diagram)
        self.refreshProperty("isOnServer")
        self.refreshProperty("isMyDiagram")

    def get(self, attr):
        ret = None
        if attr == "hasActiveLayers":
            if self._scene:
                ret = self._scene.hasActiveLayers
            else:
                ret = False
        elif attr == "isOnServer":
            if self._scene:
                ret = self._scene.serverDiagram() is not None
            else:
                ret = False
        elif attr == "isMyDiagram":
            if self._scene and self._scene.serverDiagram() and self._session.user:
                ret = (
                    self._session.user.username
                    == self._scene.serverDiagram().user.username
                )
            else:
                ret = False
        elif attr == "isInEditorMode":
            if util.isInstance(self.parent(), "DocumentView"):
                ret = self._isInEditorMode
            else:
                ret = False
        elif attr == "timelineModel":
            if self._scene:
                ret = self._scene.timelineModel
            else:
                ret = self._nullTimelineModel
        elif attr == "searchModel":
            if self._scene:
                ret = self._scene.searchModel
            else:
                return self._nullSearchModel
        elif attr == "peopleModel":
            if self._scene:
                ret = self._scene.peopleModel
            else:
                ret = self._nullPeopleModel
        elif attr == "accessRightsModel":
            if self._scene:
                ret = self._scene.accessRightsModel
            else:
                ret = self._nullAccessRightsModel
        elif attr == "categoriesModel":
            if self._scene:
                ret = self._scene.categoriesModel
            else:
                ret = self._nullCategoriesModel
        elif attr == "session":
            ret = self._session
        else:
            ret = super().get(attr)
        return ret

    def set(self, attr, value):
        if attr == "scene":
            if self._scene:
                self._scene.activeLayersChanged.disconnect(self.onActiveLayersChanged)
                self._scene.searchModel.changed.disconnect(self.onSearchChanged)
                self._scene.removePropertyListener(self)
        super().set(attr, value)
        if attr == "scene":
            if self._scene:
                self._scene.activeLayersChanged.connect(self.onActiveLayersChanged)
                self._scene.searchModel.changed.connect(self.onSearchChanged)
                items = [self._scene]
                self._scene.addPropertyListener(self)
                self._scene.setSession(self.session)
            else:
                items = []
            super().set("authenticated", False)
            self._blockRefresh = True
            self.set("items", items)
            self._blockRefresh = False
            self.refreshAllProperties()
        elif attr == "eventPropertiesTemplateIndex":
            self.setEventPropertiesTemplateIndex(value)

    def onActiveLayersChanged(self):
        self.refreshProperty("hasActiveLayers")

    def onItemProperty(self, prop):
        """Changed signals for scene properties have to be accounted for here."""
        if prop.name() in ("readOnly", "currentDateTime"):
            self.refreshProperty(prop.name())

    def onSearchChanged(self):
        if self._scene:
            if (
                self._scene.searchModel.hideRelationships
                != self._scene.hideEmotionalProcess
            ):
                self._scene.setHideEmotionalProcess(
                    self._scene.searchModel.hideRelationships
                )
        self.searchChanged.emit()

    def onEditorMode(self, on):
        self._isInEditorMode = on
        self.refreshProperty("isInEditorMode")

    @pyqtSlot(int)
    @util.blocked
    def setEventPropertiesTemplateIndex(self, index):
        if index < 0 or not self._scene:
            return
        propAttrs = [entry["attr"] for entry in self._scene.eventProperties()]
        if self._scene.eventProperties():
            hasPropSet = 0
            for event in self._scene.events():
                for attr in propAttrs:
                    prop = event.dynamicProperty(attr)
                    if prop.get() is not None:
                        hasPropSet += 1
            if hasPropSet:
                btn = QMessageBox.question(
                    QApplication.activeWindow(),
                    "Delete existing timeline variables?",
                    "This will replace the existing timeline variables and their %i values with variables from the template. Are you sure you want to do this?"
                    % hasPropSet,
                )
                if btn == QMessageBox.No:
                    return
        newProps = []
        if index == 0:  # Havstad Model
            newProps = ["Δ Symptom", "Δ Anxiety", "Δ Functioning", "Δ Relationship"]
        elif index == 1:  # Papero Model
            newProps = [
                "Resourcefulness",
                "Tension Management",
                "Connectivity & Integration",
                "Systems Thinking",
                "Goal Structure",
            ]
        elif index == 2:  # Stinson Model
            newProps = ["Toward/Away", "Δ Arousal", "Δ Symptom", "Mechanism"]
        commands.replaceEventProperties(self._scene, newProps)
        # for name in [e['name'] for e in self._scene.eventProperties()]:
        #     commands.removeEventProperty(self._scene, name)
        # for name in newProps:
        #     commands.createEventProperty(self._scene, name)

    @pyqtSlot()
    def addEventProperty(self):
        name = util.newNameOf(
            self._scene.eventProperties(),
            tmpl=self.NEW_VAR_TMPL,
            key=lambda x: x["name"],
        )
        commands.createEventProperty(self._scene, name)

    @pyqtSlot(int)
    def removeEventProperty(self, index):
        entry = self._scene.eventProperties()[index]
        commands.removeEventProperty(self._scene, entry["name"])

    @pyqtSlot(QItemSelectionModel)
    def flashTimelineItems(self, selectionModel):
        model = selectionModel.model()
        selection = selectionModel.selectedRows()
        items = [model.idForRow(index.row()) for index in selection]
        if items:
            self.flashItems.emit(items)

    @pyqtSlot(int)
    def flashTimelineItem(self, row):
        id = self.scene.timelineModel.idForRow(row)
        if id is not None:
            self.flashItems.emit([id])

    @pyqtSlot(int, result=QObject)
    def item(self, id):
        ret = self.scene.findById(id)
        QQmlEngine.setObjectOwnership(ret, QQmlEngine.CppOwnership)
        return ret


def __test__(scene, parent):
    pass  # set in global


qmlRegisterType(SceneModel, "PK.Models", 1, 0, "SceneModel")
