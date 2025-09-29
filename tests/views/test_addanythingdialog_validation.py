import logging

import pytest

from pkdiagram import util
from pkdiagram.scene import Person, LifeChange
from pkdiagram.views import AddAnythingDialog

# from test_peoplepicker import add_and_keyClicks, add_new_person, add_existing_person
from .test_addanythingdialog import (
    view,
    START_DATETIME,
    END_DATETIME,
)

log = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.component("AddAnythingDialog"),
    pytest.mark.depends_on("Scene"),
]


def test_required_field_kind(view):
    view.expectedFieldLabel(view.item.property("kindLabel"))


def test_required_field_Monadic(view):

    submitted = util.Condition(view.view.submitted)

    view.set_kind(LifeChange.Birth)

    view.expectedFieldLabel(view.item.property("personLabel"))
    view.personPicker.set_new_person("John Doe")

    view.expectedFieldLabel(view.item.property("startDateTimeLabel"))
    view.set_startDateTime(START_DATETIME)

    view.clickAddButton()
    assert submitted.wait() == True


def test_required_field_CustomIndividual(view):
    submitted = util.Condition(view.view.submitted)

    view.set_kind(LifeChange.CustomIndividual)

    view.expectedFieldLabel(view.item.property("peopleLabel"))
    view.peoplePicker.add_new_person("John Doe")

    view.expectedFieldLabel(view.item.property("descriptionLabel"))
    view.set_description("Some description")

    view.expectedFieldLabel(view.item.property("startDateTimeLabel"))
    view.set_startDateTime(START_DATETIME)

    view.clickAddButton()
    assert submitted.wait() == True


@pytest.mark.parametrize("endDateTime", [None, END_DATETIME])
def test_required_field_Dyadic(view, endDateTime):

    submitted = util.Condition(view.view.submitted)

    view.set_kind(LifeChange.Conflict)

    view.expectedFieldLabel(view.item.property("moversLabel"))
    view.moversPicker.add_new_person("John Doe")

    view.expectedFieldLabel(view.item.property("receiversLabel"))
    view.receiversPicker.add_new_person("Jane Doe")

    view.expectedFieldLabel(view.item.property("startDateTimeLabel"))
    view.set_startDateTime(START_DATETIME)

    view.set_isDateRange(True)

    if endDateTime:
        view.set_endDateTime(endDateTime)

    view.clickAddButton()
    assert submitted.wait() == True


def test_required_field_PairBond(view):
    submitted = util.Condition(view.view.submitted)

    view.set_kind(LifeChange.Married)

    view.expectedFieldLabel(view.item.property("personALabel"))
    view.personAPicker.set_new_person("John Doe")

    view.expectedFieldLabel(view.item.property("personBLabel"))
    view.personBPicker.set_new_person("Jane Doe")

    view.expectedFieldLabel(view.item.property("startDateTimeLabel"))
    view.set_startDateTime(START_DATETIME)

    view.clickAddButton()
    assert submitted.wait() == True


@pytest.mark.parametrize(
    "kind", [LifeChange.Birth, LifeChange.Adopted, LifeChange.Death]
)
def test_confirm_replace_singular_events(qtbot, scene, view, kind):
    PRIOR_DATETIME = util.Date(2011, 1, 1)
    submitted = util.Condition(view.view.submitted)
    person = scene.addItem(Person(name="John", lastName="Doe"))
    if kind == LifeChange.Birth:
        person.setBirthDateTime(PRIOR_DATETIME)
    elif kind == LifeChange.Adopted:
        person.setAdoptedDateTime(PRIOR_DATETIME)
    elif kind == LifeChange.Death:
        person.setDeceasedDateTime(PRIOR_DATETIME)
    view.set_kind(kind)
    view.personPicker.set_existing_person(person)
    view.set_startDateTime(START_DATETIME)
    qtbot.clickYesAfter(
        lambda: view.clickAddButton(),
        text=AddAnythingDialog.S_REPLACE_EXISTING.format(n_existing=1, kind=kind.name),
    )
    assert submitted.callCount == 1
    if kind == LifeChange.Birth:
        assert person.birthDateTime() == START_DATETIME
    elif kind == LifeChange.Adopted:
        assert person.adoptedDateTime() == START_DATETIME
    elif kind == LifeChange.Death:
        assert person.deceasedDateTime() == START_DATETIME


def test_confirm_adding_many_dyadic_symbols(qtbot, scene, view):
    peopleA = [
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
    ]
    peopleB = [
        Person(name="Jack", lastName="Doe"),
        Person(name="Jill", lastName="Doe"),
    ]
    scene.addItems(*(peopleA + peopleB))
    view.set_kind(LifeChange.Reciprocity)
    view.moversPicker.add_existing_person(peopleA[0])
    view.moversPicker.add_existing_person(peopleA[1])
    view.receiversPicker.add_existing_person(peopleB[0])
    view.receiversPicker.add_existing_person(peopleB[1])
    view.set_startDateTime(START_DATETIME)
    qtbot.clickYesAfter(
        lambda: view.clickAddButton(),
        text=AddAnythingDialog.S_ADD_MANY_SYMBOLS.format(numSymbols=4),
    )
    assert len(scene.emotions()) == 4
    assert len(scene.people()) == 4


