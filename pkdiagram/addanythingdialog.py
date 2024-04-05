import logging

from .pyqt import pyqtSignal, QMessageBox, QObject, QEvent, Qt, pyqtSignal, QPointF
from . import objects, util, commands
from .objects import Person, Emotion, Event, Marriage
from .qmldrawer import QmlDrawer
from .util import EventKind


_log = logging.getLogger(__name__)


class AddAnythingDialog(QmlDrawer):

    QmlDrawer.registerQmlMethods(
        [
            {"name": "clear"},
            {"name": "test_peopleListItem", "return": True},
            {"name": "setPeopleHelpText"},
            {"name": "initWithPairBond"},
            {"name": "initWithMultiplePeople"},
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

    def __init__(self, parent=None, sceneModel=None):
        super().__init__(
            "qml/AddAnythingDialog.qml",
            parent=parent,
            resizable=False,
            objectName="addEverythingDialog",
            sceneModel=sceneModel,
        )
        self._returnTo = None
        self._canceled = False

    def onInitQml(self):
        super().onInitQml()
        self.qml.rootObject().setProperty("widget", self)
        self.qml.rootObject().cancel.connect(self.onCancel)

    def eventFilter(self, o, e):
        if e.type() == QEvent.KeyPress and e.key() == Qt.Key_Escape:
            e.accept()
            self.onCancel()
            return True
        return False

    def initForSelection(self, selection):
        self.clear()
        pairBond = Marriage.marriageForSelection(selection)
        if pairBond:
            self.initWithPairBond(pairBond.id)
        elif any(x.isPerson for x in selection):
            ids = [x.id for x in selection if x.isPerson]
            self.initWithMultiplePeople(ids)

    def onDone(self):
        _log.info(f"AddAnythingDialog.onDone")

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

        # Validation: Required fields

        def _invalidPersonPickerLabel():
            kindValue = self.rootProp("kind")
            if not kindValue:
                return
            kind = EventKind(kindValue)
            ret = None
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
            _log.info(f"AddAnythingForm validation DIALOG: {msg}")
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

        _log.info(f"Adding {len(newPeople)} new people to scene")
        commands.stack().beginMacro(
            f"Add {kind.value} event, with {len(newPeople)} new people."
        )
        commands.addPeople(self.scene, newPeople)

        # Kind-specific logic

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

                # Optional: Add Parents
                if (parentA or parentB) and kind in (
                    EventKind.Birth,
                    EventKind.Adopted,
                ):
                    if not parentA:
                        parentA = commands.addPerson(
                            self.scene,
                            util.PERSON_KIND_FEMALE,
                            QPointF(),
                            self.scene.newPersonSize(),
                        )
                    if not parentB:
                        parentB = commands.addPerson(
                            self.scene,
                            util.PERSON_KIND_MALE,
                            QPointF(),
                            self.scene.newPersonSize(),
                        )
                    marriage = Marriage.marriageForSelection([parentA, parentB])
                    if not marriage:
                        marriage = commands.addMarriage(self.scene, parentA, parentB)
                    commands.setParents(person, marriage)
            elif kind == EventKind.Cutoff:
                kwargs = {"endDateTime": endDateTime} if isDateRange else {}
                commands.addEmotion(
                    self.scene,
                    Emotion(
                        kind=util.ITEM_CUTOFF,
                        personA=person,
                        startDateTime=startDateTime,
                        **kwargs,
                    ),
                )

        elif kind == EventKind.CustomIndividual:
            kwargs = {"location": location} if location else {}
            for person in people:
                commands.addEvent(
                    person,
                    Event(description=description, dateTime=startDateTime, **kwargs),
                )

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
            commands.addEvent(
                marriage,
                Event(startDateTime=startDateTime, **kwargs),
            )

        elif EventKind.isDyadic(kind):
            itemMode = EventKind.itemModeFor(kind)
            if isDateRange:
                kwargs = {"endDateTime": endDateTime}
            else:
                kwargs = {}
            for personA in movers:
                for personB in receivers:
                    commands.addEmotion(
                        self.scene,
                        Emotion(
                            kind=itemMode,
                            personA=personA,
                            personB=personB,
                            startDateTime=startDateTime,
                            **kwargs,
                        ),
                    )
        else:
            raise ValueError(f"Don't know how to handle EventKind {kind}")

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


def __test__(scene, parent):
    dlg = AddAnythingDialog(parent)
    dlg.setScene(scene)
    dlg.show(animate=False)
    parent.show()
    parent.resize(400, 600)
    return dlg
