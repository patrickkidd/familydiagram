import pytest

from btcopilot.schema import EventKind, RelationshipKind
from pkdiagram import util
from pkdiagram.scene import Event, Person, Marriage


from .test_eventform import view


pytestmark = [
    pytest.mark.component("EventForm"),
    pytest.mark.depends_on("Scene"),
]

START_DATETIME = util.Date(2001, 1, 1, 6, 7)
END_DATETIME = util.Date(2002, 1, 1, 6, 7)
ONE_NAME = "John Doe"

DEPENDS = pytest.mark.depends_on("PersonPicker", "PeoplePicker", "DatePicker")


def test_init_no_selection(view):
    assert view.item.property("kind") == None
    assert view.view.personEntry() == None


def test_init_with_existing_person(scene, view):
    person = scene.addItem(
        Person(name="Joseph", lastName="Donner", gender=util.PERSON_KIND_FEMALE)
    )
    view.view.addEvent([person])
    assert view.item.property("kind") == None
    personEntry = view.view.personEntry()
    assert personEntry["person"] == person
    assert personEntry["gender"] == util.PERSON_KIND_FEMALE


def test_init_with_pairbond_people_selected(scene, view):
    person, spouse = scene.addItems(
        Person(name="Joseph", lastName="Donner"),
        Person(name="Josephina", lastName="Donner"),
    )
    marriage = scene.addItem(Marriage(personA=person, personB=spouse))
    view.view.addEvent([person, spouse])
    assert view.item.property("kind") == None
    assert view.personPicker.item.property("person") == person
    assert view.spousePicker.item.property("person") == None


def test_init_with_pairbond_selected(scene, view):
    person, spouse = scene.addItems(
        Person(name="Joseph", lastName="Donner"),
        Person(name="Josephina", lastName="Donner"),
    )
    marriage = scene.addItem(Marriage(personA=person, personB=spouse))
    view.view.addEvent([marriage])
    assert view.item.property("kind") == None
    assert view.personPicker.item.property("person") == person
    assert view.spousePicker.item.property("person") == None


def test_init_with_individuals_selected(scene, view):
    personA, personB, personC, personD = scene.addItems(
        Person(name="Joseph", lastName="Donner"),
        Person(name="Josephina", lastName="Donner"),
        Person(name="Josephine", lastName="Donner"),
        Person(name="Josephine", lastName="Donner"),
    )
    view.view.addEvent([personA, personB, personC])
    assert view.item.property("kind") == None
    assert view.view.personEntry()["person"] == personA


def test_init_Shift(scene, view):
    person, target = scene.addItems(Person(name="person"), Person(name="target"))
    event = scene.addItem(
        Event(
            EventKind.Shift,
            person=person,
            relationship=RelationshipKind.Conflict,
            relationshipTargets=[target],
        )
    )
    view.view.editEvents([event])
    util.waitALittle()
    assert view.item.property("kind") == EventKind.Shift.value
    assert view.view.personEntry()["person"] == person
    assert view.item.property("relationship") == RelationshipKind.Conflict.value
    assert view.relationshipField.property("value") == RelationshipKind.Conflict.value
    assert view.view.targetsEntries() == [
        {
            "gender": "male",
            "person": target,
            "isNewPerson": False,
            "personName": "target",
        }
    ]
