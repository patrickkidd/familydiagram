import logging

import pytest

from pkdiagram import util, objects
from pkdiagram.pyqt import Qt, QApplication, QVBoxLayout, QWidget, QQuickItem
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


def set_new_person(
    dlg: QmlWidgetHelper,
    textInput: str,
    personPicker: str = "personPicker",
    gender: str = None,
    returnToFinish: bool = True,
) -> QQuickItem:
    _log.info(f"set_new_person('{textInput}', {returnToFinish})")

    if gender is None:
        gender = util.PERSON_KIND_NAMES[0]

    # textEdit = dlg.findChild(QQuickItem, "textEdit")
    assert dlg.itemProp(f"{personPicker}.popupListView", "visible") == False
    dlg.keyClicks(
        f"{personPicker}.textEdit",
        textInput,
        resetFocus=False,
        returnToFinish=returnToFinish,
    )
    if gender:
        dlg.clickComboBoxItem(f"{personPicker}.genderBox", gender)
    QApplication.processEvents()


def set_existing_person(
    dlg: QmlWidgetHelper,
    person: str,
    autoCompleteInput: str = None,
    personPicker: str = "personPicker",
    returnToFinish: bool = False,
) -> QQuickItem:
    if not autoCompleteInput:
        autoCompleteInput = person.fullNameOrAlias()

    _log.info(
        f"set_existing_person('{personPicker}.textEdit', '{autoCompleteInput}', returnToFinish={returnToFinish})"
    )
    assert dlg.itemProp(f"{personPicker}.popupListView", "visible") == False
    personPickerItem = dlg.findItem(personPicker)
    numVisibleAutoCompleteItemsUpdated = util.Condition(
        personPickerItem.numVisibleAutoCompleteItemsUpdated
    )
    dlg.keyClicks(
        f"{personPicker}.textEdit",
        autoCompleteInput,
        resetFocus=False,
        returnToFinish=False,
    )
    assert numVisibleAutoCompleteItemsUpdated.wait() == True
    assert dlg.itemProp(f"{personPicker}.textEdit", "text") == autoCompleteInput
    assert dlg.itemProp(f"{personPicker}.popupListView", "visible") == True
    assert dlg.itemProp(f"{personPicker}.popupListView", "numVisibleItems") > 0
    if person:
        dlg.clickListViewItem_actual(
            f"{personPicker}.popupListView", person.fullNameOrAlias()
        )
        assert dlg.itemProp(f"{personPicker}.popupListView", "visible") == False


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
