import logging

import pytest

from pkdiagram.pyqt import Qt, QDateTime, QPointF
from pkdiagram import util
from pkdiagram.scene import (
    Person,
    Event,
    Layer,
    Scene,
)
from pkdiagram.views import QmlDrawer
from pkdiagram.models import LayerItemLayersModel


pytestmark = [
    pytest.mark.component("PersonProperties"),
    pytest.mark.depends_on("PersonPropertiesModel"),
]


_log = logging.getLogger(__name__)


@pytest.fixture
def view(qtbot, qmlEngine, scene):
    qmlEngine.setScene(scene)
    _view = QmlDrawer(
        qmlEngine,
        "qml/PersonProperties.qml",
        propSheetModel="personModel",
        resizable=True,
    )
    _view.setScene(qmlEngine.sceneModel.scene)
    _view.checkInitQml()
    _view.model = _view.rootProp(_view.propSheetModel)
    _view.show()
    qtbot.addWidget(_view)
    qtbot.waitActive(_view)

    yield _view

    _view.hide()  # resets .items
    _view.deinit()
    qmlEngine.setScene(None)
    scene.deinit()


def test_init_fields(view, scene):

    FIRST_NAME = "Someone"
    MIDDLE_NAME = "Middle"
    LAST_NAME = "Last"
    NICK_NAME = "Nick"
    BIRTH_NAME = "Birth"
    SIZE = 5
    NOTES = "who knows anyway"
    DIAGRAM_NOTES = "Diagram notes\n\nmulti-line\n\n\n\n entry"

    person = scene.addItem(
        Person(
            name=FIRST_NAME,
            middleName=MIDDLE_NAME,
            lastName=LAST_NAME,
            nickName=NICK_NAME,
            birthName=BIRTH_NAME,
            size=SIZE,
            gender=util.PERSON_KIND_FEMALE,
            adopted=True,
            deceased=True,
            notes=NOTES,
            diagramNotes=DIAGRAM_NOTES,
            primary=True,
            hideDetails=True,
            hideDates=False,
            hideVariables=False,
        )
    )
    view.show([person])

    assert view.rootProp("firstNameEdit").property("text") == FIRST_NAME
    assert view.rootProp("middleNameEdit").property("text") == MIDDLE_NAME
    assert view.rootProp("lastNameEdit").property("text") == LAST_NAME
    assert view.rootProp("nickNameEdit").property("text") == NICK_NAME
    assert view.rootProp("birthNameEdit").property("text") == BIRTH_NAME
    assert view.rootProp("sizeBox").property(
        "currentText"
    ) == util.personSizeNameFromSize(SIZE)
    assert view.rootProp("kindBox").property("currentText") == "Female"
    assert view.rootProp("adoptedBox").property("checkState") == Qt.Checked
    assert view.rootProp("primaryBox").property("checkState") == Qt.Checked
    assert view.rootProp("deceasedBox").property("checkState") == Qt.Checked
    assert view.rootProp("hideDetailsBox").property("checkState") == Qt.Checked
    assert view.rootProp("hideDatesBox").property("checkState") == Qt.Unchecked
    assert view.rootProp("hideVariablesBox").property("checkState") == Qt.Unchecked
    assert view.rootProp("notesEdit").property("text") == NOTES


