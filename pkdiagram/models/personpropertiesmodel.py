from pkdiagram.pyqt import (
    Qt,
    QObject,
    QDate,
    QDateTime,
    qmlRegisterType,
)
from pkdiagram import util, scene
from pkdiagram.scene import EventKind, Person, Event
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
            {"attr": "everAdopted", "convertTo": Qt.CheckState},
            {"attr": "deceased", "convertTo": Qt.CheckState},
            {"attr": "primary", "convertTo": Qt.CheckState},
            {"attr": "hideDetails", "convertTo": Qt.CheckState},
            {"attr": "hideDates", "convertTo": Qt.CheckState},
            {"attr": "hideVariables", "convertTo": Qt.CheckState},
            {"attr": "bigFont", "convertTo": Qt.CheckState},
            {"attr": "age", "type": int, "default": -1},
            {"attr": "birthDateTime", "type": QDateTime, "default": QDateTime()},
            {"attr": "deceasedDateTime", "type": QDateTime, "default": QDateTime()},
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
        if not self._items or prop.item.person() not in self._items:
            return

        if prop.name() == "dateTime":
            if prop.item.kind() == EventKind.Birth:
                self.refreshProperty("birthDateTime")
            elif prop.item.kind() == EventKind.Death:
                self.refreshProperty("deceasedDateTime")

    def onItemEventAddedOrRemoved(self, event):
        """Undo+redo wasn't resetting date fields because it
        wasn't getting the added|removed signals.
        """
        if not self._items or event.person() not in self._items:
            return

        if event.kind() == EventKind.Birth:
            self.refreshProperty("birthDateTime")
        elif event.kind() == EventKind.Adopted:
            self.refreshProperty("everAdopted")
        elif event.kind() == EventKind.Death:
            self.refreshProperty("deceasedDateTime")

    def set(self, attr, value):
        if attr == "scene":
            if self._scene:
                self._scene.eventAdded.disconnect(self.onItemEventAddedOrRemoved)
                self._scene.eventRemoved.disconnect(self.onItemEventAddedOrRemoved)
                self._scene.eventChanged.disconnect(self.onEventProperty)
            super().set(attr, value)
            if self._scene:
                self._scene.eventAdded.connect(self.onItemEventAddedOrRemoved)
                self._scene.eventRemoved.connect(self.onItemEventAddedOrRemoved)
                self._scene.eventChanged.connect(self.onEventProperty)
            return
        elif attr == "sizeIndex":
            size = util.personSizeFromIndex(value)
            self.set("size", size)
        elif attr == "genderIndex":
            gender = util.personKindFromIndex(value)
            self.set("gender", gender)
        elif attr == "deemphasize":
            with self._scene.macro("Set person(s) deemphasized"):
                if value:
                    for item in self._items:
                        item.setItemOpacity(util.DEEMPHASIZED_OPACITY, undo=True)
                else:
                    for item in self._items:
                        item.prop("itemOpacity").reset(undo=True)
        # elif attr == "age":
        #     # Calculate birth year from age
        #     if self.deceased and self.deceasedDateTime:
        #         x = self.deceasedDateTime.addYears(-value)
        #     else:
        #         x = QDateTime.currentDateTime().addYears(-value)
        #     birthDateTime = QDateTime(QDate(x.date().year(), 1, 1))

        #     # Update birth events directly without using property setter
        #     with self._scene.macro("Set birth datetime from age"):
        #         for item in self._items:
        #             events = item.scene().eventsFor(item, kinds=EventKind.Birth)
        #             if events:
        #                 events[0].setDateTime(birthDateTime, undo=True)
        #             else:
        #                 self._scene.addItem(
        #                     Event(EventKind.Birth, item, dateTime=birthDateTime)
        #                 )
        #     self.refreshProperty("age")
        #     self.refreshProperty("birthDateTime")

        return super().set(attr, value)

    def get(self, attr):
        if not self._scene:
            return super().get(attr)
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
        elif attr == "birthDateTime":

            def get_birth_datetime(item):
                events = self._scene.eventsFor(item, kinds=EventKind.Birth)
                return events[0].dateTime() if events else QDateTime()

            ret = self.sameOf(attr, get_birth_datetime)
        elif attr == "everAdopted":
            adoptedEvents = {
                item: self._scene.eventsFor(item, kinds=EventKind.Adopted)
                for item in self._items
            }
            ret = util.sameOf(
                self._items,
                lambda item: len(self._scene.eventsFor(item, kinds=EventKind.Adopted))
                > 0,
            )
            if all(len(events) > 0 for events in adoptedEvents.values()):
                ret = Qt.Checked
            elif any(len(events) > 0 for events in adoptedEvents.values()):
                ret = Qt.PartiallyChecked
            else:
                ret = Qt.Unchecked
        elif attr == "deceasedDateTime":
            ret = util.sameOf(self._items, lambda x: x.deceasedDateTime())
            if ret is None:
                ret = QDateTime()
            x = 1
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
        elif attr == "itemPos":
            with self._scene.resettingSomeLayerProps():
                super().reset(attr)
        else:
            super().reset(attr)


qmlRegisterType(PersonPropertiesModel, "PK.Models", 1, 0, "PersonPropertiesModel")
