import logging

import pytest
import mock

from pkdiagram import util, objects, EventKind, SceneModel, Scene, Person
from pkdiagram.pyqt import Qt, QQuickItem, QApplication
from pkdiagram.addanythingdialog import AddAnythingDialog

# from test_peoplepicker import add_and_keyClicks, add_new_person, add_existing_person
from tests.test_addanythingdialog import (
    scene,
    dlg,
    START_DATETIME,
    END_DATETIME,
)

log = logging.getLogger(__name__)


def test_required_field_Monadic(dlg):

    submitted = util.Condition(dlg.submitted)

    dlg.set_kind(EventKind.Birth)

    dlg.expectedFieldLabel("personLabel")
    dlg.set_new_person("personPicker", "John Doe")

    dlg.expectedFieldLabel("startDateTimeLabel")
    dlg.set_startDateTime(START_DATETIME)

    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.wait() == True


def test_required_field_CustomIndividual(dlg):
    submitted = util.Condition(dlg.submitted)

    dlg.set_kind(EventKind.CustomIndividual)

    dlg.expectedFieldLabel("peopleLabel")
    dlg.add_new_person("peoplePicker", "John Doe")

    dlg.expectedFieldLabel("descriptionLabel")
    dlg.set_description("Some description")

    dlg.expectedFieldLabel("startDateTimeLabel")
    dlg.set_startDateTime(START_DATETIME)

    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.wait() == True


def test_required_field_Dyadic(dlg):

    submitted = util.Condition(dlg.submitted)

    dlg.set_kind(EventKind.Conflict)

    dlg.expectedFieldLabel("moversLabel")
    dlg.add_new_person("moversPicker", "John Doe")

    dlg.expectedFieldLabel("receiversLabel")
    dlg.add_new_person("receiversPicker", "Jane Doe")

    dlg.expectedFieldLabel("startDateTimeLabel")
    dlg.set_startDateTime(START_DATETIME)

    dlg.set_isDateRange(True)

    dlg.expectedFieldLabel("endDateTimeLabel")
    dlg.set_endDateTime(END_DATETIME)

    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.wait() == True


def test_required_field_PairBond(dlg):
    submitted = util.Condition(dlg.submitted)

    dlg.set_kind(EventKind.Married)

    dlg.expectedFieldLabel("personALabel")
    dlg.set_new_person("personAPicker", "John Doe")

    dlg.expectedFieldLabel("personBLabel")
    dlg.set_new_person("personBPicker", "Jane Doe")

    dlg.expectedFieldLabel("startDateTimeLabel")
    dlg.set_startDateTime(START_DATETIME)

    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.wait() == True


@pytest.mark.parametrize("kind", [EventKind.Birth, EventKind.Adopted, EventKind.Death])
def test_confirm_replace_singular_events(qtbot, scene, dlg, kind):
    PRIOR_DATETIME = util.Date(2011, 1, 1)
    submitted = util.Condition(dlg.submitted)
    person = scene.addItem(Person(name="John", lastName="Doe"))
    if kind == EventKind.Birth:
        person.setBirthDateTime(PRIOR_DATETIME)
    elif kind == EventKind.Adopted:
        person.setAdoptedDateTime(PRIOR_DATETIME)
    elif kind == EventKind.Death:
        person.setDeceasedDateTime(PRIOR_DATETIME)
    dlg.set_kind(kind)
    dlg.set_existing_person("personPicker", person)
    dlg.set_startDateTime(START_DATETIME)
    qtbot.clickYesAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_REPLACE_EXISTING.format(n_existing=1, kind=kind.name),
    )
    assert submitted.callCount == 1
    if kind == EventKind.Birth:
        assert person.birthDateTime() == START_DATETIME
    elif kind == EventKind.Adopted:
        assert person.adoptedDateTime() == START_DATETIME
    elif kind == EventKind.Death:
        assert person.deceasedDateTime() == START_DATETIME


def test_confirm_adding_many_dyadic_symbols(qtbot, scene, dlg):
    peopleA = [
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
    ]
    peopleB = [
        Person(name="Jack", lastName="Doe"),
        Person(name="Jill", lastName="Doe"),
    ]
    scene.addItems(*(peopleA + peopleB))
    dlg.set_kind(EventKind.Reciprocity)
    dlg.add_existing_person("moversPicker", peopleA[0])
    dlg.add_existing_person("moversPicker", peopleA[1])
    dlg.add_existing_person("receiversPicker", peopleB[0])
    dlg.add_existing_person("receiversPicker", peopleB[1])
    dlg.set_startDateTime(START_DATETIME)
    qtbot.clickYesAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_ADD_MANY_SYMBOLS.format(numSymbols=4),
    )
    assert len(scene.emotions()) == 4
    assert len(scene.people()) == 4


