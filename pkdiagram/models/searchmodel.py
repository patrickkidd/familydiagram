import logging

from ..pyqt import QObject, QDateTime, pyqtSlot, pyqtSignal
from .qobjecthelper import QObjectHelper
from .modelhelper import ModelHelper
from ..objects import Layer

_log = logging.getLogger(__name__)


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
            {"attr": "category"},
            {"attr": "isBlank", "type": bool},
        ],
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._initializing = True
        self.initQObjectHelper(storage=True)
        # self.categoryChanged.connect(self.onChanged)
        # self.descriptionChanged.connect(self.onChanged)
        # self.endDateTimeChanged.connect(self.onChanged)
        # self.hideRelationshipsChanged.connect(self.onChanged)
        # self.loggedStartDateTimeChanged.connect(self.onChanged)
        # self.loggedEndDateTimeChanged.connect(self.onChanged)
        # self.startDateTimeChanged.connect(self.onChanged)
        # self.nodalChanged.connect(self.onChanged)
        # self.tagsChanged.connect(self.onChanged)
        self.initQObjectHelper(storage=True)
        self._initializing = False

    @pyqtSlot()
    def clear(self):
        self.reset("category")
        self.reset("description")
        self.reset("startDateTime")
        self.reset("endDateTime")
        self.reset("loggedStartDateTime")
        self.reset("loggedEndDateTime")
        self.reset("hideRelationships")
        self.reset("nodal")
        self.reset("tags")
        self.reset("hideRelationships")

    def get(self, attr):
        if attr == "isBlank":
            ret = True
            for name in (
                "category",
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

    def set(self, attr, value):
        if attr == "category" and self.scene:
            layer = self.scene.query1(type=Layer, name=value)
            if layer:
                iLayer = self.scene.layers().index(layer)
                self.set("tags", [value])
                self.scene.setExclusiveActiveLayerIndex(iLayer)
            else:
                _log.warning(f"Layer '{value}' not found.")
        super().set(attr, value)

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

    # Verbs

    def shouldHide(self, event):
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
