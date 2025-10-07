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
    event = scene.addItem(
        Event(person, kind=EventKind.Birth, description=EventKind.Birth.name)
    )
    event.setDateTime(START_DATETIME)
    event.setLocation("Old Location")
    event.setNotes("Old Notes")

    view.view.editEvents([event])
    assert view.item.property("kindBox").property("enabled") == False
    assert view.view.personEntry()["person"] == person
    assert view.item.property("kind") == EventKind.Birth
    assert view.item.property("startDateTime") == START_DATETIME
    assert view.item.property("location") == "Old Location"
    assert view.item.property("notes") == "Old Notes"


def test_init_Death(scene, view):
    person = scene.addItem(Person(name="John Doe"))
    event = scene.addItem(
        Event(person, kind=EventKind.Death, description=EventKind.Death.name)
    )
    event.setDateTime(START_DATETIME)
    event.setLocation("Old Location")
    event.setNotes("Old Notes")
    person.setDeceased(True)
    person.setDeceasedDateTime(START_DATETIME)

    view.view.editEvents([event])
    assert view.view.personEntry()["person"] == person
    assert view.item.property("kind") == EventKind.Death
    assert view.item.property("startDateTime") == START_DATETIME
    assert view.item.property("location") == "Old Location"
    assert view.item.property("notes") == "Old Notes"


def test_init_Shift(scene, view):
    mother = scene.addItem(Person(name="Mother"))
    event = scene.addItem(
        Event(
            parent=mother,
            kind=EventKind.Shift,
            location="Some Location",
            notes="Some Notes",
            dateTime=START_DATETIME,
        )
    )
    event.setDescription("Some Description")
    view.view.editEvents([event])
    assert view.item.property("kind") == EventKind.Shift
    assert view.view.personEntry()["person"] == mother
    assert view.view.targetsEntries() == []
    assert view.view.trianglesEntries() == []
    assert view.item.property("description") == "Some Description"
    assert view.item.property("startDateTime") == START_DATETIME
    assert view.item.property("location") == "Some Location"
    assert view.item.property("notes") == "Some Notes"


def test_init_Shift_Conflict(scene, view):
    mother = scene.addItem(Person(name="Mother"))
    father = scene.addItem(Person(name="Father"))
    conflict = scene.addItem(
        Emotion(
            kind=util.ITEM_CONFLICT,
            personA=mother,
            personB=father,
            startDateTime=START_DATETIME,
            endDateTime=END_DATETIME,
        )
    )
    conflict.startEvent.setLocation("Some Location")
    conflict.startEvent.setNotes("Some Notes")
    view.view.editEvents([conflict.startEvent])
    util.waitALittle()
    assert view.view.personEntry()["person"] == mother
    assert view.view.targetsEntries()[0]["person"] == father
    assert view.item.property("kind") == EventKind.Shift
    assert view.item.property("relationship") == RelationshipKind.Conflict
    assert view.item.property("description") == "Conflict began"
    assert view.item.property("startDateTime") == START_DATETIME
    assert view.item.property("location") == "Some Location"
    assert view.item.property("notes") == "Some Notes"


def test_init_Shift_Triangle(scene, view):
    mother = scene.addItem(Person(name="Mother"))
    father = scene.addItem(Person(name="Father"))
    lover = scene.addItem(Person(name="Lover"))
    triangle = scene.addItem(
        Emotion(
            kind=util.ITEM_INSIDE,
            personA=mother,
            personB=lover,
            personC=father,
            startDateTime=START_DATETIME,
            endDateTime=END_DATETIME,
        )
    )
    triangle.startEvent.setRelationshipTriangles([father])
    view.view.editEvents([triangle.startEvent])
    util.waitALittle()
    assert view.view.personEntry()["person"] == mother
    assert view.view.targetsEntries()[0]["person"] == lover
    assert view.view.trianglesEntries()[0]["person"] == father
    assert view.item.property("kind") == EventKind.Shift
    assert view.item.property("relationship") == RelationshipKind.Inside
    assert view.item.property("startDateTime") == START_DATETIME
    assert view.item.property("endDateTime") == END_DATETIME
    assert view.item.property("isDateRange") is True


@pytest.mark.parametrize("kind", [EventKind.Birth, EventKind.Adopted, EventKind.Death])
def test_edit_isPerson(scene, view, kind):
    person = scene.addItem(Person(name="John Doe"))
    event = None
    if kind == EventKind.Birth:
        event = person.birthEvent
    elif kind == EventKind.Adopted:
        event = person.adoptedEvent
        person.setAdopted(True)
    elif kind == EventKind.Death:
        event = person.deathEvent
        person.setDeceased(True)
    event.setDateTime(START_DATETIME)
    view.view.editEvents([event])
    view.set_location("New Location")
    view.set_notes("New Notes")
    view.set_startDateTime(START_DATETIME)
    if kind == EventKind.Death:
        with patch(
            "PyQt5.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes
        ) as question:
            view.clickSaveButton()
            assert question.call_args[0][2] == EventForm.S_REPLACE_EXISTING.format(
                n_existing=1, kind=EventKind.Death.name
            )
    else:
        view.clickSaveButton()

    assert len(person.events()) == 1
    assert event.kind() == kind
    assert event.description() == kind.name
    assert event.location() == "New Location"
    assert event.notes() == "New Notes"
    assert event.dateTime() == START_DATETIME


@pytest.mark.parametrize(
    "kind",
    [EventKind.Bonded, EventKind.Married, EventKind.Separated, EventKind.Divorced],
)
@pytest.mark.parametrize("legacy", [False, True])
def test_edit_isPairBond(scene, view, kind: EventKind, legacy: bool):
    person = scene.addItem(Person(name="John Doe"))
    spouse = scene.addItem(Person(name="Jane Doe"))
    marriage = scene.addItem(Marriage(person, spouse))
    if legacy:
        event = scene.addItem(Event(marriage, kind=kind))
    else:
        event = scene.addItem(Event(person, kind=kind))
        event.setSpouse(spouse)
    event.setRelationshipTargets([spouse])
    view.view.editEvents([event])
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()

    # assert len(person.events()) == 1
    assert event.kind() == kind
    assert event.dateTime() == START_DATETIME
    if legacy:
        assert event.parent == marriage
        assert event.parent.personA() == person
        assert event.parent.personB() == spouse
    else:
        assert event.parent == person
        assert event.spouse() == spouse
