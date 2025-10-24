import pytest

from btcopilot.schema import EventKind, RelationshipKind, VariableShift
from pkdiagram import util
from pkdiagram.scene import Person, ItemMode

from .test_eventform import view, START_DATETIME, END_DATETIME


DEPENDS = pytest.mark.depends_on("PersonPicker", "PeoplePicker", "DatePicker")


@pytest.mark.parametrize("isDateRange", [True, False])
def test_add_variables(scene, view, isDateRange):
    person = scene.addItem(Person(name="John Doe"))
    scene.addEventProperty(util.ATTR_SYMPTOM)
    scene.addEventProperty(util.ATTR_ANXIETY)
    scene.addEventProperty(util.ATTR_RELATIONSHIP)
    scene.addEventProperty(util.ATTR_FUNCTIONING)
    view.set_kind(EventKind.Shift)
    view.personPicker.set_existing_person(person)
    view.set_startDateTime(START_DATETIME)
    if isDateRange:
        view.set_endDateTime(END_DATETIME)
    view.set_symptom(VariableShift.Up)
    view.set_anxiety(VariableShift.Down)
    view.set_relationship(RelationshipKind.Conflict)
    view.set_description("Some description")
    view.targetsPicker.add_new_person("Jane Doe")
    view.set_functioning(VariableShift.Same)
    view.clickSaveButton()
    dynamicPropertyNames = [entry["name"] for entry in scene.eventProperties()]
    assert dynamicPropertyNames == [
        util.ATTR_SYMPTOM,
        util.ATTR_ANXIETY,
        util.ATTR_RELATIONSHIP,
        util.ATTR_FUNCTIONING,
    ]
    event = scene.eventsFor(person)[0]
    assert event.symptom() == VariableShift.Up
    assert event.anxiety() == VariableShift.Down
    assert event.relationship() == RelationshipKind.Conflict
    assert event.functioning() == VariableShift.Same


def test_existing_variables(scene, view):
    scene.addEventProperty(util.ATTR_SYMPTOM)
    scene.addEventProperty(util.ATTR_ANXIETY)
    scene.addEventProperty(util.ATTR_RELATIONSHIP)
    scene.addEventProperty(util.ATTR_FUNCTIONING)
    person = scene.addItem(Person(name="John Doe"))
    view.set_kind(EventKind.Shift)
    view.personPicker.set_existing_person(person)
    view.set_startDateTime(START_DATETIME)
    view.set_symptom(VariableShift.Up)
    view.set_anxiety(VariableShift.Down)
    view.set_relationship(RelationshipKind.Conflict)
    view.targetsPicker.add_new_person("Jane Doe")
    view.set_description("Some description")
    view.set_functioning(VariableShift.Same)
    view.clickSaveButton()
    dynamicPropertyNames = [entry["name"] for entry in scene.eventProperties()]
    assert dynamicPropertyNames == [
        util.ATTR_SYMPTOM,
        util.ATTR_ANXIETY,
        util.ATTR_RELATIONSHIP,
        util.ATTR_FUNCTIONING,
    ]
    event = scene.eventsFor(person)[0]
    assert event.symptom() == VariableShift.Up
    assert event.anxiety() == VariableShift.Down
    assert event.relationship() == RelationshipKind.Conflict
    assert event.functioning() == VariableShift.Same


def test_triangle(scene, view):
    person = scene.addItem(Person(name="John Doe"))
    inside = scene.addItem(Person(name="Inside"))
    outside = scene.addItem(Person(name="Outside"))
    view.set_kind(EventKind.Shift)
    view.personPicker.set_existing_person(person)
    view.set_relationship(RelationshipKind.Inside)
    view.targetsPicker.add_existing_person(inside)
    view.trianglesPicker.add_existing_person(outside)
    view.set_startDateTime(START_DATETIME)
    view.set_description("Some description")
    view.clickSaveButton()
    emotion = scene.emotionsFor(person)[0]
    assert emotion.kind() == RelationshipKind.Inside
    assert emotion.sourceEvent().relationshipTargets() == [inside]
    assert emotion.sourceEvent().relationshipTriangles() == [outside]
