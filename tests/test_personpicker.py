import logging

import pytest

from pkdiagram import util
from pkdiagram.pyqt import QApplication, QVBoxLayout, QWidget, QQuickItem
from pkdiagram import Scene, Person, QmlWidgetHelper, SceneModel
from pkdiagram.widgets.qml.personpicker import set_new_person, set_existing_person


_log = logging.getLogger(__name__)


class PersonPickerTest(QWidget, QmlWidgetHelper):

    QmlWidgetHelper.registerQmlMethods(
        [
            {"name": "setPersonIdSelected"},
        ]
    )

    def __init__(self, sceneModel, parent=None):
        super().__init__(parent)
        QVBoxLayout(self)
        self.initQmlWidgetHelper(
            "tests/qml/PersonPickerTest.qml", sceneModel=sceneModel
        )
        self.checkInitQml()


@pytest.fixture
def scene():
    scene = Scene()
    scene._sceneModel = SceneModel()
    scene._sceneModel.scene = scene
    yield scene


@pytest.fixture
def picker(scene, qtbot):
    dlg = PersonPickerTest(scene._sceneModel)
    dlg.resize(600, 800)
    dlg.setRootProp("sceneModel", scene._sceneModel)
    dlg.show()
    dlg.findItem("personPicker").clear()
    qtbot.addWidget(dlg)
    qtbot.waitActive(dlg)
    assert dlg.isVisible()

    yield dlg

    dlg.hide()


def test_set_new_person(scene, picker):
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
