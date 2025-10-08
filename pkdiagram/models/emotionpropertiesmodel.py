from pkdiagram.pyqt import QObject, QDateTime, qmlRegisterType, pyqtProperty
from pkdiagram import util
from pkdiagram.scene import Item, Emotion
from .modelhelper import ModelHelper


class EmotionPropertiesModel(QObject, ModelHelper):

    PROPERTIES = Item.adjustedClassProperties(
        Emotion,
        [
            {"attr": "kindIndex", "type": int, "default": -1},
            {"attr": "intensityIndex", "type": int, "default": -1},
            {"attr": "itemName"},
            {"attr": "dyadic", "type": bool},
        ],
    )

    ModelHelper.registerQtProperties(PROPERTIES)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initModelHelper()

    def get(self, attr):
        ret = None
        if attr == "kindIndex":
            kind = super().get("kind")
            if kind == -1:
                ret = -1
            else:
                kindsMap = self.kindsMap
                entry = next(x for x in kindsMap if x["kind"] == kind)
                ret = kindsMap.index(entry)
        elif attr == "intensityIndex":
            allSame = util.sameOf(self._items, lambda x: x.prop("intensity").get())
            if allSame is not None:
                intensity = super().get("intensity")
                ret = util.emotionIntensityIndexFromIntensity(intensity)
            else:
                ret = self.defaultFor(attr)
        elif attr == "startDateTime":
            x = util.sameOf(self._items, lambda item: item.startEvent.dateTime())
            ret = self.getterConvertTo(attr, x)
        elif attr == "endDateTime":
            x = util.sameOf(self._items, lambda item: item.endEvent.dateTime())
            ret = self.getterConvertTo(attr, x)
        elif attr == "startEventId":
            ret = util.sameOf(self._items, lambda item: item.startEvent.id)
        elif attr == "endEventId":
            ret = util.sameOf(self._items, lambda item: item.endEvent.id)
        elif attr == "parentName":
            ret = util.sameOf(self._items, lambda item: item.kind().name)
        elif attr == "dyadic":
            ret = util.sameOf(self._items, lambda item: item.isDyadic())
        if ret is None:
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
