import logging

import pytest
import mock

from pkdiagram import util, objects, EventKind, SceneModel, Scene, Person
from pkdiagram.pyqt import Qt, QQuickItem, QApplication
from pkdiagram.addanythingdialog import AddAnythingDialog
from test_peoplepicker import add_and_keyClicks, add_new_person, add_existing_person
from tests.test_addanythingdialog import (
    _add_new_person,
    _add_existing_person,
    _run_dateTimePickers,
    _set_fields,
    scene,
    dlg,
    ONE_NAME,
    SET_START_DATETIME,
    SET_END_DATETIME,
)

_log = logging.getLogger(__name__)


# def _add_person(
#     dlg: AddAnythingDialog,
#     peoplePickerItem: str,
#     firstName=ONE_FIRST_NAME,
#     lastName=ONE_LAST_NAME,
#     returnToFinish=True
# ):
#     personItemAddDone = util.Condition(dlg.findItem(peoplePickerItem).itemAddDone)
#     dlg.mouseClick(f"{peoplePickerItem}.buttons.addButton")
#     assert personItemAddDone.wait() == True
#     personItem = personItemAddDone.callArgs[1][0]
#     textEdit = personItem.findChild(QQuickItem, "textEdit")
#     dlg.keyClicks(textEdit, f"{firstName} {lastName}", resetFocus=False, returnToFinish=returnToFinish)


def test_init(dlg):
    assert [
        i for i in dlg.findItem("kindBox").property("model")
    ] == EventKind.menuLabels()
    assert dlg.rootProp("kind") == None


def test_init_with_existing_people(dlg):
    existingPeopleA = [
        Person(name="Joseph", lastName="Donner"),
        Person(name="Josephina", lastName="Donner"),
    ]
    existingPeopleB = [
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
    ]
    dlg.scene.addItems(*(existingPeopleA + existingPeopleB))
    dlg.setExistingPeopleA(existingPeopleA)
    dlg.setExistingPeopleB(existingPeopleB)
    assert {x.id for x in dlg.existingPeopleA()} == {x.id for x in existingPeopleA}
    assert [x.id for x in dlg.existingPeopleB()] == [x.id for x in existingPeopleB]
    assert dlg.itemProp("peopleALabel", "text")


@pytest.mark.parametrize("kind", [x for x in EventKind if not EventKind.isDyadic(x)])
def test_monadic_event_people_pickers(dlg, kind):
    dlg.clickComboBoxItem("kindBox", EventKind.menuLabelFor(kind))
    assert dlg.itemProp("peoplePickerB", "visible") == False
    assert dlg.itemProp("peopleBLabel", "visible") == False


@pytest.mark.parametrize("kind", [x for x in EventKind if EventKind.isDyadic(x)])
def test_dyadic_event_people_pickers(dlg, kind):
    dlg.clickComboBoxItem("kindBox", EventKind.menuLabelFor(kind))
    assert dlg.itemProp("peoplePickerB", "visible") == True
    assert dlg.itemProp("peopleBLabel", "visible") == True


@pytest.mark.skip("Not finished")
def test_startDateTime_pickers(qtbot, dlg):
    dlg.clear()

    DATE_TIME = util.Date(2023, 2, 1)

    _run_dateTimePickers(
        dlg, DATE_TIME, "startDateButtons", "startDatePicker", "startTimePicker"
    )
    assert dlg.rootProp("startDateTime") == DATE_TIME


@pytest.mark.skip("Not finished")
def test_endDateTime_pickers(qtbot, dlg):
    dlg.clear()

    DATE_TIME = util.Date(2023, 2, 1)

    dlg.mouseClick("isDateRangeBox")
    assert dlg.itemProp("isDateRangeBox", "checked")

    _run_dateTimePickers(
        dlg, DATE_TIME, "endDateButtons", "endDatePicker", "endTimePicker"
    )
    assert dlg.rootProp("endDateTime") == DATE_TIME


def test_add_new_person_born(dlg):
    scene = dlg.sceneModel.scene
    submitted = util.Condition(dlg.submitted)
    _set_fields(dlg, kind=EventKind.Birth, personA="Someone New", fillRequired=True)
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


