import pytest
from mock import patch

from pkdiagram import util
from pkdiagram.scene import EventKind, RelationshipKind, Person, Marriage, person


from .test_eventform import view


pytestmark = [
    pytest.mark.component("EventForm"),
    pytest.mark.depends_on("Scene"),
]

START_DATETIME = util.Date(2001, 1, 1, 6, 7)
END_DATETIME = util.Date(2002, 1, 1, 6, 7)
ONE_NAME = "John Doe"

DEPENDS = pytest.mark.depends_on("PersonPicker", "PeoplePicker", "DatePicker")


def test_tags(scene, view):
    TAG_1, TAG_2 = "tag1", "tag2"

    view.set_kind(EventKind.VariableShift)
    view.personPicker.set_new_person("John Doe")
    view.set_description("Something happened")
    view.set_startDateTime(START_DATETIME)
    view.add_tag(TAG_1)
    view.add_tag(TAG_2)
    view.set_active_tags([TAG_1, TAG_2])
    view.clickSaveButton()
    assert set([tag for event in scene.events() for tag in event.tags()]) == {
        TAG_1,
        TAG_2,
    }


def test_Birth_default_spouse_default_child(scene, view):
    mother = scene.addItem(Person(name="Mother"))
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(mother)
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()

    assert len(scene.people()) == 3
    spouse = next(x for x in mother.marriages[0].people if x is not mother)
    child = mother.marriages[0].children[0]
    assert spouse.name() == None
    assert child.name() == None
    event = child.events()[0]
    assert event.uniqueId() == EventKind.Birth.value
    assert event.description() == EventKind.Birth.name


def test_Birth_existing_parents_existing_child(scene, view):
    father = scene.addItem(Person(name="Father"))
    mother = scene.addItem(Person(name="Mother"))
    child = scene.addItem(Person(name="Child"))

    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(mother)
    view.spousePicker.set_existing_person(father)
    view.childPicker.set_existing_person(child)
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()
    assert len(scene.people()) == 3
    assert set(mother.marriages[0].people) == {mother, father}
    assert set(child.parents().people) == {mother, father}
    event = child.events()[0]
    assert event.uniqueId() == EventKind.Birth.value
    assert event.description() == EventKind.Birth.name


@pytest.mark.parametrize("before", [True, False])
def test_Birth_add_another_sets_currentDateTime(scene, view, before):

    mother = scene.addItem(Person(name="Mother"))
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(mother)
    view.childPicker.set_new_person("John Doe")
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()
    assert scene.currentDateTime() == START_DATETIME
    child = scene.query1(name="John", lastName="Doe")

    if before:
        second_dateTime = START_DATETIME.addDays(-10)
    else:
        second_dateTime = START_DATETIME.addDays(10)

    view.view.addEvent()
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(mother)
    view.childPicker.set_existing_person(child)
    view.set_startDateTime(second_dateTime)
    with patch("PyQt5.QtWidgets.QMessageBox.question") as question:
        view.clickSaveButton()
    assert question.call_count == 1
    if before:
        assert scene.currentDateTime() == START_DATETIME
    else:
        assert scene.currentDateTime() == second_dateTime


def test_Birth_existing_pairbond_default_spouse(scene, view, qmlEngine):
    father = scene.addItem(Person(name="John", lastName="Doe"))
    mother = scene.addItem(Person(name="Jane", lastName="Doe"))
    child = scene.addItem(Person(name="Josephine", lastName="Doe"))
    marriage = scene.addItem(Marriage(mother, father))
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(mother)
    view.spousePicker.set_existing_person(father)
    view.childPicker.set_existing_person(child)
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()
    assert set(mother.marriages[0].people) == {mother, father}
    assert set(child.parents().people) == {mother, father}


def test_Birth_multiple_pairbonds_exiting_spouse(scene, view, qmlEngine):
    father = scene.addItem(Person(name="John", lastName="Doe"))
    mother = scene.addItem(Person(name="Jane", lastName="Doe"))
    child = scene.addItem(Person(name="Josephine", lastName="Doe"))
    second_husband = scene.addItem(Person(name="Jim", lastName="Doe"))
    marriage1 = scene.addItem(Marriage(mother, father))
    marriage2 = scene.addItem(Marriage(mother, second_husband))
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(mother)
    view.spousePicker.set_existing_person(father)
    view.childPicker.set_existing_person(child)
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()
    assert set(mother.marriages[0].people) == {mother, father}
    assert set(child.parents().people) == {mother, father}


