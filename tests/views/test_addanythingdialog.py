import logging

import pytest
import mock

from pkdiagram import util
from pkdiagram.scene import Person, Marriage, EventKind, PathItem
from pkdiagram.views import AddAnythingDialog

from tests.views import TestAddAnythingDialog

_log = logging.getLogger(__name__)


ONE_NAME = "John Doe"
START_DATETIME = util.Date(2001, 1, 1, 6, 7)
END_DATETIME = util.Date(2002, 1, 1, 6, 7)

DEPENDS = pytest.mark.depends_on("PersonPicker", "PeoplePicker", "DatePicker")


@pytest.fixture
def view(qtbot, scene, qmlEngine):
    qmlEngine.setScene(scene)
    widget = AddAnythingDialog(qmlEngine)
    widget.resize(600, 800)
    widget.setScene(scene)
    widget.show()
    qtbot.addWidget(widget)
    qtbot.waitActive(widget)
    assert widget.isShown()
    # widget.adjustFlickableHack()

    view = TestAddAnythingDialog(widget)
    view.initForSelection([])

    yield view

    widget.setScene(None)
    widget.hide()
    widget.deinit()


def test_init(view):
    assert view.item.property("kind") == None
    assert view.kindBox.property("currentIndex") == -1
    assert view.tagsEdit.property("isDirty") == False


def test_clear_CustomIndividual(view):
    view.set_kind(EventKind.CustomIndividual)  # dyadic for end date
    view.set_startDateTime(START_DATETIME)
    view.set_description("something")
    view.set_notes("here are some notes")
    view.set_anxiety(util.VAR_VALUE_UP)
    view.set_symptom(util.VAR_VALUE_DOWN)
    view.set_functioning(util.VAR_VALUE_SAME)
    view.add_tag("tag1")
    view.set_active_tags(["tag1"])
    view.clickClearButton()
    assert view.item.property("startDateTime") == None
    assert view.item.property("endDateTime") == None
    assert view.item.property("description") == ""
    assert view.item.property("notes") == ""
    assert view.item.property("anxiety") == None
    assert view.item.property("symptom") == None
    assert view.item.property("functioning") == None
    assert view.item.property("eventModel").tags == []


def test_clear_Dyadic(view):
    view.initForSelection([])
    view.set_kind(EventKind.Cutoff)  # dyadic for end date
    view.set_startDateTime(START_DATETIME)
    view.set_endDateTime(END_DATETIME)
    view.set_notes("here are some notes")
    view.set_anxiety(util.VAR_VALUE_UP)
    view.set_symptom(util.VAR_VALUE_DOWN)
    view.set_functioning(util.VAR_VALUE_SAME)
    view.add_tag("tag1")
    view.set_active_tags(["tag1"])
    view.clickClearButton()
    assert view.item.property("startDateTime") == None
    assert view.item.property("endDateTime") == None
    assert view.item.property("notes") == ""
    assert view.item.property("anxiety") == None
    assert view.item.property("symptom") == None
    assert view.item.property("functioning") == None
    assert view.item.property("eventModel").tags == []


def test_clear_birth(view):
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("John Done")
    view.personAPicker.set_new_person("Jon Done")
    view.personBPicker.set_new_person("Jane Done")
    assert view.personPicker.item.property("isSubmitted") == True
    assert view.personAPicker.item.property("isSubmitted") == True
    assert view.personBPicker.item.property("isSubmitted") == True
    view.clickClearButton()
    assert view.personPicker.item.property("isSubmitted") == False
    assert view.personAPicker.item.property("isSubmitted") == False
    assert view.personBPicker.item.property("isSubmitted") == False


def test_clear_monadic(view):
    view.set_kind(EventKind.Adopted)
    view.personPicker.set_new_person("John Done")
    assert view.personPicker.item.property("isSubmitted") == True
    view.clickClearButton()
    assert view.personPicker.item.property("isSubmitted") == False


def test_clear_custom_individual(view):
    view.set_kind(EventKind.CustomIndividual)
    view.peoplePicker.add_new_person("John Done")
    assert view.item.peopleEntries().toVariant()
    view.clickClearButton()
    assert view.item.peopleEntries().toVariant() == []


def test_clear_pairbond(view):
    view.set_kind(EventKind.Married)
    view.personAPicker.set_new_person("John Done")
    view.personBPicker.set_new_person("Jane Done")
    assert view.personAPicker.item.property("isSubmitted")
    assert view.personBPicker.item.property("isSubmitted")
    view.clickClearButton()
    assert not view.personAPicker.item.property("isSubmitted")
    assert not view.personBPicker.item.property("isSubmitted")