@pytest.mark.parametrize("kind", [x for x in EventKind if EventKind.isCustom(x)])
def test_description_disabled_for_uniqueId(dlg, kind):
    dlg.clickComboBoxItem("kindBox", EventKind.menuLabelFor(kind))
    assert dlg.itemProp("descriptionEdit", "enabled") == False


@pytest.mark.parametrize("kind", [x for x in EventKind])
def test_labels_for_event_kinds(dlg, kind):
    dlg.clickComboBoxItem("kindBox", EventKind.menuLabelFor(kind))
    assert dlg.itemProp("peopleALabel", "text") == EventKind.personALabel(kind)

    if EventKind.isDyadic(kind) or EventKind.isPairBond(kind):
        assert dlg.itemProp("peopleBLabel", "visible") == True
        assert dlg.itemProp("peopleBLabel", "text") == EventKind.personBLabel(kind)
    else:
        assert dlg.itemProp("peopleBLabel", "visible") == False


@pytest.mark.parametrize("kind", [x for x in EventKind if EventKind.isMonadic(x)])
def test_dynamic_fields_for_monadic(dlg, kind):
    dlg.clickComboBoxItem("kindBox", EventKind.menuLabelFor(kind))
    # _set_required_fields(dlg, kind=kind)
    assert dlg.itemProp("descriptionEdit", "enabled") == EventKind.isCustom(kind)
    assert dlg.itemProp("peopleALabel", "text") == EventKind.personALabel(kind)
    assert dlg.itemProp("peopleBLabel", "visible") == False
    assert dlg.itemProp("peoplePickerB", "visible") == False


@pytest.mark.parametrize("kind", [x for x in EventKind if EventKind.isPairBond(x)])
def test_dynamic_fields_for_pair_bond_kind(dlg, kind):
    _set_fields(dlg, kind=kind, fillRequired=True)
    assert dlg.itemProp("descriptionEdit", "enabled") == False
    assert dlg.itemProp("peopleALabel", "text") == EventKind.personALabel(kind)
    assert dlg.itemProp("peopleBLabel", "visible") == True
    assert dlg.itemProp("peoplePickerB", "visible") == True
    assert dlg.itemProp("peopleBLabel", "text") == EventKind.personBLabel(kind)


@pytest.mark.parametrize("kind", [x for x in EventKind if not EventKind.isDyadic(x)])
def test_dynamic_fields_for_non_dyadic_kind(dlg, kind):
    _set_fields(dlg, kind=kind, fillRequired=True)
    assert dlg.itemProp("descriptionEdit", "enabled") == EventKind.isCustom(kind)
    assert dlg.itemProp("peopleALabel", "text") == EventKind.personALabel(kind)
    assert dlg.itemProp("peopleBLabel", "visible") == EventKind.isDyadic(kind)
    assert dlg.itemProp("peoplePickerB", "visible") == EventKind.isDyadic(kind)
    assert dlg.itemProp("peopleBLabel", "text") == EventKind.personBLabel(kind)


# def test_add_new_people_pair_bond(dlg):
#     scene = dlg.sceneModel.scene


# def test_person_help_text_add_one_person(qtbot, dlg):
#     _set_required_fields(dlg, people=False, fillRequired=False)
#     _add_new_person(dlg)
#     dlg.clickComboBoxItem("kindBox", EventKind.Birth.name)
#     assert (
#         dlg.itemProp("eventHelpText", "text")
#         == AddAnythingDialog.S_EVENT_MULTIPLE_INDIVIDUALS
#     )


# def test_dyadic_with_gt_two_people(qtbot, dlg):
#     _set_required_fields(dlg, people=False, fillRequired=False)
#     _add_new_person(dlg, firstName="John", lastName="Doe")
#     _add_new_person(dlg, firstName="Jane", lastName="Doe")
#     _add_new_person(dlg, firstName="Joseph", lastName="Belgard")
#     dlg.clickComboBoxItem("kindBox", EventKind.Birth.name)
#     assert (
#         dlg.itemProp("eventHelpText", "text")
#         == AddAnythingDialog.S_EVENT_MULTIPLE_INDIVIDUALS
#     )


# - add_new_people_as_pair_bond
# - add_two_existing_as_pair_bond_married
# - add_one_existing_one_new_as_pair_bond
# - select_isDateRange_for_distinct_event_type
# - select_not_isDateRange_for_range_event_type
# - select_dyadic_event_with_one_person_selected
# - select_dyadic_event_with_three_people_selected
#
