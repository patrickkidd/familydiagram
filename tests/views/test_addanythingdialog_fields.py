import logging

import pytest
import mock

from pkdiagram import util
from pkdiagram.scene import Person, Marriage, EventKind, RelationshipKind


from .test_addanythingdialog import view

_log = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.component("AddAnythingDialog"),
    pytest.mark.depends_on("Scene"),
]


@pytest.mark.parametrize(
    "kind,spouseVisible,childVisible",
    [
        (EventKind.Birth, True, True),
        (EventKind.Adopted, True, True),
        (EventKind.Death, False, False),
        (EventKind.Bonded, True, False),
        (EventKind.Married, True, False),
        (EventKind.Separated, True, False),
        (EventKind.Divorced, True, False),
        (EventKind.Moved, True, False),
    ],
    ids=[
        "Birth",
        "Adopted",
        "Death",
        "Bonded",
        "Married",
        "Separated",
        "Divorced",
        "Moved",
    ],
)
def test_eventkind_fields_response(
    view, kind: EventKind, spouseVisible: bool, childVisible: bool
):
    view.set_kind(kind)
    assert view.spousePicker.item.property("visible") == spouseVisible
    assert view.childPicker.item.property("visible") == childVisible
    assert view.descriptionEdit.property("visible") == False
    for item in [
        view.symptomLabel,
        view.symptomField,
        view.anxietyLabel,
        view.anxietyField,
        view.relationshipLabel,
        view.relationshipField,
        view.functioningLabel,
        view.functioningField,
    ]:
        assert item.property("visible") == False


def test_onKindChanged_clears_triangle_fields(scene, view):

    DATETIME = util.Date(2023, 1, 1)
    person = scene.addItem(Person(name="Jane", lastName="Doe"))
    person2 = scene.addItem(Person(name="John", lastName="Doe"))
    person3 = scene.addItem(Person(name="Baby", lastName="Doe"))
    view.set_kind(EventKind.VariableShift)
    view.personPicker.set_existing_person(person)
    view.set_relationship(RelationshipKind.Inside)  # unhappy path
    view.set_description("Something happened")
    view.targetsPicker.add_existing_person(person2)
    view.trianglesPicker.add_existing_person(person3)
    view.set_startDateTime(DATETIME)
    view.set_endDateTime(DATETIME)
    view.add_tag("tag1")
    view.add_tag("tag2")
    view.set_active_tags(["tag1", "tag2"])

    view.set_kind(EventKind.Birth)

    assert view.relationshipField.property("value") == None
    assert view.descriptionEdit.property("text") == ""
    assert view.view.targetsEntries() == []
    assert view.view.trianglesEntries() == []
    assert (
        view.item.property("selectedPeopleModel").rowCount() == 1  # person
    )  # hidden pickers retained selections
    # not cleared
    assert view.view.personEntry()["person"] == person
    assert view.item.property("startDateTime") == DATETIME
    assert view.item.property("endDateTime") == DATETIME
    assert view.isDateRangeBox.property("checked") == True
    assert view.item.property("eventModel").property("tags") == ["tag1", "tag2"]


def test_onKindChanged_clears_pairbond_fields(scene, view):
    person = scene.addItem(Person(name="Jane", lastName="Doe"))
    spouse = scene.addItem(Person(name="John", lastName="Doe"))
    child = scene.addItem(Person(name="Baby", lastName="Doe"))
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(person)
    view.spousePicker.set_existing_person(spouse)
    view.childPicker.set_existing_person(child)

    view.set_kind(EventKind.VariableShift)
    assert view.relationshipField.property("value") == None
    assert view.view.personEntry()["person"] == person
    assert view.view.spouseEntry() == None
    assert view.view.childEntry() == None
    assert view.view.targetsEntries() == []
    assert view.view.trianglesEntries() == []
    assert (
        view.item.property("selectedPeopleModel").rowCount() == 1  # person
    )  # hidden pickers retained selections
    # not cleared
    assert view.view.personEntry()["person"] == person


@pytest.mark.parametrize(
    "relationship, labelText",
    [
        (RelationshipKind.Conflict, "Other(s)"),
        (RelationshipKind.Distance, "Other(s)"),
        (RelationshipKind.Underfunctioning, "Overfunctioner(s)"),
        (RelationshipKind.Overfunctioning, "Underfunctioner(s)"),
        (RelationshipKind.Projection, "Focused"),
        (RelationshipKind.Toward, "To"),
        (RelationshipKind.Away, "From"),
        (RelationshipKind.DefinedSelf, "Other(s)"),
        (RelationshipKind.Inside, "Inside(s)"),
        (RelationshipKind.Outside, "Outside(s)"),
    ],
    ids=[
        "Conflict",
        "Distance",
        "Underfunctioning",
        "Overfunctioning",
        "Projection",
        "Toward",
        "Away",
        "DefinedSelf",
        "Inside",
        "Outside",
    ],
)
def test_relationship_targets_labels(view, relationship, labelText):
    view.set_kind(EventKind.VariableShift)
    view.set_relationship(relationship)
    assert view.targetsLabel.property("text") == labelText


@pytest.mark.parametrize(
    "relationship",
    [
        RelationshipKind.Conflict,
        RelationshipKind.Distance,
        RelationshipKind.Toward,
        RelationshipKind.Away,
        RelationshipKind.DefinedSelf,
        RelationshipKind.Inside,
        RelationshipKind.Outside,
    ],
)
def test_relationship_triangles(view, relationship):
    view.set_kind(EventKind.VariableShift)
    view.set_relationship(relationship)
    assert view.targetsPicker.item.property("visible") == True


def test_startDateTime_pickers(view):
    view.clickClearButton()

    DATE_TIME = util.Date(2023, 2, 1)

    view.set_startDateTime(DATE_TIME)

    assert view.item.property("startDateTime") == DATE_TIME


def test_endDateTime_pickers(view):
    view.clickClearButton()

    DATE_TIME = util.Date(2023, 2, 1)

    view.set_kind(EventKind.Bonded)
    view.set_endDateTime(DATE_TIME)

    # util.dumpWidget(view)

    assert view.isDateRangeBox.property("checked") == True
    assert view.item.property("endDateTime") == DATE_TIME


# def test_add_new_people_pair_bond(view):
#     scene = sceneModel.scene


# def test_person_help_text_add_one_person(qtbot, view):
#     _set_required_fields(view, people=False, fillRequired=False)
#     _add_new_person(view)
#     view.clickComboBoxItem("kindBox", EventKind.Birth.name)
#     assert (
#         view.eventHelpText.property("text")
#         == AddAnythingDialog.S_EVENT_MULTIPLE_INDIVIDUALS
#     )


# def test_dyadic_with_gt_two_people(qtbot, view):
#     _set_required_fields(view, people=False, fillRequired=False)
#     _add_new_person(view, firstName="John", lastName="Doe")
#     _add_new_person(view, firstName="Jane", lastName="Doe")
#     _add_new_person(view, firstName="Joseph", lastName="Belgard")
#     view.clickComboBoxItem("kindBox", EventKind.Birth.name)
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
