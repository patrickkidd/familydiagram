import os
import logging
from datetime import datetime

from pkdiagram.pyqt import QDateTime
from pkdiagram import util, slugify
from pkdiagram.scene import EventKind, RelationshipKind, Item, Property
from pkdiagram.scene.commands import SetEventPerson


_log = logging.getLogger(__name__)


class Event(Item):
    """
    Canonical way to add:
        event = Event(personOrPairbond, dateTime=QDateTime.currentDateTime(), kind=EventKind.Birth)
        scene.addItem(event)

    Events are also added / removed from the scene whenever the person is added / removed from the scene.
    """

    Item.registerProperties(
        (
            # Core fields
            {"attr": "kind", "default": EventKind.Shift.value},  # EventKind
            {"attr": "dateTime", "type": QDateTime},
            {"attr": "endDateTime", "type": QDateTime},
            {"attr": "unsure", "default": True},
            {"attr": "description"},
            {"attr": "nodal", "default": False},
            {
                "attr": "notes"
            },  # only when manually drawing emotions on diagram. Can't retroactively add dates to a symbol anymore, so overlap
            {"attr": "color", "type": str, "default": None},
            {"attr": "location"},
            {"attr": "includeOnDiagram", "default": False},
            # Person references (stored as IDs)
            {"attr": "person", "type": int, "default": None},
            {"attr": "spouse", "type": int, "default": None},
            {"attr": "child", "type": int, "default": None},
            # Shift fields
            {"attr": "relationshipTargets", "type": list, "default": []},
            {"attr": "relationshipTriangles", "type": list, "default": []},
            {
                "attr": "relationshipIntensity",
                "type": int,
                "default": util.DEFAULT_EMOTION_INTENSITY,
                "onset": "updateGeometry",
            },
        )
    )

    def __init__(
        self,
        kind: EventKind,
        person: "Person",
        spouse: "Person | None" = None,
        child: "Person | None" = None,
        anxiety: "Person | None" = None,
        symptom: str | None = None,
        relationship: RelationshipKind | None = None,
        functioning: str | None = None,
        relationshipTargets: "list[Person]" = [],
        relationshipTriangles: "list[Person]" = [],
        **kwargs,
    ):
        if not isinstance(kind, EventKind):
            raise TypeError(
                f"Event() requires kind=EventKind, got {type(kind).__name__}"
            )
        super().__init__(kind=kind.value, person=person.id, **kwargs)
        self.isEvent = True
        self.dynamicProperties = []  # { 'attr': 'symptom', 'name': '𝚫 Symptom' }
        if "id" in kwargs:
            self.id = kwargs["id"]
        self._aliasDescription = None
        self._aliasNotes = None
        self._aliasParentName = None
        self._onShowAliases = False
        self._updatingDescription = False
        if spouse is not None:
            self.setSpouse(spouse)
        if child is not None:
            self.setChild(child)
        if anxiety is not None:
            self.addDynamicProperty(util.ATTR_ANXIETY).set(anxiety)
        if symptom is not None:
            self.addDynamicProperty(util.ATTR_SYMPTOM).set(symptom)
        if relationship is not None:
            self.addDynamicProperty(util.ATTR_RELATIONSHIP).set(relationship.value)
        if functioning is not None:
            self.addDynamicProperty(util.ATTR_FUNCTIONING).set(functioning)
        if relationshipTargets:
            self.setRelationshipTargets(relationshipTargets)
        if relationshipTriangles:
            self.setRelationshipTriangles(relationshipTriangles)

    def itemName(self):
        if self.person():
            return "<%s>: %s" % (self.person().itemName(), self.description())
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
        if self.dateTime() and not other.dateTime():
            return True
        elif not self.dateTime() and other.dateTime():
            return False
        elif self.dateTime() and other.dateTime():
            return self.dateTime() < other.dateTime()
        elif self.person() == other.person:
            if self.person() is None:
                return False
            elif self.person().isPerson:
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
            elif self.person().isMarriage:
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

    def _do_setPerson(self, person: "Person"):
        was = self.person()
        if was:
            was.onEventRemoved()
        if person:
            person.onEventAdded()
        wasDescription = self.description()
        wasNotes = self.notes()
        self.updateDescription()  # Anonymize
        self.updateNotes()  # Anonymize
        if self.description() != wasDescription:
            self.onProperty(self.prop("description"))
        if self.notes() != wasNotes:
            self.onProperty(self.prop("notes"))

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
        person = self.person()
        if person:
            person.onEventProperty(prop)

    def scene(self) -> "Scene":
        if self.person():
            if self.person().isScene:
                return self.person()
            else:
                return self.person().scene()

    def kind(self) -> EventKind:
        value = self.prop("kind").get()
        if value is None:
            # This should never happen with new code, but handle legacy data gracefully
            _log.warning(f"Event {self.id} has no kind, defaulting to Shift")
            return EventKind.Shift
        return EventKind(value)

    def setKind(self, x: EventKind, undo=False):
        """Set the event kind."""
        if not isinstance(x, EventKind):
            raise TypeError(f"setKind() requires EventKind, got {type(x).__name__}")
        self.prop("kind").set(x.value, undo=undo)

    def shouldShowAliases(self):
        scene = self.scene()
        return scene and scene.shouldShowAliases()

    def updateDescription(self, undo=False):
        """Force re-write of aliases."""
        if self._updatingDescription:
            return
        self._updatingDescription = True
        prop = self.prop("description")
        wasDescription = prop.get()
        newDescription = None
        if self.person():
            if self.kind() == EventKind.Moved:
                newDescription = (
                    "Moved to %s" % self.location() if self.location() else "Moved"
                )
            else:
                newDescription = self.kind().menuLabel()

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

    def notes(self):
        if self.shouldShowAliases():
            if self._aliasNotes is None and self.prop("notes").get():  # first time
                self.updateNotes()
            return self._aliasNotes
        else:
            return self.prop("notes").get()

    def personName(self) -> str:
        return self.person().alias()

    def toText(self):
        return str(self)

    def documentsPath(self):
        if hasattr(self.person(), "documentsPath") and self.person().documentsPath():
            return os.path.join(self.person().documentsPath(), "Events", str(self.id))

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

    # Person

    def person(self) -> "Person":
        id = self.prop("person").get()
        return self.scene().find(id=id) if id and self.scene() else None

    # Pair-Bond Events

    def marriage(self):
        from pkdiagram.scene import Marriage

        person = self.person()
        spouse = self.spouse()

        if person and spouse:
            marriages = Marriage.marriagesFor(person, spouse)
            if marriages[0]:
                return marriages[0]

    def setSpouse(self, person: "Person", notify=True, undo=False):
        self.prop("spouse").set(person.id, notify=notify, undo=undo)

    def spouse(self) -> "Person":
        from pkdiagram.scene import Person

        id = self.prop("spouse").get()
        return self.scene().find(id=id, types=Person) if self.scene() else None

    def setChild(self, person: "Person", notify=True, undo=False):
        self.prop("child").set(person.id, notify=notify, undo=undo)

    def child(self) -> "Person":
        from pkdiagram.scene import Person

        id = self.prop("child").get()
        return self.scene().find(id=id, types=Person) if self.scene() else None

    ## Variables

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
