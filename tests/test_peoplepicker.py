import logging

import pytest

from pkdiagram import util, objects
from pkdiagram.pyqt import Qt, QVBoxLayout, QWidget, QQuickItem
from pkdiagram import Scene, Person, QmlWidgetHelper, SceneModel

_log = logging.getLogger(__name__)


class PeoplePickerTest(QWidget, QmlWidgetHelper):
    def __init__(self, sceneModel, parent=None):
        super().__init__(parent)
        QVBoxLayout(self)
        self.initQmlWidgetHelper(
            "tests/qml/PeoplePickerTest.qml", sceneModel=sceneModel
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
    dlg = PeoplePickerTest(scene._sceneModel)
    dlg.resize(600, 800)
    dlg.setRootProp("sceneModel", scene._sceneModel)
    dlg.show()
    dlg.findItem("peoplePicker").clear()
    qtbot.addWidget(dlg)
    qtbot.waitActive(dlg)
    assert dlg.isVisible()

    yield dlg

    dlg.hide()


def add_and_keyClicks(
    dlg: QmlWidgetHelper,
    textInput: str,
    peoplePicker="peoplePicker",
    returnToFinish: bool = True,
) -> QQuickItem:

    _log.info(f"add_and_keyClicks('{textInput}', {returnToFinish})")

    peoplePickerItem = dlg.findItem(peoplePicker)
    itemAddDone = util.Condition(peoplePickerItem.itemAddDone)
    dlg.mouseClick(f"{peoplePicker}.addButton")
    assert itemAddDone.wait() == True
    itemDelegate = itemAddDone.callArgs[-1][0]
    textEdit = itemDelegate.findChild(QQuickItem, "textEdit")
    popupListView = itemDelegate.findChild(QQuickItem, "popupListView")
    assert popupListView.property("visible") == False
    dlg.keyClicks(textEdit, textInput, resetFocus=False, returnToFinish=returnToFinish)
    return itemDelegate


def add_new_person(
    dlg: QmlWidgetHelper,
    textInput: str,
    peoplePicker="peoplePicker",
    gender: str = None,
    returnToFinish=True,
) -> QQuickItem:
    itemDelegate = add_and_keyClicks(
        dlg,
        textInput,
        peoplePicker=peoplePicker,
        returnToFinish=returnToFinish,
    )
    if gender is not None:
        genderBox = itemDelegate.findChild("genderBox")
        assert genderBox is not None, f"Could not find genderBox for {itemDelegate}"
        dlg.clickComboBoxItem(genderBox, gender)

    return itemDelegate


def add_existing_person(
    picker: QmlWidgetHelper,
    person: Person,
    autoCompleteInput: str = None,
    peoplePicker="peoplePicker",
) -> QQuickItem:
    if autoCompleteInput is None:
        autoCompleteInput = person.fullNameOrAlias()
    itemDelegate = add_and_keyClicks(
        picker,
        autoCompleteInput,
        peoplePicker=peoplePicker,
        returnToFinish=False,
    )
    popupListView = itemDelegate.findChild(QQuickItem, "popupListView")
    assert popupListView.property("visible") == True
    picker.clickListViewItem_actual(popupListView, person.fullNameOrAlias()) == True
    return itemDelegate


def _delete_person(
    picker: QmlWidgetHelper, delegate: QQuickItem, peoplePicker="peoplePicker"
):
    _log.info(f"_delete_person({delegate})")
    picker.mouseClick(delegate)
    removeButton = picker.findItem("buttons_removeButton")
    picker.mouseClick(removeButton)


def _get_role_id(model, role_name):
    roles = model.roleNames()
    for role_id, name in roles.items():
        if name == role_name:
            return role_id


def test_one_existing_one_not(scene, picker):
    model = picker.itemProp("peoplePicker", "model")
    patrick = scene.query1(name="Patrick", lastName="Stinson")

    existingPersonDelegate = add_existing_person(
        picker, patrick, autoCompleteInput="Sti"
    )
    assert picker.itemProp("peoplePicker.model", "count") == 1
    assert (
        existingPersonDelegate.findChild(QQuickItem, "isNewBox").property("visible")
        == False
    )
    assert (
        existingPersonDelegate.findChild(QQuickItem, "checkImage").property("visible")
        == True
    )
    existingPerson = scene.query1(firstName="Patrick", lastName="Stinson")
    PersonNameRole = _get_role_id(model, "personName")
    IsNewPersonRole = _get_role_id(model, "isNewPerson")
    PersonRole = _get_role_id(model, "person")  # Added dynamically
    person = model.index(0, 0).data(PersonRole)
    isNewPerson = model.index(0, 0).data(IsNewPersonRole)
    personName = model.index(0, 0).data(PersonNameRole)
    assert PersonRole is not None
    assert model.rowCount() == 1
    assert model.index(0, 0).data(PersonRole) == existingPerson

    newPersonDelegate = add_new_person(picker, "Someone new")
    assert picker.itemProp("peoplePicker.model", "count") == 2
    assert (
        newPersonDelegate.findChild(QQuickItem, "isNewBox").property("visible") == True
    )
    assert (
        newPersonDelegate.findChild(QQuickItem, "checkImage").property("visible")
        == False
    )
    newPerson = scene.query1(firstName="Someone", lastName="New")
    assert model.index(0, 0).data(PersonRole) == existingPerson
    assert model.index(1, 0).data(PersonRole) == newPerson


def test_add_lots_of_mixed(scene, picker):
    patrick = scene.query1(name="Patrick")
    lulu = scene.query1(name="Lulu")
    connie = scene.query1(name="Connie")
    model = picker.itemProp("peoplePicker", "model")
    add_existing_person(picker, patrick, autoCompleteInput="Sti")
    add_new_person(picker, "Someone new")
    add_existing_person(picker, lulu, autoCompleteInput="Lulu")
    add_existing_person(picker, connie, autoCompleteInput="Ser")
    add_new_person(picker, "Someone new 2")
    add_new_person(picker, "Someone new 3")
    add_new_person(picker, "Someone new 4")

    PersonRole = _get_role_id(model, "person")  # Added dynamically
    IsNewPersonRole = _get_role_id(model, "isNewPerson")  # Added dynamically
    model = picker.itemProp("peoplePicker", "model")
    assert model.rowCount() == 7
    newPeople = [
        model.index(i, 0).data(PersonRole)
        for i in range(model.rowCount())
        if model.index(i, 0).data(IsNewPersonRole)
    ]
    existingPeople = [
        model.index(i, 0).data(PersonRole)
        for i in range(model.rowCount())
        if not model.index(i, 0).data(IsNewPersonRole)
    ]
    assert len(newPeople) == 4
    assert len(existingPeople) == 3


def test_add_then_delete_then_add(scene, picker):
    patrick = scene.query1(name="Patrick")
    connie = scene.query1(name="Connie")
    model = picker.itemProp("peoplePicker", "model")
    delegate = add_existing_person(picker, patrick, autoCompleteInput="Sti")
    assert model.rowCount() == 1
    _delete_person(picker, delegate)
    assert model.rowCount() == 0
    add_existing_person(picker, connie, autoCompleteInput="Ser")
    assert model.rowCount() == 1


def test_maintain_selectedPeopleModel(scene, picker):
    patrick = scene.query1(name="Patrick")
    model = picker.itemProp("peoplePicker", "model")
    delegate = add_existing_person(picker, patrick, autoCompleteInput="Sti")
    assert model.rowCount() == 1
    assert picker.itemProp("peoplePicker.selectedPeopleModel", "count") == 1
    _delete_person(picker, delegate)
    assert model.rowCount() == 0
    assert picker.itemProp("peoplePicker.selectedPeopleModel", "count") == 0


# test_one_existing_one_not
# test_cancel_add_new
# test_add_existing_then_delete
# test_add_new__then_delete