def test_confirm_adding_many_individual_events(qtbot, scene, view):
    DESCRIPTION = "Something happened"
    people = [
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
        Person(name="Jack", lastName="Doe"),
        Person(name="Jill", lastName="Doe"),
    ]
    scene.addItems(*people)
    view.set_kind(LifeChange.CustomIndividual)
    view.peoplePicker.add_existing_person(people[0])
    view.peoplePicker.add_existing_person(people[1])
    view.peoplePicker.add_existing_person(people[2])
    view.peoplePicker.add_existing_person(people[3])
    view.set_startDateTime(START_DATETIME)
    view.set_description(DESCRIPTION)
    qtbot.clickYesAfter(
        lambda: view.clickAddButton(),
        text=AddAnythingDialog.S_ADD_MANY_SYMBOLS.format(numSymbols=4),
    )
    for i, person in enumerate(people):
        assert (
            len(people[0].events()) == 1
        ), f"Person {i} has the wrong number of events"
        assert (
            people[0].events()[0].description() == DESCRIPTION
        ), f"Person {i} has the wrong description"


def test_add_dyadic_event_with_one_person_selected(qtbot, scene, view):
    person = scene.addItem(Person(name="John", lastName="Doe"))
    view.set_kind(LifeChange.Conflict)
    view.moversPicker.add_existing_person(person)
    name = view.item.property("receiversLabel").property("text")
    expectedText = AddAnythingDialog.S_REQUIRED_FIELD_ERROR.format(name=name)
    qtbot.clickOkAfter(
        lambda: view.clickAddButton(),
        text=expectedText,
    )


def test_add_dyadic_event_with_three_people_selected(qtbot, view):
    view.set_kind(LifeChange.Away)
    view.moversPicker.add_new_person("John Doe")
    view.moversPicker.add_new_person("Jane Doe")
    view.receiversPicker.add_new_person("Jack Doe")
    view.receiversPicker.add_new_person("Jill Doe")
    view.set_startDateTime(START_DATETIME)
    qtbot.clickYesAfter(
        lambda: view.clickAddButton(),
        text=AddAnythingDialog.S_ADD_MANY_SYMBOLS.format(numSymbols=4),
    )


# Unsubmitted - Birth


def test_person_submitted_Birth_personPicker(view):
    view.set_kind(LifeChange.Birth)
    view.personPicker.set_new_person("John Doe", returnToFinish=False, resetFocus=True)
    view.pickerNotSubmitted(view.item.property("personLabel"))


def test_person_submitted_Birth_personAPicker(view):
    view.set_kind(LifeChange.Birth)
    view.personPicker.set_new_person("John Doe")
    view.personAPicker.set_new_person("Johnny Doe", returnToFinish=False)
    view.pickerNotSubmitted(view.item.property("personALabel"))


def test_person_submitted_Birth_personBPicker(view):
    view.set_kind(LifeChange.Birth)
    view.personPicker.set_new_person("John Doe")
    view.personAPicker.set_new_person("Johnny Doe")
    view.personBPicker.set_new_person("Janet Doe", returnToFinish=False)
    view.pickerNotSubmitted(view.item.property("personBLabel"))


# Unsubmitted - CustomIndividual


def test_person_submitted_CustomIndividual_personPicker(view):
    view.set_kind(LifeChange.CustomIndividual)
    view.peoplePicker.add_new_person("John Doe", returnToFinish=False)
    view.pickerNotSubmitted(view.item.property("peopleLabel"))


# Unsubmitted - Bonded


def test_person_submitted_Bonded_personAPicker(view):
    view.set_kind(LifeChange.Bonded)
    view.personAPicker.set_new_person("John Doe", returnToFinish=False)
    view.pickerNotSubmitted(view.item.property("personALabel"))


def test_person_submitted_Bonded_personBPicker(view):
    view.set_kind(LifeChange.Bonded)
    view.personAPicker.set_new_person("John Doe")
    view.personBPicker.set_new_person("Jane Doe", returnToFinish=False)
    view.pickerNotSubmitted(view.item.property("personBLabel"))


# Unsubmitted - Fusion


def test_person_submitted_Fusion_moversPicker(view):
    view.set_kind(LifeChange.Fusion)
    view.moversPicker.add_new_person("John Doe", returnToFinish=False)
    view.pickerNotSubmitted(view.item.property("moversLabel"))


def test_person_submitted_Fusion_receiversPicker(view):
    view.set_kind(LifeChange.Fusion)
    view.moversPicker.add_new_person("John Doe")
    view.receiversPicker.add_new_person("Jane Doe", returnToFinish=False)
    view.pickerNotSubmitted(view.item.property("receiversLabel"))
