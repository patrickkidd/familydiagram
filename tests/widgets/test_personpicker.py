import logging

import pytest

from pkdiagram import util
from pkdiagram.pyqt import QVBoxLayout, QWidget, QUrl, QApplication
from pkdiagram.scene import Person
from pkdiagram.widgets import QmlWidgetHelper

from tests.widgets import TestPersonPicker
from pathlib import Path


_log = logging.getLogger(__name__)


@pytest.fixture
def picker(qmlEngine, create_qml):

    SOURCE_FPATH = str(
        Path(__file__).resolve().parent.parent.parent
        / "pkdiagram"
        / "resources"
        / "qml"
        / "PK"
        / "PersonPicker.qml"
    )

    # _log.info(SOURCE_FPATH)

    helper = create_qml(SOURCE_FPATH)
    _ret = TestPersonPicker(helper, helper.qml.rootObject())
    _ret.item.setProperty("scenePeopleModel", qmlEngine.peopleModel)
    yield _ret


def test_set_new_person(picker):
    PERSON_NAME = "Someone New"
    picker.set_new_person(PERSON_NAME, returnToFinish=True)
    assert picker.item.property("isSubmitted") == True
    assert picker.item.property("person") == None
    assert picker.item.property("personName") == PERSON_NAME
    assert picker.item.property("isNewPerson") == True
    assert picker.item.property("gender") == util.PERSON_KIND_MALE


def test_set_existing_person(scene, picker):
    person = scene.addItem(Person(name="John", lastName="Doe"))

    picker.set_existing_person(person, autoCompleteInput="Joh")
    assert picker.item.property("isSubmitted") == True
    assert picker.item.property("isNewPerson") == False
    assert picker.item.property("person") == person
    assert picker.item.property("gender") == person.gender()
    assert picker.item.property("isNewBox").property("visible") == False
    assert picker.item.property("checkImage").property("visible") == True
    assert picker.item.property("selectedPeopleModel").property("count") == 1


def test_show_autocomplete_popup(scene, picker):
    scene.addItem(Person(name="John", lastName="Doe"))
    picker.set_existing_person(None, autoCompleteInput="Joh", returnToFinish=False)
    # picker.keyClicks(
    #     f"personPicker.textEdit",
    #     "Joh",
    #     resetFocus=False,
    #     returnToFinish=False,
    # )
    assert picker.textEdit.property("text") == "Joh"
    assert picker.popupListView.property("visible") == True
    assert picker.popupListView.property("numVisibleItems") == 1


def test_cannot_add_selected_person(scene, picker):
    person = scene.addItem(Person(name="John", lastName="Doe"))
    picker.item.setPersonIdSelected(person.id)
    picker.set_new_person("Patri", gender=False, returnToFinish=False)
    assert picker.popupListView.property("visible") == False
    assert picker.popupListView.property("numVisibleItems") == 0


def test_clear_button_existing_person(scene, picker):
    person = scene.addItem(
        Person(name="John", lastName="Doe", gender=util.PERSON_KIND_FEMALE)
    )
    picker.set_existing_person(person, autoCompleteInput="Joh")
    selectedPeopleModel = picker.item.property("selectedPeopleModel")
    assert selectedPeopleModel.rowCount() == 1
    assert picker.item.property("isSubmitted") == True
    assert picker.item.property("isNewPerson") == False
    assert picker.item.property("person") == person
    assert picker.item.property("gender") == person.gender()

    picker.item.clear()
    assert selectedPeopleModel.rowCount() == 0
    assert picker.item.property("isSubmitted") == False
    assert picker.item.property("isNewPerson") == False
    assert picker.item.property("person") == None
    assert picker.item.property("gender") == util.PERSON_KIND_MALE
    assert picker.item.property("genderBox").property("currentIndex") == 0


def test_clear_button_new_person(picker):

    PERSON_NAME = "Someone New"

    picker.set_new_person(PERSON_NAME, returnToFinish=True)
    assert picker.item.property("isSubmitted") == True
    assert picker.item.property("isNewPerson") == True
    assert picker.item.property("personName") == PERSON_NAME
    assert picker.item.property("gender") == util.PERSON_KIND_MALE

    picker.item.clear()
    assert picker.item.property("isSubmitted") == False
    assert picker.item.property("isNewPerson") == False
    assert picker.item.property("personName") == ""
    assert picker.item.property("gender") == None
