import logging

import pytest
import mock

from pkdiagram import util
from pkdiagram.scene import Person, Marriage, EventKind


from .test_addanythingdialog import dlg

_log = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.component("AddAnythingDialog"),
    pytest.mark.depends_on("Scene"),
]


def test_init_no_selection(dlg):
    assert [
        i for i in dlg.findItem("kindBox").property("model")
    ] == EventKind.menuLabels()
    assert dlg.rootProp("kind") == None


def test_init_with_existing_person(scene, dlg):
    assert [
        i for i in dlg.findItem("kindBox").property("model")
    ] == EventKind.menuLabels()
    person = scene.addItem(
        Person(name="Joseph", lastName="Donner", gender=util.PERSON_KIND_FEMALE)
    )
    dlg.test_initForSelection([person])
    peopleEntries = dlg.peopleEntries()
    assert dlg.rootProp("kind") == EventKind.CustomIndividual.value
    assert len(peopleEntries) == 1
    assert peopleEntries[0]["person"] == person
    assert peopleEntries[0]["gender"] == util.PERSON_KIND_FEMALE


def test_init_with_pairbond_people_selected(dlg):
    personA = Person(name="Joseph", lastName="Donner")
    personB = Person(name="Josephina", lastName="Donner")
    marriage = Marriage(personA=personA, personB=personB)
    dlg.scene.addItems(personA, personB, marriage)
    dlg.test_initForSelection([personA, personB])
    assert dlg.rootProp("kind") == EventKind.CustomPairBond.value
    assert dlg.itemProp("personAPicker", "person") == personA
    assert dlg.itemProp("personBPicker", "person") == personB


def test_init_with_pairbond_selected(dlg):
    personA = Person(name="Joseph", lastName="Donner")
    personB = Person(name="Josephina", lastName="Donner")
    marriage = Marriage(personA=personA, personB=personB)
    dlg.scene.addItems(personA, personB, marriage)
    dlg.test_initForSelection([marriage])
    assert dlg.rootProp("kind") == EventKind.CustomPairBond.value
    assert dlg.itemProp("personAPicker", "person") == personA
    assert dlg.itemProp("personBPicker", "person") == personB


def test_init_with_individuals_selected(dlg):
    personA = Person(name="Joseph", lastName="Donner")
    personB = Person(name="Josephina", lastName="Donner")
    personC = Person(name="Josephine", lastName="Donner")
    personD = Person(name="Josephine", lastName="Donner")
    dlg.scene.addItems(personA, personB, personC, personD)
    dlg.test_initForSelection([personA, personB, personC])
    assert dlg.rootProp("kind") == EventKind.CustomIndividual.value
    assert {x["person"].id for x in dlg.peopleEntries()} == {
        personA.id,
        personB.id,
        personC.id,
    }


@pytest.mark.parametrize("kind", [x for x in EventKind])
def test_fields_for_kind(dlg, kind):
    dlg.clickComboBoxItem("kindBox", EventKind.menuLabelFor(kind))
    assert dlg.itemProp("personLabel", "visible") == EventKind.isMonadic(kind)
    assert dlg.itemProp("personPicker", "visible") == EventKind.isMonadic(kind)

    assert dlg.itemProp("peopleLabel", "visible") == (
        kind == EventKind.CustomIndividual
    )
    assert dlg.itemProp("peoplePicker", "visible") == (
        kind == EventKind.CustomIndividual
    )

    assert (
        dlg.itemProp("personALabel", "text") == "Person A"
        if EventKind.isPairBond(kind)
        else "Parent A"
    )
    assert (
        dlg.itemProp("personBLabel", "text") == "Person B"
        if EventKind.isPairBond(kind)
        else "Parent B"
    )
    assert dlg.itemProp("personALabel", "visible") == (
        EventKind.isPairBond(kind) or EventKind.isChild(kind)
    )
    assert dlg.itemProp("personAPicker", "visible") == (
        EventKind.isPairBond(kind) or EventKind.isChild(kind)
    )
    assert dlg.itemProp("personBLabel", "visible") == (
        EventKind.isPairBond(kind) or EventKind.isChild(kind)
    )
    assert dlg.itemProp("personBPicker", "visible") == (
        EventKind.isPairBond(kind) or EventKind.isChild(kind)
    )

    assert dlg.itemProp("moversLabel", "visible") == EventKind.isDyadic(kind)
    assert dlg.itemProp("moversPicker", "visible") == EventKind.isDyadic(kind)
    assert dlg.itemProp("receiversLabel", "visible") == EventKind.isDyadic(kind)
    assert dlg.itemProp("receiversPicker", "visible") == EventKind.isDyadic(kind)

    assert dlg.itemProp("descriptionLabel", "visible") == EventKind.isCustom(kind)
    assert dlg.itemProp("descriptionEdit", "visible") == EventKind.isCustom(kind)

    assert dlg.itemProp("anxietyBox", "visible") != EventKind.isRSymbol(kind)
    assert dlg.itemProp("functioningBox", "visible") != EventKind.isRSymbol(kind)
    assert dlg.itemProp("symptomBox", "visible") != EventKind.isRSymbol(kind)


def test_startDateTime_pickers(dlg):
    dlg.mouseClick("clearFormButton")

    DATE_TIME = util.Date(2023, 2, 1)

    dlg.set_startDateTime(DATE_TIME)

    assert dlg.rootProp("startDateTime") == DATE_TIME


def test_endDateTime_pickers(dlg):
    dlg.mouseClick("clearFormButton")

    DATE_TIME = util.Date(2023, 2, 1)

    dlg.set_kind(EventKind.Conflict)
    dlg.set_endDateTime(DATE_TIME)

    # util.dumpWidget(dlg)

    assert dlg.itemProp("isDateRangeBox", "checked") == True
    assert dlg.rootProp("endDateTime") == DATE_TIME


# def test_add_new_people_pair_bond(dlg):
#     scene = dlg.sceneModel.scene


# def test_person_help_text_add_one_person(qtbot, dlg):
#     _set_required_fields(dlg, people=False, fillRequired=False)
#     _add_new_person(dlg)
#     dlg.clickComboBoxItem("kindBox", EventKind.Birth.name)
#     assert (
#         dlg.itemProp("eventHelpText", "text")
#         == AddAnythingDialog.S_EVENT_MULTIPLE_INDIVIDUALS
#     )


# def test_dyadic_with_gt_two_people(qtbot, dlg):
#     _set_required_fields(dlg, people=False, fillRequired=False)
#     _add_new_person(dlg, firstName="John", lastName="Doe")
#     _add_new_person(dlg, firstName="Jane", lastName="Doe")
#     _add_new_person(dlg, firstName="Joseph", lastName="Belgard")
#     dlg.clickComboBoxItem("kindBox", EventKind.Birth.name)
#     assert (
#         dlg.itemProp("eventHelpText", "text")
#         == AddAnythingDialog.S_EVENT_MULTIPLE_INDIVIDUALS
#     )


# - add_new_people_as_pair_bond
# - add_two_existing_as_pair_bond_married
# - add_one_existing_one_new_as_pair_bond
# - select_isDateRange_for_distinct_event_type
# - select_not_isDateRange_for_range_event_type
# - select_dyadic_event_with_one_person_selected
# - select_dyadic_event_with_three_people_selected
#
