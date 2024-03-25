import logging

import pytest
import mock

from pkdiagram import util, objects, EventKind, SceneModel, Scene, Person
from pkdiagram.pyqt import Qt, QQuickItem, QApplication
from pkdiagram.addanythingdialog import AddAnythingDialog
from test_peoplepicker import add_and_keyClicks, add_new_person, add_existing_person

_log = logging.getLogger(__name__)


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


def _add_new_person(
    dlg: AddAnythingDialog,
    peoplePickerObjectName,
    textInput: str,
    returnToFinish: bool = True,
):
    add_new_person(
        dlg,
        textInput,
        peoplePickerObjectName=peoplePickerObjectName,
        returnToFinish=returnToFinish,
    )


def _add_existing_person(
    dlg: AddAnythingDialog,
    peoplePickerObjectName,
    person: Person,
):
    add_existing_person(dlg, person, peoplePickerObjectName=peoplePickerObjectName)


def _run_dateTimePickers(dlg, dateTime, buttonsItem, datePickerItem, timePickerItem):
    S_DATE = util.dateString(dateTime)
    S_TIME = util.timeString(dateTime)

    _log.info(
        f"Setting {buttonsItem}, {datePickerItem}, {timePickerItem} to {dateTime}"
    )

    dlg.keyClicks(
        f"{buttonsItem}.dateTextInput",
        S_DATE,
        resetFocus=False,
    )
    dlg.keyClicks(
        f"{buttonsItem}.timeTextInput",
        S_TIME,
        resetFocus=False,
    )
    assert dlg.itemProp(buttonsItem, "dateTime") == dateTime
    assert dlg.itemProp(datePickerItem, "dateTime") == dateTime
    assert dlg.itemProp(timePickerItem, "dateTime") == dateTime


ONE_NAME = "John Doe"
SET_START_DATETIME = util.Date(2001, 1, 1, 6, 7)
SET_END_DATETIME = util.Date(2002, 1, 1, 6, 7)


def _set_fields(
    dlg,
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
            startDateTime = SET_START_DATETIME
        if endDateTime is None:
            endDateTime = SET_END_DATETIME

    if kind not in (None, False):
        _log.info(f"Setting kind to {kind}")
        dlg.clickComboBoxItem("kindBox", EventKind.menuLabelFor(kind))

    if peopleA not in (None, False):
        if not isinstance(peopleA, list):
            peopleA = [peopleA]
        for person in peopleA:
            _log.info(f"Adding person to peopleA: {person}")
            prePeople = dlg.itemProp("peoplePickerA", "model").rowCount()
            if isinstance(person, Person):
                _add_existing_person(dlg, "peoplePickerA", person)
            else:
                _add_new_person(dlg, "peoplePickerA", person, returnToFinish=False)
            assert dlg.itemProp("peoplePickerA", "model").rowCount() == prePeople + 1

    if peopleB not in (None, False) and (
        EventKind.isDyadic(kind) or EventKind.isPairBond(kind)
    ):
        if not isinstance(peopleB, list):
            peopleB = [peopleB]
        for person in peopleB:
            _log.info(f"Adding person to peopleB: {person}")
            prePeople = dlg.itemProp("peoplePickerB", "model").rowCount()
            if isinstance(person, Person):
                _add_existing_person(dlg, "peoplePickerB", person)
            else:
                _add_new_person(dlg, "peoplePickerB", person, returnToFinish=False)
            assert dlg.itemProp("peoplePickerB", "model").rowCount() == prePeople + 1

    if description not in (None, False):
        _log.info(f'Setting description to "{description}"')
        dlg.keyClicks("descriptionEdit", description)

    if location not in (None, False):
        _log.info(f'Setting location to "{location}"')
        dlg.keyClicks("locationEdit", location)

    if startDateTime not in (None, False):
        _run_dateTimePickers(
            dlg, startDateTime, "startDateButtons", "startDatePicker", "startTimePicker"
        )

    if endDateTime not in (None, False):
        dlg.mouseClick("isDateRangeBox")
        assert dlg.rootProp("isDateRange") == True
        _run_dateTimePickers(
            dlg, endDateTime, "endDateButtons", "endDatePicker", "endTimePicker"
        )


def test_add_new_person(dlg, scene):
    submitted = util.Condition(dlg.submitted)
    _add_new_person(dlg, "peoplePickerA", "John Doe", returnToFinish=False)
    _set_fields(dlg, peopleA=False, fillRequired=True)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 1, "submitted signal emitted too many times"

    scene = dlg.sceneModel.scene
    assert len(scene.people()) == 1, f"Incorrect number of people added to scene"
    person = scene.query1(name="John", lastName="Doe")
    assert person, f"Could not find created person {ONE_NAME}"
    assert len(person.events()) == 1, f"Incorrect number of events added to scene"
    event = person.events()[0]
    assert event.uniqueId() == EventKind.Birth.value
    assert event.description() == EventKind.Birth.name


def test_add_existing_person(qtbot, scene, dlg):
    existingPerson = Person(name="John", lastName="Doe")
    scene.addItems(existingPerson)
    submitted = util.Condition(dlg.submitted)
    _set_fields(dlg, peopleA=existingPerson, fillRequired=True)

    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.callCount == 1, "submitted signal emitted too many times"
    assert len(scene.people()) == 1


def test_add_dyadic_event_two_existing_selected(qtbot, scene, dlg):
    patrick = scene.addItem(Person(name="Patrick", lastName="Stinson"))
    connie = scene.addItem(Person(name="Connie", lastName="Service"))
    _set_fields(
        dlg,
        peopleA=patrick,
        peopleB=connie,
        kind=EventKind.Conflict,
        startDateTime=util.Date(2023, 2, 1),
    )
    dlg.mouseClick("AddEverything_submitButton")
    assert len(scene.people()) == 2
    assert len(patrick.emotions()) == 1
    assert len(connie.emotions()) == 1
    assert patrick.emotions() == connie.emotions()
    assert patrick.emotions[0].kind == util.ITEM_CONFLICT


def test_add_dyadic_event_with_one_person_selected(qtbot, dlg):
    _set_fields(
        dlg, kind=EventKind.Conflict, peopleA=True, peopleB=False, fillRequired=True
    )
    qtbot.clickOkAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_EVENT_DYADIC,
    )


@pytest.mark.parametrize("eventKind", [x for x in EventKind if EventKind.isDyadic(x)])
def test_add_dyadic_event_with_three_people_selected(qtbot, dlg, eventKind):
    _set_fields(
        dlg,
        kind=eventKind,
        peopleA=["Someone New", "Someone Strange"],
        peopleB="Someone Else",
        fillRequired=True,
    )
    # dlg.clickComboBoxItem("kindBox", eventKind.name)
    qtbot.clickOkAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_EVENT_DYADIC,
    )