def test_set_props(view, scene):
    person = scene.addItem(Person())
    view.show([person])

    ## Values

    FIRST_NAME = "Someone"
    MIDDLE_NAME = "Middle"
    LAST_NAME = "Last"
    NICK_NAME = "Nick"
    BIRTH_NAME = "Birth"
    SIZE = "Small"
    GENDER = util.personKindFromIndex(1)
    ADOPTED = Qt.Checked
    PRIMARY = Qt.Checked
    DECEASED = Qt.Checked
    NOTES = "who knows anyway"
    HIDE_DETAILS = Qt.Checked
    HIDE_DATES = Qt.Checked
    HIDE_VARIABLES = Qt.Checked
    DIAGRAM_NOTES = "Diagram notes\n\nmulti-line\n\n\n\n entry"

    ## Items

    personPage = view.rootProp("personPage")

    firstNameEdit = view.rootProp("firstNameEdit")
    middleNameEdit = view.rootProp("middleNameEdit")
    lastNameEdit = view.rootProp("lastNameEdit")
    nickNameEdit = view.rootProp("nickNameEdit")
    birthNameEdit = view.rootProp("birthNameEdit")
    sizeBox = view.rootProp("sizeBox")
    kindBox = view.rootProp("kindBox")
    adoptedBox = view.rootProp("adoptedBox")
    primaryBox = view.rootProp("primaryBox")

    deceasedBox = view.rootProp("deceasedBox")
    notesEdit = view.rootProp("notesEdit")
    hideDetailsBox = view.rootProp("hideDetailsBox")
    hideDatesBox = view.rootProp("hideDatesBox")
    hideVariablesBox = view.rootProp("hideVariablesBox")
    diagramNotesEdit = view.rootProp("diagramNotesEdit")

    ## Set

    view.keyClicksItem(firstNameEdit, FIRST_NAME)
    view.keyClicksItem(middleNameEdit, MIDDLE_NAME)
    view.keyClicksItem(lastNameEdit, LAST_NAME)
    view.keyClicksItem(nickNameEdit, NICK_NAME)
    view.keyClicksItem(birthNameEdit, BIRTH_NAME)

    view.clickComboBoxItem(sizeBox, SIZE)
    view.clickComboBoxItem(kindBox, util.personKindNameFromKind(GENDER))

    view.scrollToItem(personPage, adoptedBox)
    view.mouseClickItem(adoptedBox)

    view.scrollToItem(personPage, deceasedBox)
    view.mouseClickItem(deceasedBox)

    view.scrollToItem(personPage, primaryBox)
    view.mouseClickItem(primaryBox)

    view.scrollToItem(personPage, hideDetailsBox)
    view.mouseClickItem(hideDetailsBox)

    view.scrollToItem(personPage, hideDatesBox)
    view.mouseClickItem(hideDatesBox)

    view.scrollToItem(personPage, hideVariablesBox)
    view.mouseClickItem(hideVariablesBox)

    view.scrollToItem(personPage, diagramNotesEdit)
    view.keyClicksItem(diagramNotesEdit, DIAGRAM_NOTES, returnToFinish=False)

    view.setCurrentTab("notes")
    view.keyClicksItem(notesEdit, NOTES, returnToFinish=False)

    ## Assert

    assert person.name() == FIRST_NAME
    assert person.middleName() == MIDDLE_NAME
    assert person.lastName() == LAST_NAME
    assert person.nickName() == NICK_NAME
    assert person.birthName() == BIRTH_NAME
    assert person.size() == util.personSizeFromName(SIZE)
    assert person.gender() == GENDER
    assert person.adopted() == util.csToBool(ADOPTED)
    assert person.primary() == util.csToBool(PRIMARY)
    assert person.deceased() == util.csToBool(DECEASED)
    assert person.notes() == NOTES
    assert person.hideDetails() == util.csToBool(HIDE_DETAILS)
    assert person.hideDates() == util.csToBool(HIDE_DATES)
    assert person.hideVariables() == util.csToBool(HIDE_VARIABLES)
    assert person.diagramNotes() == DIAGRAM_NOTES
    assert person.notes() == NOTES


def test_person_readOnlyFields(view, qmlEngine, scene):
    person = Person()
    scene.addItem(person)
    scene.setReadOnly(True)
    qmlEngine.sceneModel.refreshProperty("readOnly")
    assert view.rootProp("firstNameEdit").property("enabled") == False
    assert view.rootProp("middleNameEdit").property("enabled") == False
    assert view.rootProp("lastNameEdit").property("enabled") == False
    assert view.rootProp("ageBox").property("enabled") == False


def test_empty_strings_reset_string_fields(view, scene):
    person = scene.addItem(Person())

    person.setName("someone")
    person.setMiddleName("middle")
    person.setLastName("last")
    person.setNickName("nick name")
    person.setBirthName("birth name")
    person.setNotes("some notes\nwith multiple\nlines")

    view.show([person])

    firstNameEdit = view.rootProp("firstNameEdit")
    middleNameEdit = view.rootProp("middleNameEdit")
    lastNameEdit = view.rootProp("lastNameEdit")
    nickNameEdit = view.rootProp("nickNameEdit")
    birthNameEdit = view.rootProp("birthNameEdit")
    notesEdit = view.rootProp("notesEdit")

    view.keyClicksClear(firstNameEdit)
    view.keyClicksClear(middleNameEdit)
    view.keyClicksClear(lastNameEdit)
    view.keyClicksClear(nickNameEdit)
    view.keyClicksClear(birthNameEdit)
    view.keyClickItem(notesEdit, Qt.Key_Backspace)
    view.resetFocusItem(notesEdit)

    assert person.name() is None
    assert person.middleName() is None
    assert person.lastName() is None
    assert person.nickName() is None
    assert person.birthName() is None
    assert person.notes() is None


