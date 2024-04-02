import logging

import pytest

from pkdiagram import util, objects
from pkdiagram.pyqt import Qt, QVBoxLayout, QWidget, QQuickItem
from pkdiagram import Scene, Person, QmlWidgetHelper, SceneModel

_log = logging.getLogger(__name__)


class PeoplePickerTest(QWidget, QmlWidgetHelper):

    QmlWidgetHelper.registerQmlMethods(
        [
            {"name": "setExistingPeople"},
            {"name": "peopleEntries", "return": True},
        ]
    )

    def __init__(self, sceneModel, parent=None):
        super().__init__(parent)
        QVBoxLayout(self)
        self.initQmlWidgetHelper(
            "tests/qml/PeoplePickerTest.qml", sceneModel=sceneModel
        )
        self.checkInitQml()

    def test_setExistingPeople(self, people):
        peoplePickerItem = self.findItem("peoplePicker")
        itemAddDone = util.Condition(peoplePickerItem.itemAddDone)
        self.setExistingPeople(people)
        while itemAddDone.callCount < len(people):
            _log.info(
                f"Waiting for {len(people) - itemAddDone.callCount} / {len(people)} itemAddDone signals"
            )
            assert itemAddDone.wait() == True
        # _log.info(f"Got {itemAddDone.callCount} / {len(people)} itemAddDone signals")


@pytest.fixture
def scene():
    scene = Scene()
    scene.addItem(Person(first_name="Patrick", last_name="Stinson"))
    scene._sceneModel = SceneModel()
    scene._sceneModel.scene = scene
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


from PyQt5.QtWidgets import QApplication


def add_and_keyClicks(
    dlg: QmlWidgetHelper,
    textInput: str,
    peoplePicker="peoplePicker",
    returnToFinish: bool = True,
) -> QQuickItem:

    # _log.info(f"add_and_keyClicks('{textInput}', '{peoplePicker}', {returnToFinish})")

    peoplePickerItem = dlg.findItem(peoplePicker)
    if not peoplePickerItem.metaObject().className().startswith("PeoplePicker"):
        raise TypeError(
            f"Expected a PeoplePicker, got {peoplePickerItem.metaObject().className()}"
        )
    elif not peoplePickerItem.property("visible"):
        raise ValueError(f"Expected PeoplePicker '{peoplePicker}' to be visible.")
    itemAddDone = util.Condition(peoplePickerItem.itemAddDone)
    QApplication.processEvents()
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
        genderLabel = next(
            x["name"] for x in util.PERSON_KINDS if x["kind"] == util.PERSON_KIND_FEMALE
        )

        genderBox = itemDelegate.findChild(QQuickItem, "genderBox")
        assert genderBox is not None, f"Could not find genderBox for {itemDelegate}"
        dlg.clickComboBoxItem(genderBox, genderLabel)

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


def test_one_existing_one_not(scene, picker):
    model = picker.itemProp("peoplePicker", "model")
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


def test_add_lots_of_mixed(scene, picker):
    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Joseph", lastName="Donner"))
    personC = scene.addItem(Person(name="Jane", lastName="Donner"))
    model = picker.itemProp("peoplePicker", "model")
    add_existing_person(picker, personA, autoCompleteInput="Joh")
    add_new_person(picker, "Someone new 1")
    add_existing_person(picker, personB, autoCompleteInput="Jose")
    add_existing_person(picker, personC, autoCompleteInput="Jan")
    add_new_person(picker, "Someone new 2")
    add_new_person(picker, "Someone new 3")
    add_new_person(picker, "Someone new 4")
    peopleEntries = picker.peopleEntries()
    newEntries = [x for x in peopleEntries if x["isNewPerson"] == True]
    existingEntries = [x for x in peopleEntries if x["isNewPerson"] == False]
    assert len(newEntries) == 4
    assert len(peopleEntries) == 7
    assert len(existingEntries) == 3


def test_add_then_delete_then_add(scene, picker):
    personA = scene.addItem(Person(name="John", lastName="Doe"))
    personB = scene.addItem(Person(name="Joseph", lastName="Donner"))
    model = picker.itemProp("peoplePicker", "model")
    delegate = add_existing_person(picker, personA, autoCompleteInput="Joh")
    assert model.rowCount() == 1
    _delete_person(picker, delegate)
    assert model.rowCount() == 0
    add_existing_person(picker, personB, autoCompleteInput="Jos")
    assert model.rowCount() == 1


def test_maintain_selectedPeopleModel(scene, picker):
    personA = scene.addItem(Person(name="John", lastName="Doe"))
    model = picker.itemProp("peoplePicker", "model")
    delegate = add_existing_person(picker, personA, autoCompleteInput="Joh")
    assert model.rowCount() == 1
    assert picker.itemProp("peoplePicker.selectedPeopleModel", "count") == 1
    _delete_person(picker, delegate)
    assert model.rowCount() == 0
    assert picker.itemProp("peoplePicker.selectedPeopleModel", "count") == 0


# test_one_existing_one_not
# test_cancel_add_new
# test_add_existing_then_delete
# test_add_new__then_delete
