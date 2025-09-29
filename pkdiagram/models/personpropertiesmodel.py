from pkdiagram.pyqt import (
    Qt,
    QObject,
    QDate,
    QDateTime,
    qmlRegisterType,
)
from pkdiagram import util, scene
from pkdiagram.scene import LifeChange
from pkdiagram.models import ModelHelper


class PersonPropertiesModel(QObject, ModelHelper):

    PROPERTIES = scene.Item.adjustedClassProperties(
        scene.Person,
        [
            {"attr": "fullNameOrAlias"},
            {"attr": "showMiddleName", "convertTo": Qt.CheckState},
            {"attr": "showLastName", "convertTo": Qt.CheckState},
            {"attr": "showNickName", "convertTo": Qt.CheckState},
            {"attr": "adopted", "convertTo": Qt.CheckState},
            {"attr": "deceased", "convertTo": Qt.CheckState},
            {"attr": "primary", "convertTo": Qt.CheckState},
            {"attr": "hideDetails", "convertTo": Qt.CheckState},
            {"attr": "hideDates", "convertTo": Qt.CheckState},
            {"attr": "hideVariables", "convertTo": Qt.CheckState},
            {"attr": "bigFont", "convertTo": Qt.CheckState},
            {"attr": "age", "type": int, "default": -1},
            {"attr": "birthDateTime", "type": QDateTime, "default": QDateTime()},
            {"attr": "adoptedDateTime", "type": QDateTime, "default": QDateTime()},
            {"attr": "deceasedDateTime", "type": QDateTime, "default": QDateTime()},
            {"attr": "birthDateUnsure", "type": bool, "convertTo": Qt.CheckState},
            {"attr": "adoptedDateUnsure", "type": bool, "convertTo": Qt.CheckState},
            {"attr": "deceasedDateUnsure", "type": bool, "convertTo": Qt.CheckState},
            {"attr": "birthLocation"},
            {"attr": "adoptedLocation"},
            {"attr": "deceasedLocation"},
            {"attr": "deceasedReason"},
            {"attr": "sizeIndex", "type": int, "default": -1},
            {"attr": "genderIndex", "type": int, "default": -1},
            {
                "attr": "deemphasize",
                "type": bool,
                "default": None,
                "convertTo": Qt.CheckState,
            },
            {"attr": "isItemPosSetInCurrentLayer", "type": bool},
        ],
    )

    ModelHelper.registerQtProperties(PROPERTIES)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initModelHelper()

    def onItemProperty(self, prop):
        super().onItemProperty(prop)
        if prop.name() == "size":
            self.refreshProperty("sizeIndex")
        elif prop.name() == "gender":
            self.refreshProperty("genderIndex")
        elif prop.name() == "deemphasize":
            self.refreshProperty("color")
            self.refreshProperty("itemOpacity")
        elif prop.name() == "color":
            self.refreshProperty("deemphasize")
        elif prop.name() == "itemOpacity":
            self.refreshProperty("deemphasize")
        elif prop.name() in ("name", "middleName", "lastName", "nickName"):
            self.refreshProperty("fullNameOrAlias")
        elif prop.name() in ("birthDateTime", "deceasedDateTime", "deceased"):
            self.refreshProperty("age")
        elif prop.name() == "itemPos":
            self.refreshProperty("isItemPosSetInCurrentLayer")

    def onEventProperty(self, prop):
        if prop.name() == "dateTime":
            if prop.item.uniqueId() == LifeChange.Birth.value:
                self.refreshProperty("birthDateTime")
            elif prop.item.uniqueId() == LifeChange.Adopted.value:
                self.refreshProperty("adoptedDateTime")
            elif prop.item.uniqueId() == LifeChange.Death.value:
                self.refreshProperty("deceasedDateTime")
        elif prop.name() == "location":
            if prop.item.uniqueId() == LifeChange.Birth.value:
                self.refreshProperty("birthLocation")
            elif prop.item.uniqueId() == LifeChange.Adopted.value:
                self.refreshProperty("adoptedLocation")
            elif prop.item.uniqueId() == LifeChange.Death.value:
                self.refreshProperty("deceasedLocation")

    def onItemEventAddedOrRemoved(self, event):
        """Undo+redo wasn't resetting date fields because it
        wasn't getting the added|removed signals.
        """
        if event.uniqueId() == LifeChange.Birth.value:
            self.refreshProperty("birthDateTime")
            self.refreshProperty("birthLocation")
        elif event.uniqueId() == LifeChange.Adopted.value:
            self.refreshProperty("adoptedDateTime")
            self.refreshProperty("adoptedLocation")
        elif event.uniqueId() == LifeChange.Death.value:
            self.refreshProperty("deceasedDateTime")
            self.refreshProperty("deceasedLocation")

    def set(self, attr, value):
        if attr == "items":
            if self._items:
                for item in self._items:
                    item.eventChanged.disconnect(self.onEventProperty)
                    item.eventAdded.disconnect(self.onItemEventAddedOrRemoved)
                    item.eventRemoved.disconnect(self.onItemEventAddedOrRemoved)
            if value:
                for item in value:
                    item.eventChanged.connect(self.onEventProperty)
                    item.eventAdded.connect(self.onItemEventAddedOrRemoved)
                    item.eventRemoved.connect(self.onItemEventAddedOrRemoved)
        elif attr == "sizeIndex":
            size = util.personSizeFromIndex(value)
            self.set("size", size)
        elif attr == "genderIndex":
            gender = util.personKindFromIndex(value)
            self.set("gender", gender)
        elif attr == "deceasedLocation":
            with self._scene.macro("Set deceased location"):
                for item in self._items:
                    item.deathEvent.setLocation(value, undo=True)
        elif attr == "birthDateUnsure":
            with self._scene.macro("Set birth datetime unsure"):
                for item in self._items:
                    item.birthEvent.setUnsure(value, undo=True)
        elif attr == "adoptedDateUnsure":
            with self._scene.macro("Set adopted datetime unsure"):
                for item in self._items:
                    item.adoptedEvent.setUnsure(value, undo=True)
        elif attr == "deceasedDateUnsure":
            with self._scene.macro("Set deceased datetime unsure"):
                for item in self._items:
                    item.deathEvent.setUnsure(value, undo=True)
        elif attr == "deemphasize":
            with self._scene.macro("Set person(s) deemphasized"):
                if value:
                    for item in self._items:
                        item.setItemOpacity(util.DEEMPHASIZED_OPACITY, undo=True)
                else:
                    for item in self._items:
                        item.prop("itemOpacity").reset(undo=True)
        elif attr == "age":
            if self.deceased and self.deceasedDateTime:
                x = self.deceasedDateTime.addYears(-value)
            else:
                x = QDateTime.currentDateTime().addYears(-value)
            self.birthDateTime = QDateTime(QDate(x.date().year(), 1, 1))
            self.refreshProperty("age")
        elif attr in (
            "birthDateTime",
            "adoptedDateTime",
            "deceasedDateTime",
            "birthLocation",
            "adoptedLocation",
            "deceasedLocation",
        ):
            x = self.setterConvertTo(attr, value)
            with self._scene.macro(f"Set '{attr}' on person(s)"):
                if attr == "birthDateTime":
                    [item.birthEvent.setDateTime(x, undo=True) for item in self._items]
                    self.refreshProperty("age")
                elif attr == "adoptedDateTime":
                    [
                        item.adoptedEvent.setDateTime(x, undo=True)
                        for item in self._items
                    ]
                elif attr == "deceasedDateTime":
                    [item.deathEvent.setDateTime(x, undo=True) for item in self._items]
                    self.refreshProperty("age")
                elif attr == "birthLocation":
                    [item.birthEvent.setLocation(x, undo=True) for item in self._items]
                elif attr == "adoptedLocation":
                    [
                        item.adoptedEvent.setLocation(x, undo=True)
                        for item in self._items
                    ]
                elif attr == "deceasedLocation":
                    [item.deathEvent.setLocation(x, undo=True) for item in self._items]
        return super().set(attr, value)

    def get(self, attr):
        ret = None
        if attr == "fullNameOrAlias":
            ret = self.sameOf(attr, lambda item: item.fullNameOrAlias())
        elif attr == "sizeIndex":
            allSame = util.sameOf(self._items, lambda x: x.prop("size").get())
            if allSame is not None:
                size = super().get("size")
                ret = util.personSizeIndexFromSize(size)
            else:
                ret = self.defaultFor(attr)
        elif attr == "genderIndex":
            allSame = util.sameOf(self._items, lambda x: x.prop("gender").get())
            if allSame is not None:
                gender = super().get("gender")
                ret = util.personKindIndexFromKind(gender)
            else:
                ret = self.defaultFor(attr)
        elif attr == "deemphasize":
            if self._items:
                # can't think through why this doesn't get calculated automatically
                allSame = True
                last = self._items[0].itemOpacity()
                for item in self._items[1:]:
                    if item.itemOpacity() != last:
                        allSame = False
                        break
                if not allSame:
                    ret = Qt.PartiallyChecked
                elif last == util.DEEMPHASIZED_OPACITY:
                    ret = Qt.Checked
                else:
                    ret = Qt.Unchecked
            else:
                ret = Qt.Unchecked
        elif attr == "isItemPosSetInCurrentLayer":
            ret = self.sameOf(attr, lambda item: item.prop("itemPos").isUsingLayer())
            if ret is None:
                ret = False
        elif attr == "notes":
            ret = self.sameOf(attr, lambda item: item.notes())  # obsolete?
        elif attr == "age":
            ret = self.sameOf(attr, lambda item: item.age())
        elif attr in (
            "birthDateTime",
            "adoptedDateTime",
            "deceasedDateTime",
            "birthLocation",
            "adoptedLocation",
            "deceasedLocation",
            "birthDateUnsure",
            "adoptedDateUnsure",
            "deceasedDateUnsure",
        ):
            if attr == "birthDateTime":
                x = self.sameOf(attr, lambda item: item.birthEvent.dateTime())
            elif attr == "adoptedDateTime":
                x = self.sameOf(attr, lambda item: item.adoptedEvent.dateTime())
            elif attr == "deceasedDateTime":
                x = self.sameOf(attr, lambda item: item.deathEvent.dateTime())
            elif attr == "birthLocation":
                x = self.sameOf(attr, lambda item: item.birthEvent.location())
            elif attr == "adoptedLocation":
                x = self.sameOf(attr, lambda item: item.adoptedEvent.location())
            elif attr == "deceasedLocation":
                x = self.sameOf(attr, lambda item: item.deathEvent.location())
            elif attr == "birthDateUnsure":
                x = self.sameOf(attr, lambda item: item.birthEvent.unsure())
            elif attr == "adoptedDateUnsure":
                x = self.sameOf(attr, lambda item: item.adoptedEvent.unsure())
            elif attr == "deceasedDateUnsure":
                x = self.sameOf(attr, lambda item: item.deathEvent.unsure())
            else:
                x = super().get(attr)
            ret = self.getterConvertTo(attr, x)
        else:
            ret = super().get(attr)
        return ret

    def reset(self, attr):
        if attr == "sizeIndex":
            super().reset("size")
        elif attr == "genderIndex":
            super().reset("gender")
        elif attr == "deemphasize":
            super().reset("itemOpacity")
        elif attr == "birthDateTime":
            with self._scene.macro("Reset birth datetime"):
                for item in self._items:
                    item.birthEvent.prop("dateTime").reset(undo=True)
        elif attr == "adoptedDateTime":
            with self._scene.macro("Reset adopted datetime"):
                for item in self._items:
                    item.adoptedEvent.prop("dateTime").reset(undo=True)
        elif attr == "deceasedDateTime":
            with self._scene.macro("Reset deceased datetime"):
                for item in self._items:
                    item.deathEvent.prop("dateTime").reset(undo=True)
        elif attr == "birthLocation":
            with self._scene.macro("Reset birth location"):
                for item in self._items:
                    item.birthEvent.prop("location").reset(undo=True)
        elif attr == "adoptedLocation":
            with self._scene.macro("Reset adopted location"):
                for item in self._items:
                    item.adoptedEvent.prop("location").reset(undo=True)
        elif attr == "deceasedLocation":
            with self._scene.macro("Reset deceased location"):
                for item in self._items:
                    item.deathEvent.prop("location").reset(undo=True)
        elif attr == "itemPos":
            with self.scene.resettingSomeLayerProps():
                super().reset(attr)
        else:
            super().reset(attr)


qmlRegisterType(PersonPropertiesModel, "PK.Models", 1, 0, "PersonPropertiesModel")
