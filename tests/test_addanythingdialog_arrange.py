import pytest
import datetime

from pkdiagram.pyqt import QApplication, Qt, QPointF
from pkdiagram import util, EventKind, MainWindow
from pkdiagram import Person, Marriage
from tests.test_addanythingdialog import scene, dlg, START_DATETIME, END_DATETIME


def test_parents_to_existing_person(qtbot, dlg):

    scene = dlg.scene
    submitted = util.Condition(dlg.submitted)

    person = Person(name="John", lastName="Doe")
    scene.addItems(person)
    spacing = person.boundingRect().width() * 2
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
    father = scene.query1(name="Father")
    mother = scene.query1(name="Mother")
    assert person.scenePos() == QPointF(0, 0)  # hasn't changed
    assert father.scenePos() == QPointF(-spacing, -spacing * 1.5)
    assert mother.scenePos() == QPointF(spacing, -spacing * 1.5)
