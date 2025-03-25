import logging

import pytest

from pkdiagram import util
from pkdiagram.pyqt import QVBoxLayout, QWidget, QQuickItem
from pkdiagram.scene import Scene, Person
from pkdiagram.widgets import QmlWidgetHelper
from pkdiagram.models import SceneModel
from pkdiagram.widgets.qml.peoplepicker import (
    add_new_person,
    add_existing_person,
    delete_person,
)

_log = logging.getLogger(__name__)


class PeoplePickerTest(QWidget, QmlWidgetHelper):

    QmlWidgetHelper.registerQmlMethods(
        [
            {"name": "setExistingPeople"},
            {"name": "peopleEntries", "return": True},
        ]
    )

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.initQmlWidgetHelper(engine, "tests/qml/PeoplePickerTest.qml")
        self.checkInitQml()

        Layout = QVBoxLayout(self)
        Layout.setContentsMargins(0, 0, 0, 0)
        Layout.addWidget(self.qml)

    def test_setExistingPeople(self, people):
        peoplePicker = self.rootProp("peoplePicker")
        itemAddDone = util.Condition(peoplePicker.itemAddDone)
        self.setExistingPeople(people)
        util.waitALittle()
        while itemAddDone.callCount < len(people):
            _log.info(
                f"Waiting for {len(people) - itemAddDone.callCount} / {len(people)} itemAddDone signals"
            )
            assert itemAddDone.wait() == True
        # _log.info(f"Got {itemAddDone.callCount} / {len(people)} itemAddDone signals")


@pytest.fixture
def scene(scene):
    scene.addItem(Person(first_name="Patrick", last_name="Stinson"))
    scene._sceneModel = SceneModel()
    scene._sceneModel.scene = scene
    yield scene


@pytest.fixture
def picker(scene, qtbot, qmlEngine):
    qmlEngine.setScene(scene)
    dlg = PeoplePickerTest(qmlEngine)
    dlg.resize(600, 800)
    dlg.show()
    dlg.rootProp("peoplePicker").clear()
    qtbot.addWidget(dlg)
    qtbot.waitActive(dlg)
    assert dlg.isVisible()

    yield dlg

    dlg.hide()
    dlg.deinit()


@pytest.fixture
def model(picker):
    yield picker.rootProp("peoplePicker").property("model")


def test_init_fields(scene, picker):
    personA = scene.addItem(
        Person(name="Joseph", lastName="Donner", gender=util.PERSON_KIND_MALE)
    )
    personB = scene.addItem(
        Person(name="Josephina", lastName="Donner", gender=util.PERSON_KIND_FEMALE)
    )
    picker.test_setExistingPeople([personA, personB])
    entries = picker.peopleEntries()
    assert len(entries) == 2
    assert entries[0]["person"] == personA
    assert entries[0]["isNewPerson"] == False
    assert entries[0]["gender"] == util.PERSON_KIND_MALE
    assert entries[1]["person"] == personB
    assert entries[1]["isNewPerson"] == False
    assert entries[1]["gender"] == util.PERSON_KIND_FEMALE


def test_one_existing_one_not(scene, picker, model):
    existingPerson = scene.addItem(Person(name="John", lastName="Doe"))
    existingPersonDelegate = add_existing_person(
        picker, existingPerson, autoCompleteInput="John"
    )
    assert (
        existingPersonDelegate.findChild(QQuickItem, "genderBox").property(
            "currentIndex"
        )
        == 0
    )
    assert (
        existingPersonDelegate.findChild(QQuickItem, "isNewBox").property("visible")
        == False
    )
    assert (
        existingPersonDelegate.findChild(QQuickItem, "checkImage").property("visible")
        == True
    )
    peopleEntries = picker.peopleEntries()
    assert len(peopleEntries) == 1
    assert peopleEntries[0]["isNewPerson"] == False
    assert peopleEntries[0]["person"] == existingPerson
    assert peopleEntries[0]["personName"] == "John Doe"
    assert peopleEntries[0]["gender"] == util.PERSON_KIND_MALE

    newPersonDelegate = add_new_person(
        picker, "Someone new", gender=util.PERSON_KIND_FEMALE
    )
    peopleEntries = picker.peopleEntries()
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
    assert (
        newPersonDelegate.findChild(QQuickItem, "isNewBox").property("visible") == True
    )
    assert (
        newPersonDelegate.findChild(QQuickItem, "checkImage").property("visible")
        == False
    )


def test_add_lots_of_mixed(scene, picker, model):
    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Joseph", lastName="Donner"))
    personC = scene.addItem(Person(name="Jane", lastName="Donner"))
    add_existing_person(picker, personA, autoCompleteInput="Joh")
    add_new_person(picker, "Someone new 1", gender=util.PERSON_KIND_FEMALE)
    add_existing_person(
        picker, personB, autoCompleteInput="Jose", gender=util.PERSON_KIND_UNKNOWN
    )
    add_existing_person(
        picker, personC, autoCompleteInput="Jan", gender=util.PERSON_KIND_ABORTION
    )
    add_new_person(picker, "Someone new 2")
    add_new_person(picker, "Someone new 3")
    add_new_person(picker, "Someone new 4")
    peopleEntries = picker.peopleEntries()
    newEntries = [x for x in peopleEntries if x["isNewPerson"] == True]
    existingEntries = [x for x in peopleEntries if x["isNewPerson"] == False]
    assert len(newEntries) == 4
    assert len(peopleEntries) == 7
    assert len(existingEntries) == 3
    joseEntry = next(x for x in existingEntries if x["person"] == personB)
    assert joseEntry["gender"] == util.PERSON_KIND_UNKNOWN
    personCEntry = next(x for x in existingEntries if x["person"] == personC)
    assert personCEntry["gender"] == util.PERSON_KIND_ABORTION


def test_add_then_delete_then_add(scene, picker, model):
    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Joseph", lastName="Donner"))
    delegate = add_existing_person(picker, personA, autoCompleteInput="Joh")
    assert model.rowCount() == 1
    delete_person(picker, delegate)
    assert model.rowCount() == 0
    add_existing_person(picker, personB, autoCompleteInput="Jos")
    assert model.rowCount() == 1


def test_maintain_selectedPeopleModel(scene, picker, model):
    personA = scene.addItem(Person(name="John", lastName="Doe"))
    delegate = add_existing_person(picker, personA, autoCompleteInput="Joh")
    assert model.rowCount() == 1
    assert picker.itemProp("peoplePicker.selectedPeopleModel", "count") == 1
    delete_person(picker, delegate)
    assert model.rowCount() == 0
    assert picker.itemProp("peoplePicker.selectedPeopleModel", "count") == 0


# test_one_existing_one_not
# test_cancel_add_new
# test_add_existing_then_delete
# test_add_new__then_delete
