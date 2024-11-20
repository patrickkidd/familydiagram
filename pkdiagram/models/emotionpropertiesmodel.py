from pkdiagram.pyqt import QObject, QDateTime, qmlRegisterType, pyqtProperty
from pkdiagram import util
from pkdiagram.scene import Item, Emotion
from pkdiagram.models import ModelHelper
from pkdiagram.app import commands


class EmotionPropertiesModel(QObject, ModelHelper):

    PROPERTIES = Item.adjustedClassProperties(
        Emotion,
        [
            {"attr": "kindIndex", "type": int, "default": -1},
            {"attr": "intensityIndex", "type": int, "default": -1},
            {"attr": "personAId", "type": int, "default": -1},
            {"attr": "personBId", "type": int, "default": -1},
            {"attr": "startDateTime", "type": QDateTime},
            {"attr": "endDateTime", "type": QDateTime},
            {"attr": "startDateUnsure", "type": bool},
            {"attr": "endDateUnsure", "type": bool},
            {"attr": "startEventId", "type": int},
            {"attr": "endEventId", "type": int},
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
        elif attr == "startDateUnsure":
            ret = util.sameOf(self._items, lambda item: item.startEvent.unsure())
        elif attr == "endDateTime":
            x = util.sameOf(self._items, lambda item: item.endEvent.dateTime())
            ret = self.getterConvertTo(attr, x)
        elif attr == "endDateUnsure":
            ret = util.sameOf(self._items, lambda item: item.endEvent.unsure())
        elif attr == "startEventId":
            ret = util.sameOf(self._items, lambda item: item.startEvent.id)
        elif attr == "endEventId":
            ret = util.sameOf(self._items, lambda item: item.endEvent.id)
        elif attr == "personAId":
            ret = util.sameOf(
                self._items, lambda item: item.personA() and item.personA().id or -1
            )
        elif attr == "personBId":
            ret = util.sameOf(
                self._items, lambda item: item.personB() and item.personB().id or -1
            )
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
        elif attr == "startDateTime":
            x = self.setterConvertTo(attr, value)
            id = commands.nextId()
            for item in self._items:
                item.startEvent.setDateTime(x, undo=id)
        elif attr == "startDateUnsure":
            id = commands.nextId()
            for item in self._items:
                item.startEvent.setUnsure(value, undo=id)
        elif attr == "endDateTime":
            x = self.setterConvertTo(attr, value)
            id = commands.nextId()
            for item in self._items:
                item.endEvent.setDateTime(x, undo=id)
        elif attr == "endDateUnsure":
            id = commands.nextId()
            for item in self._items:
                item.endEvent.setUnsure(value, undo=id)
        elif attr == "personAId" and self._scene:
            person = self._scene.find(id=value)
            if self._addMode:
                for item in self._items:
                    item.setPersonA(person)
            else:
                id = commands.nextId()
                for item in self._items:
                    if person != item.personA():
                        commands.setEmotionPerson(item, personA=person, id=id)
        elif attr == "personBId" and self._scene:
            person = self._scene.find(id=value)
            if self._addMode:
                for item in self._items:
                    item.setPersonB(person)
            else:
                id = commands.nextId()
                for item in self._items:
                    if person != item.personB():
                        commands.setEmotionPerson(item, personB=person, id=id)
        return super().set(attr, value)

    def reset(self, attr):
        if attr == "intensityIndex":
            super().reset("intensity")
        elif attr == "startDateTime":
            id = commands.nextId()
            for item in self._items:
                item.startEvent.prop("dateTime").reset(undo=id)
        elif attr == "endDateTime":
            id = commands.nextId()
            for item in self._items:
                item.endEvent.prop("dateTime").reset(undo=id)
        super().reset(attr)

    @pyqtProperty(list, constant=True)
    def kindsMap(self):
        ret = [
            {"kind": kind, "label": entry["label"], "slug": entry["slug"]}
            for kind, entry in Emotion.ITEM_MAP.items()
        ]
        return ret


qmlRegisterType(EmotionPropertiesModel, "PK.Models", 1, 0, "EmotionPropertiesModel")
