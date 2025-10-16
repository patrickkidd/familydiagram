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

    view.set_kind(EventKind.Shift)
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
    assert len(scene.events()) == 1
    assert len(scene.marriages()) == 1
    event = scene.events()[0]
    marriage = scene.marriages()[0]
    spouse = marriage.personB()
    child = event.child()
    assert event.spouse() == spouse
    assert event.child() == child
    assert marriage.personA() == mother
    assert spouse.name() == None
    assert child.name() == None
    assert child.parents() == marriage
    assert event.kind() == EventKind.Birth


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
    event = scene.events()[0]
    assert event.kind() == EventKind.Birth
    assert event.person() == mother
    assert event.spouse() == father
    assert event.child() == child


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
    assert scene.eventsFor(child, kinds=EventKind.Birth) != []

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


def test_Birth_existing_pairbond_default_spouse(scene, view):
    father = scene.addItem(Person(name="John", lastName="Doe"))
    mother = scene.addItem(Person(name="Jane", lastName="Doe"))
    child = scene.addItem(Person(name="Josephine", lastName="Doe"))
    marriage = scene.addItem(Marriage(mother, father))
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(mother)
    view.childPicker.set_existing_person(child)
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()

    assert len(scene.people()) == 4
    assert len(scene.marriages()) == 2
    default_spouse = scene.people()[3]
    event = scene.eventsFor(child, kinds=EventKind.Birth)[0]
    assert event.kind() == EventKind.Birth
    assert event.spouse() == default_spouse
    assert event.child() == child
    assert child.parents().personA() == mother
    assert child.parents().personB() == default_spouse


def test_Birth_multiple_pairbonds_existing_spouse(scene, view):
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

    assert len(scene.people()) == 4
    assert len(scene.marriages()) == 2
    event = scene.eventsFor(child, kinds=EventKind.Birth)[0]
    assert event.kind() == EventKind.Birth
    assert event.person() == mother
    assert event.spouse() == father
    assert event.child() == child
    assert child.parents() == marriage1
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
    assert len(scene.eventsFor(mother)) == 1
    event = scene.eventsFor(mother)[0]
    assert event.dateTime() == START_DATETIME

    view.clickClearButton()
    view.view.addEvent()
    view.set_kind(EventKind.Shift)
    view.personPicker.set_existing_person(newPerson)
    view.set_startDateTime(START_DATETIME.addDays(15))
    view.set_symptom(util.VAR_SYMPTOM_DOWN)
    view.set_description("Something happened")
    view.clickSaveButton()
    assert len(scene.people()) == 3
    events = scene.eventsFor(newPerson)
    assert len(events) == 2
    assert events[0].kind() == EventKind.Birth
    assert events[0].dateTime() == START_DATETIME
    assert events[1].description() == "Something happened"
    assert events[1].dateTime() == START_DATETIME.addDays(15)


def test_flash_new_items(scene, view):
    view.set_kind(EventKind.Shift)
    view.personPicker.set_new_person("John Doe")
    view.set_relationship(RelationshipKind.Conflict)
    view.targetsPicker.add_new_person("Jane Doe")
    view.set_startDateTime(START_DATETIME)
    view.set_description("Something happened")
    with patch("pkdiagram.scene.ItemAnimationHelper.flash", autospec=True) as flash:
        view.clickSaveButton()
    personA = scene.query1(name="John", lastName="Doe")
    personB = scene.query1(name="Jane", lastName="Doe")
    emotion = scene.emotionsFor(personA)[0]
    assert flash.call_count == 5
    assert flash.call_args_list[0][0][0] in personA.detailsText.extraTextItems
    assert flash.call_args_list[1][0][0] in personB.detailsText.extraTextItems
    assert flash.call_args_list[2][0][0] == personA
    assert flash.call_args_list[3][0][0] == personB
    assert flash.call_args_list[4][0][0] == emotion


def test_PairBond_add_existing(scene, view):
    TAG_1, TAG_2 = "tag1", "tag2"

    KIND = EventKind.Separated

    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Jane", lastName="Doe"))
    marriage = scene.addItem(Marriage(personA, personB))
    view.set_kind(KIND)
    view.personPicker.set_existing_person(personA)
    view.spousePicker.set_existing_person(personB)
    view.set_startDateTime(START_DATETIME)
    view.add_tag(TAG_1)
    view.add_tag(TAG_2)
    view.set_active_tags([TAG_1, TAG_2])
    view.clickSaveButton()
    assert len(scene.people()) == 2
    assert personA.marriages == personB.marriages == [marriage]
    assert len(scene.eventsFor(marriage)) == 1
    event = scene.eventsFor(marriage)[0]
    assert event.kind() == KIND


def test_PairBond_add_multiple_events_to_new_pairbond(scene, view):
    KIND_1 = EventKind.Separated

    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Jane", lastName="Doe"))
    marriage = scene.addItem(Marriage(personA, personB))
    view.set_kind(KIND_1)
    view.personPicker.set_existing_person(personA)
    view.spousePicker.set_existing_person(personB)
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()
    assert len(scene.people()) == 2
    assert personA.marriages == personB.marriages == [marriage]
    assert len(scene.eventsFor(marriage)) == 1
    event = scene.eventsFor(marriage)[0]
    assert event.kind() == KIND_1

    KIND_2 = EventKind.Bonded

    view.clickClearButton()
    view.set_kind(KIND_2)
    view.personPicker.set_existing_person(personA)
    view.spousePicker.set_existing_person(personB)
    view.set_startDateTime(START_DATETIME.addDays(-30))
    view.clickSaveButton()
    assert len(scene.people()) == 2
    assert personA.marriages == personB.marriages == [marriage]
    events = scene.eventsFor(marriage)
    assert len(events) == 2
    assert events[0].kind() == KIND_2
    assert events[1].kind() == KIND_1
