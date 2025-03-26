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
def pp(qtbot, qmlEngine):
    scene = Scene()
    qmlEngine.setScene(scene)
    pp = QmlDrawer(
        qmlEngine,
        "qml/PersonProperties.qml",
        propSheetModel="personModel",
        resizable=True,
    )
    pp.setScene(qmlEngine.sceneModel.scene)
    pp.checkInitQml()
    pp.model = pp.rootProp(pp.propSheetModel)
    pp.show()
    qtbot.addWidget(pp)
    qtbot.waitActive(pp)

    yield pp

    pp.hide()  # resets .items
    pp.deinit()
    qmlEngine.setScene(None)
    scene.deinit()


def test_init_fields(pp):

    FIRST_NAME = "Someone"
    MIDDLE_NAME = "Middle"
    LAST_NAME = "Last"
    NICK_NAME = "Nick"
    BIRTH_NAME = "Birth"
    SIZE = 5
    ADOPTED_DATE_TIME = util.Date(1982, 6, 16)
    BIRTH_DATE_TIME = util.Date(1980, 5, 11)
    DECEASED_DATE_TIME = util.Date(2001, 1, 1)
    DECEASED_REASON = "heart attack"
    NOTES = "who knows anyway"
    DIAGRAM_NOTES = "Diagram notes\n\nmulti-line\n\n\n\n entry"

    person = Person(
        name=FIRST_NAME,
        middleName=MIDDLE_NAME,
        lastName=LAST_NAME,
        nickName=NICK_NAME,
        birthName=BIRTH_NAME,
        size=SIZE,
        gender=util.PERSON_KIND_FEMALE,
        birthDateTime=BIRTH_DATE_TIME,
        adopted=True,
        adoptedDateTime=ADOPTED_DATE_TIME,
        deceased=True,
        deceasedDateTime=DECEASED_DATE_TIME,
        deceasedReason=DECEASED_REASON,
        notes=NOTES,
        diagramNotes=DIAGRAM_NOTES,
        primary=True,
        hideDetails=True,
        hideDates=False,
        hideVariables=False,
    )
    pp.scene.addItem(person)
    pp.show([person])

    assert pp.rootProp("firstNameEdit").property("text") == FIRST_NAME
    assert pp.rootProp("middleNameEdit").property("text") == MIDDLE_NAME
    assert pp.rootProp("lastNameEdit").property("text") == LAST_NAME
    assert pp.rootProp("nickNameEdit").property("text") == NICK_NAME
    assert pp.rootProp("birthNameEdit").property("text") == BIRTH_NAME
    assert pp.rootProp("sizeBox").property(
        "currentText"
    ) == util.personSizeNameFromSize(SIZE)
    assert pp.rootProp("kindBox").property("currentText") == "Female"
    assert pp.rootProp("adoptedBox").property("checkState") == Qt.Checked
    assert pp.rootProp("adoptedDateButtons").property("dateTime") == ADOPTED_DATE_TIME
    assert pp.rootProp("primaryBox").property("checkState") == Qt.Checked
    assert pp.rootProp("birthDateButtons").property("dateTime") == BIRTH_DATE_TIME
    assert pp.rootProp("adoptedDateButtons").property("dateTime") == ADOPTED_DATE_TIME
    assert pp.rootProp("deceasedBox").property("checkState") == Qt.Checked
    assert pp.rootProp("deceasedDateButtons").property("dateTime") == DECEASED_DATE_TIME
    assert pp.rootProp("deceasedReasonEdit").property("text") == DECEASED_REASON
    assert pp.rootProp("hideDetailsBox").property("checkState") == Qt.Checked
    assert pp.rootProp("hideDatesBox").property("checkState") == Qt.Unchecked
    assert pp.rootProp("hideVariablesBox").property("checkState") == Qt.Unchecked
    assert pp.rootProp("notesEdit").property("text") == NOTES


