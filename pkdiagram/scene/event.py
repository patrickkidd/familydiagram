import os

from pkdiagram.app import commands
from pkdiagram.pyqt import QDateTime
from pkdiagram import util
from pkdiagram.scene import EventKind, Item


class Event(Item):

    Item.registerProperties(
        (
            {"attr": "dateTime", "type": QDateTime},
            {"attr": "unsure", "default": True},
            {"attr": "description"},
            {"attr": "nodal", "default": False},
            {"attr": "notes"},
            {"attr": "parentName"},
            {"attr": "location"},
            {"attr": "uniqueId"},  # TODO: Rename to `kind`, one of EventKind
            {"attr": "includeOnDiagram", "default": False},
        )
    )

    def __init__(self, parent=None, **kwargs):
        super().__init__(**kwargs)
        self.isEvent = True
        self.dynamicProperties = []  # { 'attr': 'symptom', 'name': '𝚫 Symptom' }
        if "id" in kwargs:
            self.id = kwargs["id"]
        if "addDummy" in kwargs:
            self.addDummy = kwargs["addDummy"]
            del kwargs["addDummy"]
        else:
            self.addDummy = False
        self._aliasDescription = None
        self._aliasNotes = None
        self._aliasParentName = None
        self._onShowAliases = False
        self.parent = None
        # avoid adding to the parent in various cases
        if parent:  # for tidyness in ctors
            self.setParent(parent, notify=False)
            self.updateDescription()

    def itemName(self):
        if self.parent:
            return "<%s>: %s" % (self.parent.itemName(), self.description())
        else:
            return str(self)

    def write(self, chunk):
        super().write(chunk)
        chunk["dynamicProperties"] = {}
        for prop in self.dynamicProperties:
            chunk["dynamicProperties"][prop.attr] = prop.get()

    def read(self, chunk, byId):
        super().read(chunk, byId)
        if self.dateTime() is not None and self.dateTime().isNull():
            self.setDateTime(None, notify=False)
        for attr, value in chunk.get("dynamicProperties", {}).items():
            prop = self.addDynamicProperty(attr)
            if prop:  # avoid duplicates
                prop.set(value, notify=False)

    def __lt__(self, other):
        if other.isEmotion:
            return True
        elif self.dateTime() and not other.dateTime():
            return True
        elif not self.dateTime() and other.dateTime():
            return False
        elif self.dateTime() and other.dateTime():
            return self.dateTime() < other.dateTime()
        elif self.parent == other.parent:
            if self.parent is None:
                return False
            elif self.parent.isPerson:
                if (
                    self.uniqueId() == EventKind.Birth.value
                    and other.uniqueId() == EventKind.Adopted.value
                ):
                    return True
                elif (
                    self.uniqueId() == EventKind.Birth.value
                    and other.uniqueId() == EventKind.Death.value
                ):
                    return True
                elif (
                    self.uniqueId() == EventKind.Adopted.value
                    and other.uniqueId() == EventKind.Birth.value
                ):
                    return False
                elif (
                    self.uniqueId() == EventKind.Adopted.value
                    and other.uniqueId() == EventKind.Death.value
                ):
                    return True
                elif (
                    self.uniqueId() == EventKind.Death.value
                    and other.uniqueId() == EventKind.Birth.value
                ):
                    return False
                elif (
                    self.uniqueId() == EventKind.Death.value
                    and other.uniqueId() == EventKind.Adopted.value
                ):
                    return False
            elif self.parent.isMarriage:
                if (
                    self.uniqueId() == EventKind.Married.value
                    and other.uniqueId() == EventKind.Separated.value
                ):
                    return True
                elif (
                    self.uniqueId() == EventKind.Married.value
                    and other.uniqueId() == EventKind.Divorced.value
                ):
                    return True
                elif (
                    self.uniqueId() == EventKind.Separated.value
                    and other.uniqueId() == EventKind.Married.value
                ):
                    return False
                elif (
                    self.uniqueId() == EventKind.Separated.value
                    and other.uniqueId() == EventKind.Divorced.value
                ):
                    return True
                elif (
                    self.uniqueId() == EventKind.Divorced.value
                    and other.uniqueId() == EventKind.Married.value
                ):
                    return False
                elif (
                    self.uniqueId() == EventKind.Divorced.value
                    and other.uniqueId() == EventKind.Separated.value
                ):
                    return False
        if self.uniqueId() and not other.uniqueId():
            return True
        elif not self.uniqueId() and other.uniqueId():
            return True
        else:
            return False

    def setParent(self, parent, notify=None, undo=False):
        """The proper way to assign a parent, also called from Event(parent)."""
        if notify is None:
            notify = not self.addDummy
        if undo:
            commands.setEventParent(self, parent)
        else:
            if not self.addDummy:
                was = self.parent
                self.parent = parent
                if was and not was.isEmotion and not was.isScene:
                    was._onRemoveEvent(self)
                if parent and not parent.isEmotion and not parent.isScene:
                    parent._onAddEvent(self)
            else:
                self.parent = parent
            wasDescription = self.description()
            wasNotes = self.notes()
            wasParentName = self.parentName()
            # >>> still needed ???
            self.updateDescription()
            self.updateNotes()
            self.updateParentName()
            # <<< still needed ???
            if self.description() != wasDescription:
                self.onProperty(self.prop("description"))
            if self.notes() != wasNotes:
                self.onProperty(self.prop("notes"))
            if self.parentName() != wasParentName:
                self.onProperty(self.prop("parentName"))

    @util.iblocked
    def onProperty(self, prop):
        if prop.name() == "description":
            if not self._onShowAliases:
                self.updateDescription()
        elif prop.name() == "notes":
            if not self._onShowAliases:
                self.updateNotes()
        elif prop.name() == "uniqueId":
            self.updateDescription()
        if not self.addDummy:
            super().onProperty(prop)
            if self.parent:
                self.parent.onEventProperty(prop)

    def scene(self):
        if self.addDummy:
            return None
        elif self.parent:
            if self.parent.isScene:
                return self.parent
            else:
                return self.parent.scene()

    def shouldShowAliases(self):
        scene = self.scene()
        return scene and scene.shouldShowAliases()

    def updateParentName(self):
        """Force re-write of aliases."""
        if not self.parent:
            return
        prop = self.prop("parentName")
        newParentName = None
        if self.parent:
            if self.parent.isPerson:
                newParentName = self.parent.name()
            elif self.parent.isMarriage or self.parent.isEmotion:
                peopleNames = self.parent.peopleNames()
                if not peopleNames:
                    peopleNames = "<not set>"
                newParentName = peopleNames
        if newParentName != prop.get():
            self.prop("parentName").set(newParentName)  # , notify=False)
        scene = self.scene()
        if prop.get() is not None and scene:
            self._aliasParentName = scene.anonymize(prop.get())
        else:
            self._aliasParentName = None

    @util.fblocked
    def updateDescription(self):
        """Force re-write of aliases."""
        # Was preventing editing of description and don't know what it is for any more.
        # if self.addDummy:
        #     return
        prop = self.prop("description")
        wasDescription = prop.get()
        newDescription = None
        uniqueId = self.uniqueId()
        if self.parent and uniqueId:
            newDescription = self.getDescriptionForUniqueId(uniqueId)
            if wasDescription != newDescription:
                if newDescription:
                    prop.set(
                        newDescription
                    )  # not sure why this was notify=False before
                else:
                    prop.reset()
        scene = self.scene()
        if prop.get() is not None and scene:
            self._aliasDescription = scene.anonymize(prop.get())
        else:
            self._aliasDescription = None

    @util.fblocked
    def updateNotes(self):
        """Force re-write of aliases."""
        if self.addDummy:
            return
        prop = self.prop("notes")
        notes = prop.get()
        scene = self.scene()
        if scene and notes is not None:
            self._aliasNotes = scene.anonymize(notes)
        else:
            self._aliasNotes = None

    def onShowAliases(self):
        self._onShowAliases = True
        prop = self.prop("description")
        if prop.get() != self._aliasDescription:
            self.onProperty(prop)
        prop = self.prop("notes")
        if prop.get() != self._aliasNotes:
            self.onProperty(prop)
        prop = self.prop("parentName")
        if prop.get() != self._aliasParentName:
            self.onProperty(prop)
        self._onShowAliases = False

    def description(self):
        if self.shouldShowAliases():
            if (
                self._aliasDescription is None and self.prop("description").get()
            ):  # first time
                self.updateDescription()
            return self._aliasDescription
        else:
            return self.prop("description").get()

    def getDescriptionForUniqueId(self, uniqueId=None):
        if not uniqueId:
            uniqueId = self.uniqueId()
        ret = None
        if self.parent:
            if self.parent.isPerson:
                if uniqueId == EventKind.Birth.value:
                    ret = util.BIRTH_TEXT
                elif uniqueId == EventKind.Adopted.value:
                    ret = util.ADOPTED_TEXT
                elif uniqueId == EventKind.Death.value:
                    ret = util.DEATH_TEXT
            elif self.parent.isMarriage:
                if uniqueId == EventKind.Bonded.value:
                    ret = "Bonded"
                elif uniqueId == EventKind.Married.value:
                    ret = "Married"
                elif uniqueId == EventKind.Divorced.value:
                    ret = "Divorced"
                elif uniqueId == EventKind.Separated.value:
                    ret = "Separated"
                elif uniqueId == "moved":
                    if self.location():
                        ret = "Moved to %s" % self.location()
                    else:
                        ret = "Moved"
            elif self.parent.isEmotion and self.parent.isInit:
                if uniqueId == "emotionStartEvent":
                    if self.parent.isSingularDate():
                        ret = self.parent.kindLabelForKind(self.parent.kind())
                    elif self.dateTime():
                        kind = self.parent.kindLabelForKind(self.parent.kind())
                        ret = f"{kind} began"
                    else:
                        ret = ""
                elif uniqueId == "emotionEndEvent":
                    if self.parent.isSingularDate():
                        ret = ""
                    elif not self.dateTime():
                        ret = ""
                    else:
                        kind = self.parent.kindLabelForKind(self.parent.kind())
                        ret = f"{kind} ended"
        return ret

    def notes(self):
        if self.shouldShowAliases():
            if self._aliasNotes is None and self.prop("notes").get():  # first time
                self.updateNotes()
            return self._aliasNotes
        else:
            return self.prop("notes").get()

    def parentName(self):
        if self.shouldShowAliases():
            if (
                self._aliasParentName is None and self.prop("parentName").get()
            ):  # first time
                self.updateParentName()
            return self._aliasParentName
        else:
            return self.prop("parentName").get()

    def toText(self):
        return str(self)

    def documentsPath(self):
        if hasattr(self.parent, "documentsPath") and self.parent.documentsPath():
            return os.path.join(self.parent.documentsPath(), "Events", str(self.id))

    ## Dynamic Properties

    def anyDynamicPropertiesSet(self):
        for prop in self.dynamicProperties:
            if prop.isset():
                return True
        return False

    def dynamicProperty(self, attr):
        for prop in self.dynamicProperties:
            if prop.name() == attr:
                return prop

    def addDynamicProperty(self, attr):
        """Doesn't add dynamic getters/setters."""
        prop = self.dynamicProperty(attr)
        if prop is None:
            prop = property.Property(self, attr=attr, dynamic=True)
            self.dynamicProperties.append(prop)
        return prop

    def renameDynamicProperty(self, oldAttr, newAttr):
        self.dynamicProperty(oldAttr).setAttr(newAttr)

    def removeDynamicProperty(self, attr):
        for prop in list(self.dynamicProperties):
            if prop.name() == attr:
                self.dynamicProperties.remove(prop)
                return

    def clearDynamicProperties(self):
        self.dynamicProperties = []
