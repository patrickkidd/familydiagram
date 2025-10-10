import pytest

from pkdiagram import util
from pkdiagram.scene import EventKind, Person, Marriage


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
    view.addEvent([person])
    assert view.item.property("kind") == None
    personEntry = view.view.personEntry()
    assert personEntry["person"] == person
    assert personEntry["gender"] == util.PERSON_KIND_FEMALE


def test_init_with_pairbond_people_selected(scene, view):
    person = Person(name="Joseph", lastName="Donner")
    spouse = Person(name="Josephina", lastName="Donner")
    marriage = Marriage(personA=person, personB=spouse)
    scene.addItems(person, spouse, marriage)
    view.addEvent([person, spouse])
    assert view.item.property("kind") == None
    assert view.personPicker.item.property("person") == person
    assert view.spousePicker.item.property("person") == None


def test_init_with_pairbond_selected(scene, view):
    person = Person(name="Joseph", lastName="Donner")
    spouse = Person(name="Josephina", lastName="Donner")
    marriage = Marriage(personA=person, personB=spouse)
    scene.addItems(person, spouse, marriage)
    view.addEvent([marriage])
    assert view.item.property("kind") == None
    assert view.personPicker.item.property("person") == person
    assert view.spousePicker.item.property("person") == None


def test_init_with_individuals_selected(scene, view):
    personA = Person(name="Joseph", lastName="Donner")
    personB = Person(name="Josephina", lastName="Donner")
    personC = Person(name="Josephine", lastName="Donner")
    personD = Person(name="Josephine", lastName="Donner")
    scene.addItems(personA, personB, personC, personD)
    view.addEvent([personA, personB, personC])
    assert view.item.property("kind") == None
    assert view.view.personEntry()["person"] == personA
