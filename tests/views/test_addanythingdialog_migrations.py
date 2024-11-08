import logging

import pytest

from pkdiagram import EventKind, Person
from pkdiagram.widgets.qml.peoplepicker import waitForPersonPickers

from .test_addanythingdialog import scene, dlg

_log = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.component("AddAnythingDialog"),
    pytest.mark.depends_on("Scene"),
]


@pytest.mark.parametrize(
    "kind",
    [
        EventKind.CustomIndividual,
        EventKind.Married,
        EventKind.Conflict,
        EventKind.Adopted,
    ],
)
def test_migrate_from_birth(scene, dlg, kind):
    personA = scene.addItem(Person(name="Joseph", lastName="Donner"))
    personB = scene.addItem(Person(name="Josephina", lastName="Donner"))
    personC = scene.addItem(Person(name="Josephine", lastName="Donner"))
    dlg.set_kind(EventKind.Birth)
    dlg.set_existing_person("personPicker", personA)
    dlg.set_existing_person("personAPicker", personB)
    dlg.set_existing_person("personBPicker", personC)
    dlg.set_kind(kind)
    waitForPersonPickers()
    if kind == EventKind.CustomIndividual:
        assert {x["person"].id for x in dlg.peopleEntries()} == {
            personA.id,
            personB.id,
            personC.id,
        }
    elif kind == EventKind.Married:
        assert dlg.personAEntry()["person"] == personA
        assert dlg.personBEntry()["person"] == personB
    elif kind == EventKind.Conflict:
        assert {x["person"].id for x in dlg.moverEntries()} == {personA.id}
        assert {x["person"].id for x in dlg.receiverEntries()} == {
            personB.id,
            personC.id,
        }
    elif kind == EventKind.Adopted:
        assert dlg.personEntry()["person"] == personA
        assert dlg.itemProp("personAPicker", "isSubmitted") == False
        assert dlg.itemProp("personBPicker", "isSubmitted") == False


@pytest.mark.parametrize(
    "kind", [EventKind.Birth, EventKind.Married, EventKind.Conflict]
)
def test_migrate_from_custom_individual(scene, dlg, kind):
    personA = scene.addItem(Person(name="Joseph", lastName="Donner"))
    personB = scene.addItem(Person(name="Josephina", lastName="Donner"))
    personC = scene.addItem(Person(name="Josephine", lastName="Donner"))
    dlg.set_kind(EventKind.CustomIndividual)
    dlg.add_existing_person("peoplePicker", personA)
    dlg.add_existing_person("peoplePicker", personB)
    dlg.add_existing_person("peoplePicker", personC)
    dlg.set_kind(kind)
    waitForPersonPickers()
    if kind == EventKind.Birth:
        assert dlg.personEntry()["person"] == personA
        assert dlg.personAEntry()["person"] == personB
        assert dlg.personBEntry()["person"] == personC
    elif kind == EventKind.Married:
        assert dlg.personAEntry()["person"] == personA
        assert dlg.personBEntry()["person"] == personB
    elif kind == EventKind.Conflict:
        assert {x["person"].id for x in dlg.moverEntries()} == {personA.id}
        assert {x["person"].id for x in dlg.receiverEntries()} == {
            personB.id,
            personC.id,
        }


@pytest.mark.parametrize(
    "kind",
    [
        EventKind.Birth,
        EventKind.CustomIndividual,
        EventKind.Conflict,
        EventKind.Separated,
    ],
)
def test_migrate_from_pairbond(scene, dlg, kind):
    personA = scene.addItem(Person(name="Joseph", lastName="Donner"))
    personB = scene.addItem(Person(name="Josephina", lastName="Donner"))
    dlg.set_kind(EventKind.Married)
    dlg.set_existing_person("personAPicker", personA)
    dlg.set_existing_person("personBPicker", personB)
    dlg.set_kind(kind)
    waitForPersonPickers()
    if kind == EventKind.Birth:
        assert dlg.personEntry()["person"] == personA
        assert dlg.personAEntry()["person"] == personB
        assert dlg.personBEntry()["person"] == None
    elif kind == EventKind.CustomIndividual:
        assert {x["person"].id for x in dlg.peopleEntries()} == {
            personA.id,
            personB.id,
        }
    elif kind == EventKind.Conflict:
        assert {x["person"].id for x in dlg.moverEntries()} == {personA.id}
        assert {x["person"].id for x in dlg.receiverEntries()} == {personB.id}
    elif kind == EventKind.Separated:
        assert dlg.personAEntry()["person"] == personA
        assert dlg.personBEntry()["person"] == personB


@pytest.mark.parametrize(
    "kind",
    [EventKind.Birth, EventKind.CustomIndividual, EventKind.Married, EventKind.Away],
)
def test_migrate_from_dyadic(scene, dlg, kind):
    personA = scene.addItem(Person(name="Joseph", lastName="Donner"))
    personB = scene.addItem(Person(name="Josephina", lastName="Donner"))
    personC = scene.addItem(Person(name="Josephine", lastName="Donner"))
    dlg.set_kind(EventKind.Conflict)
    dlg.add_existing_person("moversPicker", personA)
    dlg.add_existing_person("moversPicker", personB)
    dlg.add_existing_person("receiversPicker", personC)
    dlg.set_kind(kind)
    waitForPersonPickers()
    if kind == EventKind.Birth:
        assert dlg.personEntry()["person"] == personA
        assert dlg.personAEntry()["person"] == personB
        assert dlg.personBEntry()["person"] == None
    elif kind == EventKind.CustomIndividual:
        assert {x["person"].id for x in dlg.peopleEntries()} == {
            personA.id,
            personB.id,
        }
    elif kind == EventKind.Married:
        assert dlg.personAEntry()["person"] == personA
        assert dlg.personBEntry()["person"] == personB
    elif kind == EventKind.Away:
        assert {x["person"].id for x in dlg.moverEntries()} == {personA.id, personB.id}
        assert {x["person"].id for x in dlg.receiverEntries()} == {personC.id}
