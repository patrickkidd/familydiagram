from pkdiagram.pyqt import QObject, Qt, qmlRegisterType
from pkdiagram.scene import EventKind, Item, Marriage
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

    def onEventsChanged(self, event):
        """Undo+redo wasn't resetting date fields because it
        wasn't getting the added|removed signals.
        """
        marriage = event.marriage()
        if not marriage and marriage in self._items:
            if event.kind() == EventKind.Married:
                self.refreshProperty("anyMarriedEvents")
                self.refreshProperty("everMarried")
            elif event.kind() == EventKind.Separated:
                self.refreshProperty("anySeparatedEvents")
                self.refreshProperty("everSeparated")
            elif event.kind() == EventKind.Divorced:
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
        if attr == "married":
            self.refreshProperty("everMarried")
        elif attr == "separated":
            self.refreshProperty("everSeparated")
        elif attr == EventKind.Divorced.value:
            self.refreshProperty("everDivorced")


qmlRegisterType(MarriagePropertiesModel, "PK.Models", 1, 0, "MarriagePropertiesModel")
