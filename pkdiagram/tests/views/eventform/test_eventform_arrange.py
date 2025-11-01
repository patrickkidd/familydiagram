import pytest
import datetime

from btcopilot.schema import EventKind, RelationshipKind
from pkdiagram.pyqt import QPointF
from pkdiagram import util
from pkdiagram.scene import Person

from .test_eventform import view, START_DATETIME, END_DATETIME


pytestmark = [
    pytest.mark.component("EventForm"),
    pytest.mark.depends_on("Scene"),
]


def test_Birth_default_parents_parents_to_existing_child(scene, view):
    person = scene.addItem(Person(name="John", lastName="Doe"))
    SPACING = person.sceneBoundingRect().width() * 2
    assert person.scenePos() == QPointF(0, 0)

    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("Father Doe")
    view.spousePicker.set_new_person(
        "Mother Doe",
        gender=util.personKindNameFromKind(util.PERSON_KIND_FEMALE),
    )
    view.childPicker.set_existing_person(person)
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()
    father = scene.query1(name="Father")
    mother = scene.query1(name="Mother")
    assert person.scenePos() == QPointF(0, 0)  # hasn't changed
    assert father.scenePos() == QPointF(-SPACING, -SPACING * 1.5)
    assert mother.scenePos() == QPointF(SPACING, -SPACING * 1.5)


def test_Birth_add_via_birth_one_default_parent(scene, view):
    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("Father Doe")
    view.childPicker.set_new_person("Son Doe")
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()
    son = scene.query1(name="Son")
    father = scene.query1(name="Father")
    mother = scene.query1(gender=util.PERSON_KIND_FEMALE)
    SPACING = son.sceneBoundingRect().width() * 2
    assert son.scenePos() == QPointF(0, SPACING * 1.5)
    assert father.scenePos() == QPointF(-SPACING, 0)
    assert mother.scenePos() == QPointF(SPACING, 0)


def test_Birth_add_new_existing_parents(scene, view):
    mother = scene.addItem(Person(name="Mother"))
    father = scene.addItem(Person(name="Father"))
    SPACING = father.boundingRect().width() * 2
    mother.setItemPosNow(QPointF(-SPACING, 0))
    father.setItemPosNow(QPointF(SPACING, 0))
    view.set_kind(EventKind.Birth)
    view.personPicker.set_existing_person(mother)
    view.spousePicker.set_existing_person(father)
    view.childPicker.set_new_person("Son Doe")
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()
    child = scene.query1(name="Son")
    assert mother.scenePos() == QPointF(-SPACING, 0)
    assert father.scenePos() == QPointF(SPACING, 0)
    spacing = child.sceneBoundingRect().width() * 2
    assert child.itemPos() == QPointF(
        0, father.marriages[0].sceneBoundingRect().bottomLeft().y() + spacing
    )


def test_Variable_add_to_existing_people(scene, view):
    father = scene.addItem(Person(name="Father"))
    mother = scene.addItem(Person(name="Mother"))
    SPACING = father.boundingRect().width() * 2
    father.setItemPosNow(QPointF(-SPACING, 0))
    mother.setItemPosNow(QPointF(SPACING, 0))
    view.set_kind(EventKind.Shift)
    view.set_relationship(RelationshipKind.Conflict)
    view.personPicker.set_existing_person(father)
    view.targetsPicker.add_existing_person(mother)
    view.set_description("argument")
    view.set_startDateTime(START_DATETIME)
    view.clickSaveButton()

    assert father.scenePos() == QPointF(-SPACING, 0)  # unchanged
    assert mother.scenePos() == QPointF(SPACING, 0)  # unchanged
