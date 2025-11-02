import logging

from pkdiagram.pyqt import QObject, QDateTime, qmlRegisterType, pyqtProperty
from pkdiagram import util
from pkdiagram.scene import Item, Emotion
from .modelhelper import ModelHelper

_log = logging.getLogger(__name__)


class EmotionPropertiesModel(QObject, ModelHelper):

    PROPERTIES = Item.adjustedClassProperties(
        Emotion,
        [
            # {"attr": "kindIndex", "type": int, "default": -1},
            {"attr": "kindLabel"},
            {"attr": "intensityIndex", "type": int, "default": -1},
            {"attr": "itemName"},
            {"attr": "dyadic", "type": bool},
            {"attr": "canEditEvent", "type": bool, "default": False},
            {"attr": "startDateTime", "type": QDateTime, "default": QDateTime()},
            {"attr": "endDateTime", "type": QDateTime, "default": QDateTime()},
        ],
    )

    ModelHelper.registerQtProperties(PROPERTIES)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initModelHelper()

    def get(self, attr):
        ret = None
        # if attr == "kindIndex":
        #     kind = super().get("kind")
        #     if kind == -1:
        #         ret = -1
        #     else:
        #         kindsMap = self.kindsMap
        #         entry = next(x for x in kindsMap if x["kind"] == kind)
        #         ret = kindsMap.index(entry)
        if attr == "kindLabel":
            kind = util.sameOf(self._items, lambda item: item.kind())
            if kind is not None:
                ret = kind.name
            else:
                ret = ""
        if attr == "intensityIndex":
            allSame = util.sameOf(self._items, lambda x: x.prop("intensity").get())
            if allSame is not None:
                intensity = super().get("intensity")
                ret = util.emotionIntensityIndexFromIntensity(intensity)
            else:
                ret = self.defaultFor(attr)
        elif attr == "startDateTime":
            x = util.sameOf(self._items, lambda item: item.startDateTime())
            ret = self.getterConvertTo(attr, x)
        elif attr == "endDateTime":
            x = util.sameOf(self._items, lambda item: item.endDateTime())
            ret = self.getterConvertTo(attr, x)
        elif attr == "parentName":
            ret = util.sameOf(self._items, lambda item: item.kind().name)
        elif attr == "dyadic":
            ret = util.sameOf(self._items, lambda item: item.isDyadic())
        elif attr == "itemName":
            ret = util.sameOf(self._items, lambda item: item.kind().name)
        elif attr == "color":
            ret = util.sameOf(self._items, lambda item: item.color())
        elif attr == "notes":
            ret = util.sameOf(self._items, lambda item: item.notes())
        if ret is None and attr not in ("color", "notes", "event"):
            ret = super().get(attr)
        return ret

    def set(self, attr, value):
        if attr == "kindIndex" and self._scene:
            if value == -1:
                super().reset("kind")
            else:
                kind = self.kindsMap[value]["kind"]
                super().set("kind", kind)
            self.refreshProperty("dyadic")
        elif attr == "intensityIndex":
            intensity = util.emotionIntensityFromIndex(value)
            self.set("intensity", intensity)
        return super().set(attr, value)

    def reset(self, attr):
        if attr == "intensityIndex":
            super().reset("intensity")
        super().reset(attr)


qmlRegisterType(EmotionPropertiesModel, "PK.Models", 1, 0, "EmotionPropertiesModel")
