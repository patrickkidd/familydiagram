import pytest

from pkdiagram import util
from pkdiagram.scene import Person, EventKind, RelationshipKind

from .test_addanythingdialog import view, START_DATETIME, END_DATETIME


DEPENDS = pytest.mark.depends_on("PersonPicker", "PeoplePicker", "DatePicker")


@pytest.mark.parametrize("isDateRange", [True, False])
def test_add_variables(scene, view, isDateRange):
    view.set_kind(EventKind.VariableShift)
    view.personPicker.set_new_person("John Doe")
    view.set_startDateTime(START_DATETIME)
    if isDateRange:
        view.set_endDateTime(END_DATETIME)
    view.set_symptom(util.VAR_SYMPTOM_UP)
    view.set_anxiety(util.VAR_ANXIETY_DOWN)
    view.set_relationship(RelationshipKind.Conflict)
    view.targetsPicker.add_new_person("Jane Doe")
    view.set_functioning(util.VAR_FUNCTIONING_SAME)
    view.clickAddButton()
    dynamicPropertyNames = [entry["name"] for entry in scene.eventProperties()]
    assert dynamicPropertyNames == [
        util.ATTR_SYMPTOM,
        util.ATTR_ANXIETY,
        util.ATTR_RELATIONSHIP,
        util.ATTR_FUNCTIONING,
    ]
    event = scene.events()[0]
    assert event.symptom() == util.VAR_SYMPTOM_UP
    assert event.anxiety() == util.VAR_ANXIETY_DOWN
    assert event.relationship() == RelationshipKind.Conflict
    assert event.functioning() == util.VAR_FUNCTIONING_SAME


def test_existing_variables(scene, view):
    scene.addEventProperty(util.ATTR_SYMPTOM)
    scene.addEventProperty(util.ATTR_ANXIETY)
    scene.addEventProperty(util.ATTR_RELATIONSHIP)
    scene.addEventProperty(util.ATTR_FUNCTIONING)
    person = scene.addItem(Person(name="John Doe"))
    view.set_kind(EventKind.VariableShift)
    view.personPicker.set_existing_person(person)
    view.set_startDateTime(START_DATETIME)
    view.set_symptom(util.VAR_SYMPTOM_UP)
    view.set_anxiety(util.VAR_ANXIETY_DOWN)
    view.set_relationship(RelationshipKind.Conflict)
    view.targetsPicker.add_new_person("Jane Doe")
    view.set_functioning(util.VAR_FUNCTIONING_SAME)
    view.clickAddButton()
    dynamicPropertyNames = [entry["name"] for entry in scene.eventProperties()]
    assert dynamicPropertyNames == [
        util.ATTR_SYMPTOM,
        util.ATTR_ANXIETY,
        util.ATTR_RELATIONSHIP,
        util.ATTR_FUNCTIONING,
    ]
    event = person.events()[0]
    assert event.symptom() == util.VAR_SYMPTOM_UP
    assert event.anxiety() == util.VAR_ANXIETY_DOWN
    assert event.relationship() == RelationshipKind.Conflict
    assert event.functioning() == util.VAR_FUNCTIONING_SAME


def test_cutoff(scene, view):
    person = scene.addItem(Person(name="John Doe"))
    view.set_kind(EventKind.VariableShift)
    view.personPicker.set_existing_person(person)
    view.set_relationship(RelationshipKind.Cutoff)
    view.set_startDateTime(START_DATETIME)
    view.set_endDateTime(END_DATETIME)
    view.clickAddButton()
    startEvent = person.events()[0]
    endEvent = person.events()[1]
    emotion = startEvent.parent()
    assert endEvent.parent() is emotion
    assert startEvent is emotion.startEvent
    assert endEvent is emotion.endEvent
    assert startEvent.parent() == emotion
    assert startEvent.relationship() == RelationshipKind.Cutoff
    assert startEvent.dateTime() == START_DATETIME
    assert startEvent.targets() == []
    assert startEvent.triangles() == []
    assert endEvent.parent() == emotion
    assert endEvent.relationship() == RelationshipKind.Cutoff
    assert endEvent.dateTime() == START_DATETIME
    assert endEvent.targets() == []
    assert endEvent.triangles() == []


def test_triangle(scene, view):
    person = scene.addItem(Person(name="John Doe"))
    inside = scene.addItem(Person(name="Inside"))
    outside = scene.addItem(Person(name="Outside"))
    view.set_kind(EventKind.VariableShift)
    view.personPicker.set_existing_person(person)
    view.set_relationship(RelationshipKind.Inside)
    view.targetsPicker.set_existing_person(inside)
    view.trianglePicker.set_existing_person(outside)
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    event = person.events()[0]
    assert event.relationship() == RelationshipKind.Inside
    assert event.targets() == [inside]
    assert event.triangles() == [outside]
