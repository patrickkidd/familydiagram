import logging

import pytest

from pkdiagram import util, objects
from pkdiagram.pyqt import Qt, QVBoxLayout, QWidget, QQuickItem
from pkdiagram import Scene, Person, QmlWidgetHelper, SceneModel
from test_peoplepicker import add_and_keyClicks


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
    scene.addItem(Person(first_name="Patrick", last_name="Stinson"))
    scene._sceneModel = SceneModel()
    scene._sceneModel.scene = scene
    scene.addItem(Person(name="Patrick", lastName="Stinson"))
    scene.addItem(Person(name="Connie", lastName="Service"))
    scene.addItem(Person(name="Lulu", lastName="Lemon"))
    scene.addItem(Person(name="John", lastName="Doey"))
    scene.addItem(Person(name="Jayne", lastName="Thermos"))
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


def set_new_keyClicks(
    picker: QmlWidgetHelper,
    textInput: str,
    gender: str = None,
    returnToFinish: bool = False,
) -> QQuickItem:
    _log.info(f"add_and_keyClicks('{textInput}', {returnToFinish})")

    if gender is None:
        gender = util.PERSON_KIND_NAMES[0]

    # textEdit = picker.findChild(QQuickItem, "textEdit")
    assert picker.itemProp("popupListView", "visible") == False
    picker.keyClicks(
        "textEdit", textInput, resetFocus=False, returnToFinish=returnToFinish
    )
    if gender:
        picker.clickComboBoxItem("genderComboBox", gender)


def set_existing_person(
    picker: QmlWidgetHelper,
    person: str,
    autoCompleteInput: str = None,
    textEdit="personPicker.textEdit",
    returnToFinish: bool = False,
) -> QQuickItem:
    _log.info(f"add_existing_keyClicks('{textEdit}', {returnToFinish})")
    textEditItem = picker.findItem(textEdit)
    assert textEditItem is not None
    assert picker.itemProp("personPicker.popupListView", "visible") == False
    picker.keyClicks(
        textEditItem, autoCompleteInput, resetFocus=False, returnToFinish=returnToFinish
    )
    assert picker.itemProp(f"personPicker.popupListView", "visible") == True
    picker.clickListViewItem_actual(
        f"personPicker.popupListView", person.fullNameOrAlias()
    ) == True


def test_add_new_person(scene, picker):
    set_new_keyClicks(picker, "Someone New", returnToFinish=True)
    assert picker.itemProp("personPicker", "isSubmitted") == True
    assert picker.itemProp("personPicker", "person") == None
    assert picker.itemProp("personPicker", "personName") == "Someone New"
    assert picker.itemProp("personPicker", "isNewPerson") == True
    assert picker.itemProp("personPicker", "gender") == "male"


def test_add_existing_person(scene, picker):
    patrick = scene.query1(name="Patrick", lastName="Stinson")
    set_existing_person(picker, patrick, autoCompleteInput="Sti")
    assert picker.itemProp("personPicker", "isSubmitted") == True
    assert picker.itemProp("personPicker", "isNewPerson") == False
    assert picker.itemProp("personPicker", "person") == patrick
    assert picker.itemProp("isNewBox", "visible") == False
    assert picker.itemProp("checkImage", "visible") == True
    assert picker.itemProp("personPicker.selectedPeopleModel", "count") == 1


def test_show_autocomplete_popup(scene, picker):
    patrick = scene.query1(name="Patrick", lastName="Stinson")
    set_new_keyClicks(picker, "Patri", gender=False, returnToFinish=False)
    assert picker.itemProp("personPicker.popupListView", "visible") == True
    assert picker.itemProp("personPicker.popupListView", "numVisibleItems") == 1


def test_cannot_add_selected_person(scene, picker):
    patrick = scene.query1(name="Patrick", lastName="Stinson")
    picker.setPersonIdSelected(patrick.id)
    # picker.rootProp("selectedPeopleModel").append(
    #     {"person": patrick, "isNewPerson": False}
    # )
    set_new_keyClicks(picker, "Patri", gender=False, returnToFinish=False)
    assert picker.itemProp("personPicker.popupListView", "visible") == False
    assert picker.itemProp("personPicker.popupListView", "numVisibleItems") == 0
