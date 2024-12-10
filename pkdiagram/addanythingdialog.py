import logging

from .pyqt import (
    pyqtSignal,
    QMessageBox,
    QEvent,
    Qt,
    pyqtSignal,
    QPointF,
    QMetaObject,
    QVariant,
    Q_RETURN_ARG,
    Q_ARG,
)
from . import util, commands, slugify
from .objects import Person, Emotion, Event, Marriage
from .qmldrawer import QmlDrawer
from .util import EventKind
from pkdiagram.widgets.qml.peoplepicker import add_new_person, add_existing_person
from pkdiagram.widgets.qml.personpicker import set_new_person, set_existing_person
from pkdiagram.widgets import ActiveListEdit

_log = logging.getLogger(__name__)


class AddAnythingDialog(QmlDrawer):

    QmlDrawer.registerQmlMethods(
        [
            {"name": "clear"},
            {"name": "adjustFlickableHack"},
            {"name": "test_peopleListItem", "return": True},
            {"name": "setPeopleHelpText"},
            {"name": "initWithPairBond"},
            {"name": "initWithMultiplePeople"},
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
        self._returnTo = None
        self._canceled = False

        # self.startTimer(1000)

    #     item = self.qml.rootObject().window().activeFocusItem()
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
        self.qml.rootObject().setProperty("widget", self)
        self.qml.rootObject().cancel.connect(self.onCancel)
        self._eventModel = self.rootProp("eventModel")

    @staticmethod
    def nextItemInChain(self, item):
        nextItem = item.nextItemInFocusChain()
        while not nextItem.isVisible() or not nextItem.isEnabled():
            nextItem = item.nextItemInFocusChain()
        return nextItem

    def onActiveFocusItemChanged(self):
        super().onActiveFocusItemChanged()
        # item = self.qml.rootObject().window().activeFocusItem()
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

    def eventFilter(self, o, e):
        if e.type() == QEvent.KeyPress and e.key() == Qt.Key_Escape:
            e.accept()
            self.onCancel()
            return True
        return False

    def initForSelection(self, selection):
        """
        Canonical entry point when showing. Could have a better name
        """
        self.clear()
        self.adjustFlickableHack()
        pairBond = Marriage.marriageForSelection(selection)
        if pairBond:
            self.initWithPairBond(pairBond.id)
        elif any(x.isPerson for x in selection):
            ids = [x.id for x in selection if x.isPerson]
            self.initWithMultiplePeople(ids)
        # just for tags
        self._eventModel.items = [Event(addDummy=True)]

    def onDone(self):
        _log.debug(f"AddAnythingDialog.onDone: {self.rootProp('kind')}")

        if self.rootProp("kind") is None:
            kind = None
        else:
            kind = EventKind(self.rootProp("kind"))
        personEntry = self.personEntry()
        personAEntry = self.personAEntry()
        personBEntry = self.personBEntry()
        peopleEntries = self.peopleEntries()
        moverEntries = self.moverEntries()
        receiverEntries = self.receiverEntries()
        description = self.rootProp("description")
        location = self.rootProp("location")
        startDateTime = self.rootProp("startDateTime")
        endDateTime = self.rootProp("endDateTime")
        isDateRange = self.rootProp("isDateRange")
        anxiety = self.rootProp("anxiety")
        functioning = self.rootProp("functioning")
        symptom = self.rootProp("symptom")
        notes = self.rootProp("notes")
        tags = self._eventModel.items[0].tags()

        personPicker = self.findItem("personPicker")
        peoplePicker = self.findItem("peoplePicker")
        personAPicker = self.findItem("personAPicker")
        personBPicker = self.findItem("personBPicker")
        moversPicker = self.findItem("moversPicker")
        receiversPicker = self.findItem("receiversPicker")

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
            text = self.itemProp(pickerLabel, "text")
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
            kindValue = self.rootProp("kind")
            if not kindValue:
                return
            kind = EventKind(kindValue)
            ret = None

            # Refactor with _isPickerRequired?
            if kind == EventKind.CustomIndividual:
                if not peopleEntries:
                    ret = "peopleLabel"
            elif EventKind.isMonadic(kind):
                if not self.itemProp("personPicker", "isSubmitted"):
                    ret = "personLabel"
            elif EventKind.isPairBond(kind):
                if not self.itemProp("personAPicker", "isSubmitted"):
                    ret = "personALabel"
                elif not self.itemProp("personBPicker", "isSubmitted"):
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
        elif not self.rootProp("kind"):
            labelObjectName = "kindLabel"
        elif not self.rootProp("description"):
            labelObjectName = "descriptionLabel"
        elif not self.rootProp("startDateTime"):
            labelObjectName = "startDateTimeLabel"
        elif self.rootProp("isDateRange") and not self.rootProp("endDateTime"):
            labelObjectName = "endDateTimeLabel"
        else:
            labelObjectName = None
        if labelObjectName:
            name = self.itemProp(labelObjectName, "text")
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
        commands.stack().beginMacro(
            f"Add {kind.value} event, with {len(newPeople)} new people."
        )
        if newPeople:
            commands.addPeople(self.scene, newPeople)

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
        propertyUndoId = commands.nextId()

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
                event.setDateTime(startDateTime, undo=propertyUndoId)
                if location:
                    event.setLocation(location, undo=propertyUndoId)
                if notes:
                    event.setNotes(notes, undo=propertyUndoId)
                event.setTags(tags)
                newEvents.append(event)

                # Prevent the new person being invisible.
                if (
                    kind in (EventKind.Birth, EventKind.Adopted, EventKind.Death)
                    and self.scene.currentDateTime() < startDateTime
                ):
                    self.scene.setCurrentDateTime(startDateTime, undo=propertyUndoId)

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
                        parentA = commands.addPerson(
                            self.scene,
                            parentAKind,
                            QPointF(),
                            self.scene.newPersonSize(),
                        )
                        newPeople.append(parentA)
                    if not parentB:
                        parentB = commands.addPerson(
                            self.scene,
                            personBKind,
                            QPointF(),
                            self.scene.newPersonSize(),
                        )
                        newPeople.append(parentB)
                    marriage = Marriage.marriageForSelection([parentA, parentB])
                    if not marriage:
                        marriage = commands.addMarriage(self.scene, parentA, parentB)
                    commands.setParents(person, marriage)
            elif kind == EventKind.Cutoff:
                kwargs = {"endDateTime": endDateTime} if isDateRange else {}
                if notes:
                    kwargs["notes"] = notes
                emotion = commands.addEmotion(
                    self.scene,
                    Emotion(
                        kind=util.ITEM_CUTOFF,
                        personA=person,
                        startDateTime=startDateTime,
                        **kwargs,
                    ),
                )
                newEvents.append(emotion.startEvent)
                if emotion.endEvent.dateTime():
                    newEvents.append(emotion.endEvent)

        elif kind == EventKind.CustomIndividual:
            kwargs = {"location": location} if location else {}
            for person in people:
                event = commands.addEvent(
                    person,
                    Event(
                        description=description,
                        dateTime=startDateTime,
                        notes=notes,
                        tags=tags,
                        **kwargs,
                    ),
                )
                newEvents.append(event)

        elif EventKind.isPairBond(kind):
            marriage = Marriage.marriageForSelection([personA, personB])
            if not marriage:
                # Generally there is only one marriage item per person. Multiple
                # marriages/weddings between the same person just get separate
                # `married`` events.
                marriage = commands.addMarriage(self.scene, personA, personB)

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
            event = commands.addEvent(
                marriage,
                Event(dateTime=startDateTime, tags=tags, **kwargs),
            )
            newEvents.append(event)

        elif EventKind.isDyadic(kind):
            itemMode = EventKind.itemModeFor(kind)
            if isDateRange:
                kwargs = {"endDateTime": endDateTime}
            else:
                kwargs = {}
            if notes:
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
                    commands.addEmotion(self.scene, emotion)
                newEvents.append(emotion.startEvent)
                if emotion.endEvent.dateTime():
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
            self.scene.setCurrentDateTime(
                timelineModel.lastEventDateTime(), undo=propertyUndoId
            )
        commands.stack().endMacro()
        self.submitted.emit()  # for testing
        self.clear()

    def canClose(self):
        if self.property("dirty") and not self._canceled:
            discard = QMessageBox.question(
                self,
                "Discard changes?",
                "Are you sure you want to discard your changes to this event? Click 'Yes' to discard your changes, or click 'No' to finish adding the event.",
            )
            if discard == QMessageBox.No:
                return False
            self._canceled = True
        return True

    def onCancel(self):
        """Cancel button; supports returnTo"""
        if not self.canClose():
            return
        super().onDone()
        # self.hide(callback=self.clear)

    ## Testing

    def set_person_picker_gender(self, personPicker, genderLabel):
        genderBox = self.itemProp(personPicker, "genderBox")
        assert genderBox is not None, f"Could not find genderBox for {personPicker}"
        self.clickComboBoxItem(genderBox, genderLabel)

    def set_people_picker_gender(self, peoplePicker, personIndex, genderLabel):
        peopleAList = self.findItem(peoplePicker)
        picker = QMetaObject.invokeMethod(
            peopleAList,
            "pickerAtIndex",
            Qt.DirectConnection,
            Q_RETURN_ARG(QVariant),
            personIndex,
        )
        assert (
            picker is not None
        ), f"Could not find picker for {peoplePicker}:{personIndex}"
        genderBox = picker.findChild("genderBox")
        assert (
            genderBox is not None
        ), f"Could not find genderBox for {peoplePicker}:{personIndex}"
        self.clickComboBoxItem(picker, genderLabel)

    def set_kind(self, kind: EventKind):
        self.clickComboBoxItem("kindBox", EventKind.menuLabelFor(kind), force=False)

    def set_description(self, description: str):
        self.keyClicks("descriptionEdit", description)

    def set_new_person(
        self,
        personPicker: str,
        textInput: str,
        gender: str = None,
        returnToFinish: bool = True,
        resetFocus: bool = False,
    ):
        set_new_person(
            self,
            textInput,
            personPicker,
            gender,
            returnToFinish=returnToFinish,
            resetFocus=resetFocus,
        )
        # _log.info(f"set_new_person('{personPicker}', '{textInput}')")
        # self.keyClicks(f"{personPicker}.textEdit", textInput, returnToFinish=True)
        if returnToFinish:
            assert self.itemProp(personPicker, "isSubmitted") == True
            assert self.itemProp(personPicker, "isNewPerson") == True
            assert self.itemProp(personPicker, "personName") == textInput
        else:
            assert self.itemProp(f"{personPicker}.textEdit", "text") == textInput

    def set_existing_person(
        self,
        personPicker: str,
        person: Person,
        autoCompleteInput: str = None,
        returnToFinish: bool = False,
        resetFocus: bool = False,
    ):
        # _log.info(
        #     f"_set_new_person('{personPicker}', {person}, autoCompleteInput='{autoCompleteInput}')"
        # )
        set_existing_person(
            self,
            person,
            autoCompleteInput,
            personPicker,
            returnToFinish=returnToFinish,
            resetFocus=resetFocus,
        )
        # assert self.itemProp(f"{personPicker}.popupListView", "visible") == False
        # if not autoCompleteInput:
        #     autoCompleteInput = person.fullNameOrAlias()
        # self.keyClicks(
        #     f"{personPicker}.textEdit",
        #     autoCompleteInput,
        #     resetFocus=False,
        #     returnToFinish=returnToFinish,
        # )
        # assert self.itemProp(f"{personPicker}.popupListView", "visible") == True
        # self.clickListViewItem_actual(
        #     f"personPicker.popupListView", person.fullNameOrAlias()
        # )

    def add_new_person(
        self,
        peoplePicker: str,
        textInput: str,
        gender: str = None,
        returnToFinish: bool = True,
        resetFocus: bool = False,
    ):
        add_new_person(
            self,
            textInput,
            peoplePicker=peoplePicker,
            gender=gender,
            returnToFinish=returnToFinish,
            resetFocus=resetFocus,
        )

    def add_existing_person(
        self,
        peoplePicker: str,
        person: Person,
        autoCompleteInput: str = None,
    ):
        add_existing_person(
            self, person, autoCompleteInput=autoCompleteInput, peoplePicker=peoplePicker
        )

    def set_dateTime(
        self,
        dateTime,
        buttonsItem,
        datePickerItem,
        timePickerItem,
        returnToFinish: bool = False,
        resetFocus: bool = False,
    ):

        S_DATE = util.dateString(dateTime)
        S_TIME = util.timeString(dateTime)

        # _log.info(
        #     f"Setting {buttonsItem}, {datePickerItem}, {timePickerItem} to {dateTime}"
        # )

        self.keyClicks(
            f"{buttonsItem}.dateTextInput",
            S_DATE,
            returnToFinish=returnToFinish,
            resetFocus=resetFocus,
        )
        self.keyClicks(
            f"{buttonsItem}.timeTextInput",
            S_TIME,
            returnToFinish=returnToFinish,
            resetFocus=resetFocus,
        )
        assert self.itemProp(buttonsItem, "dateTime") == dateTime
        assert self.itemProp(datePickerItem, "dateTime") == dateTime
        assert self.itemProp(timePickerItem, "dateTime") == dateTime

    def set_startDateTime(self, dateTime):
        self.set_dateTime(
            dateTime, "startDateButtons", "startDatePicker", "startTimePicker"
        )

    def set_isDateRange(self, on):
        if not self.rootProp("isDateRange"):
            assert self.itemProp("endDateTimeLabel", "visible") == False
            assert self.itemProp("endDateButtons", "visible") == False
            assert self.itemProp("endDatePicker", "visible") == False
            assert self.itemProp("endTimePicker", "visible") == False
            assert (
                self.itemProp("isDateRangeBox", "visible") == True
            ), f"isDateRangeBox hidden; incorrect event kind '{self.rootProp('kind')}'"
            self.setItemProp("isDateRangeBox", "checked", True)
            # self.mouseClick("isDateRangeBox")
            assert self.rootProp("isDateRange") == True

    def set_endDateTime(self, dateTime):
        self.set_isDateRange(True)
        assert self.itemProp("endDateTimeLabel", "visible") == True
        assert self.itemProp("endDateButtons", "visible") == True
        assert self.itemProp("endDatePicker", "visible") == True
        assert self.itemProp("endTimePicker", "visible") == True
        self.set_dateTime(dateTime, "endDateButtons", "endDatePicker", "endTimePicker")

        # Annoying behavior only in test (so far)
        # Re-set the checkbox since clicking into the text boxes seems to uncheck it
        if not self.rootProp("isDateRange"):
            self.setItemProp("isDateRangeBox", "checked", True)

    def set_notes(self, notes):
        self.keyClicks("notesEdit", notes, returnToFinish=False)

    def expectedFieldLabel(self, expectedTextLabel):
        name = self.itemProp(expectedTextLabel, "text")
        expectedText = self.S_REQUIRED_FIELD_ERROR.format(name=name)
        util.qtbot.clickOkAfter(
            lambda: self.mouseClick("AddEverything_submitButton"),
            text=expectedText,
        )

    def pickerNotSubmitted(self, pickerLabel):
        name = self.itemProp(pickerLabel, "text")
        expectedText = self.S_PICKER_NEW_PERSON_NOT_SUBMITTED.format(pickerLabel=name)
        util.qtbot.clickOkAfter(
            lambda: self.mouseClick("AddEverything_submitButton"),
            text=expectedText,
        )

    def set_anxiety(self, x):
        self.setVariable("anxiety", x)

    def set_functioning(self, x):
        self.setVariable("functioning", x)

    def set_symptom(self, x):
        self.setVariable("symptom", x)

    def _scrollToTagsField(self):
        # y = self.itemProp("addPage.tagsField", "y")
        # addPage = self.findItem("addPage")
        # tagsEdit = self.findItem("tagsEdit")
        # contentY = tagsEdit.mapToItem(addPage, QPointF(0, y)).y()
        # _log.debug(f"Scrolling to tags field at contentY: {contentY}")
        self.setItemProp("addPage", "contentY", 200)

    def add_tag(self, tag: str):
        self._scrollToTagsField()
        tagsEdit = ActiveListEdit(self, self.rootProp("tagsEdit"))
        tagsEdit.clickAddAndRenameRow(tag)

    def set_active_tags(self, tags: list[str]):
        self._scrollToTagsField()
        tagsEdit = ActiveListEdit(self, self.rootProp("tagsEdit"))
        for tag in tags:
            tagsEdit.clickActiveBox(tag)

    # scripts

    def add_person_by_birth(self, personName: str, startDateTime) -> Person:
        self.set_kind(EventKind.Birth)
        self.set_new_person("personPicker", personName)
        self.set_startDateTime(startDateTime)
        self.mouseClick("AddEverything_submitButton")
        person = self.scene.query1(methods={"fullNameOrAlias": personName})
        return person

    def add_marriage_to_person(self, person: Person, spouseName, startDateTime):
        pre_marriages = set(person.marriages)
        self.set_kind(EventKind.Married)
        self.set_existing_person("personAPicker", person)
        self.set_new_person("personBPicker", spouseName)
        self.set_startDateTime(startDateTime)
        self.mouseClick("AddEverything_submitButton")
        spouse = self.scene.query1(methods={"fullNameOrAlias": spouseName})
        return (set(person.marriages) - pre_marriages).pop()

    def add_event_to_marriage(self, marriage: Marriage, kind: EventKind, startDateTime):
        pre_events = set(marriage.events())
        self.set_kind(kind)
        self.set_existing_person("personAPicker", marriage.personA())
        self.set_existing_person("personBPicker", marriage.personB())
        self.set_startDateTime(startDateTime)
        self.mouseClick("AddEverything_submitButton")
        return (set(marriage.events()) - pre_events).pop()


def __test__(scene, parent):
    dlg = AddAnythingDialog(parent)
    dlg.setScene(scene)
    dlg.show(animate=False)
    parent.show()
    parent.resize(400, 600)
    return dlg