def test_clear_dyadic(view):
    view.set_kind(EventKind.Conflict)
    view.moversPicker.add_new_person("John Doe")
    view.moversPicker.add_new_person("Jane Doe")
    view.receiversPicker.add_new_person("Jane Doe")
    view.receiversPicker.add_new_person("Jane Done")
    assert view.item.moverEntries().toVariant()
    assert view.item.receiverEntries().toVariant()
    view.clickClearButton()
    assert view.item.moverEntries().toVariant() == []
    assert view.item.receiverEntries().toVariant() == []


def test_add_new_person_via_Birth(scene, view, qmlEngine):
    TAG_1, TAG_2 = "tag1", "tag2"

    submitted = util.Condition(view.view.submitted)
    view.initForSelection([])
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("John Doe")
    view.set_startDateTime(START_DATETIME)
    view.add_tag(TAG_1)
    view.add_tag(TAG_2)
    view.set_active_tags([TAG_1, TAG_2])
    view.clickAddButton()
    assert submitted.callCount == 1, "submitted signal emitted too many times"

    scene = qmlEngine.sceneModel.scene
    assert len(scene.people()) == 1, f"Incorrect number of people added to scene"
    person = scene.query1(name="John", lastName="Doe")
    assert person, f"Could not find created person {ONE_NAME}"
    assert len(person.events()) == 1, f"Incorrect number of events added to scene"
    event = person.events()[0]
    assert event.uniqueId() == EventKind.Birth.value
    assert event.description() == EventKind.Birth.name
    assert event.tags() == [TAG_1, TAG_2]


def test_add_new_person_via_Birth_with_one_parent(scene, view, qmlEngine):
    submitted = util.Condition(view.view.submitted)
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("John Doe")
    view.personAPicker.set_new_person(
        "Joseph Doe",
        gender=util.personKindNameFromKind(util.PERSON_KIND_MALE),
    )
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    assert submitted.callCount == 1, "submitted signal emitted too many times"

    scene = qmlEngine.sceneModel.scene
    assert len(scene.people()) == 3, f"Incorrect number of people added to scene"
    person = scene.query1(name="John", lastName="Doe")
    personA = scene.query1(name="Joseph", lastName="Doe")
    personB = next(x for x in scene.people() if x.id not in {person.id, personA.id})
    assert person, f"Could not find created person {ONE_NAME}"
    assert len(person.events()) == 1, f"Incorrect number of events added to scene"
    event = person.events()[0]
    assert event.uniqueId() == EventKind.Birth.value
    assert event.description() == EventKind.Birth.name
    assert len(person.parents().people) == 2
    assert personA in person.parents().people
    assert personB.gender() == util.PERSON_KIND_FEMALE


@pytest.mark.parametrize("before", [True, False])
def test_add_second_Birth_sets_currentDateTime(scene, view, before):
    view.initForSelection([])
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("John Doe")
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    assert scene.currentDateTime() == START_DATETIME

    if before:
        second_dateTime = START_DATETIME.addDays(-10)
    else:
        second_dateTime = START_DATETIME.addDays(10)

    view.initForSelection([])
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("John Doe")
    view.set_startDateTime(second_dateTime)
    view.clickAddButton()
    if before:
        assert scene.currentDateTime() == START_DATETIME
    else:
        assert scene.currentDateTime() == second_dateTime


def test_add_new_person_with_one_existing_parent_one_new_via_Birth(
    scene, view, qmlEngine
):
    BIRTH_NOTES = """asd fd fgfg"""

    parentA = scene.addItem(Person(name="John", lastName="Doe"))
    submitted = util.Condition(view.view.submitted)
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("Josephine Doe")
    view.personAPicker.set_existing_person(parentA)
    view.personBPicker.set_new_person("Jane Doe")
    view.set_startDateTime(START_DATETIME)
    view.set_notes(BIRTH_NOTES)
    view.clickAddButton()
    assert submitted.callCount == 1, "submitted signal not emitted exactly once"

    scene = qmlEngine.sceneModel.scene
    assert len(scene.people()) == 3, f"Incorrect number of people added to scene"
    child = scene.query1(name="Josephine", lastName="Doe")
    assert child, f"Could not find created child {ONE_NAME}"
    assert len(child.events()) == 1, f"Incorrect number of events added to scene"
    event = child.events()[0]
    assert event.uniqueId() == EventKind.Birth.value
    assert event.description() == EventKind.Birth.name
    assert event.notes() == BIRTH_NOTES

    parentA = scene.query1(name="John", lastName="Doe")
    parentB = scene.query1(name="Jane", lastName="Doe")
    assert {x.id for x in child.parents().people} == {parentA.id, parentB.id}


