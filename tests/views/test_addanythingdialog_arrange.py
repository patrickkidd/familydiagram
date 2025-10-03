import pytest
import datetime

from pkdiagram.pyqt import QPointF
from pkdiagram import util
from pkdiagram.scene import EventKind, Person
from pkdiagram.scene.relationshipkind import RelationshipKind

from .test_addanythingdialog import view, START_DATETIME, END_DATETIME


pytestmark = [
    pytest.mark.component("AddAnythingDialog"),
    pytest.mark.depends_on("Scene"),
]


def test_Birth_default_parents_parents_to_existing_person(scene, view):
    submitted = util.Condition(view.view.submitted)

    person = Person(name="John", lastName="Doe")
    scene.addItems(person)
    SPACING = person.boundingRect().width() * 2
    assert person.scenePos() == QPointF(0, 0)

    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("Father Doe")
    view.spousePicker.set_new_person(
        "Mother Doe",
        gender=util.personKindNameFromKind(util.PERSON_KIND_FEMALE),
    )
    view.childPicker.set_existing_person(person=person)
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    assert submitted.wait() == True
    father = scene.query1(name="Father")
    mother = scene.query1(name="Mother")
    assert person.scenePos() == QPointF(0, 0)  # hasn't changed
    assert father.scenePos() == QPointF(-SPACING, -SPACING * 1.5)
    assert mother.scenePos() == QPointF(SPACING, -SPACING * 1.5)


def test_Birth_add_via_birth_one_default_parent(scene, view):
    submitted = util.Condition(view.view.submitted)

    view.set_kind(EventKind.Birth)
    view.personPicker.set_new_person("Father Doe")
    view.childPicker.set_new_person("Son Doe")
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    assert submitted.wait() == True
    son = scene.query1(name="Son")
    father = scene.query1(name="Father")
    mother = scene.query1(gender=util.PERSON_KIND_FEMALE)
    SPACING = son.boundingRect().width() * 2
    assert son.scenePos() == QPointF(0, SPACING * 1.5)
    assert father.scenePos() == QPointF(-SPACING, 0)
    assert mother.scenePos() == QPointF(SPACING, 0)


def test_Variable_add_to_existing_people(scene, view):
    father = scene.addItem(Person(name="Father"))
    mother = scene.addItem(Person(name="Mother"))
    SPACING = father.boundingRect().width() * 2
    father.setItemPosNow(QPointF(-SPACING, 0))
    mother.setItemPosNow(QPointF(SPACING, 0))
    view.set_kind(EventKind.VariableShift)
    view.set_relationship(RelationshipKind.Conflict)
    view.personPicker.set_existing_person(father)
    view.targetsPicker.add_existing_person(mother)
    view.set_description("argument")
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()

    assert father.scenePos() == QPointF(-SPACING, 0)  # unchanged
    assert mother.scenePos() == QPointF(SPACING, 0)  # unchanged
