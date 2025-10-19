import logging

from pkdiagram.pyqt import (
    pyqtSignal,
    Q_RETURN_ARG,
    Q_ARG,
    Qt,
    QPointF,
    QMetaObject,
    QVariant,
    QMessageBox,
)
from pkdiagram import util
from pkdiagram.scene import (
    EventKind,
    RelationshipKind,
    Person,
    Emotion,
    Event,
    Marriage,
    Item,
)
from pkdiagram.models import TagsModel
from pkdiagram.views import QmlDrawer

_log = logging.getLogger(__name__)


class EventForm(QmlDrawer):

    QmlDrawer.registerQmlMethods(
        [
            {"name": "clear"},
            {"name": "initWithPerson"},
            {"name": "initWithNoSelection"},
            {"name": "setVariable"},
            {"name": "personEntry", "return": True, "parser": lambda x: x.toVariant()},
            {"name": "spouseEntry", "return": True, "parser": lambda x: x.toVariant()},
            {"name": "childEntry", "return": True, "parser": lambda x: x.toVariant()},
            {
                "name": "targetsEntries",
                "return": True,
                "parser": lambda x: [x for x in x.toVariant()],
            },
            {
                "name": "trianglesEntries",
                "return": True,
                "parser": lambda x: [x for x in x.toVariant()],
            },
        ]
    )

    doneEditing = pyqtSignal()

    S_REQUIRED_FIELD_ERROR = "'{name}' is a required field."
    S_HELP_TEXT_ADD_PEOPLE = "This will add {numPeople} people to the diagram"
    S_REPLACE_EXISTING = (
        "This will replace {n_existing} of the {kind} events in the selected people."
    )
    S_PICKER_NEW_PERSON_NOT_SUBMITTED = "You have entered a name for a new person in the '{pickerLabel}' field, but have not pressed enter yet."

    def __init__(self, engine, parent=None, **contextProperties):
        super().__init__(
            engine,
            "qml/EventForm.qml",
            parent=parent,
            resizable=False,
            objectName="addEverythingDialog",
            **contextProperties,
        )
        self._events = []
        self._dummyItem = None
        self._tagsModel: TagsModel | None = None

        # self.startTimer(1000)

    #     item = self.item.window().activeFocusItem()
    #     if item:
    #         nextItem = item.nextItemInFocusChain()
    #         nextItemParent = nextItem.parent()
    #         while not nextItemParent.objectName():
    #             nextItemParent = nextItemParent.parent()
    #         _log.info(
    #             f"timerEvent: {item.objectName() if item else None}, "
    #             f"nextItem: {nextItemParent.objectName()}.{nextItem.objectName() if nextItem else None}"
    #         )

    def onInitQml(self):
        super().onInitQml()
        self.item = self.qml.rootObject()
        self.item.setProperty("widget", self)
        self.item.cancel.connect(self.onCancel)
        self._tagsModel = self.item.property("tagsModel")

    @staticmethod
    def nextItemInChain(item):
        nextItem = item.nextItemInFocusChain()
        while not nextItem.isVisible() or not nextItem.isEnabled():
            nextItem = item.nextItemInFocusChain()
        return nextItem

    # def onActiveFocusItemChanged(self):
    #     super().onActiveFocusItemChanged()
    #     item = self.item.window().activeFocusItem()
    #     if item:
    #         nextItem = item.nextItemInFocusChain()
    #         while not nextItem.isVisible() or not nextItem.isEnabled():
    #             nextItem = item.nextItemInFocusChain()
    #         nextItemParent = nextItem.parent()
    #         while nextItemParent and not nextItemParent.objectName():
    #             nextItemParent = nextItemParent.parent()
    #         itemName = nextItem.objectName()
    #         if nextItemParent:
    #             parentName = nextItemParent.objectName()
    #         else:
    #             parentName = "{None}"
    #         itemClassName = nextItem.metaObject().className()
    #     else:
    #         itemName = ""
    #         itemClassName = ""
    #         parentName = ""
    #     _log.info(
    #         f"EventForm.onActiveFocusItemChanged: {parentName}.{itemName}[{itemClassName}]"
    #     )

    def addEvent(self, selection: list[Item] = None):
        self.clear()
        self.item.setProperty("isEditing", False)
        self.item.setProperty("events", [])
        self._events = []
        self._dummyItem = Item()
        self.scene.addItem(self._dummyItem)
        self._tagsModel.items = [self._dummyItem]
        if selection:
            people = [x for x in selection if x.isPerson]
            marriages = [x for x in selection if x.isMarriage]
            if people:
                self.initWithPerson(people[0].id)
            elif marriages:
                self.initWithPerson(marriages[0].personA().id)
            else:
                self.initWithNoSelection()
        else:
            self.initWithNoSelection()

    def editEvents(self, events: list[Event]):
        """
        Only populate fields where all events agree.
        """
        self.clear()
        self.item.setProperty("isEditing", True)
        self.item.setProperty("events", events)
        self._events = events

        person = util.sameOf(events, lambda e: e.person())
        if person:
            self.item.property("personPicker").setExistingPersonId(person.id)

        kind: EventKind | None = util.sameOf(events, lambda e: e.kind())
        if kind:
            self.item.property("kindBox").setCurrentValue(kind.value)

            if kind.isPairBond():
                spouse = util.sameOf(events, lambda x: x.spouse())
                if spouse:
                    self.item.property("spousePicker").setExistingPersonId(spouse.id)
            if kind.isOffspring():
                child = util.sameOf(events, lambda x: x.child())
                if child:
                    self.item.property("childPicker").setExistingPersonId(child.id)

        # Set dates only if all events agree
        startDateTime = util.sameOf(events, lambda e: e.dateTime())
        if startDateTime:
            self.item.setProperty("startDateTime", startDateTime)

        endDateTime = util.sameOf(events, lambda e: e.endDateTime())
        if endDateTime:
            self.item.property("isDateRangeBox").setProperty("checked", True)
            self.item.setProperty("endDateTime", endDateTime)

        # Set text fields only if all events agree
        description = util.sameOf(events, lambda e: e.description())
        if description:
            self.item.setProperty("description", description)

        location = util.sameOf(events, lambda e: e.location())
        if location:
            self.item.setProperty("location", location)

        # Set variable fields only if all events agree
        symptom = util.sameOf(events, lambda e: e.symptom())
        if symptom is not None:
            self.item.setProperty("symptom", symptom)

        anxiety = util.sameOf(events, lambda e: e.anxiety())
        if anxiety is not None:
            self.item.setProperty("anxiety", anxiety)

        relationship = util.sameOf(events, lambda e: e.relationship())
        if relationship is not None:
            self.item.setProperty("relationship", relationship.value)
            self.item.property("relationshipField").setValue(relationship.value)
            if relationship in (RelationshipKind.Inside, RelationshipKind.Outside):
                triangles = util.sameOf(events, lambda x: x.relationshipTriangles())
                if triangles:
                    self.item.property("trianglesPicker").setExistingPeopleIds(
                        [x.id for x in triangles]
                    )
            else:
                targets = util.sameOf(events, lambda x: x.relationshipTargets())
                if targets:
                    self.item.property("targetsPicker").setExistingPeopleIds(
                        [x.id for x in targets]
                    )

        functioning = util.sameOf(events, lambda e: e.functioning())
        if functioning is not None:
            self.item.setProperty("functioning", functioning)

        notes = util.sameOf(events, lambda e: e.notes())
        if notes:
            self.item.setProperty("notes", notes)

        # Initialize relationship targets if all events agree
        targets = util.sameOf(
            events,
            lambda e: (
                tuple(e.relationshipTargets()) if e.relationshipTargets() else None
            ),
        )
        if targets:
            self.item.property("targetsPicker").setExistingPeopleIds(
                [x.id for x in targets]
            )

        # Initialize relationship triangles if all events agree (for Inside/Outside)
        if relationship in (RelationshipKind.Inside, RelationshipKind.Outside):
            triangles = util.sameOf(
                events,
                lambda e: (
                    tuple(e.relationshipTriangles())
                    if e.relationshipTriangles()
                    else None
                ),
            )
            if triangles:
                self.item.property("trianglesPicker").setExistingPeopleIds(
                    [x.id for x in triangles]
                )

        color = util.sameOf(events, lambda e: e.color())
        if color:
            self.item.property("colorBox").setProperty("color", color)

        self._tagsModel.items = events

    def onDone(self):

        relationship: RelationshipKind | None = None
        if self.item.property("relationship"):
            relationship = RelationshipKind(self.item.property("relationship"))

        # Validation: Unsubmitted changes

        def pickerDirtyAndNotSubmitted(pickerItem):
            if pickerItem.metaObject().className().startswith("PersonPicker"):
                text = pickerItem.property("textEdit").property("text")
                isSubmitted = pickerItem.property("isSubmitted")
                if isSubmitted:
                    return False
                if text and not isSubmitted:
                    return True
                return False
            else:
                model = pickerItem.property("model")
                for i in range(model.rowCount()):
                    personPicker = QMetaObject.invokeMethod(
                        pickerItem,
                        "pickerAtIndex",
                        Qt.DirectConnection,
                        Q_RETURN_ARG(QVariant),
                        Q_ARG(QVariant, i),
                    )
                    if personPicker.property("textEdit").property(
                        "text"
                    ) and not personPicker.property("isSubmitted"):
                        return True
                return False

        if pickerDirtyAndNotSubmitted(self.item.property("personPicker")):
            pickerLabel = "personLabel"
        elif pickerDirtyAndNotSubmitted(self.item.property("spousePicker")):
            pickerLabel = "spouseLabel"
        elif pickerDirtyAndNotSubmitted(self.item.property("childPicker")):
            pickerLabel = "childLabel"
        elif pickerDirtyAndNotSubmitted(self.item.property("targetsPicker")):
            pickerLabel = "targetsLabel"
        elif pickerDirtyAndNotSubmitted(self.item.property("trianglesPicker")):
            pickerLabel = "trianglesLabel"
        else:
            pickerLabel = None

        if pickerLabel:
            text = self.item.property(pickerLabel).property("text")
            msg = self.S_PICKER_NEW_PERSON_NOT_SUBMITTED.format(pickerLabel=text)
            _log.debug(f"Warning: Unconfirmed field, {msg}")
            QMessageBox.warning(
                self,
                "Unconfirmed field",
                msg,
                QMessageBox.Ok,
            )
            return

        # Validation: Required fields

        kind: EventKind | None = None
        if self.item.property("kind"):
            kind = EventKind(self.item.property("kind"))

        isEditing = self.item.property("isEditing")

        invalidLabel = None

        if not isEditing and not self.item.property("kind"):
            invalidLabel = "kindLabel"

        elif not self.item.property("personPicker").property("isSubmitted"):
            invalidLabel = "personLabel"

        elif kind and kind == EventKind.Death:
            pass

        # elif (
        #     kind
        #     and kind.isPairBond()
        #     and not self.item.property("spousePicker").property("isSubmitted")
        # ):
        #     invalidLabel = "spouseLabel"

        # elif kind and kind in (EventKind.Birth, EventKind.Adopted):
        #     if not self.item.property("childPicker").property("isSubmitted"):
        #         invalidLabel = "childLabel"

        elif relationship and not self.item.property("description"):
            invalidLabel = "descriptionLabel"

        elif relationship and (
            not self.targetsEntries()
            or not self.item.property("targetsPicker").allSubmitted()
        ):
            invalidLabel = "targetsLabel"

        elif (
            relationship in (RelationshipKind.Inside, RelationshipKind.Outside)
            and not self.item.property("trianglesPicker").allSubmitted()
        ):
            invalidLabel = "trianglesLabel"

        elif not self.item.property("startDateTime"):
            invalidLabel = "startDateTimeLabel"

        # Allowing open-ended dyadic date ranges for now.
        # elif self.item.property("isDateRange") and not self.item.property("endDateTime"):
        #     invalidLabel = "endDateTimeLabel"

        else:
            invalidLabel = None

        if invalidLabel:
            name = self.item.property(invalidLabel).property("text")
            msg = self.S_REQUIRED_FIELD_ERROR.format(name=name)
            _log.debug(f"EventForm validation DIALOG: {msg}")
            QMessageBox.warning(
                self,
                "Required field",
                msg,
                QMessageBox.Ok,
            )
            return

        # Validation: Confirmations

        childEntry = self.childEntry()
        personEntry = self.personEntry()
        if (
            kind in (EventKind.Birth, EventKind.Adopted)
            and childEntry
            and not childEntry["isNewPerson"]
            and childEntry["person"]
        ):
            childPerson = childEntry["person"]
            if (kind == EventKind.Birth and childPerson.birthDateTime()) or (
                kind == EventKind.Adopted
                and self.scene.eventsFor(childPerson, kinds=EventKind.Adopted)
            ):
                button = QMessageBox.question(
                    self,
                    f"Replace {kind.name} event(s)?",
                    self.S_REPLACE_EXISTING.format(n_existing=1, kind=kind.name),
                )
                if button == QMessageBox.NoButton:
                    return

        elif kind == EventKind.Death and (
            personEntry and not personEntry["isNewPerson"] and personEntry["person"]
        ):

            person = personEntry["person"]
            if person.deceasedDateTime():
                button = QMessageBox.question(
                    self,
                    f"Replace {kind.name} event?",
                    self.S_REPLACE_EXISTING.format(n_existing=1, kind=kind.name),
                )
                if button == QMessageBox.NoButton:
                    return

        with self.scene.macro(f"Add '{kind.name}' event" if kind else "Add event"):
            self._save()

        self._events = []

    def _save(self):
        """
        Only here to be easily wrapped in a macro.
        """

        _log.debug(f"EventForm._save()")

        # Who

        personEntry = self.personEntry()
        spouseEntry = self.spouseEntry()
        childEntry = self.childEntry()

        # What

        kind: EventKind | None = None
        if self.item.property("kind"):
            kind = EventKind(self.item.property("kind"))
        description = self.item.property("description")
        symptom = self.item.property("symptom")
        anxiety = self.item.property("anxiety")
        if self.item.property("relationship"):
            relationship = RelationshipKind(self.item.property("relationship"))

            targetsEntries = self.targetsEntries()
            if not targetsEntries:
                targetsEntries = []

            trianglesEntries = self.trianglesEntries()
            if not trianglesEntries:
                trianglesEntries = []

        else:
            relationship: RelationshipKind | None = None
            targetsEntries = []
            trianglesEntries = []

        functioning = self.item.property("functioning")

        # When

        startDateTime = self.item.property("startDateTime")
        endDateTime = self.item.property("endDateTime")
        isDateRange = self.item.property("isDateRange")
        isDateRangeDirty = self.item.property("isDateRangeDirty")

        # Where

        location = self.item.property("location")

        # How

        notes = self.item.property("notes")

        # Meta
        color = self.item.property("colorBox").property("color")
        checkedTags = self._tagsModel.checkedTags()
        uncheckedTags = self._tagsModel.uncheckedTags()
        isEditing = self.item.property("isEditing")
        if isEditing:
            # Instead of real-time editing of tags only, enforce all checked and
            # unchecked tags on each event
            pass

        # Add People

        # Gather existing people and new people

        def _entry2Person(entry) -> Person:
            parts = entry["personName"].split(" ")
            firstName, lastName = parts[0], " ".join(parts[1:])
            return Person(
                name=firstName,
                lastName=lastName,
                gender=entry["gender"],
                size=self.scene.newPersonSize(),
            )

        person = None
        spouse = None
        child = None
        targets = []
        triangles = []

        newPeople = []
        newTargets = []
        newTriangles = []
        existingPeople = []
        if personEntry and personEntry["isNewPerson"]:
            person = _entry2Person(personEntry)
            newPeople.append(person)
        elif personEntry:
            person = personEntry["person"]
            existingPeople.append(person)
        if spouseEntry and spouseEntry["isNewPerson"]:
            spouse = _entry2Person(spouseEntry)
            newPeople.append(spouse)
        elif spouseEntry:
            spouse = spouseEntry["person"]
            existingPeople.append(spouse)
        if childEntry and childEntry["isNewPerson"]:
            child = _entry2Person(childEntry)
            newPeople.append(child)
        elif childEntry:
            child = childEntry["person"]
            existingPeople.append(child)
        for entry in targetsEntries:
            if entry["isNewPerson"]:
                targetPerson = _entry2Person(entry)
                newPeople.append(targetPerson)
                newTargets.append(targetPerson)
            else:
                targetPerson = entry["person"]
                existingPeople.append(targetPerson)
            targets.append(targetPerson)
        for entry in trianglesEntries:
            if entry["isNewPerson"]:
                trianglePerson = _entry2Person(entry)
                newPeople.append(trianglePerson)
                newTriangles.append(trianglePerson)
            else:
                trianglePerson = entry["person"]
                existingPeople.append(trianglePerson)
            triangles.append(trianglePerson)

        _log.debug(
            f"Adding {len(newPeople)} new people to scene, found {len(existingPeople)} existing people"
        )
        if newPeople:
            self.scene.addItems(*newPeople, undo=True)

        # Ensure variables in scene

        if any([symptom, anxiety, relationship, functioning]):
            existingEventProperties = [
                entry["name"] for entry in self.scene.eventProperties()
            ]
            if symptom and util.ATTR_SYMPTOM not in existingEventProperties:
                self.scene.addEventProperty(util.ATTR_SYMPTOM)
            if anxiety and util.ATTR_ANXIETY not in existingEventProperties:
                self.scene.addEventProperty(util.ATTR_ANXIETY)
            if relationship and util.ATTR_RELATIONSHIP not in existingEventProperties:
                self.scene.addEventProperty(util.ATTR_RELATIONSHIP)
            if functioning and util.ATTR_FUNCTIONING not in existingEventProperties:
                self.scene.addEventProperty(util.ATTR_FUNCTIONING)

        # Compile new Events, Marriages, Emotions

        newMarriages = []
        newEmotions = []

        if isEditing:

            for event in self._events:
                if kind != event.kind():
                    event.setKind(kind, undo=True)
                if spouse != event.spouse():
                    event.setSpouse(spouse, undo=True)
                if child and child != event.child():
                    event.setChild(child, undo=True)
                if kind == EventKind.Adopted:
                    event.child().setAdopted(True, undo=True)
                event.setDateTime(startDateTime, undo=True)
                if endDateTime != event.endDateTime():
                    event.setEndDateTime(endDateTime, undo=True)
                elif isDateRangeDirty and not isDateRange:
                    event.setEndDateTime(QDateTime(), undo=True)
                if symptom != event.symptom():
                    event.setSymptom(symptom, undo=True)
                if anxiety != event.anxiety():
                    event.setAnxiety(anxiety, undo=True)
                if relationship != event.relationship():
                    event.setRelationship(relationship, undo=True)
                    if targets:
                        event.setRelationshipTargets(targets, undo=True)
                    if relationship in (
                        RelationshipKind.Inside,
                        RelationshipKind.Outside,
                    ):
                        event.setRelationshipTriangles(triangles, undo=True)
                if functioning != event.functioning():
                    event.setFunctioning(functioning, undo=True)
                if description and description != event.description():
                    event.setDescription(description, undo=True)
                if location and location != event.location():
                    event.setLocation(location, undo=True)
                if notes and notes != event.notes():
                    event.setNotes(notes, undo=True)
                if color != event.color():
                    event.setColor(color, undo=True)
                # Tags
                if not isEditing:
                    event.setTags(checkedTags, undo=True)
                else:
                    current_tags = set(event.tags())
                    current_tags -= set(uncheckedTags)
                    current_tags |= set(checkedTags)
                    event.setTags(list(current_tags), undo=True)

        else:

            kwargs = {}
            if kind.isPairBond():

                marriage = None
                if spouse:
                    marriage = self.scene.marriageFor(person, spouse)

                # Default spouse if not added
                else:
                    if person.gender() == util.PERSON_KIND_MALE:
                        spouseKind = util.PERSON_KIND_FEMALE
                    elif person and person.gender() == util.PERSON_KIND_FEMALE:
                        spouseKind = util.PERSON_KIND_MALE
                    else:
                        spouseKind = util.PERSON_KIND_FEMALE
                    spouse = self.scene.addItem(
                        Person(
                            gender=spouseKind,
                            size=self.scene.newPersonSize(),
                        ),
                        undo=True,
                    )
                    newPeople.append(spouse)

                if not marriage:
                    marriage = self.scene.addItem(Marriage(person, spouse), undo=True)
                    newMarriages.append(marriage)

                # Default child if not added
                if kind in (EventKind.Birth, EventKind.Adopted):
                    if not child:

                        child = self.scene.addItem(
                            Person(size=self.scene.newPersonSize()), undo=True
                        )

                    child.setParents(marriage, undo=True)

                if kind == EventKind.Adopted:
                    child.setAdopted(True, undo=True)

                kwargs["child"] = child
                kwargs["spouse"] = spouse

            if endDateTime:
                kwargs["endDateTime"] = endDateTime
            if symptom is not None:
                kwargs["symptom"] = symptom
            if anxiety is not None:
                kwargs["anxiety"] = anxiety
            if relationship is not None:
                kwargs["relationship"] = relationship
                if targets:
                    kwargs["relationshipTargets"] = targets
                if relationship in (
                    RelationshipKind.Inside,
                    RelationshipKind.Outside,
                ):
                    kwargs["relationshipTriangles"] = triangles
            if functioning is not None:
                kwargs["functioning"] = functioning
            if description:
                kwargs["description"] = description
            if location:
                kwargs["location"] = location
            if notes:
                kwargs["notes"] = notes
            if color:
                kwargs["color"] = color
            if checkedTags:
                kwargs["tags"] = checkedTags

            event = self.scene.addItem(
                Event(kind, person, dateTime=startDateTime, **kwargs), undo=True
            )
            newEmotions.extend(self.scene.emotionsFor(event))

        # Arrange people
        spacing = (newPeople[0].sceneBoundingRect().width() * 2) if newPeople else 0

        if kind and kind.isOffspring():

            def _arrange_parents(childPos, parentA, parentB):
                # Use shared spec for positioning logic
                parent_size = parentA.size()
                spec = util.inferredParentSpec(childPos, parent_size)

                # Apply positions based on actual gender of parents
                if parentA.gender() == util.PERSON_KIND_MALE:
                    parentA.setItemPosNow(spec.male_pos)
                    parentB.setItemPosNow(spec.female_pos)
                else:
                    parentA.setItemPosNow(spec.female_pos)
                    parentB.setItemPosNow(spec.male_pos)

            if set(newPeople) == {person, spouse, child}:
                child.setItemPosNow(QPointF(0, spacing * 1.5))
                _arrange_parents(child.scenePos(), person, spouse)
            elif set(newPeople) == {person, spouse} and child:
                _arrange_parents(child.scenePos(), person, spouse)
            elif (
                {child} == set(newPeople) and child.parents() and child.parents().people
            ):
                parentA, parentB = child.parents().people
                parentAPos = parentA.itemPos()
                parentBPos = parentB.itemPos()
                xLeft = min(parentAPos.x(), parentBPos.x())
                xRight = max(parentAPos.x(), parentBPos.x())
                marriage = self.scene.marriageFor(parentA, parentB)
                siblings = [x for x in marriage.children if x != child]
                if siblings:
                    newSiblings = list(
                        sorted(
                            siblings + [child],
                            key=lambda x: x.birthDateTime(),
                        )
                    )
                    newIndex = newSiblings.index(child)
                    if newIndex == 0:
                        child.setItemPosNow(
                            QPointF(newSiblings[1].x() - spacing, newSiblings[1].y())
                        )
                    elif newIndex == len(newSiblings) - 1:
                        child.setItemPosNow(
                            QPointF(newSiblings[-2].x() + spacing, newSiblings[-2].y())
                        )
                    else:
                        child.setItemPosNow(
                            QPointF(
                                newSiblings[newIndex - 1].x()
                                + (
                                    newSiblings[newIndex + 1].x()
                                    - newSiblings[newIndex - 1].x()
                                )
                                / 2,
                                newSiblings[newIndex - 1].y(),
                            )
                        )
                else:
                    child.setItemPosNow(
                        QPointF(
                            xRight - (xRight - xLeft) / 2,
                            marriage.sceneBoundingRect().bottomLeft().y() + spacing,
                        )
                    )

        elif kind and spouse:
            if {person, spouse} == set(newPeople):
                person.setItemPosNow(QPointF(-spacing, 0))
                spouse.setItemPosNow(QPointF(spacing, 0))
            elif person in newPeople:
                if person.gender() == util.PERSON_KIND_MALE:
                    person.setItemPosNow(spouse.pos() + QPointF(-spacing * 2, 0))
                else:
                    person.setItemPosNow(spouse.pos() + QPointF(spacing * 2, 0))
            elif spouse in newPeople:
                if spouse.gender() == util.PERSON_KIND_MALE:
                    spouse.setItemPosNow(person.pos() + QPointF(-spacing * 2, 0))
                else:
                    spouse.setItemPosNow(person.pos() + QPointF(spacing * 2, 0))

        if relationship:
            existingTargets = [
                x["person"] for x in targetsEntries if not x["isNewPerson"]
            ]
            existingTriangles = [
                x["person"] for x in trianglesEntries if not x["isNewPerson"]
            ]
            personReference = person.pos() if person in newPeople else QPointF()
            targetsReference = (
                existingTargets[0].pos() if existingTargets else QPointF()
            )
            trianglesReference = (
                existingTriangles[0].pos() if existingTriangles else QPointF()
            )
            if person in newPeople:
                person.setItemPosNow(personReference + QPointF(-spacing, 0))
            for i, target in enumerate(newTargets):
                target.setItemPosNow(targetsReference + QPointF(spacing, i * (spacing)))
            for i, target in enumerate(newTriangles):
                target.setItemPosNow(
                    trianglesReference + QPointF(spacing, i * (spacing))
                )
        # elif kind == EventKind.CustomIndividual:
        #     existingPeople = [x for x in people if x not in newPeople]
        #     peopleReference = existingPeople[0].pos() if existingPeople else QPointF()
        #     for i, person in enumerate(newPeople):
        #         person.setItemPosNow(peopleReference + QPointF(-spacing, i * (spacing)))

        timelineModel = self.qmlEngine().rootContext().contextProperty("timelineModel")
        # Prevent the new person being invisible.
        if (
            newPeople
            and kind in (EventKind.Birth, EventKind.Adopted, EventKind.Death)
            and self.scene.currentDateTime() < startDateTime
        ):
            self.scene.setCurrentDateTime(startDateTime, undo=True)
        elif newEmotions:
            self.scene.setCurrentDateTime(newEmotions[0].startDateTime(), undo=True)
        elif self.scene.currentDateTime().isNull() and timelineModel.rowCount() > 0:
            self.scene.setCurrentDateTime(timelineModel.lastEventDateTime(), undo=True)
        for pathItem in newPeople + newMarriages + newEmotions:
            pathItem.flash()
        if self.item.property("isEditing"):
            self.doneEditing.emit()
        self.clear()
        self._cleanup()

    def canClose(self):
        if self.property("dirty"):
            discard = QMessageBox.question(
                self,
                "Discard changes?",
                "Are you sure you want to discard your changes to this event? Click 'Yes' to discard your changes, or click 'No' to finish adding the event.",
            )
            if discard == QMessageBox.No:
                return False
        return True

    def onCancel(self):
        """
        Same as onDone but no add logic.
        """
        self._cleanup()
        self.hideRequested.emit()

    def _cleanup(self):
        # if self._events and isinstance(self._events[0], DummyEvent):
        #     self.scene.removeItem(self._events[0])
        self._events = []
        self.scene.removeItem(self._dummyItem)
        self._dummyItem = None
        self._tagsModel.items = []