def test_scene_readOnlyFields(view, qmlEngine, scene):
    scene.setReadOnly(True)
    qmlEngine.sceneModel.refreshProperty("readOnly")
    layer = scene.addItem(
        Layer(active=True)
    )  # so meta ctls are properly enabled/disabled
    person = scene.addItem(Person())
    view.show([person])

    assert not view.rootProp("firstNameEdit").property("enabled")
    assert not view.rootProp("middleNameEdit").property("enabled")
    assert not view.rootProp("lastNameEdit").property("enabled")
    assert not view.rootProp("nickNameEdit").property("enabled")
    assert not view.rootProp("birthNameEdit").property("enabled")
    assert not view.rootProp("sizeBox").property("enabled")
    assert not view.rootProp("kindBox").property("enabled")
    assert not view.rootProp("adoptedBox").property("enabled")
    assert not view.rootProp("primaryBox").property("enabled")
    assert not view.rootProp("deceasedBox").property("enabled")
    assert not view.rootProp("notesEdit").property("enabled")
    assert not view.rootProp("hideDetailsBox").property("enabled")
    assert not view.rootProp("hideDatesBox").property("enabled")
    assert not view.rootProp("hideVariablesBox").property("enabled")
    assert not view.rootProp("colorBox").property("enabled")
    assert not view.rootProp("resetColorButton").property("enabled")
    assert not view.rootProp("deemphasizeBox").property("enabled")
    assert not view.rootProp("resetDeemphasizeButton").property("enabled")


def test_clear_layered_pos(view, monkeypatch, scene):
    """It was taking two clicks to clear the person props."""
    resetItemPosButton = view.rootProp("resetItemPosButton")
    layer = Layer()
    scene.addItem(layer)
    scene.setStorePositionsInLayers(True)
    person = Person()
    scene.addItem(person)
    view.show([person])
    view.setCurrentTab("meta")

    monkeypatch.setattr(scene, "isMovingSomething", lambda: True)
    person.setItemPos(QPointF(100, 100))  # default
    layer.setActive(True)
    layer.setStoreGeometry(True)
    person.setItemPos(QPointF(200, 200))  # in layer
    personModel = view.rootProp("personModel")
    assert personModel.itemPos == QPointF(200, 200)
    assert personModel.itemPos == person.itemPos()
    assert resetItemPosButton.property("enabled") == True
    assert personModel.isItemPosSetInCurrentLayer == True

    view.mouseClickItem(resetItemPosButton)
    assert personModel.itemPos == QPointF(100, 100)
    assert personModel.isItemPosSetInCurrentLayer == False
    assert resetItemPosButton.property("enabled") == False


# def test_tabKeys():
#     ui = view.ui
#     person = Person()
#     view.show([person])

#     view.keyClick(view, Qt.Key_BracketRight, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 1

#     view.keyClick(view, Qt.Key_BracketRight, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 2

#     view.keyClick(view, Qt.Key_BracketLeft, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 1

#     view.keyClick(view, Qt.Key_BracketLeft, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 0

#     view.keyClick(view, Qt.Key_BracketLeft, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 0