def test_set_props(pp):
    person = Person()
    pp.scene.addItem(person)
    pp.show([person])

    ## Values

    FIRST_NAME = "Someone"
    MIDDLE_NAME = "Middle"
    LAST_NAME = "Last"
    NICK_NAME = "Nick"
    BIRTH_NAME = "Birth"
    SIZE = "Small"
    GENDER = util.personKindFromIndex(1)
    ADOPTED = Qt.Checked
    ADOPTED_DATE_TIME = util.Date(1982, 6, 16)
    PRIMARY = Qt.Checked
    BIRTH_DATE_TIME = util.Date(1980, 5, 11)
    DECEASED = Qt.Checked
    DECEASED_DATE_TIME = util.Date(2001, 1, 1)
    DECEASED_REASON = "heart attack"
    NOTES = "who knows anyway"
    HIDE_DETAILS = Qt.Checked
    HIDE_DATES = Qt.Checked
    HIDE_VARIABLES = Qt.Checked
    DIAGRAM_NOTES = "Diagram notes\n\nmulti-line\n\n\n\n entry"

    ## Items

    personPage = pp.rootProp("personPage")

    firstNameEdit = pp.rootProp("firstNameEdit")
    middleNameEdit = pp.rootProp("middleNameEdit")
    lastNameEdit = pp.rootProp("lastNameEdit")
    nickNameEdit = pp.rootProp("nickNameEdit")
    birthNameEdit = pp.rootProp("birthNameEdit")
    sizeBox = pp.rootProp("sizeBox")
    kindBox = pp.rootProp("kindBox")
    adoptedBox = pp.rootProp("adoptedBox")
    adoptedDateButtons = pp.rootProp("adoptedDateButtons")
    primaryBox = pp.rootProp("primaryBox")

    birthDateButtons = pp.rootProp("birthDateButtons")
    adoptedDateButtons = pp.rootProp("adoptedDateButtons")
    deceasedBox = pp.rootProp("deceasedBox")
    deceasedDateButtons = pp.rootProp("deceasedDateButtons")
    deceasedReasonEdit = pp.rootProp("deceasedReasonEdit")
    notesEdit = pp.rootProp("notesEdit")
    hideDetailsBox = pp.rootProp("hideDetailsBox")
    hideDatesBox = pp.rootProp("hideDatesBox")
    hideVariablesBox = pp.rootProp("hideVariablesBox")
    diagramNotesEdit = pp.rootProp("diagramNotesEdit")

    ## Set

    pp.keyClicksItem(firstNameEdit, FIRST_NAME)
    pp.keyClicksItem(middleNameEdit, MIDDLE_NAME)
    pp.keyClicksItem(lastNameEdit, LAST_NAME)
    pp.keyClicksItem(nickNameEdit, NICK_NAME)
    pp.keyClicksItem(birthNameEdit, BIRTH_NAME)

    pp.clickComboBoxItem(sizeBox, SIZE)
    pp.clickComboBoxItem(kindBox, util.personKindNameFromKind(GENDER))

    pp.scrollToItem(personPage, birthDateButtons)
    pp.keyClicksItem(
        birthDateButtons.property("dateTextInput"), util.dateString(BIRTH_DATE_TIME)
    )

    pp.scrollToItem(personPage, adoptedBox)
    pp.mouseClickItem(adoptedBox)
    pp.keyClicksItem(
        adoptedDateButtons.property("dateTextInput"), util.dateString(ADOPTED_DATE_TIME)
    )

    pp.scrollToItem(personPage, deceasedBox)
    pp.mouseClickItem(deceasedBox)
    pp.keyClicksItem(
        deceasedDateButtons.property("dateTextInput"),
        util.dateString(DECEASED_DATE_TIME),
    )
    pp.scrollToItem(personPage, deceasedReasonEdit)
    pp.keyClicksItem(deceasedReasonEdit, DECEASED_REASON)

    pp.scrollToItem(personPage, primaryBox)
    pp.mouseClickItem(primaryBox)

    pp.scrollToItem(personPage, hideDetailsBox)
    pp.mouseClickItem(hideDetailsBox)

    pp.scrollToItem(personPage, hideDatesBox)
    pp.mouseClickItem(hideDatesBox)

    pp.scrollToItem(personPage, hideVariablesBox)
    pp.mouseClickItem(hideVariablesBox)

    pp.scrollToItem(personPage, diagramNotesEdit)
    pp.keyClicksItem(diagramNotesEdit, DIAGRAM_NOTES, returnToFinish=False)

    pp.setCurrentTab("notes")
    pp.keyClicksItem(notesEdit, NOTES, returnToFinish=False)

    ## Assert

    assert person.name() == FIRST_NAME
    assert person.middleName() == MIDDLE_NAME
    assert person.lastName() == LAST_NAME
    assert person.nickName() == NICK_NAME
    assert person.birthName() == BIRTH_NAME
    assert person.size() == util.personSizeFromName(SIZE)
    assert person.gender() == GENDER
    assert person.adopted() == util.csToBool(ADOPTED)
    assert person.adoptedDateTime() == ADOPTED_DATE_TIME
    assert person.primary() == util.csToBool(PRIMARY)
    assert person.birthDateTime() == BIRTH_DATE_TIME
    assert person.deceased() == util.csToBool(DECEASED)
    assert person.deceasedDateTime() == DECEASED_DATE_TIME
    assert person.deceasedReason() == DECEASED_REASON
    assert person.notes() == NOTES
    assert person.hideDetails() == util.csToBool(HIDE_DETAILS)
    assert person.hideDates() == util.csToBool(HIDE_DATES)
    assert person.hideVariables() == util.csToBool(HIDE_VARIABLES)
    assert person.diagramNotes() == DIAGRAM_NOTES
    assert person.notes() == NOTES


