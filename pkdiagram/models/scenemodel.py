import logging

from pkdiagram.pyqt import (
    QDateTime,
    QObject,
    QVariant,
    pyqtSlot,
    pyqtSignal,
    qmlRegisterType,
    QQmlEngine,
)
from pkdiagram import scene, util
from ..scene import Scene
from .modelhelper import ModelHelper

_log = logging.getLogger(__name__)


class SceneModel(QObject, ModelHelper):
    """
    The main entry point for binding to scene properties, and also upstream
    communication with the DocumentView.
    """

    NEW_VAR_TMPL = "Variable %i"

    addEvent = pyqtSignal([QVariant, QVariant])
    addEmotion = pyqtSignal([], [QVariant])
    selectionChanged = pyqtSignal()  # called from prop sheets (deprecated)
    showSearch = pyqtSignal()
    searchChanged = pyqtSignal()
    trySetShowAliases = pyqtSignal(bool)
    inspectItem = pyqtSignal(int)
    flashItems = pyqtSignal(list)
    uploadToServer = pyqtSignal()

    PROPERTIES = scene.Item.adjustedClassProperties(
        Scene,
        [
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._activeFeatures = []
        self._isInEditorMode = False
        self._session = None  # probably shouldn't be here
        self.initModelHelper(storage=True)

    def setServerDiagram(self, diagram):
        self._scene.setServerDiagram(diagram)
        self.refreshProperty("isOnServer")
        self.refreshProperty("isMyDiagram")

    def onSceneProperty(self, prop):
        """Virtual"""
        super().onSceneProperty(prop)
        self.refreshProperty(prop.name())

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
            ret = self._isInEditorMode
        elif attr == "session":
            ret = self._session
        else:
            ret = super().get(attr)
        return ret

    def set(self, attr, value):
        if attr == "scene":
            if self._scene:
                self._scene.activeLayersChanged.disconnect(self.onActiveLayersChanged)
                self._scene.removePropertyListener(self)
        elif attr == "session":
            self._session = value
        super().set(attr, value)
        if attr == "scene":
            if self._scene:
                self._scene.activeLayersChanged.connect(self.onActiveLayersChanged)
                items = [self._scene]
                self._scene.addPropertyListener(self)
            else:
                items = []
            super().set("authenticated", False)
            self._blockRefresh = True
            self.set("items", items)
            self._blockRefresh = False
            self.refreshAllProperties()

    def onActiveLayersChanged(self):
        self.refreshProperty("hasActiveLayers")

    def onItemProperty(self, prop):
        """Changed signals for scene properties have to be accounted for here."""
        if prop.name() in ("readOnly", "currentDateTime"):
            self.refreshProperty(prop.name())

    def onEditorMode(self, on):
        self._isInEditorMode = on
        self.refreshProperty("isInEditorMode")

    @pyqtSlot()
    def onUploadToServer(self):
        """
        Just here to avoid signals connected to signals for debugging purposes.
        """
        self.uploadToServer.emit()

    @pyqtSlot(int, result=QObject)
    def item(self, id):
        ret = self.scene.findById(id)
        QQmlEngine.setObjectOwnership(ret, QQmlEngine.CppOwnership)
        return ret

    @pyqtSlot(QDateTime)
    def setCurrentDateTime(self, dateTime: QDateTime):
        if self._scene:
            self._scene.setCurrentDateTime(dateTime, undo=True)


def __test__(scene, parent):
    pass  # set in global


qmlRegisterType(SceneModel, "PK.Models", 1, 0, "SceneModel")
