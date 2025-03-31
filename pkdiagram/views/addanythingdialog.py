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
from pkdiagram.scene import EventKind, Person, Emotion, Event, Marriage
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
            {"name": "test_peopleListItem", "return": True},
            {"name": "setPeopleHelpText"},
            {"name": "initWithPairBond"},
            {"name": "initWithMultiplePeople"},
            {"name": "initWithNoSelection"},
            {"name": "setVariable"},
            {"name": "personEntry", "return": True, "parser": lambda x: x.toVariant()},
            {"name": "personAEntry", "return": True, "parser": lambda x: x.toVariant()},
            {"name": "personBEntry", "return": True, "parser": lambda x: x.toVariant()},
            {
                "name": "peopleEntries",
                "return": True,
                "parser": lambda x: [x for x in x.toVariant()],
            },
            {
                "name": "receiverEntries",
                "return": True,
                "parser": lambda x: [x for x in x.toVariant()],
            },
            {
                "name": "moverEntries",
                "return": True,
                "parser": lambda x: [x for x in x.toVariant()],
            },
        ]
    )

    submitted = pyqtSignal()

    S_REQUIRED_FIELD_ERROR = "'{name}' is a required field."
    S_EVENT_MONADIC_MULTIPLE_INDIVIDUALS = "This event type pertains to individuals so a separate event will be added to each one."
    S_HELP_TEXT_ADD_PEOPLE = "This will add {numPeople} people to the diagram"
    S_REPLACE_EXISTING = (
        "This will replace {n_existing} of the {kind} events in the selected people."
    )
    S_ADD_MANY_SYMBOLS = "Are you sure you want to create {numSymbols} symbols, with a separate symbol between each mover and each receiver listed?"
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
    def nextItemInChain(self, item):
        nextItem = item.nextItemInFocusChain()
        while not nextItem.isVisible() or not nextItem.isEnabled():
            nextItem = item.nextItemInFocusChain()
        return nextItem

    def onActiveFocusItemChanged(self):
        super().onActiveFocusItemChanged()
        # item = self.item.window().activeFocusItem()
        # if item:
        #     nextItem = item.nextItemInFocusChain()
        #     while not nextItem.isVisible() or not nextItem.isEnabled():
        #         nextItem = item.nextItemInFocusChain()
        #     nextItemParent = nextItem.parent()
        #     while not nextItemParent.objectName():
        #         nextItemParent = nextItemParent.parent()
        #     itemName = nextItem.objectName()
        #     parentName = nextItemParent.objectName()
        # else:
        #     itemName = ""
        #     parentName = ""
        # _log.info(
        #     f"AddAnythingDialog.onActiveFocusItemChanged: {parentName}.{itemName}"
        # )

    def initForSelection(self, selection: list):
        """
        Canonical entry point when showing. Could have a better name
        """
        self.clear()
        pairBond = Marriage.marriageForSelection(selection)
        # just for tags
        self._dummyEvent = DummyEvent(self.scene)
        self.scene.addItem(self._dummyEvent)
        self._eventModel.items = [self._dummyEvent]
        #
        if pairBond:
            self.initWithPairBond(pairBond.id)
        elif any(x.isPerson for x in selection):
            ids = [x.id for x in selection if x.isPerson]
            self.initWithMultiplePeople(ids)
        else:
            self.initWithNoSelection()

    def onDone(self):

        ## Validation first

        if self.item.property("kind") is None:
            kind = None
        else:
            kind = EventKind(self.item.property("kind"))
        personEntry = self.personEntry()
        personAEntry = self.personAEntry()
        personBEntry = self.personBEntry()
        peopleEntries = self.peopleEntries()
        moverEntries = self.moverEntries()
        receiverEntries = self.receiverEntries()
        description = self.item.property("description")
        location = self.item.property("location")
        startDateTime = self.item.property("startDateTime")
        endDateTime = self.item.property("endDateTime")
        isDateRange = self.item.property("isDateRange")
        anxiety = self.item.property("anxiety")
        functioning = self.item.property("functioning")
        symptom = self.item.property("symptom")
        notes = self.item.property("notes")
        tags = self._eventModel.items[0].tags()

        personPicker = self.item.property("personPicker")
        peoplePicker = self.item.property("peoplePicker")
        personAPicker = self.item.property("personAPicker")
        personBPicker = self.item.property("personBPicker")
        moversPicker = self.item.property("moversPicker")
        receiversPicker = self.item.property("receiversPicker")

        def _isPickerRequired(kind: EventKind, pickerName: str):
            if EventKind.isMonadic(kind) and pickerName == "personPicker":
                return True
            elif kind == EventKind.CustomIndividual and pickerName == "peoplePicker":
                return True
            elif EventKind.isPairBond(kind) and pickerName in (
                "personAPicker",
                "personBPicker",
            ):
                return True
            elif EventKind.isDyadic(kind) and pickerName in (
                "moversPicker",
                "receiversPicker",
            ):
                return True
            else:
                return False

        # Validation: Unsubmitted changes

        def pickerDirtyAndNotSubmitted(pickerItem):
            if pickerItem.metaObject().className().startswith("PersonPicker"):
                text = pickerItem.property("textEdit").property("text")
                isSubmitted = pickerItem.property("isSubmitted")
                if isSubmitted:
                    return False
                # required = _isPickerRequired(kind, pickerItem.objectName())
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

        if pickerDirtyAndNotSubmitted(personPicker):
            pickerLabel = "personLabel"
        elif pickerDirtyAndNotSubmitted(personAPicker):
            pickerLabel = "personALabel"
        elif pickerDirtyAndNotSubmitted(personBPicker):
            pickerLabel = "personBLabel"
        elif pickerDirtyAndNotSubmitted(peoplePicker):
            pickerLabel = "peopleLabel"
        elif pickerDirtyAndNotSubmitted(moversPicker):
            pickerLabel = "moversLabel"
        elif pickerDirtyAndNotSubmitted(receiversPicker):
            pickerLabel = "receiversLabel"
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

        def _invalidPersonPickerLabel():
            kindValue = self.item.property("kind")
            if not kindValue:
                return
            kind = EventKind(kindValue)
            ret = None

            # Refactor with _isPickerRequired?
            if kind == EventKind.CustomIndividual:
                if not peopleEntries:
                    ret = "peopleLabel"
            elif EventKind.isMonadic(kind):
                if not personPicker.property("isSubmitted"):
                    ret = "personLabel"
            elif EventKind.isPairBond(kind):
                if not personAPicker.property("isSubmitted"):
                    ret = "personALabel"
                elif not personBPicker.property("isSubmitted"):
                    ret = "personBLabel"
            elif EventKind.isDyadic(kind):
                if not moverEntries:
                    ret = "moversLabel"
                elif not receiverEntries:
                    ret = "receiversLabel"
            return ret

        invalidPersonPickerLabel = _invalidPersonPickerLabel()

        if invalidPersonPickerLabel:
            labelObjectName = invalidPersonPickerLabel
        elif not self.item.property("kind"):
            labelObjectName = "kindLabel"
        elif not self.item.property("description"):
            labelObjectName = "descriptionLabel"
        elif not self.item.property("startDateTime"):
            labelObjectName = "startDateTimeLabel"
        # Allowing open-ended dyadic date ranges for now.
        # elif self.item.property("isDateRange") and not self.item.property("endDateTime"):
        #     labelObjectName = "endDateTimeLabel"
        else:
            labelObjectName = None
        if labelObjectName:
            name = self.item.property(labelObjectName).property("text")
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

        if EventKind.isMonadic(kind):
            person = personEntry.get("person")
            if person:
                if any(
                    [
                        kind == EventKind.Birth and person.birthDateTime(),
                        kind == EventKind.Adopted and person.adoptedDateTime(),
                        kind == EventKind.Death and person.deceasedDateTime(),
                    ]
                ):
                    button = QMessageBox.question(
                        self,
                        f"Replace {kind.name} event(s)?",
                        self.S_REPLACE_EXISTING.format(n_existing=1, kind=kind.name),
                    )
                    if button == QMessageBox.NoButton:
                        return

        elif EventKind.isDyadic(kind):
            numSymbols = len(moverEntries) * len(receiverEntries)
            if numSymbols > 3:
                button = QMessageBox.question(
                    self,
                    "Create large number of symbols?",
                    self.S_ADD_MANY_SYMBOLS.format(numSymbols=numSymbols),
                )
                if button == QMessageBox.NoButton:
                    return

        elif kind == EventKind.CustomIndividual:
            numSymbols = len(peopleEntries)
            if numSymbols > 3:
                button = QMessageBox.question(
                    self,
                    "Create large number of symbols?",
                    self.S_ADD_MANY_SYMBOLS.format(numSymbols=numSymbols),
                )
                if button == QMessageBox.NoButton:
                    return

        with self.scene.macro(f"Add '{kind.name}' event"):
            self._addEvent()

        self.scene.removeItem(self._dummyEvent)
        self._dummyEvent = None

    def _addEvent(self):
        """
        Only here to be easily wrapped in a macro.
        """
        _log.debug(f"AddAnythingDialog.onDone: {self.item.property('kind')}")

        if self.item.property("kind") is None:
            kind = None
        else:
            kind = EventKind(self.item.property("kind"))
        personEntry = self.personEntry()
        personAEntry = self.personAEntry()
        personBEntry = self.personBEntry()
        peopleEntries = self.peopleEntries()
        moverEntries = self.moverEntries()
        receiverEntries = self.receiverEntries()
        description = self.item.property("description")
        location = self.item.property("location")
        startDateTime = self.item.property("startDateTime")
        endDateTime = self.item.property("endDateTime")
        isDateRange = self.item.property("isDateRange")
        anxiety = self.item.property("anxiety")
        functioning = self.item.property("functioning")
        symptom = self.item.property("symptom")
        notes = self.item.property("notes")
        tags = self._eventModel.items[0].tags()

        # Add People

        person = None
        personA = None
        personB = None
        parentA = None
        parentB = None
        people = None
        movers = None
        receivers = None
        newPeople = None
        newMarriages = []
        newEmotions = []

        def _entries2People(entries):
            existingPeople = []
            newPeople = []
            for entry in entries:
                if entry["isNewPerson"]:
                    parts = entry["personName"].split(" ")
                    firstName, lastName = parts[0], " ".join(parts[1:])
                    person = Person(
                        name=firstName, lastName=lastName, gender=entry["gender"]
                    )
                    newPeople.append(person)
                else:
                    existingPeople.append(entry["person"])
            return existingPeople, newPeople

        if EventKind.isMonadic(kind):
            existingPersons, newPersons = _entries2People([personEntry])
            if existingPersons:
                person = existingPersons[0]
            else:
                person = newPersons[0]
            existingPersonsA, newPersonsA = _entries2People([personAEntry])
            if existingPersonsA:
                parentA = existingPersonsA[0]
            else:
                parentA = newPersonsA[0]
            existingPersonsB, newPersonsB = _entries2People([personBEntry])
            if existingPersonsB:
                parentB = existingPersonsB[0]
            else:
                parentB = newPersonsB[0]
            newPeople = newPersons + newPersonsA + newPersonsB
        elif kind == EventKind.CustomIndividual:
            existingPeople, newPeople = _entries2People(peopleEntries)
            people = existingPeople + newPeople
        elif EventKind.isPairBond(kind):
            existingPeopleA, newPeopleA = _entries2People([personAEntry])
            if existingPeopleA:
                personA = existingPeopleA[0]
            else:
                personA = newPeopleA[0]
            existingPeopleB, newPeopleB = _entries2People([personBEntry])
            if existingPeopleB:
                personB = existingPeopleB[0]
            else:
                personB = newPeopleB[0]
            newPeople = newPeopleA + newPeopleB
        elif EventKind.isDyadic(kind):
            existingMovers, newMovers = _entries2People(moverEntries)
            existingReceivers, newReceivers = _entries2People(receiverEntries)
            movers = existingMovers + newMovers
            receivers = existingReceivers + newReceivers
            newPeople = newMovers + newReceivers

        _log.debug(f"Adding {len(newPeople)} new people to scene")
        if newPeople:
            self.scene.addItems(*newPeople)

        # Ensure variables in scene

        if anxiety is not None or functioning is not None or symptom is not None:
            existingEventProperties = [
                entry["name"] for entry in self.scene.eventProperties()
            ]
            if anxiety and util.ATTR_ANXIETY not in existingEventProperties:
                self.scene.addEventProperty(util.ATTR_ANXIETY)
            if functioning and util.ATTR_FUNCTIONING not in existingEventProperties:
                self.scene.addEventProperty(util.ATTR_FUNCTIONING)
            if symptom and util.ATTR_SYMPTOM not in existingEventProperties:
                self.scene.addEventProperty(util.ATTR_SYMPTOM)

        # Add Events

        newEvents = []

        if EventKind.isMonadic(kind):
            if kind in (EventKind.Birth, EventKind.Adopted, EventKind.Death):
                event = None
                if kind == EventKind.Birth:
                    event = person.birthEvent
                elif kind == EventKind.Adopted:
                    event = person.adoptedEvent
                    person.setAdopted(True)
                elif kind == EventKind.Death:
                    event = person.deathEvent
                event.setDateTime(startDateTime, undo=True)
                if location:
                    event.setLocation(location, undo=True)
                if notes:
                    event.setNotes(notes, undo=True)
                event.setTags(tags)
                newEvents.append(event)

                # Prevent the new person being invisible.
                if (
                    kind in (EventKind.Birth, EventKind.Adopted, EventKind.Death)
                    and self.scene.currentDateTime() < startDateTime
                ):
                    self.scene.setCurrentDateTime(startDateTime, undo=True)

                # Optional: Add Parents
                if (parentA or parentB) and kind in (
                    EventKind.Birth,
                    EventKind.Adopted,
                ):
                    if parentB and parentB.gender() == util.PERSON_KIND_MALE:
                        personAKind = util.PERSON_KIND_FEMALE
                    elif parentB and parentB.gender() == util.PERSON_KIND_FEMALE:
                        personAKind = util.PERSON_KIND_MALE
                    else:
                        parentAKind = util.PERSON_KIND_FEMALE

                    if parentA and parentA.gender() == util.PERSON_KIND_MALE:
                        personBKind = util.PERSON_KIND_FEMALE
                    elif parentA and parentA.gender() == util.PERSON_KIND_FEMALE:
                        personBKind = util.PERSON_KIND_MALE
                    else:
                        parentBKind = util.PERSON_KIND_FEMALE

                    if not parentA:
                        parentA = Person(
                            gender=parentAKind,
                            itemPos=QPointF(),
                            size=self.scene.newPersonSize(),
                        )
                        self.scene.addItem(parentA, undo=True)
                        newPeople.append(parentA)
                    if not parentB:
                        parentB = Person(
                            gender=personBKind,
                            itemPos=QPointF(),
                            size=self.scene.newPersonSize(),
                        )
                        self.scene.addItem(parentB, undo=True)
                        newPeople.append(parentB)
                    marriage = Marriage.marriageForSelection([parentA, parentB])
                    if not marriage:
                        marriage = Marriage(parentA, parentB)
                        self.scene.addItem(marriage, undo=True)
                        newMarriages.append(marriage)
                    person.setParents(marriage, undo=True)
            elif kind == EventKind.Cutoff:
                kwargs = {"endDateTime": endDateTime} if isDateRange else {}
                if notes:
                    kwargs["notes"] = notes
                emotion = Emotion(
                    kind=util.ITEM_CUTOFF,
                    personA=person,
                    startDateTime=startDateTime,
                    **kwargs,
                )
                self.scene.addItem(emotion, undo=True)
                newEmotions.append(emotion)
                newEvents.append(emotion.startEvent)
                if emotion.endEvent.dateTime():
                    newEvents.append(emotion.endEvent)

        elif kind == EventKind.CustomIndividual:
            kwargs = {"location": location} if location else {}
            for person in people:
                event = Event(
                    person,
                    description=description,
                    dateTime=startDateTime,
                    notes=notes,
                    tags=tags,
                    **kwargs,
                )
                self.scene.addItem(event, undo=True)
                newEvents.append(event)

        elif EventKind.isPairBond(kind):
            marriage = Marriage.marriageForSelection([personA, personB])
            if not marriage:
                # Generally there is only one marriage item per person. Multiple
                # marriages/weddings between the same person just get separate
                # `married`` events.
                marriage = Marriage(personA, personB)
                self.scene.addItem(marriage, undo=True)
                newMarriages.append(marriage)

            kwargs = {"endDateTime": endDateTime} if isDateRange else {}
            if kind == EventKind.CustomPairBond:
                kwargs["description"] = description
            else:
                kwargs["uniqueId"] = kind.value
            if location:
                kwargs["location"] = location
            if notes:
                kwargs["notes"] = notes

            _log.debug(
                f"Adding {kind} event to marriage {marriage} w/ {marriage.personA()} and {marriage.personB()}"
            )
            event = Event(marriage, dateTime=startDateTime, tags=tags, **kwargs)
            self.scene.addItem(event, undo=True)
            newEvents.append(event)

        elif EventKind.isDyadic(kind):
            itemMode = EventKind.itemModeFor(kind)
            if isDateRange:
                kwargs = {"endDateTime": endDateTime}
            else:
                kwargs = {}
            if notes and not startDateTime:
                kwargs["notes"] = notes
            for personA in movers:
                for personB in receivers:
                    emotion = Emotion(
                        kind=itemMode,
                        personA=personA,
                        personB=personB,
                        startDateTime=startDateTime,
                        tags=tags,
                        **kwargs,
                    )
                    emotion.startEvent.setTags(tags)
                    self.scene.addItem(emotion, undo=True)
                    if startDateTime:
                        # Have to set notes after setting scene for anonimize()
                        emotion.startEvent.setNotes(notes)
                    newEmotions.append(emotion)
                newEvents.append(emotion.startEvent)
                if emotion.endEvent.dateTime():
                    emotion.endEvent.setNotes(notes)
                    newEvents.append(emotion.endEvent)
        else:
            raise ValueError(f"Don't know how to handle EventKind {kind}")

        for event in newEvents:
            if anxiety is not None:
                event.dynamicProperty(util.ATTR_ANXIETY).set(anxiety)
            if functioning is not None:
                event.dynamicProperty(util.ATTR_FUNCTIONING).set(functioning)
            if symptom is not None:
                event.dynamicProperty(util.ATTR_SYMPTOM).set(symptom)

        # Arrange people
        spacing = (newPeople[0].boundingRect().width() * 2) if newPeople else None
        if EventKind.isMonadic(kind):

            def _arrange_parents(childPos, parentA, parentB):
                if parentA.gender() == util.PERSON_KIND_MALE:
                    parentA.setItemPosNow(childPos + QPointF(-spacing, -spacing * 1.5))
                    parentB.setItemPosNow(childPos + QPointF(spacing, -spacing * 1.5))
                else:
                    parentA.setItemPosNow(childPos + QPointF(spacing, -spacing * 1.5))
                    parentB.setItemPosNow(childPos + QPointF(-spacing, -spacing * 1.5))

            if {person, parentA, parentB} == set(newPeople):
                person.setItemPosNow(QPointF(0, spacing * 1.5))
                _arrange_parents(person.scenePos(), parentA, parentB)
            elif {parentA, parentB} == set(newPeople):
                _arrange_parents(person.scenePos(), parentA, parentB)
            elif (
                {person} == set(newPeople)
                and person.parents()
                and person.parents().people
            ):
                parentA, parentB = person.parents().people
                parentAPos = parentA.itemPos()
                parentBPos = parentB.itemPos()
                xLeft = min(parentAPos.x(), parentBPos.x())
                xRight = max(parentAPos.x(), parentBPos.x())
                marriage = Marriage.marriagesFor(parentA, parentB)[0]
                siblings = [x for x in marriage.children if x != person]
                if siblings:
                    newSiblings = list(
                        sorted(
                            siblings + [person],
                            key=lambda x: x.birthDateTime(),
                        )
                    )
                    newIndex = newSiblings.index(person)
                    if newIndex == 0:
                        person.setItemPosNow(
                            QPointF(newSiblings[1].x() - spacing, newSiblings[1].y())
                        )
                    elif newIndex == len(newSiblings) - 1:
                        person.setItemPosNow(
                            QPointF(newSiblings[-2].x() + spacing, newSiblings[-2].y())
                        )
                    else:
                        person.setItemPosNow(
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
                    person.setItemPosNow(QPointF((xRight - xLeft) / 2, parentAPos.y()))

        elif EventKind.isPairBond(kind):
            if {personA, personB} == set(newPeople):
                personA.setItemPosNow(QPointF(-spacing, 0))
                personB.setItemPosNow(QPointF(spacing, 0))
            elif personA in newPeople:
                if personA.gender() == util.PERSON_KIND_MALE:
                    personA.setItemPosNow(personB.pos() + QPointF(-spacing * 2, 0))
                else:
                    personA.setItemPosNow(personB.pos() + QPointF(spacing * 2, 0))
            elif personB in newPeople:
                if personB.gender() == util.PERSON_KIND_MALE:
                    personB.setItemPosNow(personA.pos() + QPointF(-spacing * 2, 0))
                else:
                    personB.setItemPosNow(personA.pos() + QPointF(spacing * 2, 0))
        elif EventKind.isDyadic(kind):
            newMovers = [x for x in movers if x in newPeople]
            newReceivers = [x for x in receivers if x in newPeople]
            existingMovers = [x for x in movers if x not in newPeople]
            existingReceivers = [x for x in receivers if x not in newPeople]
            moverReference = existingMovers[0].pos() if existingMovers else QPointF()
            receiverReference = (
                existingReceivers[0].pos() if existingReceivers else QPointF()
            )
            for i, mover in enumerate(newMovers):
                mover.setItemPosNow(moverReference + QPointF(-spacing, i * (spacing)))
            for i, receiver in enumerate(newReceivers):
                receiver.setItemPosNow(
                    receiverReference + QPointF(spacing, i * (spacing))
                )
        elif kind == EventKind.CustomIndividual:
            existingPeople = [x for x in people if x not in newPeople]
            peopleReference = existingPeople[0].pos() if existingPeople else QPointF()
            for i, person in enumerate(newPeople):
                person.setItemPosNow(peopleReference + QPointF(-spacing, i * (spacing)))

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
