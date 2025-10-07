from pkdiagram.pyqt import QObject, QDateTime, pyqtSlot, pyqtSignal
from .qobjecthelper import QObjectHelper
from .modelhelper import ModelHelper
from pkdiagram.scene import Item, Property, Event


class SearchModel(QObject, QObjectHelper):
    """Just a Scene-global placeholder for a bunch of properties."""

    changed = pyqtSignal()

    PROPERTIES = ModelHelper.registerQtProperties(
        [
            {"attr": "description", "type": str},
            {"attr": "startDateTime", "type": QDateTime, "default": QDateTime()},
            {"attr": "endDateTime", "type": QDateTime, "default": QDateTime()},
            {"attr": "loggedStartDateTime", "type": QDateTime, "default": QDateTime()},
            {"attr": "loggedEndDateTime", "type": QDateTime, "default": QDateTime()},
            {"attr": "nodal", "type": bool, "default": False},
            {"attr": "tags", "type": list},
            {"attr": "hideRelationships", "type": bool, "default": False},
            {"attr": "isBlank", "type": bool},
        ],
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._initializing = True

        # # Item-like hack
        # self._propertyListeners = []
        # self._properties = {}
        # for entry in self.PROPERTIES:
        #     _type = entry["type"] if "type" in entry else str
        #     _default = entry["default"] if "default" in entry else _type()
        #     prop = Property(self, attr=entry["attr"], type=_type, default=_default)
        #     prop.set(_default, notify=False)
        #     self._properties[entry["attr"]] = prop

        self.initQObjectHelper(storage=True)
        # self.startDateTimeChanged.connect(self.onChanged)
        # self.endDateTimeChanged.connect(self.onChanged)
        # self.loggedStartDateTimeChanged.connect(self.onChanged)
        # self.loggedEndDateTimeChanged.connect(self.onChanged)
        # self.descriptionChanged.connect(self.onChanged)
        # self.nodalChanged.connect(self.onChanged)
        # self.tagsChanged.connect(self.onChanged)
        # self.hideRelationshipsChanged.connect(self.onChanged)
        self._initializing = False

    @pyqtSlot()
    def clear(self):
        self.reset("description")
        self.reset("startDateTime")
        self.reset("endDateTime")
        self.reset("loggedStartDateTime")
        self.reset("loggedEndDateTime")
        self.reset("nodal")
        self.reset("tags")
        self.reset("hideRelationships")

    def get(self, attr):
        if attr == "isBlank":
            ret = True
            for name in (
                "description",
                "startDateTime",
                "endDateTime",
                "loggedStartDateTime",
                "loggedEndDateTime",
                "nodal",
                "tags",
                "hideRelationships",
            ):
                if getattr(self, name) != self.defaultFor(name):
                    ret = False
                    break
        else:
            ret = super().get(attr)
        return ret

    # Item-like hacks for TagsModel

    # def prop(self, attr):
    #     return self._properties[attr]

    # def addPropertyListener(self, x):
    #     if not x in self._propertyListeners:
    #         self._propertyListeners.append(x)

    # def removePropertyListener(self, x):
    #     if x in self._propertyListeners:
    #         self._propertyListeners.remove(x)

    def onQObjectHelperPropertyChanged(self, attr, value):
        if self._initializing:
            return
        if attr in (
            "description",
            "startDateTime",
            "endDateTime",
            "loggedStartDateTime",
            "loggedEndDateTime",
            "nodal",
            "tags",
        ):
            self.changed.emit()
            self.refreshProperty("isBlank")

        # # Item-like hack
        # prop = self._properties[attr]
        # prop.set(value, notify=False)
        # for item in self.__propertyListeners:
        #     item.onProperty(prop)

    # Verbs

    def shouldHide(self, event: Event):
        """Search kernel."""
        nullLoggedDate = bool(
            not event.loggedDateTime() or event.loggedDateTime().isNull()
        )
        hidden = False
        if self.nodal and not event.nodal():
            hidden = True
        elif self.hideRelationships and event.parent.isEmotion:
            hidden = True
        elif not event.dateTime() or event.dateTime().isNull():
            hidden = True
        elif (self.loggedStartDateTime or self.loggedEndDateTime) and nullLoggedDate:
            hidden = True
        elif (self.loggedStartDateTime and not nullLoggedDate) and QDateTime(
            event.loggedDateTime()
        ) < self.loggedStartDateTime:
            hidden = True
        elif (self.loggedEndDateTime and not nullLoggedDate) and QDateTime(
            event.loggedDateTime()
        ) > self.loggedEndDateTime:
            hidden = True
        elif self.startDateTime and QDateTime(event.dateTime()) < self.startDateTime:
            hidden = True
        elif self.endDateTime and QDateTime(event.dateTime()) > self.endDateTime:
            hidden = True
        elif self.description and (
            self.description.lower()
            not in (event.description().lower() if event.description() else "")
        ):
            hidden = True
        elif self.tags and not event.hasTags(self.tags):  # ignore search model tags
            hidden = True
        elif (
            event.parent
            and event.parent.isEmotion
            and event is event.parent.endEvent
            and event.parent.isSingularDate()
        ):
            hidden = True
        return hidden
