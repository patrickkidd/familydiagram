import logging

from .pyqt import pyqtSignal, QMessageBox, QObject, QEvent, Qt, pyqtSignal
from . import objects, util, commands
from .objects import Person, Emotion, Event
from .qmldrawer import QmlDrawer
from .util import EventKinds


_log = logging.getLogger(__name__)


class AddAnythingDialog(QmlDrawer):

    QmlDrawer.registerQmlMethods(
        [
            {"name": "clear"},
            {"name": "test_peopleListItem", "return": True},
            {"name": "setPeopleHelpText"},
        ]
    )

    submitted = pyqtSignal()

    S_REQUIRED_FIELD_ERROR = "'{name}' is a required field."
    S_EVENT_MONADIC_MULTIPLE_INDIVIDUALS = "This event type pertains to individuals so a separate event will be added to each one."
    S_EVENT_DYADIC = "This event type can only be added to two people."
    S_HELP_TEXT_ADD_PEOPLE = "This will add {numPeople} people to the diagram"

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

    def onDone(self):
        _log.info(f"AddAnythingDialog.onDone")

        # Required fields
        if self.rootProp("peopleModel").rowCount() == 0:
            objectName = "peopleLabel"
        elif not self.rootProp("kind"):
            objectName = "kindLabel"
        elif not self.rootProp("description"):
            objectName = "descriptionLabel"
        elif not self.rootProp("location"):
            objectName = "locationLabel"
        elif not self.rootProp("startDateTime"):
            objectName = "startDateTimeLabel"
        elif self.rootProp("isDateRange") and not self.rootProp("endDateTime"):
            objectName = "endDateTimeLabel"
        else:
            objectName = None
        if objectName:
            name = self.itemProp(objectName, "text")
            msg = self.S_REQUIRED_FIELD_ERROR.format(name=name)
            _log.info(f"AddAnythingForm validation: {msg}")
            QMessageBox.information(
                self,
                "Required field",
                msg,
                QMessageBox.Ok,
            )

        # Validate correct values

        # Validation checks from AddAnythingDialog.qml
        # if not self.event.kind(): # or not self.event.kind().isValid():
        undo_id = commands.nextId()
        items_to_add = []

        people = []
        peopleInfos = []
        peopleModel = self.rootProp("peopleModel")
        for i in range(peopleModel.rowCount()):
            modelData = peopleModel.get(i).toVariant()
            peopleInfos.append(
                {
                    "fullNameOrAlias": modelData.property("fullNameOrAlias"),
                    "id": modelData.property("id"),
                    "isNew": modelData.property("isNew"),
                }
            )
        kind = self.rootProp("kind")
        description = self.rootProp("description")
        location = self.rootProp("location")
        startDateTime = self.rootProp("startDateTime")
        endDateTime = self.rootProp("endDateTime")
        anxiety = self.rootProp("anxiety")
        functioning = self.rootProp("functioning")
        symptom = self.rootProp("symptom")

        for item in peopleInfos:
            if item["isNew"]:
                parts = item["fullNameOrAlias"].split(" ")
                firstName, lastName = parts[0], parts[1:]
                person = Person(name=firstName, lastName=lastName)
                items_to_add.append(person)
                people.append(person)
            else:
                id = item["id"]
                people.append(self.scene.findById(id))

        if kind == EventKinds.Birth.value:
            for person in people:
                person.setBirthDateTime(startDateTime, undo=undo_id)
                if location:
                    person.birthEvent.setLocation(location)

        self.scene.addItems(*items_to_add)
        self.submitted.emit()  # for testing

    def validateFields(self):
        peopleInfos = self.rootProp("peopleModel")
        kind = self.rootProp("kind")
        description = self.rootProp("description")
        location = self.rootProp("location")
        startDateTime = self.rootProp("startDateTime")
        endDateTime = self.rootProp("endDateTime")
        anxiety = self.rootProp("anxiety")
        functioning = self.rootProp("functioning")
        symptom = self.rootProp("symptom")

        # Number of people for event type
        if EventKinds.isMonadic(kind) and len(peopleInfos) != 1:
            self.findItem("peopleHelpText").setProperty(
                "text",
                self.S_EVENT_MONADIC_MULTIPLE_INDIVIDUALS.format(
                    numPeople=len(peopleInfos)
                ),
            )

        if EventKinds.isDyadic(kind) and len(peopleInfos) != 2:
            QMessageBox.warning(self, "Dyadic event", self.S_EVENT_DYADIC)

        return False

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
