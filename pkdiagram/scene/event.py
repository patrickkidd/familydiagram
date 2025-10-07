import os
from datetime import datetime

from pkdiagram.pyqt import QDateTime
from pkdiagram import util, slugify
from pkdiagram.scene import EventKind, RelationshipKind, Item, Property
from pkdiagram.scene.commands import SetEventPerson


class Event(Item):
    """
    Canonical way to add:
        event = Event(personOrPairbond, dateTime=QDateTime.currentDateTime(), kind=EventKind.Birth)
        scene.addItem(event)

    Events are also added / removed from the scene whenever the person is added / removed from the scene.
    """

    Item.registerProperties(
        (
            {"attr": "kind"},
            {"attr": "dateTime", "type": QDateTime},
            {"attr": "endDateTime", "type": QDateTime},
            {"attr": "unsure", "default": True},
            {"attr": "description"},
            {"attr": "nodal", "default": False},
            {"attr": "notes"},
            {"attr": "color", "type": str, "default": None},
            {"attr": "personName"},
            {"attr": "location"},
            {"attr": "spouse", "type": int, "default": None},
            {"attr": "child", "type": int, "default": None},
            {"attr": "relationshipTargets", "type": list, "default": []},
            {"attr": "relationshipTriangles", "type": list, "default": []},
            {
                "attr": "relationshipIntensity",
                "type": int,
                "default": util.DEFAULT_EMOTION_INTENSITY,
                "onset": "updateGeometry",
            },
            {"attr": "includeOnDiagram", "default": False},
        )
    )

    def __init__(
        self,
        person=None,
        dynamicProperties: dict | None = None,
        relationshipTargets: "list[Person]" = [],
        relationshipTriangles: "list[Person]" = [],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.isEvent = True
        self.dynamicProperties = []  # { 'attr': 'symptom', 'name': '𝚫 Symptom' }
        if "id" in kwargs:
            self.id = kwargs["id"]
        self._aliasDescription = None
        self._aliasNotes = None
        self._aliasParentName = None
        self._onShowAliases = False
        self._updatingDescription = False
        self._emotions = []  # relationships only
        self.person: Item | None = None
        if dynamicProperties:
            for attr, value in dynamicProperties.items():
                self.addDynamicProperty(attr).set(value)
        if relationshipTargets:
            self.setRelationshipTargets(relationshipTargets)
        if relationshipTriangles:
            self.setRelationshipTriangles(relationshipTriangles)
        # avoid adding to the person in various cases
        if person:  # for tidyness in ctors
            self._do_setPerson(person)
            self.updateDescription()

    def itemName(self):
        if self.person:
            return "<%s>: %s" % (self.person.itemName(), self.description())
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
        elif self.person == other.person:
            if self.person is None:
                return False
            elif self.person.isPerson:
                if self.kind() == EventKind.Birth and other.kind() == EventKind.Adopted:
                    return True
                elif self.kind() == EventKind.Birth and other.kind() == EventKind.Death:
                    return True
                elif (
                    self.kind() == EventKind.Adopted and other.kind() == EventKind.Birth
                ):
                    return False
                elif (
                    self.kind() == EventKind.Adopted and other.kind() == EventKind.Death
                ):
                    return True
                elif self.kind() == EventKind.Death and other.kind() == EventKind.Birth:
                    return False
                elif (
                    self.kind() == EventKind.Death and other.kind() == EventKind.Adopted
                ):
                    return False
            elif self.person.isMarriage:
                if (
                    self.kind() == EventKind.Married
                    and other.kind() == EventKind.Separated
                ):
                    return True
                elif (
                    self.kind() == EventKind.Married
                    and other.kind() == EventKind.Divorced
                ):
                    return True
                elif (
                    self.kind() == EventKind.Separated
                    and other.kind() == EventKind.Married
                ):
                    return False
                elif (
                    self.kind() == EventKind.Separated
                    and other.kind() == EventKind.Divorced
                ):
                    return True
                elif (
                    self.kind() == EventKind.Divorced
                    and other.kind() == EventKind.Married
                ):
                    return False
                elif (
                    self.kind() == EventKind.Divorced
                    and other.kind() == EventKind.Separated
                ):
                    return False
        if self.kind() and not other.kind():
            return True
        elif not self.kind() and other.kind():
            return True
        else:
            return False

    def _do_setPerson(self, person):
        was = self.person
        self.person = person
        if was and not was.isEmotion and not was.isScene:
            was._onRemoveEvent(self)
        if person and not person.isEmotion and not person.isScene:
            person._onAddEvent(self)
        wasDescription = self.description()
        wasNotes = self.notes()
        wasParentName = self.personName()
        # >>> still needed ???
        self.updateDescription()
        self.updateNotes()
        self.updateParentName()
        # <<< still needed ???
        if self.description() != wasDescription:
            self.onProperty(self.prop("description"))
        if self.notes() != wasNotes:
            self.onProperty(self.prop("notes"))
        if self.personName() != wasParentName:
            self.onProperty(self.prop("personName"))

    def setPerson(self, person, undo=False):
        """The proper way to assign a person, also called from Event(person)."""
        if undo:
            scene = self.scene()
            if not scene:
                scene = person.scene()
            scene.push(SetEventPerson(self, person))
        else:
            self._do_setPerson(person)

    def onProperty(self, prop):
        if prop.name() == "location" and self.kind() == EventKind.Moved:
            if not self._onShowAliases:
                self.updateDescription()
        elif prop.name() == "notes":
            if not self._onShowAliases:
                self.updateNotes()
        # Disabled because this is probably only ever set from the emotion
        # properties and now we aggreate kind and description into a single
        #     QUndoEvent. elif prop.name() == "kind":
        #     self.updateDescription()
        super().onProperty(prop)
        if self.person:
            self.person.onEventProperty(prop)

    def scene(self) -> "Scene":
        if self.person:
            if self.person.isScene:
                return self.person
            else:
                return self.person.scene()

    def kind(self) -> EventKind:
        return EventKind(self.prop("kind").get())

    def setKind(self, x: EventKind):
        self.prop("kind").set(x)

    def shouldShowAliases(self):
        scene = self.scene()
        return scene and scene.shouldShowAliases()

    def updateParentName(self):
        """Force re-write of aliases."""
        if not self.person:
            return
        prop = self.prop("personName")
        newParentName = None
        if self.person:
            if self.person.isPerson:
                newParentName = self.person.name()
            elif self.person.isMarriage or self.person.isEmotion:
                peopleNames = self.person.peopleNames()
                if not peopleNames:
                    peopleNames = "<not set>"
                newParentName = peopleNames
        if newParentName != prop.get():
            self.prop("personName").set(newParentName)  # , notify=False)
        scene = self.scene()
        if prop.get() is not None and scene:
            self._aliasParentName = scene.anonymize(prop.get())
        else:
            self._aliasParentName = None

    def updateDescription(self, undo=False):
        """Force re-write of aliases."""
        if self._updatingDescription:
            return
        self._updatingDescription = True
        prop = self.prop("description")
        wasDescription = prop.get()
        newDescription = None
        if self.person:
            newDescription = self.getDescriptionForKind(self.kind())
            if wasDescription != newDescription:
                if newDescription:
                    prop.set(newDescription, undo=undo)
                else:
                    prop.reset(undo=undo)
        scene = self.scene()
        if prop.get() is not None and scene:
            self._aliasDescription = scene.anonymize(prop.get())
        else:
            self._aliasDescription = None
        self._updatingDescription = False

    def updateNotes(self):
        """Force re-write of aliases."""
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
        prop = self.prop("personName")
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

    def getDescriptionForKind(self, kind=None):
        ret = None
        if self.person:
            if self.person.isPerson:
                if kind == EventKind.Birth:
                    ret = util.BIRTH_TEXT
                elif kind == EventKind.Adopted:
                    ret = util.ADOPTED_TEXT
                elif kind == EventKind.Death:
                    ret = util.DEATH_TEXT
            elif self.person.isMarriage:
                if kind == EventKind.Bonded:
                    ret = "Bonded"
                elif kind == EventKind.Married:
                    ret = "Married"
                elif kind == EventKind.Divorced:
                    ret = "Divorced"
                elif kind == EventKind.Separated:
                    ret = "Separated"
                elif kind == "moved":
                    if self.location():
                        ret = "Moved to %s" % self.location()
                    else:
                        ret = "Moved"
            elif self.person.isEmotion and self.person.isInit:
                if kind == "emotionStartEvent":
                    if self.person.isSingularDate():
                        ret = self.person.kindLabelForKind(self.person.kind())
                    elif self.dateTime():
                        kind = self.person.kindLabelForKind(self.person.kind())
                        ret = f"{kind} began"
                    else:
                        ret = ""
                elif kind == "emotionEndEvent":
                    if self.person.isSingularDate():
                        ret = ""
                    elif not self.dateTime():
                        ret = ""
                    else:
                        kind = self.person.kindLabelForKind(self.person.kind())
                        ret = f"{kind} ended"
        return ret

    def notes(self):
        if self.shouldShowAliases():
            if self._aliasNotes is None and self.prop("notes").get():  # first time
                self.updateNotes()
            return self._aliasNotes
        else:
            return self.prop("notes").get()

    def personName(self):
        if self.shouldShowAliases():
            if (
                self._aliasParentName is None and self.prop("personName").get()
            ):  # first time
                self.updateParentName()
            return self._aliasParentName
        else:
            return self.prop("personName").get()

    def toText(self):
        return str(self)

    def documentsPath(self):
        if hasattr(self.person, "documentsPath") and self.person.documentsPath():
            return os.path.join(self.person.documentsPath(), "Events", str(self.id))

    ## Dynamic Properties

    def anyDynamicPropertiesSet(self):
        for prop in self.dynamicProperties:
            if prop.isset():
                return True
        return False

    def dynamicProperty(self, attr):
        attr = slugify(attr)
        for prop in self.dynamicProperties:
            if prop.name() == attr:
                return prop

    def addDynamicProperty(self, attr):
        """Doesn't add dynamic getters/setters."""
        attr = slugify(attr)
        prop = self.dynamicProperty(attr)
        if prop is None:
            prop = Property(self, attr=attr, dynamic=True)
            self.dynamicProperties.append(prop)
        return prop

    def renameDynamicProperty(self, oldAttr, newAttr):
        self.dynamicProperty(oldAttr).setAttr(newAttr)

    def removeDynamicProperty(self, attr):
        attr = slugify(attr)
        for prop in list(self.dynamicProperties):
            if prop.name() == attr:
                self.dynamicProperties.remove(prop)
                return

    def clearDynamicProperties(self):
        self.dynamicProperties = []

    # Pair-Bond Events

    def setSpouse(self, person: "Person", notify=True, undo=False):
        self.prop("spouse").set(person.id, notify=notify, undo=undo)

    def spouse(self) -> "Person":
        from pkdiagram.scene import Person

        id = self.prop("spouse").get()
        if not id:
            return None
        people = self.scene().find(ids=[id], types=Person)
        if people:
            return people[0]
        return None

    def setChild(self, person: "Person", notify=True, undo=False):
        self.prop("child").set(person.id, notify=notify, undo=undo)

    def child(self) -> "Person":
        from pkdiagram.scene import Person

        id = self.prop("child").get()
        if not id:
            return None
        people = self.scene().find(ids=[id], types=Person)
        if people:
            return people[0]
        return None

    # Variables

    def symptom(self):
        prop = self.dynamicProperty(util.ATTR_SYMPTOM)
        if prop:
            return prop.get()

    def anxiety(self):
        prop = self.dynamicProperty(util.ATTR_ANXIETY)
        if prop:
            return prop.get()

    def relationship(self) -> RelationshipKind:
        prop = self.dynamicProperty(util.ATTR_RELATIONSHIP)
        if prop:
            x = prop.get()
            if x:
                return RelationshipKind(x)

    def functioning(self):
        prop = self.dynamicProperty(util.ATTR_FUNCTIONING)
        if prop:
            return prop.get()

    def setSymptom(self, value, notify=True, undo=False):
        prop = self.dynamicProperty(util.ATTR_SYMPTOM)
        if prop:
            prop.set(value, notify=notify, undo=undo)

    def setAnxiety(self, value, notify=True, undo=False):
        prop = self.dynamicProperty(util.ATTR_ANXIETY)
        if prop:
            prop.set(value, notify=notify, undo=undo)

    def setRelationship(self, value: RelationshipKind, notify=True, undo=False):
        prop = self.dynamicProperty(util.ATTR_RELATIONSHIP)
        if prop:
            prop.set(value.value, notify=notify, undo=undo)

    def emotions(self) -> list["Emotion"]:
        """
        Canonical constructor for emotions unless drawn directly on the diagram with no dates.
        """
        from pkdiagram.scene import Emotion

        if self.relationship():
            if not self._emotions:
                from pkdiagram.scene import Emotion

                for target in self.relationshipTargets():
                    emotion = self.scene.addItem(
                        Emotion(
                            kind=self.relationship(),
                            target=target,
                            event=self,
                            tags=self.tags(),
                            **kwargs,
                        ),
                        undo=True,
                    )
                    self._emotions.append(emotion)
            return self._emotions
        else:
            return []

    def setRelationshipTargets(self, targets: list["Person"], notify=True, undo=False):
        if not isinstance(targets, list):
            targets = [targets]
        ids = []
        for person in targets:
            ids.append(person.id)
        self.prop("relationshipTargets").set(ids, notify=notify, undo=undo)

    def relationshipTargets(self) -> list["Person"]:
        from pkdiagram.scene import Person

        ids = self.prop("relationshipTargets").get()
        if not ids:
            return []
        return self.scene().find(ids=ids, types=Person)

    def setRelationshipTriangles(self, triangles: list, notify=True, undo=False):
        if not isinstance(triangles, list):
            triangles = [triangles]
        ids = []
        for person in triangles:
            ids.append(person.id)
        self.prop("relationshipTriangles").set(ids, notify=notify, undo=undo)

    def relationshipTriangles(self) -> list:
        from pkdiagram.scene import Person

        ids = self.prop("relationshipTriangles").get()
        if not ids:
            return []
        return self.scene().find(ids=ids, types=Person)

    def setFunctioning(self, value, notify=True, undo=False):
        prop = self.dynamicProperty(util.ATTR_FUNCTIONING)
        if prop:
            prop.set(value, notify=notify, undo=undo)