def test_add_new_person_with_one_existing_parent_via_Birth(scene, view, qmlEngine):
    BIRTH_NOTES = "asd fd fgfg "

    parentA = scene.addItem(Person(name="John", lastName="Doe"))
    submitted = util.Condition(view.view.submitted)
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("Josephine Doe")
    view.personAPicker.set_existing_person(parentA)
    view.set_startDateTime(START_DATETIME)
    view.set_notes(BIRTH_NOTES)
    view.clickAddButton()
    assert submitted.callCount == 1, "submitted signal not emitted exactly once"

    scene = qmlEngine.sceneModel.scene
    assert len(scene.people()) == 3, f"Incorrect number of people added to scene"
    child = scene.query1(name="Josephine", lastName="Doe")
    assert child, f"Could not find created child {ONE_NAME}"
    assert len(child.events()) == 1, f"Incorrect number of events added to scene"
    event = child.events()[0]
    assert event.uniqueId() == EventKind.Birth.value
    assert event.description() == EventKind.Birth.name
    assert event.notes() == BIRTH_NOTES

    parentA = scene.query1(name="John", lastName="Doe")
    parentB = next(x for x in scene.people() if x.id not in {parentA.id, child.id})
    assert parentB.name() == None
    assert parentB.fullNameOrAlias() == ""


def test_add_new_person_via_CustomIndividual(view, scene, qmlEngine):
    DESCRIPTION = "Something Happened"
    GENDER = util.PERSON_KIND_FEMALE
    NOTES = """Here is another
    multi-line
comment.
"""
    TAG_1, TAG_2 = "tag1", "tag2"

    submitted = util.Condition(view.view.submitted)
    view.set_kind(EventKind.CustomIndividual)
    view.peoplePicker.add_new_person("John Doe", gender=GENDER)
    view.set_description(DESCRIPTION)
    view.set_startDateTime(START_DATETIME)
    view.set_notes(NOTES)
    view.add_tag(TAG_1)
    view.add_tag(TAG_2)
    view.set_active_tags([TAG_1, TAG_2])
    view.clickAddButton()
    assert submitted.callCount == 1, "submitted signal emitted too many times"

    scene = qmlEngine.sceneModel.scene
    assert len(scene.people()) == 1, f"Incorrect number of people added to scene"
    person = scene.query1(name="John", lastName="Doe")
    assert person, f"Could not find created person {ONE_NAME}"
    assert person.gender() == GENDER
    assert len(person.events()) == 1, f"Incorrect number of events added to scene"
    event = person.events()[0]
    assert event.uniqueId() == None
    assert event.description() == DESCRIPTION
    assert event.notes() == NOTES


def test_add_new_person_adopted(scene, view):
    submitted = util.Condition(view.view.submitted)
    view.set_kind(EventKind.Adopted)
    view.personPicker.set_new_person("John Doe")
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    newPerson = scene.query1(name="John", lastName="Doe")
    assert submitted.callCount == 1
    assert len(scene.people()) == 1
    assert newPerson.adopted() == True
    assert newPerson.adoptedDateTime() == START_DATETIME


def test_add_multiple_events_to_new_person(scene, view):
    DESCRIPTION = "Something happened"
    submitted = util.Condition(view.view.submitted)
    view.set_kind(EventKind.CustomIndividual)
    view.peoplePicker.add_new_person("John Doe")
    view.set_startDateTime(START_DATETIME)
    view.set_description(DESCRIPTION)
    view.clickAddButton()
    newPerson = scene.query1(name="John", lastName="Doe")
    assert submitted.callCount == 1
    assert len(scene.people()) == 1
    assert len(newPerson.events()) == 1
    assert newPerson.events()[0].description() == DESCRIPTION
    assert newPerson.events()[0].dateTime() == START_DATETIME

    view.clickClearButton()
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(newPerson)
    view.set_startDateTime(START_DATETIME.addDays(15))
    view.clickAddButton()
    newPerson = scene.query1(name="John", lastName="Doe")
    assert submitted.callCount == 2
    assert len(scene.people()) == 1
    assert len(newPerson.events()) == 2
    assert newPerson.events()[0].uniqueId() == EventKind.Birth.value
    assert newPerson.events()[0].dateTime() == START_DATETIME.addDays(15)
    assert newPerson.events()[1].description() == DESCRIPTION
    assert newPerson.events()[1].dateTime() == START_DATETIME


