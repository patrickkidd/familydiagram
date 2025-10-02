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
)
from pkdiagram.views import QmlDrawer

_log = logging.getLogger(__name__)


class DummyEvent(Event):
    def __init__(self, scene):
        super().__init__()
        self._scene = scene

    def scene(self):
        return self._scene


class AddAnythingDialog(QmlDrawer):

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

    submitted = pyqtSignal()

    S_REQUIRED_FIELD_ERROR = "'{name}' is a required field."
    S_HELP_TEXT_ADD_PEOPLE = "This will add {numPeople} people to the diagram"
    S_REPLACE_EXISTING = (
        "This will replace {n_existing} of the {kind} events in the selected people."
    )
    S_PICKER_NEW_PERSON_NOT_SUBMITTED = "You have entered a name for a new person in the '{pickerLabel}' field, but have not pressed enter yet."

    def __init__(self, engine, parent=None, **contextProperties):
        super().__init__(
            engine,
            "qml/AddAnythingDialog.qml",
            parent=parent,
            resizable=False,
            objectName="addEverythingDialog",
            **contextProperties,
        )
        self._dummyEvent = None

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
        self._eventModel = self.item.property("eventModel")

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
    #         f"AddAnythingDialog.onActiveFocusItemChanged: {parentName}.{itemName}[{itemClassName}]"
    #     )

    def initForSelection(self, selection: list):
        """
        Canonical entry point when showing. Could have a better name
        """
        self.clear()

        # just for tags
        self._dummyEvent = DummyEvent(self.scene)
        self.scene.addItem(self._dummyEvent)
        self._eventModel.items = [self._dummyEvent]

        #
        pairBond = Marriage.marriageForSelection(selection)
        if pairBond:
            self.initWithPerson(pairBond.personA().id)
        elif any(x.isPerson for x in selection):
            id = next(x.id for x in selection if x.isPerson)
            self.initWithPerson(id)
        else:
            self.initWithNoSelection()

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

        invalidLabel = None

        if not self.item.property("kind"):
            invalidLabel = "kindLabel"

        elif not self.item.property("personPicker").property("isSubmitted"):
            invalidLabel = "personLabel"

        elif kind and kind == EventKind.Death:
            pass

        elif (
            kind
            and kind
            in (
                EventKind.Bonded,
                EventKind.Married,
                EventKind.Separated,
                EventKind.Divorced,
            )
            and not self.item.property("spousePicker").property("isSubmitted")
        ):
            invalidLabel = "spouseLabel"

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
            _log.debug(f"AddAnythingDialog validation DIALOG: {msg}")
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
                kind == EventKind.Adopted and childPerson.adoptedDateTime()
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
            self._addEvent()

        self.scene.removeItem(self._dummyEvent)
        self._dummyEvent = None

    def _addEvent(self):
        """
        Only here to be easily wrapped in a macro.
        """

        _log.debug(f"AddAnythingDialog._addEvent()")

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
        relationship: RelationshipKind | None = None
        if self.item.property("relationship"):
            relationship = RelationshipKind(self.item.property("relationship"))
        functioning = self.item.property("functioning")

        # When

        startDateTime = self.item.property("startDateTime")
        endDateTime = self.item.property("endDateTime")
        isDateRange = self.item.property("isDateRange")

        # Where

        location = self.item.property("location")

        # How

        notes = self.item.property("notes")

        # Meta

        tags = self._eventModel.items[0].tags()

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

        targetsEntries = self.targetsEntries()
        if not targetsEntries:
            targetsEntries = []

        trianglesEntries = self.trianglesEntries()
        if not trianglesEntries:
            trianglesEntries = []

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
            self.scene.addItems(*newPeople)

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

        # Compile Events, Marriages, Emotions

        events = []
        newMarriages = []
        newEmotions = []

        if kind in (EventKind.Birth, EventKind.Adopted, EventKind.Death):

            # Prevent the new person being invisible.
            if (
                kind in (EventKind.Birth, EventKind.Adopted, EventKind.Death)
                and self.scene.currentDateTime() < startDateTime
            ):
                self.scene.setCurrentDateTime(startDateTime, undo=True)

            # Set up spouse and child relations; all births now have 2 parents and a child
            if kind in (EventKind.Birth, EventKind.Adopted):

                # Default child if not added
                if not child:
                    child = self.scene.addItem(
                        Person(
                            size=self.scene.newPersonSize(),
                        ),
                        undo=True,
                    )
                    newPeople.append(child)

                # Default spouse if not added
                if not spouse:
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

                marriage = Marriage.marriageForSelection([person, spouse])
                if not marriage:
                    marriage = Marriage(person, spouse)
                    self.scene.addItem(marriage, undo=True)
                    newMarriages.append(marriage)

                if child.parents != marriage:
                    child.setParents(marriage, undo=True)

            if kind == EventKind.Birth:
                event = child.birthEvent
            elif kind == EventKind.Adopted:
                event = child.adoptedEvent
                child.setAdopted(True)
            elif kind == EventKind.Death:
                event = person.deathEvent

            event.setDateTime(startDateTime, undo=True)

        elif kind and spouse:
            marriage = Marriage.marriageForSelection([person, spouse])
            if not marriage:
                # Generally there is only one marriage item per person. Multiple
                # marriages/weddings between the same person just get separate
                # `married`` events.
                marriage = Marriage(person, spouse)
                self.scene.addItem(marriage, undo=True)
                newMarriages.append(marriage)

            kwargs = {"endDateTime": endDateTime} if isDateRange else {}
            kwargs["uniqueId"] = kind.value
            if kind != EventKind.VariableShift:
                kwargs["description"] = kind.name
            else:
                kwargs["description"] = description

            _log.debug(
                f"Adding {kind.name} event to marriage {marriage} w/ {marriage.personA()} and {marriage.personB()}"
            )
            event = Event(marriage, dateTime=startDateTime, **kwargs)
            self.scene.addItem(event, undo=True)
            events.append(event)

        elif relationship:
            itemMode = relationship.itemMode()
            if isDateRange:
                kwargs = {"endDateTime": endDateTime}
            else:
                kwargs = {}
            kwargs["description"] = description
            if notes and not startDateTime:
                kwargs["notes"] = notes
            for target in targets:
                emotion = Emotion(
                    kind=itemMode,
                    personA=person,
                    personB=target,
                    startDateTime=startDateTime,
                    tags=tags,
                    **kwargs,
                )
                self.scene.addItem(emotion, undo=True)
                newEmotions.append(emotion)
                events.append(emotion.startEvent)
                emotion.startEvent.setRelationshipTargets(targets)
                if emotion.endEvent.dateTime():
                    events.append(emotion.endEvent)
                if relationship in (RelationshipKind.Inside, RelationshipKind.Outside):
                    emotion.startEvent.setRelationshipTargets(targets)
                    emotion.endEvent.setRelationshipTriangles(triangles)

        else:
            kwargs = {"location": location} if location else {}
            event = Event(
                person,
                description=description,
                dateTime=startDateTime,
                **kwargs,
            )
            self.scene.addItem(event, undo=True)
            events.append(event)

        for event in events:
            if symptom is not None:
                event.dynamicProperty(util.ATTR_SYMPTOM).set(symptom)
            if anxiety is not None:
                event.dynamicProperty(util.ATTR_ANXIETY).set(anxiety)
            if relationship is not None:
                event.dynamicProperty(util.ATTR_RELATIONSHIP).set(relationship)
            if functioning is not None:
                event.dynamicProperty(util.ATTR_FUNCTIONING).set(functioning)
            event.setTags(tags, undo=True)
            if location:
                event.setLocation(location, undo=True)
            if notes:
                event.setNotes(notes, undo=True)
            if relationship in (RelationshipKind.Inside, RelationshipKind.Outside):
                event.setRelationship

        # Arrange people
        spacing = (newPeople[0].boundingRect().width() * 2) if newPeople else 0

        if kind and kind.isOffspring():

            def _arrange_parents(childPos, parentA, parentB):
                if parentA.gender() == util.PERSON_KIND_MALE:
                    parentA.setItemPosNow(childPos + QPointF(-spacing, -spacing * 1.5))
                    parentB.setItemPosNow(childPos + QPointF(spacing, -spacing * 1.5))
                else:
                    parentA.setItemPosNow(childPos + QPointF(spacing, -spacing * 1.5))
                    parentB.setItemPosNow(childPos + QPointF(-spacing, -spacing * 1.5))

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
                marriage = Marriage.marriagesFor(parentA, parentB)[0]
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
                    child.setItemPosNow(QPointF((xRight - xLeft) / 2, parentAPos.y()))

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
        if self.scene.currentDateTime().isNull() and timelineModel.rowCount() > 0:
            self.scene.setCurrentDateTime(timelineModel.lastEventDateTime(), undo=True)
        for pathItem in newPeople + newMarriages + newEmotions:
            pathItem.flash()
        self.submitted.emit()  # for testing
        self.clear()

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
        self.scene.removeItem(self._dummyEvent)
        self._dummyEvent = None
        self.hideRequested.emit()
