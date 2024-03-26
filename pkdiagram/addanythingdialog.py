import logging

from .pyqt import pyqtSignal, QMessageBox, QObject, QEvent, Qt, pyqtSignal
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
            {"name": "initWithPairBond" },
            {"name": "initWithPeople" },
            {
                "name": "existingPeopleA",
                "return": True,
                "parser": lambda x: [x for x in x.toVariant()],
            },
            {
                "name": "existingPeopleB",
                "return": True,
                "parser": lambda x: [x for x in x.toVariant()],
            },
        ]
    )

    submitted = pyqtSignal()

    S_REQUIRED_FIELD_ERROR = "'{name}' is a required field."
    S_EVENT_MONADIC_MULTIPLE_INDIVIDUALS = "This event type pertains to individuals so a separate event will be added to each one."
    S_EVENT_DYADIC = "This event type can only be added to two people."
    S_HELP_TEXT_ADD_PEOPLE = "This will add {numPeople} people to the diagram"
    S_REPLACE_EXISTING = "This will replace {n_existing} of the {eventKind} events in the selected people."
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
        pairBond = Marriage.marriageForSelection(selection)
        if pairBond:
            self.initWithPairBond(pairBond)

        elif any(x.isPerson for x in selection):
            self.initWithPeople(selection)

    def onDone(self):
        _log.info(f"AddAnythingDialog.onDone")

        # Required fields
        if not self.rootProp("kind"):
            objectName = "kindLabel"
        elif self.itemProp("peoplePickerA", "model").rowCount() == 0:
            objectName = "peopleALabel"
        elif (
            EventKind.isDyadic(EventKind(self.rootProp("kind")))
            and self.itemProp("peoplePickerB", "model").rowCount() == 0
        ):
            objectName = "peopleBLabel"
        elif not self.rootProp("description"):
            objectName = "descriptionLabel"
        # elif not self.rootProp("location"):
        #     objectName = "locationLabel"
        elif not self.rootProp("startDateTime"):
            objectName = "startDateTimeLabel"
        elif self.rootProp("isDateRange") and not self.rootProp("endDateTime"):
            objectName = "endDateTimeLabel"
        else:
            objectName = None
        if objectName:
            name = self.itemProp(objectName, "text")
            msg = self.S_REQUIRED_FIELD_ERROR.format(name=name)
            _log.info(f"AddAnythingForm validation DIALOG: {msg}")
            QMessageBox.warning(
                self,
                "Required field",
                msg,
                QMessageBox.Ok,
            )
            return

        # Validation checks from AddAnythingDialog.qml

        people = []
        peopleInfosA = []
        peopleInfosB = []
        for peoplePicker in ("peoplePickerA", "peoplePickerB"):
            model = self.itemProp(peoplePicker, "model")
            for i in range(model.rowCount()):
                modelData = model.get(i).toVariant()
                info = {
                    "personName": modelData.property("personName"),
                    "person": modelData.property("person"),
                }
                if peoplePicker == "peoplePickerA":
                    peopleInfosA.append(info)
                elif peoplePicker == "peoplePickerB":
                    peopleInfosB.append(info)
        kind = self.rootProp("kind")
        description = self.rootProp("description")
        location = self.rootProp("location")
        startDateTime = self.rootProp("startDateTime")
        endDateTime = self.rootProp("endDateTime")
        anxiety = self.rootProp("anxiety")
        functioning = self.rootProp("functioning")
        symptom = self.rootProp("symptom")

        eventKind = EventKind(kind)
        peopleA = [p["person"] for p in peopleInfosA]
        peopleB = [p["person"] for p in peopleInfosB]

        undo_id = commands.nextId()
        people_to_add = []

        for item in peopleInfosA + peopleInfosB:
            if not item["person"]:
                parts = item["personName"].split(" ")
                firstName, lastName = parts[0], " ".join(parts[1:])
                person = Person(name=firstName, lastName=lastName)
                people_to_add.append(person)
                people.append(person)

        if eventKind in (EventKind.Birth, EventKind.Adopted, EventKind.Death):

            if eventKind == EventKind.Birth:
                n_existing = sum([1 for x in peopleA if x.birthDateTime()])
            elif eventKind == EventKind.Adopted:
                n_existing = sum([1 for x in peopleA if x.adoptedDateTime()])
            elif eventKind == EventKind.Death:
                n_existing = sum([1 for x in peopleA if x.deceasedDateTime()])
            else:
                n_existing = 0
            if (
                n_existing > 0
                and QMessageBox.question(
                    self,
                    f"Replace {eventKind.name} event(s)?",
                    self.S_REPLACE_EXISTING.format(
                        n_existing=n_existing, eventKind=eventKind
                    ),
                )
                == QMessageBox.NoButton
            ):
                return

        if eventKind in (
            EventKind.Conflict,
            EventKind.Distance,
            EventKind.Reciprocity,
            EventKind.Projection,
            EventKind.Fusion,
            EventKind.Toward,
            EventKind.Away,
            EventKind.Inside,
            EventKind.Outside,
            EventKind.DefinedSelf,
        ):
            numSymbols = len(peopleInfosA) * len(peopleInfosB)
            if numSymbols > 3:
                button = QMessageBox.question(
                    self,
                    "Create large number of symbols?",
                    self.S_ADD_MANY_SYMBOLS.format(numSymbols=numSymbols),
                )
                if button == QMessageBox.NoButton:
                    return

        commands.addPeople(self.scene, people_to_add, id=undo_id)

        # Kind-specific logic

        if eventKind in (EventKind.Birth, EventKind.Adopted):
            for person in peopleA:
                if eventKind == EventKind.Birth:
                    person.birthEvent.setDateTime(startDateTime, undo=undo_id)
                    if location:
                        person.birthEvent.setLocation(location, undo=undo_id)
                elif eventKind == EventKind.Adopted:
                    person.adoptedEvent.setDateTime(startDateTime, undo=undo_id)
                    if location:
                        person.adoptedEvent.setLocation(location, undo=undo_id)
                elif eventKind == EventKind.Death:
                    person.deceasedEvent.setDateTime(startDateTime, undo=undo_id)
                    if location:
                        person.deathEvent.setLocation(location, undo=undo_id)

        elif eventKind == EventKind.CustomIndividual:
            commands.addEvent(
                Event(
                    personA,
                    description=description,
                    location=location,
                    uniqueId=eventKind.value,
                ),
                id=undo_id,
            )

        elif eventKind in (
            EventKind.Bonded,
            EventKind.Married,
            EventKind.Separated,
            EventKind.Divorced,
            EventKind.Moved,
            EventKind.CustomPairBond,
        ):
            personA = peopleA[0]
            personB = peopleB[0]
            marriage = Marriage.marriageFor(personA, personB)
            if not marriage:
                # Generally there is only one marriage item per person. Multiple
                # marriages/weddings between the same person just get separate
                # `married`` events.
                marriage = commands.addMarriage(
                    self.scene, personA, personB, id=undo_id
                )

            commands.addEvent(
                marriage,
                Event(marriage, uniqueId=eventKind.value, location=location),
                id=undo_id,
            )
        elif eventKind in (
            EventKind.Conflict,
            EventKind.Distance,
            EventKind.Reciprocity,
            EventKind.Projection,
            EventKind.Fusion,
            EventKind.Toward,
            EventKind.Away,
            EventKind.Inside,
            EventKind.Outside,
            EventKind.DefinedSelf,
        ):
            itemMode = EventKind.itemModeFor(eventKind)
            for personA in peopleA:
                for personB in peopleB:
                    commands.addEmotion(
                        self.scene,
                        Emotion(kind=itemMode, personA=personA, personB=personB),
                        id=undo_id,
                    )
        else:
            raise ValueError(f"Don't know how to handle event kind {eventKind}")

        # FORM = [
        #     "kind",
        #     "description",
        #     "anxiety",
        #     "functioning",
        #     "symptom",
        #     "location",
        #     "description",
        #     "isDateRange",
        #     "startDateTime",
        #     "startDateUnsure",
        #     "endDateTime",
        #     "endDateUnsure",
        #     "nodal",
        # ]
        # values = {k: self.property(k) for k, v in FORM.items()}
        self.submitted.emit()  # for testing

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
        self.hide(callback=self.reset)


def __test__(scene, parent):
    dlg = AddAnythingDialog(parent)
    dlg.setScene(scene)
    dlg.show(animate=False)
    parent.show()
    parent.resize(400, 600)
    return dlg
