import logging

import pytest
import mock

from pkdiagram import util
from pkdiagram.scene import Person, Marriage, LifeChange


from .test_addanythingdialog import view

_log = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.component("AddAnythingDialog"),
    pytest.mark.depends_on("Scene"),
]


def test_init_no_selection(view):
    assert [i for i in view.kindBox.property("model")] == LifeChange.menuLabels()
    assert view.item.property("kind") == None


def test_init_with_existing_person(scene, view):
    assert [i for i in view.kindBox.property("model")] == LifeChange.menuLabels()
    person = scene.addItem(
        Person(name="Joseph", lastName="Donner", gender=util.PERSON_KIND_FEMALE)
    )
    view.initForSelection([person])
    peopleEntries = view.item.peopleEntries().toVariant()
    assert view.item.property("kind") == LifeChange.CustomIndividual.value
    assert len(peopleEntries) == 1
    assert peopleEntries[0]["person"] == person
    assert peopleEntries[0]["gender"] == util.PERSON_KIND_FEMALE


def test_init_with_pairbond_people_selected(scene, view):
    personA = Person(name="Joseph", lastName="Donner")
    personB = Person(name="Josephina", lastName="Donner")
    marriage = Marriage(personA=personA, personB=personB)
    scene.addItems(personA, personB, marriage)
    view.initForSelection([personA, personB])
    assert view.item.property("kind") == LifeChange.CustomPairBond.value
    assert view.personAPicker.item.property("person") == personA
    assert view.personBPicker.item.property("person") == personB


def test_init_with_pairbond_selected(scene, view):
    personA = Person(name="Joseph", lastName="Donner")
    personB = Person(name="Josephina", lastName="Donner")
    marriage = Marriage(personA=personA, personB=personB)
    scene.addItems(personA, personB, marriage)
    view.initForSelection([marriage])
    assert view.item.property("kind") == LifeChange.CustomPairBond.value
    assert view.personAPicker.item.property("person") == personA
    assert view.personBPicker.item.property("person") == personB


def test_init_with_individuals_selected(scene, view):
    personA = Person(name="Joseph", lastName="Donner")
    personB = Person(name="Josephina", lastName="Donner")
    personC = Person(name="Josephine", lastName="Donner")
    personD = Person(name="Josephine", lastName="Donner")
    scene.addItems(personA, personB, personC, personD)
    view.initForSelection([personA, personB, personC])
    assert view.item.property("kind") == LifeChange.CustomIndividual.value
    assert {x["person"].id for x in view.item.peopleEntries().toVariant()} == {
        personA.id,
        personB.id,
        personC.id,
    }


@pytest.mark.parametrize("kind", [x for x in LifeChange])
def test_fields_for_kind(view, kind):
    view.view.clickComboBoxItem(view.kindBox, LifeChange.menuLabelFor(kind))
    assert view.personLabel.property("visible") == LifeChange.isMonadic(kind)
    assert view.personPicker.item.property("visible") == LifeChange.isMonadic(kind)

    assert view.peopleLabel.property("visible") == (kind == LifeChange.CustomIndividual)
    assert view.peoplePicker.item.property("visible") == (
        kind == LifeChange.CustomIndividual
    )

    assert (
        view.item.property("personALabel").property("text") == "Person A"
        if LifeChange.isPairBond(kind)
        else "Parent A"
    )
    assert (
        view.item.property("personBLabel").property("text") == "Person B"
        if LifeChange.isPairBond(kind)
        else "Parent B"
    )
    assert view.item.property("personALabel").property("visible") == (
        LifeChange.isPairBond(kind) or LifeChange.isChild(kind)
    )
    assert view.personAPicker.item.property("visible") == (
        LifeChange.isPairBond(kind) or LifeChange.isChild(kind)
    )
    assert view.item.property("personBLabel").property("visible") == (
        LifeChange.isPairBond(kind) or LifeChange.isChild(kind)
    )
    assert view.personBPicker.item.property("visible") == (
        LifeChange.isPairBond(kind) or LifeChange.isChild(kind)
    )

    assert view.moversLabel.property("visible") == LifeChange.isDyadic(kind)
    assert view.moversPicker.item.property("visible") == LifeChange.isDyadic(kind)
    assert view.receiversLabel.property("visible") == LifeChange.isDyadic(kind)
    assert view.receiversPicker.item.property("visible") == LifeChange.isDyadic(kind)

    assert view.item.property("descriptionLabel").property(
        "visible"
    ) == LifeChange.isCustom(kind)
    assert view.descriptionEdit.property("visible") == LifeChange.isCustom(kind)

    assert view.item.property("anxietyBox").property("visible") != LifeChange.isRSymbol(
        kind
    )
    assert view.item.property("functioningBox").property(
        "visible"
    ) != LifeChange.isRSymbol(kind)
    assert view.item.property("symptomBox").property("visible") != LifeChange.isRSymbol(
        kind
    )


def test_startDateTime_pickers(view):
    view.clickClearButton()

    DATE_TIME = util.Date(2023, 2, 1)

    view.set_startDateTime(DATE_TIME)

    assert view.item.property("startDateTime") == DATE_TIME


def test_endDateTime_pickers(view):
    view.clickClearButton()

    DATE_TIME = util.Date(2023, 2, 1)

    view.set_kind(LifeChange.Conflict)
    view.set_endDateTime(DATE_TIME)

    # util.dumpWidget(view)

    assert view.isDateRangeBox.property("checked") == True
    assert view.item.property("endDateTime") == DATE_TIME


# def test_add_new_people_pair_bond(view):
#     scene = sceneModel.scene


# def test_person_help_text_add_one_person(qtbot, view):
#     _set_required_fields(view, people=False, fillRequired=False)
#     _add_new_person(view)
#     view.clickComboBoxItem("kindBox", LifeChange.Birth.name)
#     assert (
#         view.eventHelpText.property("text")
#         == AddAnythingDialog.S_EVENT_MULTIPLE_INDIVIDUALS
#     )


# def test_dyadic_with_gt_two_people(qtbot, view):
#     _set_required_fields(view, people=False, fillRequired=False)
#     _add_new_person(view, firstName="John", lastName="Doe")
#     _add_new_person(view, firstName="Jane", lastName="Doe")
#     _add_new_person(view, firstName="Joseph", lastName="Belgard")
#     view.clickComboBoxItem("kindBox", LifeChange.Birth.name)
#     assert (
#         view.eventHelpText.property("text")
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
