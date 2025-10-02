import pytest

from pkdiagram import util
from pkdiagram.scene import EventKind, Person, Marriage


from .test_addanythingdialog import view


pytestmark = [
    pytest.mark.component("AddAnythingDialog"),
    pytest.mark.depends_on("Scene"),
]

START_DATETIME = util.Date(2001, 1, 1, 6, 7)
END_DATETIME = util.Date(2002, 1, 1, 6, 7)
ONE_NAME = "John Doe"

DEPENDS = pytest.mark.depends_on("PersonPicker", "PeoplePicker", "DatePicker")


def test_init_no_selection(view):
    assert [i for i in view.kindBox.property("model")] == EventKind.menuLabels()
    assert view.item.property("kind") == None


def test_init_with_existing_person(scene, view):
    assert [i for i in view.kindBox.property("model")] == EventKind.menuLabels()
    person = scene.addItem(
        Person(name="Joseph", lastName="Donner", gender=util.PERSON_KIND_FEMALE)
    )
    view.initForSelection([person])
    peopleEntries = view.item.peopleEntries().toVariant()
    assert view.item.property("kind") == EventKind.CustomIndividual.value
    assert len(peopleEntries) == 1
    assert peopleEntries[0]["person"] == person
    assert peopleEntries[0]["gender"] == util.PERSON_KIND_FEMALE


def test_init_with_pairbond_people_selected(scene, view):
    personA = Person(name="Joseph", lastName="Donner")
    personB = Person(name="Josephina", lastName="Donner")
    marriage = Marriage(personA=personA, personB=personB)
    scene.addItems(personA, personB, marriage)
    view.initForSelection([personA, personB])
    assert view.item.property("kind") == EventKind.CustomPairBond.value
    assert view.personAPicker.item.property("person") == personA
    assert view.personBPicker.item.property("person") == personB


def test_init_with_pairbond_selected(scene, view):
    personA = Person(name="Joseph", lastName="Donner")
    personB = Person(name="Josephina", lastName="Donner")
    marriage = Marriage(personA=personA, personB=personB)
    scene.addItems(personA, personB, marriage)
    view.initForSelection([marriage])
    assert view.item.property("kind") == EventKind.CustomPairBond.value
    assert view.personAPicker.item.property("person") == personA
    assert view.personBPicker.item.property("person") == personB


def test_init_with_individuals_selected(scene, view):
    personA = Person(name="Joseph", lastName="Donner")
    personB = Person(name="Josephina", lastName="Donner")
    personC = Person(name="Josephine", lastName="Donner")
    personD = Person(name="Josephine", lastName="Donner")
    scene.addItems(personA, personB, personC, personD)
    view.initForSelection([personA, personB, personC])
    assert view.item.property("kind") == EventKind.CustomIndividual.value
    assert {x["person"].id for x in view.item.peopleEntries().toVariant()} == {
        personA.id,
        personB.id,
        personC.id,
    }
