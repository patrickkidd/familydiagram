import pytest
from mock import patch

from pkdiagram.pyqt import QMessageBox
from pkdiagram import util
from pkdiagram.scene import (
    EventKind,
    RelationshipKind,
    Person,
    Event,
    Marriage,
    Emotion,
    ItemMode,
)
from pkdiagram.views.eventform import EventForm

from .test_eventform import view, START_DATETIME, END_DATETIME


@pytest.fixture(autouse=True)
def variables(scene):
    scene.addEventProperty(util.ATTR_SYMPTOM)
    scene.addEventProperty(util.ATTR_ANXIETY)
    scene.addEventProperty(util.ATTR_RELATIONSHIP)
    scene.addEventProperty(util.ATTR_FUNCTIONING)


def test_init_Birth(scene, view):
    person = scene.addItem(Person(name="John Doe"))
    event = scene.addItem(Event(EventKind.Birth, person, dateTime=START_DATETIME))
    event.setLocation("Old Location")
    event.setNotes("Old Notes")

    view.view.editEvents([event])
    assert view.item.property("kindBox").property("enabled") == False
    assert view.view.personEntry()["person"] == person
    assert view.item.property("kind") == EventKind.Birth.value
    assert view.item.property("startDateTime") == START_DATETIME
    assert view.item.property("location") == "Old Location"
    assert view.item.property("notes") == "Old Notes"


def test_init_Death(scene, view):
    person = scene.addItem(Person(name="John Doe"))
    event = scene.addItem(Event(EventKind.Death, person, dateTime=START_DATETIME))
    event.setLocation("Old Location")
    event.setNotes("Old Notes")

    view.view.editEvents([event])
    assert view.view.personEntry()["person"] == person
    assert view.item.property("kind") == EventKind.Death.value
    assert view.item.property("startDateTime") == START_DATETIME
    assert view.item.property("location") == "Old Location"
    assert view.item.property("notes") == "Old Notes"


def test_init_Shift(scene, view):
    mother = scene.addItem(Person(name="Mother"))
    event = scene.addItem(
        Event(
            EventKind.Shift,
            mother,
            dateTime=START_DATETIME,
        )
    )
    event.setLocation("Some Location")
    event.setNotes("Some Notes")
    event.setDescription("Some Description")
    view.view.editEvents([event])
    assert view.item.property("kind") == EventKind.Shift.value
    assert view.view.personEntry()["person"] == mother
    assert view.view.targetsEntries() == []
    assert view.view.trianglesEntries() == []
    assert view.item.property("description") == "Some Description"
    assert view.item.property("startDateTime") == START_DATETIME
    assert view.item.property("location") == "Some Location"
    assert view.item.property("notes") == "Some Notes"


def test_init_Shift_Conflict(scene, view):
    mother, father = scene.addItems(Person(name="Mother"), Person(name="Father"))
    conflictEvent = scene.addItem(
        Event(
            EventKind.Shift,
            mother,
            relationship=RelationshipKind.Conflict,
            relationshipTargets=[father],
            dateTime=START_DATETIME,
            endDateTime=END_DATETIME,
        )
    )
    conflictEvent.setLocation("Some Location")
    conflictEvent.setNotes("Some Notes")
    conflictEvent.setDescription("Conflict began")
    conflict = scene.emotionsFor(conflictEvent)[0]
    view.view.editEvents([conflictEvent])
    util.waitALittle()
    assert view.view.personEntry()["person"] == mother
    assert view.view.targetsEntries()[0]["person"] == father
    assert view.item.property("kind") == EventKind.Shift.value
    assert view.item.property("relationship") == RelationshipKind.Conflict.value
    assert view.item.property("description") == "Conflict began"
    assert view.item.property("startDateTime") == START_DATETIME
    assert view.item.property("location") == "Some Location"
    assert view.item.property("notes") == "Some Notes"


def test_init_Shift_Triangle(scene, view):
    mother, father, lover = scene.addItems(
        Person(name="Mother"), Person(name="Father"), Person(name="Lover")
    )
    triangleEvent = scene.addItem(
        Event(
            EventKind.Shift,
            mother,
            relationship=RelationshipKind.Inside,
            relationshipTargets=[lover],
            relationshipTriangles=[father],
            dateTime=START_DATETIME,
            endDateTime=END_DATETIME,
        )
    )
    triangle = scene.emotionsFor(triangleEvent)[0]
    view.view.editEvents([triangleEvent])
    util.waitALittle()
    assert view.view.personEntry()["person"] == mother
    assert view.view.targetsEntries()[0]["person"] == lover
    assert view.view.trianglesEntries()[0]["person"] == father
    assert view.item.property("kind") == EventKind.Shift.value
    assert view.item.property("relationship") == RelationshipKind.Inside.value
    assert view.item.property("startDateTime") == START_DATETIME
    assert view.item.property("endDateTime") == END_DATETIME
    assert view.item.property("isDateRange") is True


@pytest.mark.parametrize("kind", [EventKind.Birth, EventKind.Adopted])
def test_edit_isPerson(scene, view, kind):
    person, spouse, child = scene.addItems(
        Person(name="John Doe"), Person(name="Jane Doe"), Person(name="Child")
    )
    marriage = scene.addItem(Marriage(person, spouse))
    event = scene.addItem(
        Event(kind, person, spouse=spouse, child=child, dateTime=START_DATETIME)
    )
    view.view.editEvents([event])
    view.set_location("New Location")
    view.set_notes("New Notes")
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()

    assert len(scene.eventsFor(marriage)) == 1
    assert event.kind() == kind
    assert event.description() == kind.name
    assert event.location() == "New Location"
    assert event.notes() == "New Notes"
    assert event.dateTime() == START_DATETIME


def test_edit_Death(scene, view):
    person = scene.addItem(Person(name="John Doe"))
    event = scene.addItem(Event(EventKind.Death, person, dateTime=START_DATETIME))
    view.view.editEvents([event])
    view.set_location("New Location")
    view.set_notes("New Notes")
    view.set_startDateTime(START_DATETIME)
    with patch(
        "PyQt5.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes
    ) as question:
        view.clickSaveButton()
        assert question.call_args[0][2] == EventForm.S_REPLACE_EXISTING.format(
            n_existing=1, kind=EventKind.Death.name
        )

    assert len(scene.eventsFor(person)) == 1
    assert event.kind() == EventKind.Death
    assert event.description() == None
    assert event.location() == "New Location"
    assert event.notes() == "New Notes"
    assert event.dateTime() == START_DATETIME


@pytest.mark.parametrize(
    "kind",
    [EventKind.Bonded, EventKind.Married, EventKind.Separated, EventKind.Divorced],
)
def test_edit_isPairBond(scene, view, kind: EventKind):
    person, spouse = scene.addItems(Person(name="John Doe"), Person(name="Jane Doe"))
    marriage = scene.addItem(Marriage(person, spouse))
    event = scene.addItem(Event(kind, person))
    event.setSpouse(spouse)
    event.setRelationshipTargets([spouse])
    view.view.editEvents([event])
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()

    # assert len(person.events()) == 1
    assert event.kind() == kind
    assert event.dateTime() == START_DATETIME
    assert event.person() == person
    assert event.spouse() == spouse