def test_names_hidden(view, scene):
    assert not scene.showAliases()  # just to be safe

    person = Person(
        name="Harold",
        middleName="Kidd",
        lastName="Stinson",
        birthName="you guessed it",
        nickName="Harry",
    )
    scene.addItem(person)
    chunk = {}
    person.write(chunk)
    person.read(chunk, chunk.get)  # assigns alias
    view.show([person])
    firstNameEdit = view.rootProp("firstNameEdit")
    middleNameEdit = view.rootProp("middleNameEdit")
    lastNameEdit = view.rootProp("lastNameEdit")
    birthNameEdit = view.rootProp("birthNameEdit")
    nickNameEdit = view.rootProp("nickNameEdit")

    assert firstNameEdit.property("enabled") == True
    assert middleNameEdit.property("enabled") == True
    assert lastNameEdit.property("enabled") == True
    assert birthNameEdit.property("enabled") == True
    assert nickNameEdit.property("enabled") == True
    assert firstNameEdit.property("text") == "Harold"
    assert middleNameEdit.property("text") == "Kidd"
    assert lastNameEdit.property("text") == "Stinson"
    assert birthNameEdit.property("text") == "you guessed it"
    assert nickNameEdit.property("text") == "Harry"

    scene.setShowAliases(True)
    assert firstNameEdit.property("enabled") == False
    assert middleNameEdit.property("enabled") == False
    assert lastNameEdit.property("enabled") == False
    assert birthNameEdit.property("enabled") == False
    assert nickNameEdit.property("enabled") == False
    assert firstNameEdit.property("text") == "[%s]" % person.alias()
    assert middleNameEdit.property("text") == ""
    assert lastNameEdit.property("text") == ""
    assert birthNameEdit.property("text") == ""
    assert nickNameEdit.property("text") == ""

    scene.setShowAliases(False)
    assert firstNameEdit.property("enabled") == True
    assert middleNameEdit.property("enabled") == True
    assert lastNameEdit.property("enabled") == True
    assert birthNameEdit.property("enabled") == True
    assert nickNameEdit.property("enabled") == True
    assert firstNameEdit.property("text") == "Harold"
    assert middleNameEdit.property("text") == "Kidd"
    assert lastNameEdit.property("text") == "Stinson"
    assert birthNameEdit.property("text") == "you guessed it"
    assert nickNameEdit.property("text") == "Harry"


def test_init_layer_list(view, scene):
    layer = Layer(name="My Layer")
    scene.addItem(layer)
    person = Person()
    view.show([person])
    model = view.rootProp("layerList").property("model")
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0)) == layer.name()


def test_multiple_people_and_layers_doesnt_break_layers_selection(view, scene):
    layer1 = Layer(name="View 1")
    layer2 = Layer(name="View 2")
    person1 = Person(name="Person 1")
    person2 = Person(name="Person 2")
    scene.addItems(layer1, layer2, person1, person2)
    person1.setLayers([layer1.id, layer2.id])
    view.show([person1, person2])
    model = view.rootProp("layerList").property("model")
    assert model.rowCount() == 2
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.PartiallyChecked
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.PartiallyChecked


def test_add_to_layer_via_model(view, scene):
    layer = Layer(name="My Layer")
    scene.addItem(layer)
    person = Person()
    person.setSelected(True)
    scene.addItem(person)
    view.show([person])
    assert layer.id not in person.layers()

    layerModel = None
    for child in view.qml.rootObject().findChildren(LayerItemLayersModel):
        if child.items == [person]:
            layerModel = child
            break

    layerModel.setData(layerModel.index(0, 0), True, layerModel.ActiveRole)
    assert layer.id in person.layers()
    assert person.isSelected()  # should stay selected

    layerModel.setData(layerModel.index(0, 0), False, layerModel.ActiveRole)
    assert layer.id not in person.layers()
    assert person.isSelected()  # should stay selected


def _test_add_to_layer(view, scene):
    layer = Layer(name="My Layer")
    scene.addItem(layer)
    person = Person()
    view.show([person])
    layerList = view.rootProp("layerList")
    assert layer.id not in person.layers() == False

    view.clickListViewItem_actual("layerList", "My Layer")
    assert layer.id in person.layers()

    view.clickListViewItem("layerList", 0)
    assert layer.id not in person.layers()


def __test_remove_event_button(view, scene, eventProps):
    view.init(scene)
    person = Person()
    event = Event(
        parent=person,
        description=eventProps["description"],
        dateTime=util.Date(2001, 2, 3),
    )
    scene.addItem(person)
    view.show([person])

    view.clickTimelineViewItem(
        "personProps_timelineView", eventProps["description"], column=3
    )
    assert view.rootProp("removeEventButton").property("enabled") == True
    view.mouseClick("removeEventButton", Qt.LeftButton)
    view.assertNoTableViewItem(
        "personProps_timelineView", eventProps["description"], column=3
    )


# TODO:
# def _test_edit_event_in_timeline(qtbot, view, scene, personProps, person):

#     event = Event(description="here we are", dateTime=util.Date(2003, 5, 11))
#     event.setParent(person)
#     view.show([person])
#     # activate(view)

#     view.ui.tabWidget.setCurrentIndex(1)
#     view.clickTableViewItem(view.ui.timelineView, "here we are", column=3)

#     view.mouseClick(view.ui.editEventButton, Qt.LeftButton)
#     assert view.eventProperties.isShown()

#     runEventProperties(view.eventProperties.ui, personProps)
#     assertEventProperties(event, personProps)

#     # TODO: Add test tags
