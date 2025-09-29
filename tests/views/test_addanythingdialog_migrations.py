import logging

import pytest

from pkdiagram.scene import LifeChange, Person

from tests.widgets import waitForPersonPickers
from tests.views.test_addanythingdialog import view

_log = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.component("AddAnythingDialog"),
    pytest.mark.depends_on("Scene"),
]


@pytest.mark.parametrize(
    "kind",
    [
        LifeChange.CustomIndividual,
        LifeChange.Married,
        LifeChange.Conflict,
        LifeChange.Adopted,
    ],
)
def test_migrate_from_birth(scene, view, kind):
    personA = scene.addItem(Person(name="Joseph", lastName="Donner"))
    personB = scene.addItem(Person(name="Josephina", lastName="Donner"))
    personC = scene.addItem(Person(name="Josephine", lastName="Donner"))
    view.set_kind(LifeChange.Birth)
    view.personPicker.set_existing_person(personA)
    view.personAPicker.set_existing_person(personB)
    view.personBPicker.set_existing_person(personC)
    view.set_kind(kind)
    waitForPersonPickers()
    if kind == LifeChange.CustomIndividual:
        assert {x["person"].id for x in view.item.peopleEntries().toVariant()} == {
            personA.id,
            personB.id,
            personC.id,
        }
    elif kind == LifeChange.Married:
        assert view.item.personAEntry().toVariant()["person"] == personA
        assert view.item.personBEntry().toVariant()["person"] == personB
    elif kind == LifeChange.Conflict:
        assert {x["person"].id for x in view.item.moverEntries().toVariant()} == {
            personA.id
        }
        assert {x["person"].id for x in view.item.receiverEntries().toVariant()} == {
            personB.id,
            personC.id,
        }
    elif kind == LifeChange.Adopted:
        assert view.item.personEntry().toVariant()["person"] == personA
        assert view.personAPicker.item.property("isSubmitted") == False
        assert view.personBPicker.item.property("isSubmitted") == False


@pytest.mark.parametrize(
    "kind", [LifeChange.Birth, LifeChange.Married, LifeChange.Conflict]
)
def test_migrate_from_custom_individual(scene, view, kind):
    personA = scene.addItem(Person(name="Joseph", lastName="Donner"))
    personB = scene.addItem(Person(name="Josephina", lastName="Donner"))
    personC = scene.addItem(Person(name="Josephine", lastName="Donner"))
    view.set_kind(LifeChange.CustomIndividual)
    view.peoplePicker.add_existing_person(personA)
    view.peoplePicker.add_existing_person(personB)
    view.peoplePicker.add_existing_person(personC)
    view.set_kind(kind)
    waitForPersonPickers()
    if kind == LifeChange.Birth:
        assert view.item.personEntry().toVariant()["person"] == personA
        assert view.item.personAEntry().toVariant()["person"] == personB
        assert view.item.personBEntry().toVariant()["person"] == personC
    elif kind == LifeChange.Married:
        assert view.item.personAEntry().toVariant()["person"] == personA
        assert view.item.personBEntry().toVariant()["person"] == personB
    elif kind == LifeChange.Conflict:
        assert {x["person"].id for x in view.item.moverEntries().toVariant()} == {
            personA.id
        }
        assert {x["person"].id for x in view.item.receiverEntries().toVariant()} == {
            personB.id,
            personC.id,
        }


@pytest.mark.parametrize(
    "kind",
    [
        LifeChange.Birth,
        LifeChange.CustomIndividual,
        LifeChange.Conflict,
        LifeChange.Separated,
    ],
)
def test_migrate_from_pairbond(scene, view, kind):
    personA = scene.addItem(Person(name="Joseph", lastName="Donner"))
    personB = scene.addItem(Person(name="Josephina", lastName="Donner"))
    view.set_kind(LifeChange.Married)
    view.personAPicker.set_existing_person(personA)
    view.personBPicker.set_existing_person(personB)
    view.set_kind(kind)
    waitForPersonPickers()
    if kind == LifeChange.Birth:
        assert view.item.personEntry().toVariant()["person"] == personA
        assert view.item.personAEntry().toVariant()["person"] == personB
        assert view.item.personBEntry().toVariant()["person"] == None
    elif kind == LifeChange.CustomIndividual:
        assert {x["person"].id for x in view.item.peopleEntries().toVariant()} == {
            personA.id,
            personB.id,
        }
    elif kind == LifeChange.Conflict:
        assert {x["person"].id for x in view.item.moverEntries().toVariant()} == {
            personA.id
        }
        assert {x["person"].id for x in view.item.receiverEntries().toVariant()} == {
            personB.id
        }
    elif kind == LifeChange.Separated:
        assert view.item.personAEntry().toVariant()["person"] == personA
        assert view.item.personBEntry().toVariant()["person"] == personB


@pytest.mark.parametrize(
    "kind",
    [
        LifeChange.Birth,
        LifeChange.CustomIndividual,
        LifeChange.Married,
        LifeChange.Away,
    ],
)
def test_migrate_from_dyadic(scene, view, kind):
    personA = scene.addItem(Person(name="Joseph", lastName="Donner"))
    personB = scene.addItem(Person(name="Josephina", lastName="Donner"))
    personC = scene.addItem(Person(name="Josephine", lastName="Donner"))
    view.set_kind(LifeChange.Conflict)
    view.moversPicker.add_existing_person(personA)
    view.moversPicker.add_existing_person(personB)
    view.receiversPicker.add_existing_person(personC)
    view.set_kind(kind)
    waitForPersonPickers()
    if kind == LifeChange.Birth:
        assert view.item.personEntry().toVariant()["person"] == personA
        assert view.item.personAEntry().toVariant()["person"] == personB
        assert view.item.personBEntry().toVariant()["person"] == None
    elif kind == LifeChange.CustomIndividual:
        assert {x["person"].id for x in view.item.peopleEntries().toVariant()} == {
            personA.id,
            personB.id,
        }
    elif kind == LifeChange.Married:
        assert view.item.personAEntry().toVariant()["person"] == personA
        assert view.item.personBEntry().toVariant()["person"] == personB
    elif kind == LifeChange.Away:
        assert {x["person"].id for x in view.item.moverEntries().toVariant()} == {
            personA.id,
            personB.id,
        }
        assert {x["person"].id for x in view.item.receiverEntries().toVariant()} == {
            personC.id
        }