def test_add_new_person_cutoff_with_date_range(scene, view):
    NOTES = """
Here are the
notes
for this event.
"""
    submitted = util.Condition(view.view.submitted)
    view.set_kind(EventKind.Cutoff)
    view.personPicker.set_new_person("John Doe")
    view.set_startDateTime(START_DATETIME)
    view.set_endDateTime(END_DATETIME)
    view.set_notes(NOTES)
    view.clickAddButton()
    newPerson = scene.query1(name="John", lastName="Doe")
    assert submitted.callCount == 1, "submitted signal emitted too many times"
    assert len(scene.people()) == 1
    assert newPerson.emotions()[0].kind() == util.ITEM_CUTOFF
    assert newPerson.emotions()[0].startEvent.dateTime() == START_DATETIME
    assert newPerson.emotions()[0].endEvent.dateTime() == END_DATETIME
    assert newPerson.emotions()[0].notes() == NOTES


@pytest.mark.parametrize("kind", [x for x in EventKind if EventKind.isDyadic(x)])
def test_add_new_dyadic(scene, view, kind):
    NOTES = """
Here are the
notes
for this event.
"""
    TAG_1, TAG_2 = "tag1", "tag2"

    view.set_kind(kind)
    view.moversPicker.add_new_person("John Doe")
    view.receiversPicker.add_new_person("Jane Doe")
    view.set_startDateTime(START_DATETIME)
    view.set_notes(NOTES)
    view.add_tag(TAG_1)
    view.add_tag(TAG_2)
    view.set_active_tags([TAG_1, TAG_2])
    with mock.patch(
        "pkdiagram.scene.ItemAnimationHelper.flash", autospec=True
    ) as flash:
        view.clickAddButton()
    personA = scene.query1(name="John", lastName="Doe")
    personB = scene.query1(name="Jane", lastName="Doe")
    emotion = personA.emotions()[0]
    assert flash.call_count == 3
    assert flash.call_args_list[0][0][0] == personA
    assert flash.call_args_list[1][0][0] == personB
    assert flash.call_args_list[2][0][0] == emotion
    assert len(scene.people()) == 2
    assert len(personA.emotions()) == 1
    assert len(personB.emotions()) == 1
    assert personA.emotions() == personB.emotions()
    assert personA.emotions()[0].kind() == EventKind.itemModeFor(kind)
    assert personA.emotions()[0].startDateTime() == START_DATETIME
    assert personA.emotions()[0].endDateTime() == START_DATETIME
    assert personA.emotions()[0].notes() == NOTES
    assert personA.emotions()[0].startEvent.notes() == NOTES
    assert personA.emotions()[0].endEvent.notes() == NOTES


def test_add_new_dyadic_isDateRange(scene, view):
    NOTES = """
Here are the
notes
for this event.
"""

    view.set_kind(EventKind.Away)
    view.moversPicker.add_new_person("John Doe")
    view.receiversPicker.add_new_person("Jane Doe")
    view.set_startDateTime(START_DATETIME)
    view.set_endDateTime(END_DATETIME)
    view.set_notes(NOTES)
    view.clickAddButton()
    personA = scene.query1(name="John", lastName="Doe")
    personB = scene.query1(name="Jane", lastName="Doe")
    assert len(scene.people()) == 2
    assert len(personA.emotions()) == 1
    assert len(personB.emotions()) == 1
    assert personA.emotions() == personB.emotions()
    assert personA.emotions()[0].kind() == util.ITEM_AWAY
    assert personA.emotions()[0].startDateTime() == START_DATETIME
    assert personA.emotions()[0].endDateTime() == END_DATETIME
    assert personA.emotions()[0].notes() == NOTES


