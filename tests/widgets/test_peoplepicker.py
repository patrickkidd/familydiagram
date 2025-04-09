import logging
from pathlib import Path

import pytest

from pkdiagram import util
from pkdiagram.pyqt import QQuickItem
from pkdiagram.scene import Person
from pkdiagram.models import SceneModel

from tests.widgets import TestPeoplePicker

_log = logging.getLogger(__name__)


@pytest.fixture
def scene(scene):
    scene.addItem(Person(first_name="Patrick", last_name="Stinson"))
    scene._sceneModel = SceneModel()
    scene._sceneModel.scene = scene
    yield scene


@pytest.fixture
def picker(qmlEngine, create_qml):
    SOURCE_FPATH = str(
        Path(__file__).resolve().parent.parent.parent
        / "pkdiagram"
        / "resources"
        / "qml"
        / "PK"
        / "PeoplePicker.qml"
    )

    _log.info(SOURCE_FPATH)

    helper = create_qml(SOURCE_FPATH)
    _ret = TestPeoplePicker(helper, helper.qml.rootObject())
    _ret.item.setProperty("scenePeopleModel", qmlEngine.peopleModel)
    yield _ret


def test_init_fields(scene, picker):
    personA = scene.addItem(
        Person(name="Joseph", lastName="Donner", gender=util.PERSON_KIND_MALE)
    )
    personB = scene.addItem(
        Person(name="Josephina", lastName="Donner", gender=util.PERSON_KIND_FEMALE)
    )
    picker.set_existing_people([personA, personB])
    entries = picker.item.peopleEntries().toVariant()
    assert len(entries) == 2
    assert entries[0]["person"] == personA
    assert entries[0]["isNewPerson"] == False
    assert entries[0]["gender"] == util.PERSON_KIND_MALE
    assert entries[1]["person"] == personB
    assert entries[1]["isNewPerson"] == False
    assert entries[1]["gender"] == util.PERSON_KIND_FEMALE


def test_one_existing_one_not(scene, picker):
    existingPerson = scene.addItem(Person(name="John", lastName="Doe"))
    existingPersonDelegate = picker.add_existing_person(
        existingPerson, autoCompleteInput="John"
    )
    assert (
        existingPersonDelegate.findChild(QQuickItem, "genderBox").property(
            "currentIndex"
        )
        == 0
    )
    assert existingPersonDelegate.property("isNewBox").property("visible") == False
    assert existingPersonDelegate.property("checkImage").property("visible") == True
    peopleEntries = picker.item.peopleEntries().toVariant()
    assert len(peopleEntries) == 1
    assert peopleEntries[0]["isNewPerson"] == False
    assert peopleEntries[0]["person"] == existingPerson
    assert peopleEntries[0]["personName"] == "John Doe"
    assert peopleEntries[0]["gender"] == util.PERSON_KIND_MALE

    newPersonDelegate = picker.add_new_person(
        "Someone new", gender=util.PERSON_KIND_FEMALE
    )
    peopleEntries = picker.item.peopleEntries().toVariant()
    assert len(peopleEntries) == 2
    assert peopleEntries[1]["isNewPerson"] == True
    assert peopleEntries[1]["person"] == None
    assert peopleEntries[1]["personName"] == "Someone new"
    assert peopleEntries[1]["gender"] == util.PERSON_KIND_FEMALE
    assert (
        existingPersonDelegate.findChild(QQuickItem, "genderBox").property(
            "currentIndex"
        )
        == 0
    )
    assert newPersonDelegate.property("isNewBox").property("visible") == True
    assert newPersonDelegate.property("checkImage").property("visible") == False


def test_add_lots_of_mixed(scene, picker):
    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Joseph", lastName="Donner"))
    personC = scene.addItem(Person(name="Jane", lastName="Donner"))
    picker.add_existing_person(personA, autoCompleteInput="Joh")
    picker.add_new_person("Someone new 1", gender=util.PERSON_KIND_FEMALE)
    picker.add_existing_person(
        personB, autoCompleteInput="Jose", gender=util.PERSON_KIND_UNKNOWN
    )
    picker.add_existing_person(
        personC, autoCompleteInput="Jan", gender=util.PERSON_KIND_ABORTION
    )
    picker.add_new_person("Someone new 2")
    picker.add_new_person("Someone new 3")
    picker.add_new_person("Someone new 4")
    peopleEntries = picker.item.peopleEntries().toVariant()
    newEntries = [x for x in peopleEntries if x["isNewPerson"] == True]
    existingEntries = [x for x in peopleEntries if x["isNewPerson"] == False]
    assert len(newEntries) == 4
    assert len(peopleEntries) == 7
    assert len(existingEntries) == 3
    joseEntry = next(x for x in existingEntries if x["person"] == personB)
    assert joseEntry["gender"] == util.PERSON_KIND_UNKNOWN
    personCEntry = next(x for x in existingEntries if x["person"] == personC)
    assert personCEntry["gender"] == util.PERSON_KIND_ABORTION


def test_add_then_delete_then_add(scene, picker):
    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Joseph", lastName="Donner"))
    delegate = picker.add_existing_person(personA, autoCompleteInput="Joh")
    assert picker.model.rowCount() == 1
    picker.delete_person(delegate)
    assert picker.model.rowCount() == 0
    picker.add_existing_person(personB, autoCompleteInput="Jos")
    assert picker.model.rowCount() == 1


def test_maintain_selectedPeopleModel(scene, picker):
    personA = scene.addItem(Person(name="John", lastName="Doe"))
    delegate = picker.add_existing_person(personA, autoCompleteInput="Joh")
    assert picker.model.rowCount() == 1
    assert picker.item.property("selectedPeopleModel").property("count") == 1
    picker.delete_person(delegate)
    assert picker.model.rowCount() == 0
    assert picker.item.property("selectedPeopleModel").property("count") == 0


# test_one_existing_one_not
# test_cancel_add_new
# test_add_existing_then_delete
# test_add_new__then_delete
