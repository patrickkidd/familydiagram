import logging

import pytest
import mock

from pkdiagram import util, objects, EventKind, SceneModel, Scene, Person, Marriage
from pkdiagram.pyqt import (
    Qt,
    QQuickItem,
    QApplication,
    QMetaObject,
    Q_RETURN_ARG,
    QVariant,
)
from pkdiagram.addanythingdialog import AddAnythingDialog
from test_personpicker import set_new_person, set_existing_person
from test_peoplepicker import add_and_keyClicks, add_new_person, add_existing_person

_log = logging.getLogger(__name__)


ONE_NAME = "John Doe"
START_DATETIME = util.Date(2001, 1, 1, 6, 7)
END_DATETIME = util.Date(2002, 1, 1, 6, 7)


class TestAddAnythingDialog(AddAnythingDialog):

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
        self.clickComboBoxItem("kindBox", EventKind.menuLabelFor(kind))

    def set_description(self, description: str):
        self.keyClicks("descriptionEdit", description)

    def set_new_person(
        self,
        personPicker: str,
        textInput: str,
        returnToFinish: bool = False,
    ):
        _log.info(f"set_new_person('{personPicker}', '{textInput}')")

        personPickerItem = self.findItem(personPicker)
        self.focusItem(personPickerItem)
        util.qtbot.keyClicks(
            self, textInput, resetFocus=False, returnToFinish=returnToFinish
        )
        assert personPickerItem.property("isSubmitted") == returnToFinish
        assert personPickerItem.property("isNewPerson") == True
        assert personPickerItem.property("personName") == textInput

    def set_existing_person(
        self,
        personPicker: str,
        person: Person,
        autoCompleteInput: str = None,
        returnToFinish: bool = False,
    ):
        _log.info(f"_set_new_person('{personPicker}', {person}, autoCompleteInput='{autoCompleteInput}')")
        if autoCompleteInput:
            autoCompleteInput = person.fullNameOrAlias()
        personPickerItem = self.findItem(personPicker)
        textEditItem = personPickerItem.findChild("textEdit")
        assert textEditItem is not None
        self.keyClicks(
            f"{personPicker}.textEdit",
            autoCompleteInput,
            resetFocus=False,
            returnToFinish=returnToFinish,
        )
        assert self.itemProp(f"{personPicker}.popupListView", "visible") == True
        self.clickListViewItem_actual(
            f"personPicker.popupListView", person.fullNameOrAlias()
        )

    def add_new_person(
        self,
        peoplePicker: str,
        textInput: str,
        gender: str = None,
        returnToFinish: bool = True,
    ):
        add_new_person(
            self,
            textInput,
            peoplePicker=peoplePicker,
            gender=gender,
            returnToFinish=returnToFinish,
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

    def set_dateTime(self, dateTime, buttonsItem, datePickerItem, timePickerItem):

        S_DATE = util.dateString(dateTime)
        S_TIME = util.timeString(dateTime)

        _log.info(
            f"Setting {buttonsItem}, {datePickerItem}, {timePickerItem} to {dateTime}"
        )

        self.keyClicks(
            f"{buttonsItem}.dateTextInput",
            S_DATE,
            resetFocus=False,
        )
        self.keyClicks(
            f"{buttonsItem}.timeTextInput",
            S_TIME,
            resetFocus=False,
        )
        assert self.itemProp(buttonsItem, "dateTime") == dateTime
        assert self.itemProp(datePickerItem, "dateTime") == dateTime
        assert self.itemProp(timePickerItem, "dateTime") == dateTime

    def set_startDateTime(self, dateTime):
        self.set_dateTime(
            self, dateTime, "startDateButtons", "startDatePicker", "startTimePicker"
        )

    def set_endDateTime(self, dateTime):
        self.set_dateTime(
            self, dateTime, "endDateButtons", "endDatePicker", "endTimePicker"
        )

    def set_fields(
        self,
        kind=None,
        peopleA=None,
        peopleB=None,
        description=None,
        location=None,
        startDateTime=None,
        endDateTime=None,
        fillRequired=False,
    ):

        if fillRequired:
            if kind is None:
                kind = EventKind.CustomIndividual
            if description is None and EventKind.isCustom(kind):
                description = "Something Happened"
            if peopleA is None:
                peopleA = ["Someone New"]
            if peopleB is None:
                peopleB = ["Someone Else"]
            if startDateTime is None:
                startDateTime = START_DATETIME
            if endDateTime is None:
                endDateTime = END_DATETIME

        if kind not in (None, False):
            _log.info(f"Setting kind to {kind}")
            self.clickComboBoxItem("kindBox", EventKind.menuLabelFor(kind))

        if peopleA not in (None, False):
            if not isinstance(peopleA, list):
                peopleA = [peopleA]
            for person in peopleA:
                _log.info(f"Adding person to peopleA: {person}")
                prePeople = self.itemProp("peoplePickerA", "model").rowCount()
                if isinstance(person, Person):
                    _add_existing_person(self, "peoplePickerA", person)
                else:
                    _add_new_person(self, "peoplePickerA", person, returnToFinish=False)
                assert (
                    self.itemProp("peoplePickerA", "model").rowCount() == prePeople + 1
                )

        if peopleB not in (None, False) and (
            EventKind.isDyadic(kind) or EventKind.isPairBond(kind)
        ):
            if not isinstance(peopleB, list):
                peopleB = [peopleB]
            for person in peopleB:
                _log.info(f"Adding person to peopleB: {person}")
                prePeople = self.itemProp("peoplePickerB", "model").rowCount()
                if isinstance(person, Person):
                    self.add_existing_person(self, "peoplePickerB", person)
                else:
                    self.add_new_person(
                        self, "peoplePickerB", person, returnToFinish=False
                    )
                assert (
                    self.itemProp("peoplePickerB", "model").rowCount() == prePeople + 1
                )

        if description not in (None, False):
            _log.info(f'Setting description to "{description}"')
            self.keyClicks("descriptionEdit", description)

        if location not in (None, False):
            _log.info(f'Setting location to "{location}"')
            self.keyClicks("locationEdit", location)

        if startDateTime not in (None, False):
            self.set_dateTime(
                self,
                startDateTime,
                "startDateButtons",
                "startDatePicker",
                "startTimePicker",
            )

        if endDateTime not in (None, False):
            self.mouseClick("isDateRangeBox")
            assert self.rootProp("isDateRange") == True
            self.set_dateTime(
                self, endDateTime, "endDateButtons", "endDatePicker", "endTimePicker"
            )


@pytest.fixture
def scene():
    scene = Scene()
    yield scene


@pytest.fixture
def dlg(qtbot, scene):
    sceneModel = SceneModel()
    sceneModel.scene = scene
    scene._sceneModel = sceneModel

    dlg = AddAnythingDialog(sceneModel=sceneModel)
    dlg.resize(600, 800)
    dlg.setRootProp("sceneModel", sceneModel)
    dlg.setScene(scene)
    dlg.show()
    dlg.clear()
    qtbot.addWidget(dlg)
    qtbot.waitActive(dlg)
    assert dlg.isShown()
    assert dlg.itemProp("AddEverything_submitButton", "text") == "Add"

    yield dlg

    dlg.setScene(None)
    dlg.hide()


def test_add_new_person_via_Birth(scene, dlg):
    submitted = util.Condition(dlg.submitted)
    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person("personPicker", "John Doe")
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 1, "submitted signal emitted too many times"

    scene = dlg.sceneModel.scene
    assert len(scene.people()) == 1, f"Incorrect number of people added to scene"
    person = scene.query1(name="Someone", lastName="New")
    assert person, f"Could not find created person {ONE_NAME}"
    assert len(person.events()) == 1, f"Incorrect number of events added to scene"
    event = person.events()[0]
    assert event.uniqueId() == EventKind.Birth.value
    assert event.description == EventKind.Birth.name


def test_add_new_person_via_CustomIndividual(dlg, scene):
    DESCRIPTION = "Something Happened"
    GENDER = util.PERSON_KIND_NAMES[util.PERSON_KIND_FEMALE]

    submitted = util.Condition(dlg.submitted)
    dlg.set_kind(EventKind.Birth)
    dlg.add_new_person(
        dlg,
        "personPicker",
        "John Doe",
        gender=GENDER,
        returnToFinish=False,
    )
    dlg.set_description(DESCRIPTION)
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 1, "submitted signal emitted too many times"

    scene = dlg.sceneModel.scene
    assert len(scene.people()) == 1, f"Incorrect number of people added to scene"
    person = scene.query1(name="John", lastName="Doe")
    assert person, f"Could not find created person {ONE_NAME}"
    assert person.gender() == GENDER
    assert len(person.events()) == 1, f"Incorrect number of events added to scene"
    event = person.events()[0]
    assert event.uniqueId() == None
    assert event.description() == DESCRIPTION


@pytest.mark.parametrize("kind", [x for x in EventKind if EventKind.isMonadic(x)])
def test_add_new_person_monadic(scene, dlg, kind):
    DESCRIPTION = "Something Happened"
    submitted = util.Condition(dlg.submitted)
    dlg.set_kind(kind)
    dlg.set_new_person("personPicker", "John Doe")
    dlg.set_description(DESCRIPTION)
    dlg.set_startDateTime(START_DATETIME)

    dlg.mouseClick("AddEverything_submitButton")
    newPerson = scene.query1(name="John", lastName="Doe")
    assert submitted.callCount == 1, "submitted signal emitted too many times"
    assert len(scene.people()) == 1
    assert len(newPerson.events()) == 1
    assert newPerson.events()[0].uniqueId() == kind.value
    assert newPerson.events()[0].description() == DESCRIPTION


@pytest.mark.parametrize("kind", [x for x in EventKind if EventKind.isMonadic(x)])
def test_use_existing_person_monadic(scene, dlg, kind):
    existingPerson = Person(name="John", lastName="Doe")
    scene.addItems(existingPerson)
    submitted = util.Condition(dlg.submitted)
    dlg.set_kind(kind)
    dlg.set_existing_person("personPicker", existingPerson)
    dlg.set_description("Something Happened")
    dlg.set_startDateTime(START_DATETIME)

    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 1, "submitted signal emitted too many times"
    assert len(scene.people()) == 1
    assert len(existingPerson.events()) == 1
    assert existingPerson.events()[0].uniqueId() == kind.value


@pytest.mark.parametrize("kind", [x for x in EventKind if EventKind.isDyadic(x)])
def test_add_new_dyadic(scene, dlg, kind):
    dlg.set_kind(kind)
    dlg.add_new_person("moversPicker", "John Doe")
    dlg.add_new_person("receiversPicker", "Jane Doe")
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    personA = scene.query1(name="John", lastName="Doe")
    personB = scene.query1(name="Jane", lastName="Doe")
    assert len(scene.people()) == 2
    assert len(personA.emotions()) == 1
    assert len(personB.emotions()) == 1
    assert personA.emotions() == personB.emotions()
    assert personA.emotions[0].uniqueId() == kind.value


@pytest.mark.parametrize("kind", [x for x in EventKind if EventKind.isDyadic(x)])
def test_add_existing_dyadic(scene, dlg, kind):
    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Jane", lastName="Doe"))
    dlg.set_kind(kind)
    dlg.add_existing_person("moversPicker", personA)
    dlg.add_existing_person("receiversPicker", personB)
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    assert len(scene.people()) == 2
    assert len(personA.emotions()) == 1
    assert len(personB.emotions()) == 1
    assert personA.emotions() == personB.emotions()
    assert personA.emotions[0].uniqueId() == kind.value


@pytest.mark.parametrize("kind", [x for x in EventKind if EventKind.isPairBond(x)])
def test_add_existing_pairbond(scene, dlg, kind):
    DESCRIPTION = "Something Happened"

    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Jane", lastName="Doe"))
    marriage = scene.addItem(Marriage(personA, personB))
    dlg.set_kind(kind)
    dlg.add_existing_person("moversPicker", personA)
    dlg.add_existing_person("receiversPicker", personB)
    if kind == EventKind.CustomPairBond:
        dlg.set_description(DESCRIPTION)
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    assert personA.marriages == personB.marriages == [marriage]
    assert len(scene.people()) == 2
    assert len(marriage.events()) == 1
    assert marriage.events()[0].uniqueId() == kind.value
    if kind == EventKind.CustomPairBond:
        assert marriage.events()[0].description() == DESCRIPTION