def test_confirm_adding_many_individual_events(qtbot, scene, dlg):
    DESCRIPTION = "Something happened"
    people = [
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
        Person(name="Jack", lastName="Doe"),
        Person(name="Jill", lastName="Doe"),
    ]
    scene.addItems(*people)
    dlg.set_kind(EventKind.CustomIndividual)
    dlg.add_existing_person("peoplePicker", people[0])
    dlg.add_existing_person("peoplePicker", people[1])
    dlg.add_existing_person("peoplePicker", people[2])
    dlg.add_existing_person("peoplePicker", people[3])
    dlg.set_startDateTime(START_DATETIME)
    dlg.set_description(DESCRIPTION)
    qtbot.clickYesAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=AddAnythingDialog.S_ADD_MANY_SYMBOLS.format(numSymbols=4),
    )
    for i, person in enumerate(people):
        assert (
            len(people[0].events()) == 1
        ), f"Person {i} has the wrong number of events"
        assert (
            people[0].events()[0].description() == DESCRIPTION
        ), f"Person {i} has the wrong description"


def test_add_dyadic_event_with_one_person_selected(qtbot, scene, dlg):
    person = scene.addItem(Person(name="John", lastName="Doe"))
    dlg.set_kind(EventKind.Conflict)
    dlg.add_existing_person("moversPicker", person)
    name = dlg.itemProp("receiversLabel", "text")
    expectedText = dlg.S_REQUIRED_FIELD_ERROR.format(name=name)
    qtbot.clickOkAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=expectedText,
    )


def test_add_dyadic_event_with_three_people_selected(qtbot, dlg):
    dlg.set_kind(EventKind.Away)
    dlg.add_new_person("moversPicker", "John Doe")
    dlg.add_new_person("moversPicker", "Jane Doe")
    dlg.add_new_person("receiversPicker", "Jack Doe")
    dlg.add_new_person("receiversPicker", "Jill Doe")
    dlg.set_startDateTime(START_DATETIME)
    qtbot.clickYesAfter(
        lambda: dlg.mouseClick("AddEverything_submitButton"),
        text=dlg.S_ADD_MANY_SYMBOLS.format(numSymbols=4),
    )


# Unsubmitted - Birth


def test_person_submitted_Birth_personPicker(dlg):
    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person(
        "personPicker", "John Doe", returnToFinish=False, resetFocus=True
    )
    dlg.pickerNotSubmitted("personLabel")


def test_person_submitted_Birth_personAPicker(dlg):
    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person("personPicker", "John Doe")
    dlg.set_new_person("personAPicker", "Johnny Doe", returnToFinish=False)
    dlg.pickerNotSubmitted("personALabel")


def test_person_submitted_Birth_personBPicker(dlg):
    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person("personPicker", "John Doe")
    dlg.set_new_person("personAPicker", "Johnny Doe")
    dlg.set_new_person("personBPicker", "Janet Doe", returnToFinish=False)
    dlg.pickerNotSubmitted("personBLabel")


# Unsubmitted - CustomIndividual


def test_person_submitted_CustomIndividual_personPicker(dlg):
    dlg.set_kind(EventKind.CustomIndividual)
    dlg.add_new_person("peoplePicker", "John Doe", returnToFinish=False)
    dlg.pickerNotSubmitted("peopleLabel")


# Unsubmitted - Bonded


def test_person_submitted_Bonded_personAPicker(dlg):
    dlg.set_kind(EventKind.Bonded)
    dlg.set_new_person("personAPicker", "John Doe", returnToFinish=False)
    dlg.pickerNotSubmitted("personALabel")


def test_person_submitted_Bonded_personBPicker(dlg):
    dlg.set_kind(EventKind.Bonded)
    dlg.set_new_person("personAPicker", "John Doe")
    dlg.set_new_person("personBPicker", "Jane Doe", returnToFinish=False)
    dlg.pickerNotSubmitted("personBLabel")


# Unsubmitted - Fusion


def test_person_submitted_Fusion_moversPicker(dlg):
    dlg.set_kind(EventKind.Fusion)
    dlg.add_new_person("moversPicker", "John Doe", returnToFinish=False)
    dlg.pickerNotSubmitted("moversLabel")


def test_person_submitted_Fusion_receiversPicker(dlg):
    dlg.set_kind(EventKind.Fusion)
    dlg.add_new_person("moversPicker", "John Doe")
    dlg.add_new_person("receiversPicker", "Jane Doe", returnToFinish=False)
    dlg.pickerNotSubmitted("receiversLabel")