def test_add_multiple_events_to_new_person(scene, view):
    mother = scene.addItem(Person(name="Mother"))
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(mother)
    view.childPicker.set_new_person("John Doe")
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()
    newPerson = scene.query1(name="John", lastName="Doe")
    assert len(scene.people()) == 3
    assert len(newPerson.events()) == 1
    assert newPerson.events()[0].description() == EventKind.Birth.name
    assert newPerson.events()[0].dateTime() == START_DATETIME

    view.clickClearButton()
    view.view.addEvent()
    view.set_kind(EventKind.VariableShift)
    view.personPicker.set_existing_person(newPerson)
    view.set_startDateTime(START_DATETIME.addDays(15))
    view.set_symptom(util.VAR_SYMPTOM_DOWN)
    view.set_description("Something happened")
    view.clickSaveButton()
    newPerson = scene.query1(name="John", lastName="Doe")
    assert len(scene.people()) == 3
    assert len(newPerson.events()) == 2
    assert newPerson.events()[0].uniqueId() == EventKind.Birth.value
    assert newPerson.events()[0].dateTime() == START_DATETIME
    assert newPerson.events()[1].description() == "Something happened"
    assert newPerson.events()[1].dateTime() == START_DATETIME.addDays(15)


def test_flash_new_items(scene, view):
    view.set_kind(EventKind.VariableShift)
    view.personPicker.set_new_person("John Doe")
    view.set_relationship(RelationshipKind.Conflict)
    view.targetsPicker.add_new_person("Jane Doe")
    view.set_startDateTime(START_DATETIME)
    view.set_description("Something happened")
    with patch("pkdiagram.scene.ItemAnimationHelper.flash", autospec=True) as flash:
        view.clickSaveButton()
    personA = scene.query1(name="John", lastName="Doe")
    personB = scene.query1(name="Jane", lastName="Doe")
    emotion = personA.emotions()[0]
    assert flash.call_count == 3
    assert flash.call_args_list[0][0][0] == personA
    assert flash.call_args_list[1][0][0] == personB
    assert flash.call_args_list[2][0][0] == emotion


def test_PairBond_add_existing(scene, view):
    TAG_1, TAG_2 = "tag1", "tag2"

    KIND = EventKind.Separated

    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Jane", lastName="Doe"))
    marriage = scene.addItem(Marriage(personA, personB))
    view.personPicker.set_existing_person(personA)
    view.set_kind(KIND)
    view.spousePicker.set_existing_person(personB)
    view.set_startDateTime(START_DATETIME)
    view.add_tag(TAG_1)
    view.add_tag(TAG_2)
    view.set_active_tags([TAG_1, TAG_2])
    view.clickSaveButton()
    assert len(scene.people()) == 2
    assert personA.marriages == personB.marriages == [marriage]
    assert len(marriage.events()) == 1
    assert marriage.events()[0].uniqueId() == KIND.value
    assert marriage.events()[0].description() == KIND.menuLabel()


def test_PairBond_add_multiple_events_to_new_pairbond(scene, view):
    KIND_1 = EventKind.Separated

    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Jane", lastName="Doe"))
    marriage = scene.addItem(Marriage(personA, personB))
    view.personPicker.set_existing_person(personA)
    view.set_kind(KIND_1)
    view.spousePicker.set_existing_person(personB)
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()
    assert len(scene.people()) == 2
    assert personA.marriages == personB.marriages == [marriage]
    assert len(marriage.events()) == 1
    assert marriage.events()[0].uniqueId() == KIND_1.value
    assert marriage.events()[0].description() == KIND_1.menuLabel()

    KIND_2 = EventKind.Bonded

    view.clickClearButton()
    view.personPicker.set_existing_person(personA)
    view.set_kind(KIND_2)
    view.spousePicker.set_existing_person(personB)
    view.set_startDateTime(START_DATETIME.addDays(-30))
    view.clickSaveButton()
    assert len(scene.people()) == 2
    assert personA.marriages == personB.marriages == [marriage]
    assert len(marriage.events()) == 2
    assert marriage.events()[0].uniqueId() == KIND_2.value
    assert marriage.events()[0].description() == KIND_2.menuLabel()
    assert marriage.events()[1].uniqueId() == KIND_1.value
    assert marriage.events()[1].description() == KIND_1.menuLabel()