def test_add_existing_dyadic(scene, view):
    personA = scene.addItem(Person(name="John", lastName="Doe"))
    view.set_kind(EventKind.Conflict)
    view.moversPicker.add_existing_person(personA)
    view.receiversPicker.add_new_person("Jane Doe")
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    personB = scene.query1(name="Jane", lastName="Doe")
    assert len(scene.people()) == 2
    assert len(personA.emotions()) == 1
    assert len(personB.emotions()) == 1
    assert personA.emotions() == personB.emotions()
    assert personA.emotions()[0].kind() == util.ITEM_CONFLICT
    assert personA.emotions()[0].startDateTime() == START_DATETIME
    assert personA.emotions()[0].endDateTime() == START_DATETIME


def test_add_multiple_dyadic_to_same_mover_different_receivers(scene, view):
    KIND_1 = EventKind.Conflict

    view.set_kind(KIND_1)
    view.moversPicker.add_new_person("John Doe")
    view.receiversPicker.add_new_person("Jane Doe")
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    personA = scene.query1(name="John", lastName="Doe")
    personB = scene.query1(name="Jane", lastName="Doe")
    assert len(scene.people()) == 2
    assert len(personA.emotions()) == 1
    assert len(personB.emotions()) == 1
    assert personA.emotions() == personB.emotions()
    assert personA.emotions()[0].kind() == util.ITEM_CONFLICT
    assert personA.emotions()[0].startDateTime() == START_DATETIME
    assert personA.emotions()[0].endDateTime() == START_DATETIME

    KIND_2 = EventKind.Away

    view.set_kind(KIND_2)
    view.moversPicker.add_existing_person(personA)
    view.receiversPicker.add_new_person("Josephine Doe")
    view.set_startDateTime(START_DATETIME.addDays(30))
    view.clickAddButton()
    personC = scene.query1(name="Josephine", lastName="Doe")
    assert len(scene.people()) == 3
    assert len(personA.emotions()) == 2
    assert len(personB.emotions()) == 1
    assert len(personC.emotions()) == 1
    assert personA.emotions()[0].kind() == util.ITEM_CONFLICT
    assert personA.emotions()[0].startDateTime() == START_DATETIME
    assert personA.emotions()[0].endDateTime() == START_DATETIME
    assert personA.emotions()[1].kind() == util.ITEM_AWAY
    assert personA.emotions()[1].startDateTime() == START_DATETIME.addDays(30)
    assert personA.emotions()[1].endDateTime() == START_DATETIME.addDays(30)


# @pytest.mark.parametrize("kind", [x for x in EventKind if EventKind.isPairBond(x)])
def test_add_existing_pairbond(scene, view):
    TAG_1, TAG_2 = "tag1", "tag2"
    KIND = EventKind.Separated

    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Jane", lastName="Doe"))
    marriage = scene.addItem(Marriage(personA, personB))
    view.set_kind(KIND)
    view.personAPicker.set_existing_person(personA)
    view.personBPicker.set_existing_person(personB)
    view.set_startDateTime(START_DATETIME)
    view.add_tag(TAG_1)
    view.add_tag(TAG_2)
    view.set_active_tags([TAG_1, TAG_2])
    view.clickAddButton()
    assert len(scene.people()) == 2
    assert personA.marriages == personB.marriages == [marriage]
    assert len(marriage.events()) == 1
    assert marriage.events()[0].uniqueId() == KIND.value
    assert marriage.events()[0].description() == EventKind.menuLabelFor(KIND)


def test_add_existing_pairbond_custom(scene, view):
    kind = EventKind.CustomPairBond
    DESCRIPTION = "Something Happened"

    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Jane", lastName="Doe"))
    marriage = scene.addItem(Marriage(personA, personB))
    view.set_kind(kind)
    view.personAPicker.set_existing_person(personA)
    view.personBPicker.set_existing_person(personB)
    view.set_description(DESCRIPTION)
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    assert len(scene.people()) == 2
    assert personA.marriages == personB.marriages == [marriage]
    assert len(marriage.events()) == 1
    assert marriage.events()[0].uniqueId() == None
    assert marriage.events()[0].description() == DESCRIPTION