def test_date_undo_redo(pp):
    personPage = pp.rootProp("personPage")
    birthDateButtons = pp.rootProp("birthDateButtons")
    birthDatePicker = pp.rootProp("birthDatePicker")
    dateTextInput = birthDateButtons.property("dateTextInput")
    personA = Person()
    personB = Person()
    pp.scene.addItems(personA, personB)
    pp.show([personA, personB])
    dateTime = QDateTime(2001, 2, 3, 0, 0)
    pp.model.birthDateTime = dateTime  # 0
    assert dateTextInput.property("text") == "02/03/2001"

    pp.scrollToItem(personPage, birthDateButtons)
    pp.focusItem(birthDateButtons).property("dateTextInput")  # open picker
    pp.mouseClickItem(birthDateButtons.property("clearButton"))  # 1
    assert dateTextInput.property("text") == "--/--/----"

    pp.scene.undo()  # 0
    assert dateTextInput.property("text") == "02/03/2001"
    assert birthDateButtons.property("dateTime") == dateTime
    assert birthDatePicker.property("dateTime") == dateTime

    pp.scene.redo()  # 1
    assert dateTextInput.property("text") == "--/--/----"

    pp.scene.undo()  # 0
    assert dateTextInput.property("text") == "02/03/2001"

    pp.scene.redo()  # 1
    assert dateTextInput.property("text") == "--/--/----"


def test_person_readOnlyFields(pp, qmlEngine):
    person = Person()
    pp.scene.addItem(person)
    pp.scene.setReadOnly(True)
    qmlEngine.sceneModel.refreshProperty("readOnly")
    assert pp.rootProp("firstNameEdit").property("enabled") == False
    assert pp.rootProp("middleNameEdit").property("enabled") == False
    assert pp.rootProp("lastNameEdit").property("enabled") == False
    assert pp.rootProp("ageBox").property("enabled") == False


# @pytest.mark.skip(
#     reason="Not be needed if timelinemodel is already tested for dynamically"
# )
# def test_pp_honors_search(pp, qmlEngine):
#     personTimelineModel = pp.findItem("personProps_timelineView").property("model")
#     # personTimelineModel.searchModel = qmlEngine.searchModel
#     person = Person()
#     pp.scene.addItem(person)
#     event1 = Event(parent=person, description="Mine 1", dateTime=util.Date(2001, 1, 1))
#     event2 = Event(parent=person, description="Yours 2", dateTime=util.Date(2001, 1, 2))
#     event3 = Event(parent=person, description="Mine 3", dateTime=util.Date(2001, 1, 3))
#     qmlEngine.searchModel.description = "Mine"
#     pp.show([person])
#     assert qmlEngine.searchModel.shouldHide(event1) == False
#     assert qmlEngine.searchModel.shouldHide(event2) == True
#     assert qmlEngine.searchModel.shouldHide(event3) == False
#     assert personTimelineModel.rowCount() == 2
#     # assert pp.findItem('personProps_timelineView.table').property('rows') == 2


