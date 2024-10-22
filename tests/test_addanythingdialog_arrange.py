import pytest
import datetime

from pkdiagram.pyqt import QApplication, Qt, QPointF
from pkdiagram import util, EventKind, MainWindow
from pkdiagram import Person, Marriage
from tests.test_addanythingdialog import scene, dlg, START_DATETIME, END_DATETIME


def test_parents_to_existing_person(dlg):
    scene = dlg.scene
    submitted = util.Condition(dlg.submitted)

    person = Person(name="John", lastName="Doe")
    scene.addItems(person)
    SPACING = person.boundingRect().width() * 2
    assert person.scenePos() == QPointF(0, 0)

    dlg.set_kind(EventKind.Birth)
    dlg.set_existing_person("personPicker", person=person)
    dlg.set_new_person("personAPicker", "Father Doe")
    dlg.set_new_person(
        "personBPicker",
        "Mother Doe",
        gender=util.personKindNameFromKind(util.PERSON_KIND_FEMALE),
    )
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.wait() == True
    father = scene.query1(name="Father")
    mother = scene.query1(name="Mother")
    assert person.scenePos() == QPointF(0, 0)  # hasn't changed
    assert father.scenePos() == QPointF(-SPACING, -SPACING * 1.5)
    assert mother.scenePos() == QPointF(SPACING, -SPACING * 1.5)


def test_add_via_birth_with_two_parents(dlg):
    scene = dlg.scene
    submitted = util.Condition(dlg.submitted)

    dlg.set_kind(EventKind.Birth)
    dlg.set_new_person("personPicker", "Son Doe")
    dlg.set_new_person("personAPicker", "Father Doe")
    dlg.set_startDateTime(START_DATETIME)
    dlg.mouseClick("AddEverything_submitButton")
    assert submitted.wait() == True
    son = scene.query1(name="Son")
    father = scene.query1(name="Father")
    mother = scene.query1(gender=util.PERSON_KIND_FEMALE)
    SPACING = son.boundingRect().width() * 2
    assert son.scenePos() == QPointF(0, SPACING * 1.5)
    assert father.scenePos() == QPointF(-SPACING, 0)
    assert mother.scenePos() == QPointF(SPACING, 0)
