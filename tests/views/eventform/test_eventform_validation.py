import logging

import pytest
from mock import patch

from pkdiagram import util
from pkdiagram.scene import Person, Event, EventKind, RelationshipKind, Marriage
from pkdiagram.views import EventForm

# from test_peoplepicker import add_and_keyClicks, add_new_person, add_existing_person
from .test_eventform import (
    view,
    START_DATETIME,
    END_DATETIME,
)

log = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.component("EventForm"),
    pytest.mark.depends_on("Scene"),
]


def test_required_fields_kind(view):
    view.expectedFieldLabel(view.item.property("kindLabel"))


def test_required_fields_Shift(view):
    view.set_kind(EventKind.Shift)

    view.expectedFieldLabel(view.item.property("personLabel"))
    view.personPicker.set_new_person("John Doe")

    view.set_relationship(RelationshipKind.Conflict)
    view.expectedFieldLabel(view.item.property("descriptionLabel"))
    view.set_description("Some description")

    view.expectedFieldLabel(view.item.property("targetsLabel"))
    view.targetsPicker.add_new_person("Jane Doe")

    view.expectedFieldLabel(view.item.property("startDateTimeLabel"))
    view.set_startDateTime(START_DATETIME)

    view.clickSaveButton()


@pytest.mark.parametrize("endDateTime", [None, END_DATETIME])
def test_required_fields_Relationship(view, endDateTime):

    view.set_kind(EventKind.Shift)
    view.personPicker.set_new_person("John Doe")
    view.set_relationship(RelationshipKind.Conflict)

    view.expectedFieldLabel(view.item.property("descriptionLabel"))
    view.set_description("Some description")

    view.expectedFieldLabel(view.item.property("targetsLabel"))
    view.targetsPicker.add_new_person("Jane Doe")

    view.expectedFieldLabel(view.item.property("startDateTimeLabel"))
    view.set_startDateTime(START_DATETIME)

    view.set_isDateRange(True)

    if endDateTime:
        view.set_endDateTime(endDateTime)

    view.clickSaveButton()


def test_confirm_replace_Birth(scene, view):
    PRIOR_DATETIME = util.Date(2011, 1, 1)
    person, spouse, child = scene.addItems(
        Person(name="Parent", lastName="Doe"),
        Person(name="Souse", lastName="Doe"),
        Person(name="John", lastName="Doe"),
    )
    scene.addItem(Marriage(person, spouse))
    scene.addItem(
        Event(
            EventKind.Birth, person, spouse=spouse, child=child, dateTime=PRIOR_DATETIME
        )
    )
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(person)
    view.childPicker.set_existing_person(child)
    view.set_startDateTime(START_DATETIME)
    with patch("PyQt5.QtWidgets.QMessageBox.question") as question:
        view.clickSaveButton()
    assert question.call_args[0][2] == EventForm.S_REPLACE_EXISTING.format(
        n_existing=1, kind=EventKind.Birth.name
    )
    assert child.birthDateTime() == START_DATETIME


def test_confirm_replace_singular_events(qtbot, scene, view):
    PRIOR_DATETIME = util.Date(2011, 1, 1)
    person = scene.addItem(
        Person(name="Parent", lastName="Doe"),
    )
    scene.addItem(
        Event(
            EventKind.Death,
            person,
            dateTime=PRIOR_DATETIME,
        )
    )
    view.set_kind(EventKind.Death)
    view.personPicker.set_existing_person(person)
    view.set_startDateTime(START_DATETIME)
    with patch("PyQt5.QtWidgets.QMessageBox.question") as question:
        view.clickSaveButton()
    assert question.call_args[0][2] == EventForm.S_REPLACE_EXISTING.format(
        n_existing=1, kind=EventKind.Death.name
    )
    assert person.deceasedDateTime() == START_DATETIME


# Unsubmitted - All


def test_person_unsubmitted_personPicker(view):
    view.set_kind(EventKind.Shift)
    view.set_relationship(RelationshipKind.Inside)
    view.personPicker.set_new_person("John Doe", returnToFinish=False)
    view.pickerNotSubmitted(view.item.property("personLabel"))


# Unsubmitted - Birth


def test_person_unsubmitted_Birth_personPicker(view):
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("John Doe", returnToFinish=False, resetFocus=True)
    view.pickerNotSubmitted(view.item.property("personLabel"))


def test_person_unsubmitted_Birth_spouse(view):
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("John Doe")
    view.spousePicker.set_new_person("Johnny Doe", returnToFinish=False)
    view.pickerNotSubmitted(view.item.property("spouseLabel"))


def test_person_unsubmitted_Birth_personBPicker(view):
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("John Doe")
    view.spousePicker.set_new_person("Johnny Doe")
    view.childPicker.set_new_person("Janet Doe", returnToFinish=False)
    view.pickerNotSubmitted(view.item.property("childLabel"))


# Unsubmitted - Bonded


def test_person_unsubmitted_Bonded_personAicker(view):
    view.set_kind(EventKind.Bonded)
    view.personPicker.set_new_person("John Doe", returnToFinish=False)
    view.pickerNotSubmitted(view.item.property("personLabel"))


def test_person_unsubmitted_Bonded_personBPicker(view):
    view.set_kind(EventKind.Bonded)
    view.personPicker.set_new_person("John Doe")
    view.spousePicker.set_new_person("Jane Doe", returnToFinish=False)
    view.pickerNotSubmitted(view.item.property("spouseLabel"))


# Unsubmitted - Triangles


def test_person_unsubmitted_Triangle_targetsPicker(view):
    view.set_kind(EventKind.Shift)
    view.set_relationship(RelationshipKind.Inside)
    view.personPicker.set_new_person("John Doe")
    view.targetsPicker.add_new_person("Jane Doe", returnToFinish=False)
    view.pickerNotSubmitted(view.item.property("targetsLabel"))
