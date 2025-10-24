import logging

import pytest

from btcopilot.schema import EventKind
from pkdiagram.scene import Person

from tests.widgets import waitForPersonPickers
from tests.views.eventform.test_eventform import view

_log = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.component("EventForm"),
    pytest.mark.depends_on("Scene"),
]


pytest.skip(
    reason="Migrations not implemented yet, may never be", allow_module_level=True
)


@pytest.mark.parametrize(
    "kind",
    [
        EventKind.Married,
        EventKind.Adopted,
    ],
)
def test_migrate_from_birth(scene, view, kind):
    personA = scene.addItem(Person(name="Joseph", lastName="Donner"))
    personB = scene.addItem(Person(name="Josephina", lastName="Donner"))
    personC = scene.addItem(Person(name="Josephine", lastName="Donner"))
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(personA)
    view.personAPicker.set_existing_person(personB)
    view.personBPicker.set_existing_person(personC)
    view.set_kind(kind)
    waitForPersonPickers()
    # if kind == EventKind.CustomIndividual:
    #     assert {x["person"].id for x in view.item.peopleEntries().toVariant()} == {
    #         personA.id,
    #         personB.id,
    #         personC.id,
    #     }
    if kind == EventKind.Married:
        assert view.item.personAEntry().toVariant()["person"] == personA
        assert view.item.personBEntry().toVariant()["person"] == personB
    # elif kind == EventKind.Conflict:
    #     assert {x["person"].id for x in view.item.moverEntries().toVariant()} == {
    #         personA.id
    #     }
    #     assert {x["person"].id for x in view.item.receiverEntries().toVariant()} == {
    #         personB.id,
    #         personC.id,
    #     }
    elif kind == EventKind.Adopted:
        assert view.item.personEntry().toVariant()["person"] == personA
        assert view.personAPicker.item.property("isSubmitted") == False
        assert view.personBPicker.item.property("isSubmitted") == False


@pytest.mark.parametrize("lifeChange", [EventKind.Birth, EventKind.Married])
def test_migrate_from_custom_individual(scene, view, lifeChange):
    personA = scene.addItem(Person(name="Joseph", lastName="Donner"))
    personB = scene.addItem(Person(name="Josephina", lastName="Donner"))
    personC = scene.addItem(Person(name="Josephine", lastName="Donner"))
    view.set_kind(EventKind.CustomIndividual)
    view.peoplePicker.add_existing_person(personA)
    view.peoplePicker.add_existing_person(personB)
    view.peoplePicker.add_existing_person(personC)
    view.set_kind(kind)
    waitForPersonPickers()
    if kind == EventKind.Birth:
        assert view.item.personEntry().toVariant()["person"] == personA
        assert view.item.personAEntry().toVariant()["person"] == personB
        assert view.item.personBEntry().toVariant()["person"] == personC
    elif kind == EventKind.Married:
        assert view.item.personAEntry().toVariant()["person"] == personA
        assert view.item.personBEntry().toVariant()["person"] == personB
    # elif kind == EventKind.Conflict:
    #     assert {x["person"].id for x in view.item.moverEntries().toVariant()} == {
    #         personA.id
    #     }
    #     assert {x["person"].id for x in view.item.receiverEntries().toVariant()} == {
    #         personB.id,
    #         personC.id,
    #     }


@pytest.mark.parametrize(
    "kind",
    [
        EventKind.Birth,
        # EventKind.CustomIndividual,
        # EventKind.Conflict,
        EventKind.Separated,
    ],
)
def test_migrate_from_pairbond(scene, view, kind):
    personA = scene.addItem(Person(name="Joseph", lastName="Donner"))
    personB = scene.addItem(Person(name="Josephina", lastName="Donner"))
    view.set_kind(EventKind.Married)
    view.personAPicker.set_existing_person(personA)
    view.personBPicker.set_existing_person(personB)
    view.set_kind(kind)
    waitForPersonPickers()
    if kind == EventKind.Birth:
        assert view.item.personEntry().toVariant()["person"] == personA
        assert view.item.personAEntry().toVariant()["person"] == personB
        assert view.item.personBEntry().toVariant()["person"] == None
    elif kind == EventKind.CustomIndividual:
        assert {x["person"].id for x in view.item.peopleEntries().toVariant()} == {
            personA.id,
            personB.id,
        }
    elif kind == EventKind.Conflict:
        assert {x["person"].id for x in view.item.moverEntries().toVariant()} == {
            personA.id
        }
        assert {x["person"].id for x in view.item.receiverEntries().toVariant()} == {
            personB.id
        }
    elif kind == EventKind.Separated:
        assert view.item.personAEntry().toVariant()["person"] == personA
        assert view.item.personBEntry().toVariant()["person"] == personB


@pytest.mark.parametrize(
    "kind",
    [
        EventKind.Birth,
        EventKind.Married,
    ],
)
def test_migrate_from_dyadic(scene, view, kind):
    personA = scene.addItem(Person(name="Joseph", lastName="Donner"))
    personB = scene.addItem(Person(name="Josephina", lastName="Donner"))
    personC = scene.addItem(Person(name="Josephine", lastName="Donner"))
    view.set_kind(EventKind.Conflict)
    view.moversPicker.add_existing_person(personA)
    view.moversPicker.add_existing_person(personB)
    view.receiversPicker.add_existing_person(personC)
    view.set_kind(kind)
    waitForPersonPickers()
    if kind == EventKind.Birth:
        assert view.item.personEntry().toVariant()["person"] == personA
        assert view.item.personAEntry().toVariant()["person"] == personB
        assert view.item.personBEntry().toVariant()["person"] == None
    elif kind == EventKind.CustomIndividual:
        assert {x["person"].id for x in view.item.peopleEntries().toVariant()} == {
            personA.id,
            personB.id,
        }
    elif kind == EventKind.Married:
        assert view.item.personAEntry().toVariant()["person"] == personA
        assert view.item.personBEntry().toVariant()["person"] == personB
    elif kind == EventKind.Away:
        assert {x["person"].id for x in view.item.moverEntries().toVariant()} == {
            personA.id,
            personB.id,
        }
        assert {x["person"].id for x in view.item.receiverEntries().toVariant()} == {
            personC.id
        }
