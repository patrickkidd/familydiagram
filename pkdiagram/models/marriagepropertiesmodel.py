from typing import Union

from btcopilot.schema import EventKind
from pkdiagram.pyqt import QObject, Qt, qmlRegisterType
from pkdiagram.scene import Item, Marriage, Property, Event
from pkdiagram.models import ModelHelper


class MarriagePropertiesModel(QObject, ModelHelper):

    PROPERTIES = Item.adjustedClassProperties(
        Marriage,
        [
            {"attr": "hideDetails", "convertTo": Qt.CheckState},
            {"attr": "hideDates", "convertTo": Qt.CheckState},
            {"attr": "bigFont", "convertTo": Qt.CheckState},
            {"attr": "personAName"},
            {"attr": "personBName"},
            {"attr": "personAId", "type": int},
            {"attr": "personBId", "type": int},
            {"attr": "married", "convertTo": Qt.CheckState},
            {"attr": "separated", "convertTo": Qt.CheckState},
            {"attr": "divorced", "convertTo": Qt.CheckState},
            {"attr": "anyMarriedEvents", "type": bool},
            {"attr": "anySeparatedEvents", "type": bool},
            {"attr": "anyDivorcedEvents", "type": bool},
        ],
    )

    ModelHelper.registerQtProperties(PROPERTIES)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initModelHelper()

    def onEventsChanged(self, item: Union[Property, Event]):
        """Undo+redo wasn't resetting date fields because it
        wasn't getting the added|removed signals.
        """
        if isinstance(item, Property):
            event = prop.item
        else:
            event = item
        if event.kind() == EventKind.Married:
            self.refreshProperty("anyMarriedEvents")
        elif event.kind() == EventKind.Separated:
            self.refreshProperty("anySeparatedEvents")
        elif event.kind() == EventKind.Divorced:
            self.refreshProperty("anyDivorcedEvents")

    def get(self, attr):
        ret = None

        if self._items:
            marriage = self._items[0]
            x = None
            if attr == "personAName":
                x = marriage.personA().name()
            elif attr == "personBName":
                x = marriage.personB().name()
            if attr == "personAId":
                x = marriage.personA().id
            elif attr == "personBId":
                x = marriage.personB().id
            elif attr == "anyMarriedEvents":
                x = marriage.anyMarriedEvents()
            elif attr == "anySeparatedEvents":
                x = marriage.anySeparatedEvents()
            elif attr == "anyDivorcedEvents":
                x = marriage.anyDivorcedEvents()
            if x is not None:
                ret = self.getterConvertTo(attr, x)
            else:
                ret = x
        if ret is None:
            ret = super().get(attr)
        return ret

    def set(self, attr, value):
        if attr == "scene":
            if self._scene:
                self._scene.eventAdded.disconnect(self.onEventsChanged)
                self._scene.eventChanged.disconnect(self.onEventsChanged)
                self._scene.eventRemoved.disconnect(self.onEventsChanged)
            if value:
                value.eventAdded.connect(self.onEventsChanged)
                value.eventChanged.connect(self.onEventsChanged)
                value.eventRemoved.connect(self.onEventsChanged)
        super().set(attr, value)


qmlRegisterType(MarriagePropertiesModel, "PK.Models", 1, 0, "MarriagePropertiesModel")