def test_add_multiple_events_to_same_pairbond(scene, view):
    KIND_1 = EventKind.Separated

    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Jane", lastName="Doe"))
    marriage = scene.addItem(Marriage(personA, personB))
    view.set_kind(KIND_1)
    view.personAPicker.set_existing_person(personA)
    view.personBPicker.set_existing_person(personB)
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    assert len(scene.people()) == 2
    assert personA.marriages == personB.marriages == [marriage]
    assert len(marriage.events()) == 1
    assert marriage.events()[0].uniqueId() == KIND_1.value
    assert marriage.events()[0].description() == EventKind.menuLabelFor(KIND_1)

    KIND_2 = EventKind.Bonded

    view.clickClearButton()
    view.set_kind(KIND_2)
    view.personAPicker.set_existing_person(personA)
    view.personBPicker.set_existing_person(personB)
    view.set_startDateTime(START_DATETIME.addDays(-30))
    view.clickAddButton()
    assert len(scene.people()) == 2
    assert personA.marriages == personB.marriages == [marriage]
    assert len(marriage.events()) == 2
    assert marriage.events()[0].uniqueId() == KIND_2.value
    assert marriage.events()[0].description() == EventKind.menuLabelFor(KIND_2)
    assert marriage.events()[1].uniqueId() == KIND_1.value
    assert marriage.events()[1].description() == EventKind.menuLabelFor(KIND_1)


def test_add_new_variables_CustomIndividual(scene, view):
    personA = scene.addItem(Person(name="John", lastName="Doe"))
    view.set_kind(EventKind.CustomIndividual)
    view.peoplePicker.add_existing_person(personA)
    view.set_anxiety(util.VAR_VALUE_UP)
    view.set_functioning(util.VAR_FUNCTIONING_DOWN)
    view.set_symptom(util.VAR_SYMPTOM_SAME)
    view.set_description("Something happened")
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    dynamicPropertyNames = [entry["name"] for entry in scene.eventProperties()]
    assert dynamicPropertyNames == [
        util.ATTR_ANXIETY,
        util.ATTR_FUNCTIONING,
        util.ATTR_SYMPTOM,
    ]
    assert (
        personA.events()[0].dynamicProperty(util.ATTR_ANXIETY).get()
        == util.VAR_VALUE_UP
    )
    assert (
        personA.events()[0].dynamicProperty("functioning").get()
        == util.VAR_FUNCTIONING_DOWN
    )
    assert personA.events()[0].dynamicProperty("symptom").get() == util.VAR_SYMPTOM_SAME


def test_add_new_variables_PairBond(scene, view):
    view.set_kind(EventKind.Bonded)
    view.personAPicker.set_new_person("John Doe")
    view.personBPicker.set_new_person("Jane Doe")
    view.set_anxiety(util.VAR_VALUE_UP)
    view.set_functioning(util.VAR_FUNCTIONING_DOWN)
    view.set_symptom(util.VAR_SYMPTOM_SAME)
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    event = scene.events(onlyDated=True)[0]
    dynamicPropertyNames = [entry["name"] for entry in scene.eventProperties()]
    assert dynamicPropertyNames == [
        util.ATTR_ANXIETY,
        util.ATTR_FUNCTIONING,
        util.ATTR_SYMPTOM,
    ]
    assert event.dynamicProperty(util.ATTR_ANXIETY).get() == util.VAR_VALUE_UP
    assert (
        event.dynamicProperty(util.ATTR_FUNCTIONING).get() == util.VAR_FUNCTIONING_DOWN
    )
    assert event.dynamicProperty(util.ATTR_SYMPTOM).get() == util.VAR_SYMPTOM_SAME


def test_add_new_variables_Dyadic(scene, view):
    view.set_kind(EventKind.Conflict)
    view.moversPicker.add_new_person("John Doe")
    view.receiversPicker.add_new_person("Jane Doe")
    view.set_anxiety(util.VAR_VALUE_UP)
    view.set_functioning(util.VAR_FUNCTIONING_DOWN)
    view.set_symptom(util.VAR_SYMPTOM_SAME)
    view.set_description("Something happened")
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    symbol = scene.emotions()[0]
    startEvent = symbol.startEvent
    assert symbol.kind() == EventKind.itemModeFor(EventKind.Conflict)
    dynamicPropertyNames = [entry["name"] for entry in scene.eventProperties()]
    assert dynamicPropertyNames == [
        util.ATTR_ANXIETY,
        util.ATTR_FUNCTIONING,
        util.ATTR_SYMPTOM,
    ]
    assert startEvent.dynamicProperty(util.ATTR_ANXIETY).get() == util.VAR_VALUE_UP
    assert (
        startEvent.dynamicProperty(util.ATTR_FUNCTIONING).get()
        == util.VAR_FUNCTIONING_DOWN
    )
    assert startEvent.dynamicProperty(util.ATTR_SYMPTOM).get() == util.VAR_SYMPTOM_SAME