@pytest.mark.parametrize(
    "itemName, propertyName",
    [
        ("firstNameEdit", "name"),
        ("middleNameEdit", "middleName"),
        ("lastNameEdit", "lastName"),
        ("nickNameEdit", "nickName"),
        ("birthNameEdit", "birthName"),
        ("deceasedReasonEdit", "deceasedReason"),
    ],
)
def test_empty_strings_reset_string_fields(pp, itemName, propertyName):
    SOME_VALUE = "some value"

    person = Person(deceased=True)
    person.prop(propertyName).set(SOME_VALUE)
    pp.scene.addItem(person)
    pp.show([person])
    item = pp.rootProp(itemName)
    pp.keyClicksClearItem(item)
    assert person.prop(propertyName).get() is None


def test_empty_strings_reset_notesField(pp):
    SOME_VALUE = "some value\nsdfsdfsdf"

    person = Person(deceased=True)
    person.prop("notes").set(SOME_VALUE)
    pp.scene.addItem(person)
    pp.show([person])
    pp.setCurrentTab("notes")
    notesEdit = pp.rootProp("notesEdit")
    pp.keyClickItem(notesEdit, Qt.Key_Backspace)
    pp.resetFocusItem(notesEdit)
    assert person.prop("notes").get() is None


@pytest.mark.parametrize(
    "dateButtonsName, eventName",
    [
        ("birthDateButtons", "birthEvent"),
        ("adoptedDateButtons", "adoptedEvent"),
        ("deceasedDateButtons", "deathEvent"),
    ],
)
def test_empty_strings_reset_dateTextInput_fields(pp, dateButtonsName, eventName):
    person = Person(adopted=True, deceased=True)
    pp.scene.addItem(person)
    event = getattr(person, eventName)
    event.setDateTime(util.Date(2001, 2, 3))
    pp.show([person])
    dateButtons = pp.rootProp(dateButtonsName)
    pp.scrollToItem(pp.rootProp("personPage"), dateButtons)
    dateTextInput = dateButtons.property("dateTextInput")
    pp.keyClicksClearItem(dateTextInput)
    assert getattr(person, eventName).dateTime() is None


@pytest.mark.parametrize(
    "locationEditName, eventName",
    [
        ("birthLocationEdit", "birthEvent"),
        ("deceasedLocationEdit", "deathEvent"),
    ],
)
def test_empty_strings_reset_event_location_fields(pp, locationEditName, eventName):
    person = Person(deceased=True)
    pp.scene.addItem(person)
    event = getattr(person, eventName)
    event.setLocation("Somewhere, US")
    pp.show([person])
    item = pp.rootProp(locationEditName)
    pp.keyClicksClearItem(item)
    assert getattr(person, eventName).location() is None


def test_scene_readOnlyFields(pp, qmlEngine):
    pp.scene.setReadOnly(True)
    qmlEngine.sceneModel.refreshProperty("readOnly")
    person = Person()
    layer = Layer(active=True)  # so meta ctls are properly enabled/disabled
    pp.scene.addItem(layer, person)
    pp.show([person])

    assert not pp.rootProp("firstNameEdit").property("enabled")
    assert not pp.rootProp("middleNameEdit").property("enabled")
    assert not pp.rootProp("lastNameEdit").property("enabled")
    assert not pp.rootProp("nickNameEdit").property("enabled")
    assert not pp.rootProp("birthNameEdit").property("enabled")
    assert not pp.rootProp("sizeBox").property("enabled")
    assert not pp.rootProp("kindBox").property("enabled")
    assert not pp.rootProp("adoptedBox").property("enabled")
    assert not pp.rootProp("adoptedDateButtons").property("enabled")
    assert not pp.rootProp("primaryBox").property("enabled")
    assert not pp.rootProp("birthDateButtons").property("enabled")
    assert not pp.rootProp("birthLocationEdit").property("enabled")
    assert not pp.rootProp("deceasedBox").property("enabled")
    assert not pp.rootProp("deceasedDateButtons").property("enabled")
    assert not pp.rootProp("deceasedLocationEdit").property("enabled")
    assert not pp.rootProp("deceasedReasonEdit").property("enabled")
    assert not pp.rootProp("deceasedDateButtons").property("enabled")
    assert not pp.rootProp("notesEdit").property("enabled")
    assert not pp.rootProp("hideDetailsBox").property("enabled")
    assert not pp.rootProp("hideDatesBox").property("enabled")
    assert not pp.rootProp("hideVariablesBox").property("enabled")
    assert not pp.rootProp("colorBox").property("enabled")
    assert not pp.rootProp("resetColorButton").property("enabled")
    assert not pp.rootProp("deemphasizeBox").property("enabled")
    assert not pp.rootProp("resetDeemphasizeButton").property("enabled")


