import os
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from btcopilot.schema import EventKind, RelationshipKind, VariableShift, DateCertainty
from pkdiagram.pyqt import QDateTime
from pkdiagram import util, slugify
from pkdiagram.scene import Item, Property

if TYPE_CHECKING:
    from pkdiagram.scene.marriage import Marriage


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
            {"attr": "dateCertainty", "type": DateCertainty, "default": None},
            {"attr": "unsure", "default": True},  # DEPRECATED: Use dateCertainty
            {"attr": "description"},
            {"attr": "nodal", "default": False},
            {
                "attr": "notes"
            },  # only when manually drawing emotions on diagram. Can't retroactively add dates to a symbol anymore, so overlap
            {"attr": "color", "type": str, "default": None},
            {"attr": "location"},
            {"attr": "includeOnDiagram", "default": None},
            # Person references (stored as IDs)
            {"attr": "person", "type": int, "default": None},
            {"attr": "spouse", "type": int, "default": None},
            {"attr": "child", "type": int, "default": None},
            # Shift fields - stored as strings, Property converts to/from enums
            {"attr": "anxiety", "type": VariableShift, "default": None},
            {"attr": "symptom", "type": VariableShift, "default": None},
            {"attr": "relationship", "type": RelationshipKind, "default": None},
            {"attr": "functioning", "type": VariableShift, "default": None},
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
        relationshipTargets: "Person | list[Person] | None" = None,
        relationshipTriangles: "Person | list[Person] | None" = None,
        **kwargs,
    ):
        from pkdiagram.scene import Person

        if not isinstance(kind, EventKind):
            raise TypeError(
                f"Event() requires kind=EventKind, got {type(kind).__name__}"
            )

        # Allow person=None during file loading (when 'id' is in kwargs)
        if person is not None and not isinstance(person, Person):
            raise TypeError(
                f"Event() requires person=Person, got {type(person).__name__}"
            )

        super().__init__(
            kind=kind.value, person=person.id if person else None, **kwargs
        )
        self.isEvent = True
        self.dynamicProperties = []  # { 'attr': 'symptom', 'name': '𝚫 Symptom' }
        if "id" in kwargs:
            self.id = kwargs["id"]
        self._aliasDescription = None
        self._aliasNotes = None
        self._aliasParentName = None
        self._onShowAliases = False
        self._updatingDescription = False

        # Cache person references
        self._person = person
        self._spouse = None
        self._child = None
        self._relationshipTargets = []
        self._relationshipTriangles = []
        self._marriage = None
        if spouse is not None:
            self._spouse = spouse
            self.prop("spouse").set(spouse.id, notify=False)
        if child is not None:
            self._child = child
            self.prop("child").set(child.id, notify=False)
        if relationshipTargets is not None:
            self.setRelationshipTargets(relationshipTargets)
        if relationshipTriangles is not None:
            self.setRelationshipTriangles(relationshipTriangles)

        for p in (
            [self._spouse, self._child]
            + self._relationshipTargets
            + self._relationshipTriangles
        ):
            if p and p.id is None:
                raise ValueError(
                    f"All referenced people must be added to the scene before passed to Event() or they won't have valid id's."
                )
        # Skip updateDescription when person=None (during file loading)
        if person is not None:
            self.updateDescription()

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
        self._person = byId(chunk.get("person")) if chunk.get("person") else None
        self._spouse = byId(chunk.get("spouse")) if chunk.get("spouse") else None
        self._child = byId(chunk.get("child")) if chunk.get("child") else None
        self._relationshipTargets = [
            byId(id) for id in chunk.get("relationshipTargets", [])
        ]
        self._relationshipTriangles = [
            byId(id) for id in chunk.get("relationshipTriangles", [])
        ]
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
        self.prop("person").set(person.id)
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
            from pkdiagram.scene.commands import SetEventPerson

            scene.push(SetEventPerson(self, person))
        else:
            self._do_setPerson(person)
        self._marriage = self.scene().marriageFor(self._person, self._spouse)

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
        if self.scene():
            person = self.person()
            if person:
                person.onEventProperty(prop)
            marriage = self.scene().marriageFor(self._person, self._spouse)
            if marriage:
                marriage.onEventProperty(prop)
            if prop.name() == "color":
                for emotion in self.scene().emotionsFor(self):
                    emotion.updatePen()

    def scene(self) -> "Scene":
        # Events are top-level items in the scene, use standard scene() lookup
        return super().scene()

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
        if self.kind() == EventKind.Moved:
            loc = self.location()
            newDescription = "Moved to %s" % loc if loc else "Moved"
        elif self.kind() == EventKind.Shift:
            # For Shift events, only auto-generate if description isn't already set
            if not wasDescription:
                newDescription = self.kind().menuLabel()
        else:
            newDescription = self.kind().menuLabel()

        if wasDescription != newDescription and newDescription is not None:
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

    def parentName(self, nickname=True) -> str:
        if self.kind().isOffspring():
            return self.child().firstNameOrAlias(nickname=nickname)
        elif self.kind() == EventKind.Death:
            return self.person().firstNameOrAlias(nickname=nickname)
        elif self.kind() == EventKind.Shift:
            if self.relationshipTargets():
                names = [self.person().firstNameOrAlias(nickname=nickname)]
                names.extend(
                    [
                        target.firstNameOrAlias(nickname=nickname)
                        for target in self.relationshipTargets()
                    ]
                )
                return " & ".join(names)
            return self.person().firstNameOrAlias(nickname=nickname)
        elif self.kind().isPairBond():
            return f"{self.person().firstNameOrAlias(nickname=nickname)} & {self.spouse().firstNameOrAlias(nickname=nickname)}"
        else:
            return self.person.firstNameOrAlias(nickname=nickname)

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

    # Person References

    def __resolvePersonReferences(self):
        from pkdiagram.scene import Person

        id = self.prop("person").get()
        if id is not None:
            self._person = self.scene().find(id=id, types=Person)
        else:
            self._person = None

        id = self.prop("spouse").get()
        if id is not None:
            self._spouse = self.scene().find(id=id, types=Person)
        else:
            self._spouse = None

        id = self.prop("child").get()
        if id is not None:
            self._child = self.scene().find(id=id, types=Person)
        else:
            self._child = None

        ids = self.prop("relationshipTargets").get()
        if ids:
            results = self.scene().find(ids=ids, types=Person)
            assert set(ids) != set(
                x.id for x in results
            ), f"Some relationshipTargets in Event {self.id} are invalid: {ids}"
            self._relationshipTargets = results

        ids = self.prop("relationshipTriangles").get()
        if ids:
            results = self.scene().find(ids=ids, types=Person)
            assert set(ids) != set(
                x.id for x in results
            ), f"Some relationshipTriangles in Event {self.id} are invalid: {ids}"
            self._relationshipTriangles = results

        if self._person and self._spouse:
            self._marriage = self.scene().marriageFor(self._person, self._spouse)
        else:
            self._marriage = None

    # Person getters

    def person(self) -> "Person":
        assert self._person is not None
        return self._person

    def spouse(self) -> "Person":
        return self._spouse

    def child(self) -> "Person":
        return self._child

    def marriage(self) -> "Marriage | None":
        return self._marriage

    def relationshipTriangles(self) -> list:
        return self._relationshipTriangles

    def relationshipTargets(self) -> list:
        return self._relationshipTargets

    def people(self) -> list["Person"]:
        """All people referenced by this event."""
        results = []
        if self._person:
            results.append(self._person)
        if self._spouse:
            results.append(self._spouse)
        if self._child:
            results.append(self._child)
        results.extend(self._relationshipTargets)
        results.extend(self._relationshipTriangles)
        return list(set(results))  # unique

    # Person setters (sill needed, or can limit editing and get rid of them?)

    def setSpouse(self, person: "Person", notify=True, undo=False):
        self.prop("spouse").set(person.id, notify=notify, undo=undo)
        self._spouse = person
        self._marriage = self.scene().marriageFor(self._person, self._spouse)

    def setChild(self, person: "Person", notify=True, undo=False):
        self.prop("child").set(person.id, notify=notify, undo=undo)
        self._child = person

    def setRelationshipTargets(self, targets: list["Person"], notify=True, undo=False):
        if not isinstance(targets, list):
            targets = [targets]
        self.prop("relationshipTargets").set(
            [x.id for x in targets], notify=notify, undo=undo
        )
        self._relationshipTargets = targets

    def setRelationshipTriangles(self, triangles: list, notify=True, undo=False):
        if not isinstance(triangles, list):
            triangles = [triangles]
        self.prop("relationshipTriangles").set(
            [x.id for x in triangles], notify=notify, undo=undo
        )
        self._relationshipTriangles = triangles
