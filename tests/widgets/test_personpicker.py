import logging

import pytest

from pkdiagram import util
from pkdiagram.pyqt import QVBoxLayout, QWidget
from pkdiagram.scene import Scene, Person
from pkdiagram.widgets import QmlWidgetHelper
from pkdiagram.widgets.qml.personpicker import set_new_person, set_existing_person


_log = logging.getLogger(__name__)


class PersonPickerTest(QWidget, QmlWidgetHelper):

    QmlWidgetHelper.registerQmlMethods(
        [
            {"name": "setPersonIdSelected"},
            {"name": "clear"},
        ]
    )

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.initQmlWidgetHelper(engine, "tests/qml/PersonPickerTest.qml")
        self.checkInitQml()
        Layout = QVBoxLayout(self)
        Layout.setContentsMargins(0, 0, 0, 0)
        Layout.addWidget(self.qml)


@pytest.fixture
def scene():
    return Scene()


@pytest.fixture
def picker(qtbot, scene, qmlEngine):
    qmlEngine.setScene(scene)
    dlg = PersonPickerTest(qmlEngine)
    dlg.resize(600, 800)
    dlg.show()
    dlg.findItem("personPicker").clear()
    qtbot.addWidget(dlg)
    qtbot.waitActive(dlg)
    assert dlg.isVisible()

    yield dlg

    dlg.hide()
    dlg.deinit()


def test_set_new_person(picker):
    PERSON_NAME = "Someone New"
    set_new_person(picker, PERSON_NAME, returnToFinish=True)
    assert picker.itemProp("personPicker", "isSubmitted") == True
    assert picker.itemProp("personPicker", "person") == None
    assert picker.itemProp("personPicker", "personName") == PERSON_NAME
    assert picker.itemProp("personPicker", "isNewPerson") == True
    assert picker.itemProp("personPicker", "gender") == util.PERSON_KIND_MALE


def test_set_existing_person(scene, picker):
    person = scene.addItem(Person(name="John", lastName="Doe"))
    set_existing_person(picker, person, autoCompleteInput="Joh")
    assert picker.itemProp("personPicker", "isSubmitted") == True
    assert picker.itemProp("personPicker", "isNewPerson") == False
    assert picker.itemProp("personPicker", "person") == person
    assert picker.itemProp("personPicker", "gender") == person.gender()
    assert picker.itemProp("isNewBox", "visible") == False
    assert picker.itemProp("checkImage", "visible") == True
    assert picker.itemProp("personPicker.selectedPeopleModel", "count") == 1


def test_show_autocomplete_popup(scene, picker):
    scene.addItem(Person(name="John", lastName="Doe"))
    set_existing_person(picker, None, autoCompleteInput="Joh", returnToFinish=False)
    # picker.keyClicks(
    #     f"personPicker.textEdit",
    #     "Joh",
    #     resetFocus=False,
    #     returnToFinish=False,
    # )
    assert picker.itemProp("personPicker.textEdit", "text") == "Joh"
    assert picker.itemProp("personPicker.popupListView", "visible") == True
    assert picker.itemProp("personPicker.popupListView", "numVisibleItems") == 1


def test_cannot_add_selected_person(scene, picker):
    person = scene.addItem(Person(name="John", lastName="Doe"))
    picker.setPersonIdSelected(person.id)
    set_new_person(picker, "Patri", gender=False, returnToFinish=False)
    assert picker.itemProp("personPicker.popupListView", "visible") == False
    assert picker.itemProp("personPicker.popupListView", "numVisibleItems") == 0


def test_clear_button_existing_person(scene, picker):
    person = scene.addItem(
        Person(name="John", lastName="Doe", gender=util.PERSON_KIND_FEMALE)
    )
    set_existing_person(picker, person, autoCompleteInput="Joh")
    selectedPeopleModel = picker.itemProp("personPicker", "selectedPeopleModel")
    assert selectedPeopleModel.rowCount() == 1
    assert picker.itemProp("personPicker", "isSubmitted") == True
    assert picker.itemProp("personPicker", "isNewPerson") == False
    assert picker.itemProp("personPicker", "person") == person
    assert picker.itemProp("personPicker", "gender") == person.gender()

    picker.clear()
    assert selectedPeopleModel.rowCount() == 0
    assert picker.itemProp("personPicker", "isSubmitted") == False
    assert picker.itemProp("personPicker", "isNewPerson") == False
    assert picker.itemProp("personPicker", "person") == None
    assert picker.itemProp("personPicker", "gender") == util.PERSON_KIND_MALE
    assert picker.itemProp("personPicker.genderBox", "currentIndex") == 0


def test_clear_button_new_person(picker):

    PERSON_NAME = "Someone New"

    set_new_person(picker, PERSON_NAME, returnToFinish=True)
    assert picker.itemProp("personPicker", "isSubmitted") == True
    assert picker.itemProp("personPicker", "isNewPerson") == True
    assert picker.itemProp("personPicker", "personName") == PERSON_NAME
    assert picker.itemProp("personPicker", "gender") == util.PERSON_KIND_MALE

    picker.clear()
    assert picker.itemProp("personPicker", "isSubmitted") == False
    assert picker.itemProp("personPicker", "isNewPerson") == False
    assert picker.itemProp("personPicker", "personName") == ""
    assert picker.itemProp("personPicker", "gender") == None
