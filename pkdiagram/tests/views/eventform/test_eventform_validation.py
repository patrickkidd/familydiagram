import pytest
from mock import patch

from btcopilot.schema import EventKind, RelationshipKind
from pkdiagram import util
from pkdiagram.scene import Person, Event, Marriage
from pkdiagram.views import EventForm

# from test_peoplepicker import add_and_keyClicks, add_new_person, add_existing_person
from .test_eventform import (
    view,
    START_DATETIME,
    END_DATETIME,
)

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
    view.spousePicker.set_existing_person(spouse)
    view.childPicker.set_existing_person(child)
    view.set_startDateTime(START_DATETIME)
    with patch("PyQt5.QtWidgets.QMessageBox.question") as question:
        view.clickSaveButton()
    assert question.call_args[0][2] == EventForm.S_REPLACE_EXISTING.format(
        n_existing=1, kind=EventKind.Birth.name
    )
    assert child.birthDateTime() == START_DATETIME


def test_confirm_replace_Death(scene, view):
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


def test_person_unsubmitted_Bonded_personAPicker(view):
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


# Birth/Adopted with partial people


def test_Birth_requires_at_least_one_person(view):
    view.set_kind(EventKind.Birth)
    view.set_startDateTime(START_DATETIME)
    with patch("PyQt5.QtWidgets.QMessageBox.warning") as warning:
        view.clickSaveButton()
    assert warning.call_count == 1
    assert warning.call_args[0][2] == EventForm.S_BIRTH_REQUIRES_ONE


def test_Birth_with_child_only(scene, view):
    child = scene.addItem(Person(name="Johnny"))
    view.set_kind(EventKind.Birth)
    view.childPicker.set_existing_person(child)
    view.set_startDateTime(START_DATETIME)
    with patch("PyQt5.QtWidgets.QMessageBox.question", return_value=None) as question:
        view.clickSaveButton()
    assert question.call_count == 1
    assert "Johnny's Parent 1" in question.call_args[0][2]
    assert "Johnny's Parent 2" in question.call_args[0][2]


def test_Birth_with_parent1_only(scene, view):
    mother = scene.addItem(Person(name="Jane"))
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(mother)
    view.set_startDateTime(START_DATETIME)
    with patch("PyQt5.QtWidgets.QMessageBox.question", return_value=None) as question:
        view.clickSaveButton()
    assert question.call_count == 1
    assert "Jane's Spouse" in question.call_args[0][2]
    assert "Jane's Child" in question.call_args[0][2]


def test_Birth_with_parent2_only(scene, view):
    father = scene.addItem(Person(name="John", gender="male"))
    view.set_kind(EventKind.Birth)
    view.spousePicker.set_existing_person(father)
    view.set_startDateTime(START_DATETIME)
    with patch("PyQt5.QtWidgets.QMessageBox.question", return_value=None) as question:
        view.clickSaveButton()
    assert question.call_count == 1
    assert "John's Spouse" in question.call_args[0][2]
    assert "John's Child" in question.call_args[0][2]


def test_Birth_with_parents_only(scene, view):
    mother = scene.addItem(Person(name="Jane"))
    father = scene.addItem(Person(name="John", gender="male"))
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(mother)
    view.spousePicker.set_existing_person(father)
    view.set_startDateTime(START_DATETIME)
    with patch("PyQt5.QtWidgets.QMessageBox.question", return_value=None) as question:
        view.clickSaveButton()
    assert question.call_count == 1
    assert "Jane & John's Child" in question.call_args[0][2]


def test_Birth_child_only_creates_parents(scene, view):
    child = scene.addItem(Person(name="Johnny"))
    view.set_kind(EventKind.Birth)
    view.childPicker.set_existing_person(child)
    view.set_startDateTime(START_DATETIME)
    with patch(
        "PyQt5.QtWidgets.QMessageBox.question",
        return_value=16384,  # QMessageBox.Yes
    ):
        view.clickSaveButton()
    assert child.parents() is not None
    parents = child.parents().people
    assert len(parents) == 2
    parentNames = {p.name() for p in parents}
    assert "Johnny's Parent 1" in parentNames
    assert "Johnny's Parent 2" in parentNames
    assert child.birthDateTime() == START_DATETIME


def test_Birth_parent1_only_creates_spouse_and_child(scene, view):
    mother = scene.addItem(Person(name="Jane", gender="female"))
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(mother)
    view.set_startDateTime(START_DATETIME)
    with patch(
        "PyQt5.QtWidgets.QMessageBox.question",
        return_value=16384,  # QMessageBox.Yes
    ):
        view.clickSaveButton()
    assert len(mother.marriages) == 1
    marriage = mother.marriages[0]
    spouse = marriage.personA() if marriage.personB() == mother else marriage.personB()
    assert spouse.name() == "Jane's Spouse"
    assert spouse.gender() == util.PERSON_KIND_MALE
    assert len(marriage.children) == 1
    child = marriage.children[0]
    assert child.name() == "Jane's Child"
    assert child.birthDateTime() == START_DATETIME


def test_Birth_male_parent_creates_female_spouse(scene, view):
    """Auto-created spouse should be opposite gender of the specified parent."""
    father = scene.addItem(Person(name="John", gender="male"))
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(father)
    view.set_startDateTime(START_DATETIME)
    with patch(
        "PyQt5.QtWidgets.QMessageBox.question",
        return_value=16384,  # QMessageBox.Yes
    ):
        view.clickSaveButton()
    marriage = father.marriages[0]
    spouse = marriage.personA() if marriage.personB() == father else marriage.personB()
    assert spouse.gender() == util.PERSON_KIND_FEMALE


