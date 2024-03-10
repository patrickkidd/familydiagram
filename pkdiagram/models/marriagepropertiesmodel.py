from ..pyqt import QObject, Qt, QDate, QDateTime, qmlRegisterType
from .. import util, objects
from ..util import EventKind
from .modelhelper import ModelHelper


class MarriagePropertiesModel(QObject, ModelHelper):

    PROPERTIES = objects.Item.adjustedClassProperties(
        objects.Marriage,
        [
            {"attr": "hideDetails", "convertTo": Qt.CheckState},
            {"attr": "bigFont", "convertTo": Qt.CheckState},
            {"attr": "personAName"},
            {"attr": "personBName"},
            {"attr": "personAId", "type": int},
            {"attr": "personBId", "type": int},
            {"attr": "married", "convertTo": Qt.CheckState},
            {"attr": "separated", "convertTo": Qt.CheckState},
            {"attr": "divorced", "convertTo": Qt.CheckState},
            {"attr": "everSeparated", "type": bool},
            {"attr": "everDivorced", "type": bool},
            {"attr": "anyMarriedEvents", "type": bool},
            {"attr": "anySeparatedEvents", "type": bool},
            {"attr": "anyDivorcedEvents", "type": bool},
            {"attr": "numEvents", "type": int},
        ],
    )

    ModelHelper.registerQtProperties(PROPERTIES)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initModelHelper()

    def onItemEventAddedOrRemoved(self, event):
        """Undo+redo wasn't resetting date fields because it
        wasn't getting the added|removed signals.
        """
        if event.uniqueId() == EventKind.Married.value:
            self.refreshProperty("anyMarriedEvents")
            self.refreshProperty("everMarried")
        elif event.uniqueId() == EventKind.Separated.value:
            self.refreshProperty("anySeparatedEvents")
            self.refreshProperty("everSeparated")
        elif event.uniqueId() == EventKind.Divorced.value:
            self.refreshProperty("everMarried")
            self.refreshProperty("everSeparated")
            self.refreshProperty("anyDivorcedEvents")
            self.refreshProperty("everDivorced")

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
            elif attr == "everMarried":
                x = marriage.everMarried()
            elif attr == "everSeparated":
                x = marriage.everSeparated()
            elif attr == "everDivorced":
                x = marriage.everDivorced()
            elif attr == "anyMarriedEvents":
                x = marriage.anyMarriedEvents()
            elif attr == "anySeparatedEvents":
                x = marriage.anySeparatedEvents()
            elif attr == "anyDivorcedEvents":
                x = marriage.anyDivorcedEvents()
            elif attr == "numEvents":
                x = len(marriage.events())
            if x is not None:
                ret = self.getterConvertTo(attr, x)
            else:
                ret = x
        if ret is None:
            ret = super().get(attr)
        return ret

    def set(self, attr, value):
        if attr == "items":
            if self._items:
                for item in self._items:
                    item.addPropertyListener
                    item.eventAdded.disconnect(self.onItemEventAddedOrRemoved)
                    item.eventRemoved.disconnect(self.onItemEventAddedOrRemoved)
            if value:
                for item in value:
                    item.eventAdded.connect(self.onItemEventAddedOrRemoved)
                    item.eventRemoved.connect(self.onItemEventAddedOrRemoved)
        super().set(attr, value)
        if attr == "married":
            self.refreshProperty("everMarried")
        elif attr == "separated":
            self.refreshProperty("everSeparated")
        elif attr == EventKind.Divorced.value:
            self.refreshProperty("everDivorced")


qmlRegisterType(MarriagePropertiesModel, "PK.Models", 1, 0, "MarriagePropertiesModel")
