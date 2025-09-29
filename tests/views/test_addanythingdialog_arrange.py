import pytest
import datetime

from pkdiagram.pyqt import QPointF
from pkdiagram import util
from pkdiagram.scene import LifeChange, Person

from .test_addanythingdialog import view, START_DATETIME, END_DATETIME


pytestmark = [
    pytest.mark.component("AddAnythingDialog"),
    pytest.mark.depends_on("Scene"),
]


def test_parents_to_existing_person(scene, view):
    submitted = util.Condition(view.view.submitted)

    person = Person(name="John", lastName="Doe")
    scene.addItems(person)
    SPACING = person.boundingRect().width() * 2
    assert person.scenePos() == QPointF(0, 0)

    view.set_kind(LifeChange.Birth)
    view.personPicker.set_existing_person(person=person)
    view.personAPicker.set_new_person("Father Doe")
    view.personBPicker.set_new_person(
        "Mother Doe",
        gender=util.personKindNameFromKind(util.PERSON_KIND_FEMALE),
    )
    view.set_startDateTime(START_DATETIME)
    view.clickAddButton()
    assert submitted.wait() == True
    father = scene.query1(name="Father")
    mother = scene.query1(name="Mother")
    assert person.scenePos() == QPointF(0, 0)  # hasn't changed
    assert father.scenePos() == QPointF(-SPACING, -SPACING * 1.5)
    assert mother.scenePos() == QPointF(SPACING, -SPACING * 1.5)


def test_add_via_birth_with_two_parents(scene, view):
    submitted = util.Condition(view.view.submitted)

    view.set_kind(LifeChange.Birth)
    view.personPicker.set_new_person("Son Doe")
    view.personAPicker.set_new_person("Father Doe")
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
