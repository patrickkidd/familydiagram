import logging

from pkdiagram.pyqt import (
    Qt,
    QObject,
    pyqtSlot,
    qmlRegisterType,
)
from pkdiagram.scene import Item, Event, Emotion
from .modelhelper import ModelHelper
from pkdiagram.pyqt import pyqtSlot


_log = logging.getLogger(__name__)


class EventPropertiesModel(QObject, ModelHelper):

    PROPERTIES = Item.adjustedClassProperties(
        Event,
        [
            {"attr": "editText"},
            {"attr": "nodal", "convertTo": Qt.CheckState},
            {"attr": "unsure", "convertTo": Qt.CheckState},
            {"attr": "numWritable", "type": int, "constant": True},
            {"attr": "parentId", "type": int},
            {"attr": "parentIsPerson", "type": bool},
            {"attr": "parentIsMarriage", "type": bool},
            {"attr": "parentIsEmotion", "type": bool},
            {"attr": "includeOnDiagram", "convertTo": Qt.CheckState},
            {"attr": "anyColor", "type": bool, "default": False},
            {"attr": "isSetting", "type": bool, "default": False},
        ],
    )

    ModelHelper.registerQtProperties(PROPERTIES)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._isSetting = False
        self.initModelHelper()

    def onItemProperty(self, prop):
        """Filter out dynamic event properties."""
        if prop.name() == "color":
            self.refreshProperty("anyColor")
        if self.propAttrsFor(prop.name()):
            super().onItemProperty(prop)

    def get(self, attr):
        ret = None
        if attr == "numWritable":
            numWritable = 0
            if self._scene and self._scene.readOnly():
                pass
            elif self._items:
                for item in self._items:
                    if item.uniqueId() is None:
                        numWritable += 1
                        break
            ret = numWritable
        elif attr == "parentId":

            def getPID(item):
                if item.parent:
                    return item.parent.id
                else:
                    return -1

            ret = self.sameOf(attr, getPID)
            if ret is None:
                ret = -1
        elif attr == "parentIsPerson":
            ret = self.sameOf(
                attr, lambda item: item.parent and item.parent.isPerson or False
            )
        elif attr == "parentIsMarriage":
            ret = self.sameOf(
                attr, lambda item: item.parent and item.parent.isMarriage or False
            )
        elif attr == "parentIsEmotion":
            ret = self.sameOf(
                attr, lambda item: item.parent and item.parent.isEmotion or False
            )
        elif attr == "notes":
            ret = self.sameOf(attr, lambda item: item.notes())
        elif attr == "editText":
            if len(self._items) == 1:
                item = self._items[0]
                if not item.parent:
                    ret = "New Event"
                elif item.parent.isPerson:
                    itemLabel = item.parent.firstNameOrAlias()
                    ret = f"{itemLabel}: {item.description()} Event"
                elif item.parent.isEmotion:
                    itemLabel = Emotion.kindLabelForKind(item.parent.kind())
                    if item.uniqueId() == "emotionStartEvent":
                        ret = f"{itemLabel}: Start Event"
                    elif item.uniqueId() == "emotionEndEvent":
                        ret = f"{itemLabel}: End Event"
                elif item.parent.isMarriage:
                    ret = f"Pair-Bond: {item.description()} Event"
                else:
                    ret = "Event"
            else:
                ret = f"{len(self._items)} Events"
        elif attr == "anyColor":
            ret = self.any("color")
        elif attr == "isSetting":
            ret = self._isSetting
        else:
            ret = super().get(attr)
        return ret

    def set(self, attr, value):
        # Not ideal, but a blocker to prevent event properties from being hidden
        # during a real-time, i.e. not submitted in aggregate, datetime edit.
        # When a datetime changes, it triggers a reset on the timeline model's
        # rows, which triggers a selection change, which (correctly) hides the
        # event props, e.g. for when the selection is changed from the graphical
        # timeline.
        was_isSetting = self._isSetting
        self._isSetting = True
        self.refreshProperty("isSetting")

        if attr == "uniqueId":
            with self._scene.macro(f"Set event type"):
                for item in self._items:
                    # notify=False prevents onProperty('uniqueId') from calling
                    # updateDescription so we can do it ourselves with
                    # undo=True. Otherwise there is no way to undo the
                    # description to the previous, potentially custom value.
                    item.setUniqueId(value, undo=True)
                    item.updateDescription(undo=True)
            self.refreshProperty("uniqueId")
            self.refreshProperty("description")
        else:
            super().set(attr, value)
        if attr == "parentId" and self._scene:
            person = self._scene.find(id=value)
            if person:
                with self._scene.macro("Set event owner"):
                    for event in self._items:
                        if event.uniqueId() is None:
                            event.setParent(person, undo=True)
            self.refreshProperty("parentId")
        elif attr == "items":
            self.refreshProperty("numWritable")
        elif attr == "scene":
            self.refreshProperty("numWritable")
        elif attr == "location" and self._scene:
            self.refreshProperty("description")
        self._isSetting = was_isSetting
        self.refreshProperty("isSetting")

    @pyqtSlot(str)
    def reset(self, attr):
        if attr == "uniqueId":
            # Aggregate uniqueId and description props into single undo command
            with self._scene.macro("Reset event id"):
                for item in self.items:
                    # notify=False here so that description isn't automatically set in onProperty('uniqueId')
                    item.prop("uniqueId").reset(notify=False, undo=True)
                    item.prop("description").reset(notify=False, undo=True)
            self.refreshProperty("uniqueId")
            self.refreshProperty("description")
        else:
            super().reset(attr)


qmlRegisterType(EventPropertiesModel, "PK.Models", 1, 0, "EventPropertiesModel")