# this wasn't thought through very well
def _test_open_tabs_retained(pp):
    """Some tabs should be disabled when editing multiple people."""
    tabBar = pp.rootProp("tabBar")
    person = Person()
    person.setBirthDateTime(util.Date(1900, 1, 1))
    pp.scene.addItem(person)

    pp.show([person])
    assert pp.currentTab() == 0
    assert pp.rootProp("timelinePage").property("enabled") == True

    # just to be able to test if it switches back after...
    pp.clickTabBarButton(tabBar, 1)
    assert pp.currentTab() == 1

    pp.hide()
    pp.show([person])
    assert pp.currentTab() == 0
    assert pp.rootProp("timelinePage").property("enabled") == True


def test_clear_layered_pos(pp, monkeypatch):
    """It was taking two clicks to clear the person props."""
    resetItemPosButton = pp.rootProp("resetItemPosButton")
    layer = Layer()
    pp.scene.addItem(layer)
    pp.scene.setStorePositionsInLayers(True)
    person = Person()
    pp.scene.addItem(person)
    pp.show([person])
    pp.setCurrentTab("meta")

    monkeypatch.setattr(pp.scene, "isMovingSomething", lambda: True)
    person.setItemPos(QPointF(100, 100))  # default
    layer.setActive(True)
    layer.setStoreGeometry(True)
    person.setItemPos(QPointF(200, 200))  # in layer
    personModel = pp.rootProp("personModel")
    assert personModel.itemPos == QPointF(200, 200)
    assert personModel.itemPos == person.itemPos()
    assert resetItemPosButton.property("enabled") == True
    assert personModel.isItemPosSetInCurrentLayer == True

    pp.mouseClickItem(resetItemPosButton)
    assert personModel.itemPos == QPointF(100, 100)
    assert personModel.isItemPosSetInCurrentLayer == False
    assert resetItemPosButton.property("enabled") == False


# def test_tabKeys():
#     ui = pp.ui
#     person = Person()
#     pp.show([person])

#     pp.keyClick(pp, Qt.Key_BracketRight, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 1

#     pp.keyClick(pp, Qt.Key_BracketRight, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 2

#     pp.keyClick(pp, Qt.Key_BracketLeft, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 1

#     pp.keyClick(pp, Qt.Key_BracketLeft, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 0

#     pp.keyClick(pp, Qt.Key_BracketLeft, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 0


def test_names_hidden(pp):
    assert not pp.scene.showAliases()  # just to be safe

    person = Person(
        name="Harold",
        middleName="Kidd",
        lastName="Stinson",
        birthName="you guessed it",
        nickName="Harry",
    )
    pp.scene.addItem(person)
    chunk = {}
    person.write(chunk)
    person.read(chunk, chunk.get)  # assigns alias
    pp.show([person])

    assert pp.rootProp("firstNameEdit").property("enabled") == True
    assert pp.rootProp("middleNameEdit").property("enabled") == True
    assert pp.rootProp("lastNameEdit").property("enabled") == True
    assert pp.rootProp("birthNameEdit").property("enabled") == True
    assert pp.rootProp("nickNameEdit").property("enabled") == True
    assert pp.rootProp("firstNameEdit").property("text") == "Harold"
    assert pp.rootProp("middleNameEdit").property("text") == "Kidd"
    assert pp.rootProp("lastNameEdit").property("text") == "Stinson"
    assert pp.rootProp("birthNameEdit").property("text") == "you guessed it"
    assert pp.rootProp("nickNameEdit").property("text") == "Harry"

    pp.scene.setShowAliases(True)
    assert pp.rootProp("firstNameEdit").property("enabled") == False
    assert pp.rootProp("middleNameEdit").property("enabled") == False
    assert pp.rootProp("lastNameEdit").property("enabled") == False
    assert pp.rootProp("birthNameEdit").property("enabled") == False
    assert pp.rootProp("nickNameEdit").property("enabled") == False
    assert pp.rootProp("firstNameEdit").property("text") == "[%s]" % person.alias()
    assert pp.rootProp("middleNameEdit").property("text") == ""
    assert pp.rootProp("lastNameEdit").property("text") == ""
    assert pp.rootProp("birthNameEdit").property("text") == ""
    assert pp.rootProp("nickNameEdit").property("text") == ""

    pp.scene.setShowAliases(False)
    assert pp.rootProp("firstNameEdit").property("enabled") == True
    assert pp.rootProp("middleNameEdit").property("enabled") == True
    assert pp.rootProp("lastNameEdit").property("enabled") == True
    assert pp.rootProp("birthNameEdit").property("enabled") == True
    assert pp.rootProp("nickNameEdit").property("enabled") == True
    assert pp.rootProp("firstNameEdit").property("text") == "Harold"
    assert pp.rootProp("middleNameEdit").property("text") == "Kidd"
    assert pp.rootProp("lastNameEdit").property("text") == "Stinson"
    assert pp.rootProp("birthNameEdit").property("text") == "you guessed it"
    assert pp.rootProp("nickNameEdit").property("text") == "Harry"