def test_Birth_no_confirmation_when_all_specified(scene, view):
    mother = scene.addItem(Person(name="Jane"))
    father = scene.addItem(Person(name="John", gender="male"))
    child = scene.addItem(Person(name="Johnny"))
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(mother)
    view.spousePicker.set_existing_person(father)
    view.childPicker.set_existing_person(child)
    view.set_startDateTime(START_DATETIME)
    with patch("PyQt5.QtWidgets.QMessageBox.question") as question:
        view.clickSaveButton()
    assert question.call_count == 0
    assert child.parents() is not None
    assert child.birthDateTime() == START_DATETIME


def test_Birth_child_only_undo_redo(scene, view):
    """Undo/redo works when creating a birth with only child specified."""
    child = scene.addItem(Person(name="Johnny"))

    assert len(scene.people()) == 1
    assert child.parents() is None

    view.set_kind(EventKind.Birth)
    view.childPicker.set_existing_person(child)
    view.set_startDateTime(START_DATETIME)
    with patch(
        "PyQt5.QtWidgets.QMessageBox.question",
        return_value=16384,  # QMessageBox.Yes
    ):
        view.clickSaveButton()

    assert len(scene.people()) == 3
    assert len(scene.marriages()) == 1
    assert len(scene.events()) == 1
    assert child.parents() is not None
    marriage = scene.marriages()[0]
    assert child in marriage.children
    parents = child.parents().people
    assert len(parents) == 2
    parentNames = {p.name() for p in parents}
    assert "Johnny's Parent 1" in parentNames
    assert "Johnny's Parent 2" in parentNames
    event = scene.events()[0]
    assert event.child() == child
    parent1 = [p for p in parents if p.name() == "Johnny's Parent 1"][0]
    parent2 = [p for p in parents if p.name() == "Johnny's Parent 2"][0]
    assert parent1.scene() == scene
    assert parent2.scene() == scene
    assert marriage.scene() == scene
    assert event.scene() == scene

    scene.undo()

    assert len(scene.people()) == 1
    assert len(scene.marriages()) == 0
    assert len(scene.events()) == 0
    assert child.parents() is None
    assert parent1.scene() is None
    assert parent2.scene() is None

    scene.redo()

    assert len(scene.people()) == 3
    assert len(scene.marriages()) == 1
    assert len(scene.events()) == 1
    assert child.parents() is not None
    marriage = scene.marriages()[0]
    assert child in marriage.children
    parents = child.parents().people
    assert len(parents) == 2
    parentNames = {p.name() for p in parents}
    assert "Johnny's Parent 1" in parentNames
    assert "Johnny's Parent 2" in parentNames
    event = scene.events()[0]
    assert event.child() == child
    assert event.dateTime() == START_DATETIME
    parent1 = [p for p in parents if p.name() == "Johnny's Parent 1"][0]
    parent2 = [p for p in parents if p.name() == "Johnny's Parent 2"][0]
    assert parent1.scene() == scene
    assert parent2.scene() == scene
    assert marriage.scene() == scene
    assert event.scene() == scene


def test_Birth_parent_only_undo_redo(scene, view):
    """Undo/redo works when creating a birth with only parent1 specified."""
    mother = scene.addItem(Person(name="Jane", gender="female"))

    assert len(scene.people()) == 1

    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(mother)
    view.set_startDateTime(START_DATETIME)
    with patch(
        "PyQt5.QtWidgets.QMessageBox.question",
        return_value=16384,  # QMessageBox.Yes
    ):
        view.clickSaveButton()

    assert len(scene.people()) == 3
    assert len(scene.marriages()) == 1
    assert len(scene.events()) == 1
    marriage = mother.marriages[0]
    spouse = marriage.personA() if marriage.personB() == mother else marriage.personB()
    assert spouse.name() == "Jane's Spouse"
    child = marriage.children[0]
    assert child.name() == "Jane's Child"
    assert child.parents() == marriage
    assert spouse.scene() == scene
    assert child.scene() == scene
    event = scene.events()[0]
    assert event.scene() == scene

    scene.undo()

    assert len(scene.people()) == 1
    assert len(scene.marriages()) == 0
    assert len(scene.events()) == 0
    assert mother.marriages == []
    assert spouse.scene() is None
    assert child.scene() is None

    scene.redo()

    assert len(scene.people()) == 3
    assert len(scene.marriages()) == 1
    assert len(scene.events()) == 1
    marriage = mother.marriages[0]
    spouse = marriage.personA() if marriage.personB() == mother else marriage.personB()
    assert spouse.name() == "Jane's Spouse"
    child = marriage.children[0]
    assert child.name() == "Jane's Child"
    assert child.parents() == marriage
    assert spouse.scene() == scene
    assert child.scene() == scene
    event = scene.events()[0]
    assert event.scene() == scene


def test_Birth_child_only_undo_redo_existing_child_remains(scene, view):
    """Existing child remains in scene after undo/redo."""
    child = scene.addItem(Person(name="Johnny"))
    childId = child.id

    view.set_kind(EventKind.Birth)
    view.childPicker.set_existing_person(child)
    view.set_startDateTime(START_DATETIME)
    with patch(
        "PyQt5.QtWidgets.QMessageBox.question",
        return_value=16384,  # QMessageBox.Yes
    ):
        view.clickSaveButton()

    scene.undo()
    assert child.scene() == scene
    assert child.id == childId
    assert child in scene.people()

    scene.redo()
    assert child.scene() == scene
    assert child.id == childId
    assert child in scene.people()
    assert child.parents() is not None