def test_init_layer_list(pp):
    layer = Layer(name="My Layer")
    pp.scene.addItem(layer)
    person = Person()
    pp.show([person])
    model = pp.rootProp("layerList").property("model")
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0)) == layer.name()


def test_multiple_people_and_layers_doesnt_break_layers_selection(pp):
    layer1 = Layer(name="View 1")
    layer2 = Layer(name="View 2")
    person1 = Person(name="Person 1")
    person2 = Person(name="Person 2")
    pp.scene.addItems(layer1, layer2, person1, person2)
    person1.setLayers([layer1.id, layer2.id])
    pp.show([person1, person2])
    model = pp.rootProp("layerList").property("model")
    assert model.rowCount() == 2
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.PartiallyChecked
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.PartiallyChecked


def test_add_to_layer_via_model(pp):
    layer = Layer(name="My Layer")
    pp.scene.addItem(layer)
    person = Person()
    person.setSelected(True)
    pp.scene.addItem(person)
    pp.show([person])
    assert layer.id not in person.layers()

    layerModel = None
    for child in pp.qml.rootObject().findChildren(LayerItemLayersModel):
        if child.items == [person]:
            layerModel = child
            break

    layerModel.setData(layerModel.index(0, 0), True, layerModel.ActiveRole)
    assert layer.id in person.layers()
    assert person.isSelected()  # should stay selected

    layerModel.setData(layerModel.index(0, 0), False, layerModel.ActiveRole)
    assert layer.id not in person.layers()
    assert person.isSelected()  # should stay selected


def _test_add_to_layer(pp):
    layer = Layer(name="My Layer")
    pp.scene.addItem(layer)
    person = Person()
    pp.show([person])
    layerList = pp.rootProp("layerList")
    assert layer.id not in person.layers() == False

    pp.clickListViewItem_actual("layerList", "My Layer")
    assert layer.id in person.layers()

    pp.clickListViewItem("layerList", 0)
    assert layer.id not in person.layers()


def __test_remove_event_button(pp, scene, eventProps):
    pp.init(scene)
    person = Person()
    event = Event(
        parent=person,
        description=eventProps["description"],
        dateTime=util.Date(2001, 2, 3),
    )
    scene.addItem(person)
    pp.show([person])

    pp.clickTimelineViewItem(
        "personProps_timelineView", eventProps["description"], column=3
    )
    assert pp.rootProp("removeEventButton").property("enabled") == True
    pp.mouseClick("removeEventButton", Qt.LeftButton)
    pp.assertNoTableViewItem(
        "personProps_timelineView", eventProps["description"], column=3
    )


# TODO:
# def _test_edit_event_in_timeline(qtbot, pp, scene, personProps, person):

#     event = Event(description="here we are", dateTime=util.Date(2003, 5, 11))
#     event.setParent(person)
#     pp.show([person])
#     # activate(pp)

#     pp.ui.tabWidget.setCurrentIndex(1)
#     pp.clickTableViewItem(pp.ui.timelineView, "here we are", column=3)

#     pp.mouseClick(pp.ui.editEventButton, Qt.LeftButton)
#     assert pp.eventProperties.isShown()

#     runEventProperties(pp.eventProperties.ui, personProps)
#     assertEventProperties(event, personProps)

#     # TODO: Add test tags
