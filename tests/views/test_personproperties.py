import pytest
from pkdiagram.app import commands
from pkdiagram.pyqt import Qt, QDateTime, QPointF
from pkdiagram import (
    util,
    Person,
    Event,
    Layer,
    QmlDrawer,
    LayerItemLayersModel,
    Scene,
)
from pkdiagram.models import SearchModel
from tests.views.test_eventproperties import runEventProperties


pytestmark = [
    pytest.mark.component("PersonProperties"),
    pytest.mark.depends_on("PersonPropertiesModel"),
]


def setPersonProperties(pp, props):
    pp.setItemProp("personPage", "contentY", 0)
    pp.keyClicks("firstNameEdit", props["name"])
    pp.keyClicks("middleNameEdit", props["middleName"])
    pp.keyClicks("lastNameEdit", props["lastName"])
    pp.keyClicks("nickNameEdit", props["nickName"])
    pp.keyClicks("birthNameEdit", props["birthName"])
    pp.clickComboBoxItem("sizeBox", util.personSizeNameFromSize(props["size"]))
    pp.clickComboBoxItem("kindBox", util.personKindNameFromKind(props["gender"]))
    pp.setItemProp("personPage", "contentY", -300)
    pp.keyClick("adoptedBox", Qt.Key_Space)
    if pp.itemProp("adoptedBox", "checkState") != props["adopted"]:
        pp.mouseClick("adoptedBox")
    assert pp.itemProp("adoptedDateButtons", "enabled") == util.csToBool(
        props["adopted"]
    )
    pp.keyClicks(
        "adoptedDateButtons.dateTextInput", util.dateString(props["adoptedDateTime"])
    )
    pp.mouseClick("primaryBox")
    if pp.itemProp("primaryBox", "checkState") != props["primary"]:
        pp.mouseClick("primaryBox")
    pp.mouseClick("deceasedBox")
    if pp.itemProp("deceasedBox", "checkState") != props["deceased"]:
        pp.keyClick("deceasedBox", Qt.Key_Space)
    assert pp.itemProp("deceasedReasonEdit", "enabled") == util.csToBool(
        props["deceased"]
    )
    assert pp.itemProp("deceasedDateButtons", "enabled") == util.csToBool(
        props["deceased"]
    )
    if util.csToBool(props["deceased"]):
        pp.keyClicks("deceasedReasonEdit", props["deceasedReason"])
        pp.keyClicks(
            "deceasedDateButtons.dateTextInput",
            util.dateString(props["deceasedDateTime"]),
        )
    pp.setCurrentTab("notes")
    pp.keyClicks("notesEdit", props["notes"])


def assertPersonProperties(person, props):
    assert person.name() == props["name"]
    assert person.middleName() == props["middleName"]
    assert person.lastName() == props["lastName"]
    assert person.nickName() == props["nickName"]
    assert person.birthName() == props["birthName"]
    assert person.gender() == props["gender"]
    assert person.adopted() == util.csToBool(props["adopted"])
    assert person.adoptedDateTime() == props["adoptedDateTime"]
    assert person.deceased() == util.csToBool(props["deceased"])
    assert person.deceasedDateTime() == props["deceasedDateTime"]
    assert person.deceasedReason() == props["deceasedReason"]
    assert person.primary() == util.csToBool(props["primary"])


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


def test_show_init(pp, personProps):
    person = Person()
    for key, value in personProps.items():
        if type(value) == Qt.CheckState:
            value = util.csToBool(value)
        if person.prop(key):
            person.prop(key).set(value)
        else:
            setterName = "set" + key[0].upper() + key[1:]
            if hasattr(person, setterName):
                getattr(person, setterName)(value)
    pp.scene.addItem(person)
    pp.show([person])
    assert pp.itemProp("firstNameEdit", "text") == personProps["name"]
    assert pp.itemProp("middleNameEdit", "text") == personProps["middleName"]
    assert pp.itemProp("lastNameEdit", "text") == personProps["lastName"]
    assert pp.itemProp("nickNameEdit", "text") == personProps["nickName"]
    assert pp.itemProp("birthNameEdit", "text") == personProps["birthName"]
    assert pp.itemProp("sizeBox", "currentText") == util.personSizeNameFromSize(
        personProps["size"]
    )
    assert pp.itemProp("kindBox", "currentText") == util.personKindNameFromKind(
        personProps["gender"]
    )
    assert pp.itemProp("adoptedBox", "checkState") == personProps["adopted"]
    if personProps["adopted"]:
        assert pp.itemProp("adoptedDateButtons", "enabled") == util.csToBool(
            personProps["adopted"]
        )
        assert (
            pp.itemProp("adoptedDateButtons", "dateTime")
            == personProps["adoptedDateTime"]
        )
    assert pp.itemProp("primaryBox", "checkState") == personProps["primary"]
    assert pp.itemProp("deceasedBox", "checkState") == personProps["deceased"]
    assert pp.itemProp("deceasedDateButtons", "enabled") == util.csToBool(
        personProps["deceased"]
    )
    assert pp.itemProp("deceasedReasonEdit", "enabled") == util.csToBool(
        personProps["deceased"]
    )
    if personProps["deceased"]:
        assert pp.itemProp("deceasedReasonEdit", "text") == "heart attack"
        assert (
            pp.itemProp("deceasedDateButtons", "dateTime")
            == personProps["deceasedDateTime"]
        )
    assert pp.itemProp("notesEdit", "text") == personProps["notes"]
    assert pp.itemProp("hideDetailsBox", "checkState") == personProps["hideDetails"]
    # pp.clickTimelineViewItem('personProps_timelineView', 'Birth', column=3)
    # if personProps['adopted']:
    #     pp.clickTableViewItem('personProps_timelineView', 'Adopted', column=3)
    # if personProps['deceased']:
    #     pp.clickTableViewItem('personProps_timelineView', 'Death', column=3)


def test_set_props(personProps, pp):
    person = Person()
    pp.scene.addItem(person)
    pp.show([person])
    setPersonProperties(pp, personProps)
    assertPersonProperties(person, personProps)


def test_init_doesnt_set_dateTimes(pp, personProps):
    person = Person()
    person.birthEvent.setDateTime(util.Date(2001, 2, 3, 4, 5, 6))
    pp.scene.addItem(person)
    pp.show([person])
    assert person.birthEvent.dateTime() == util.Date(2001, 2, 3, 4, 5, 6)


def test_date_undo_redo(pp, personProps):
    personA = Person()
    personB = Person()
    pp.scene.addItems(personA, personB)
    pp.show([personA, personB])
    dateTime = QDateTime(2001, 2, 3, 0, 0)
    pp.model.birthDateTime = dateTime  # 0
    assert pp.itemProp("birthDateButtons.dateTextInput", "text") == "02/03/2001"

    pp.scrollToVisible("personPage", "birthDateButtons")
    pp.focusItem("birthDateButtons.dateTextInput")  # open picker
    pp.mouseClick("birthDateButtons.clearButton")  # 1
    assert pp.itemProp("birthDateButtons.dateTextInput", "text") == "--/--/----"

    commands.stack().undo()  # 0
    assert pp.itemProp("birthDateButtons.dateTextInput", "text") == "02/03/2001"
    assert pp.itemProp("birthDateButtons", "dateTime") == dateTime
    assert pp.itemProp("birthDatePicker", "dateTime") == dateTime

    util.HERE = True

    commands.stack().redo()  # 1
    assert pp.itemProp("birthDateButtons.dateTextInput", "text") == "--/--/----"

    commands.stack().undo()  # 0
    assert pp.itemProp("birthDateButtons.dateTextInput", "text") == "02/03/2001"

    commands.stack().redo()  # 1
    assert pp.itemProp("birthDateButtons.dateTextInput", "text") == "--/--/----"


def test_person_readOnlyFields(pp, qmlEngine):
    person = Person()
    pp.scene.addItem(person)
    pp.scene.setReadOnly(True)
    qmlEngine.sceneModel.refreshProperty("readOnly")
    assert pp.itemProp("firstNameEdit", "enabled") == False
    assert pp.itemProp("middleNameEdit", "enabled") == False
    assert pp.itemProp("lastNameEdit", "enabled") == False
    assert pp.itemProp("ageBox", "enabled") == False


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


def test_empty_strings_reset_fields(pp, personProps):
    person = Person()
    pp.scene.addItem(person)
    pp.show([person])
    setPersonProperties(pp, personProps)

    # clear all fields possible
    pp.keyClicksClear("firstNameEdit")
    pp.keyClicksClear("middleNameEdit")
    pp.keyClicksClear("lastNameEdit")
    pp.keyClicksClear("nickNameEdit")
    pp.keyClicksClear("birthNameEdit")
    # no gender buttons
    pp.keyClicksClear("birthDateButtons.dateTextInput")
    pp.keyClicksClear("birthLocationEdit")
    # no adopted box
    pp.keyClicksClear("adoptedDateButtons.dateTextInput")
    # no primary box
    # no deceased box
    pp.keyClicksClear("deceasedReasonEdit")
    pp.keyClicksClear("deceasedLocationEdit")
    pp.keyClicksClear("deceasedDateButtons.dateTextInput")
    pp.setCurrentTab("notes")
    pp.keyClicksClear("notesEdit")  # no idea...

    assert person.name() is None
    assert person.middleName() is None
    assert person.lastName() is None
    assert person.nickName() is None
    assert person.birthName() is None
    assert person.birthEvent.location() is None
    assert person.birthDateTime() is None
    assert person.adoptedDateTime() is None
    assert person.deceasedDateTime() is None
    assert person.deathEvent.location() is None
    assert person.deceasedReason() is None
    assert person.notes() is None  # no idea..


def test_scene_readOnlyFields(pp, qmlEngine):
    pp.scene.setReadOnly(True)
    qmlEngine.sceneModel.refreshProperty("readOnly")
    person = Person()
    layer = Layer(active=True)  # so meta ctls are properly enabled/disabled
    pp.scene.addItem(layer, person)
    pp.show([person])

    assert not pp.itemProp("firstNameEdit", "enabled")
    assert not pp.itemProp("middleNameEdit", "enabled")
    assert not pp.itemProp("lastNameEdit", "enabled")
    assert not pp.itemProp("nickNameEdit", "enabled")
    assert not pp.itemProp("birthNameEdit", "enabled")
    assert not pp.itemProp("sizeBox", "enabled")
    assert not pp.itemProp("kindBox", "enabled")
    assert not pp.itemProp("adoptedBox", "enabled")
    assert not pp.itemProp("adoptedDateButtons", "enabled")
    assert not pp.itemProp("primaryBox", "enabled")
    assert not pp.itemProp("birthDateButtons", "enabled")
    assert not pp.itemProp("birthLocationEdit", "enabled")
    assert not pp.itemProp("deceasedBox", "enabled")
    assert not pp.itemProp("deceasedDateButtons", "enabled")
    assert not pp.itemProp("deceasedLocationEdit", "enabled")
    assert not pp.itemProp("deceasedReasonEdit", "enabled")
    assert not pp.itemProp("deceasedDateButtons", "enabled")
    assert not pp.itemProp("notesEdit", "enabled")
    assert not pp.itemProp("hideDetailsBox", "enabled")
    assert not pp.itemProp("colorBox", "enabled")
    assert not pp.itemProp("resetColorButton", "enabled")
    assert not pp.itemProp("deemphasizeBox", "enabled")
    assert not pp.itemProp("resetDeemphasizeButton", "enabled")


# this wasn't thought through very well
def _test_open_tabs_retained(pp):
    """Some tabs should be disabled when editing multiple people."""
    person = Person()
    person.setBirthDateTime(util.Date(1900, 1, 1))
    pp.scene.addItem(person)

    pp.show([person])
    assert pp.currentTab() == 0
    assert pp.itemProp("timelinePage", "enabled") == True

    # just to be able to test if it switches back after...
    pp.clickTabBarButton("tabBar", 1)
    assert pp.currentTab() == 1

    pp.hide()
    pp.show([person])
    assert pp.currentTab() == 0
    assert pp.itemProp("timelinePage", "enabled") == True


def test_clear_layered_pos(pp, monkeypatch):
    """It was taking two clicks to clear the person props."""
    layer = Layer()
    pp.scene.addItem(layer)
    pp.scene.setStorePositionsInLayers(True)
    person = Person()
    pp.scene.addItem(person)
    pp.show([person])
    pp.setCurrentTab("meta")

    monkeypatch.setattr(pp.scene, "isMovingSomething", lambda: True)
    person.setPos(QPointF(100, 100))  # default
    layer.setActive(True)
    layer.setStoreGeometry(True)
    person.setPos(QPointF(200, 200))  # in layer
    personModel = pp.rootProp("personModel")
    assert personModel.itemPos == QPointF(200, 200)
    assert personModel.itemPos == person.itemPos()
    assert pp.itemProp("resetItemPosButton", "enabled") == True
    assert personModel.isItemPosSetInCurrentLayer == True

    pp.mouseClick("resetItemPosButton")
    assert personModel.itemPos == QPointF(100, 100)
    assert personModel.isItemPosSetInCurrentLayer == False
    assert pp.itemProp("resetItemPosButton", "enabled") == False


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

    assert pp.itemProp("firstNameEdit", "enabled") == True
    assert pp.itemProp("middleNameEdit", "enabled") == True
    assert pp.itemProp("lastNameEdit", "enabled") == True
    assert pp.itemProp("birthNameEdit", "enabled") == True
    assert pp.itemProp("nickNameEdit", "enabled") == True
    assert pp.itemProp("firstNameEdit", "text") == "Harold"
    assert pp.itemProp("middleNameEdit", "text") == "Kidd"
    assert pp.itemProp("lastNameEdit", "text") == "Stinson"
    assert pp.itemProp("birthNameEdit", "text") == "you guessed it"
    assert pp.itemProp("nickNameEdit", "text") == "Harry"

    pp.scene.setShowAliases(True)
    assert pp.itemProp("firstNameEdit", "enabled") == False
    assert pp.itemProp("middleNameEdit", "enabled") == False
    assert pp.itemProp("lastNameEdit", "enabled") == False
    assert pp.itemProp("birthNameEdit", "enabled") == False
    assert pp.itemProp("nickNameEdit", "enabled") == False
    assert pp.itemProp("firstNameEdit", "text") == "[%s]" % person.alias()
    assert pp.itemProp("middleNameEdit", "text") == ""
    assert pp.itemProp("lastNameEdit", "text") == ""
    assert pp.itemProp("birthNameEdit", "text") == ""
    assert pp.itemProp("nickNameEdit", "text") == ""

    pp.scene.setShowAliases(False)
    assert pp.itemProp("firstNameEdit", "enabled") == True
    assert pp.itemProp("middleNameEdit", "enabled") == True
    assert pp.itemProp("lastNameEdit", "enabled") == True
    assert pp.itemProp("birthNameEdit", "enabled") == True
    assert pp.itemProp("nickNameEdit", "enabled") == True
    assert pp.itemProp("firstNameEdit", "text") == "Harold"
    assert pp.itemProp("middleNameEdit", "text") == "Kidd"
    assert pp.itemProp("lastNameEdit", "text") == "Stinson"
    assert pp.itemProp("birthNameEdit", "text") == "you guessed it"
    assert pp.itemProp("nickNameEdit", "text") == "Harry"


def test_init_layer_list(pp):
    layer = Layer(name="My Layer")
    pp.scene.addItem(layer)
    person = Person()
    pp.show([person])
    model = pp.itemProp("layerList", "model")
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
    model = pp.itemProp("layerList", "model")
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
    assert layer.id not in person.layers() == False

    pp.clickListViewItem_actual("layerList", "My Layer")
    assert layer.id in person.layers()

    pp.clickListViewItem("layerList", 0)
    assert layer.id not in person.layers()


def __test_remove_event_button(pp, qmlScene, eventProps):
    pp.init(qmlScene)
    person = Person()
    event = Event(
        person, description=eventProps["description"], dateTime=util.Date(2001, 2, 3)
    )
    qmlScene.addItem(person)
    pp.show([person])

    pp.clickTimelineViewItem(
        "personProps_timelineView", eventProps["description"], column=3
    )
    assert pp.itemProp("removeEventButton", "enabled") == True
    pp.mouseClick("removeEventButton", Qt.LeftButton)
    pp.assertNoTableViewItem(
        "personProps_timelineView", eventProps["description"], column=3
    )


# TODO: what does this have to do with PersonProperties?
def _test_load_event_from_fd(simpleFamilyScene):
    person = next([p for p in simpleFamilyScene.people() if p.name() == "Guy2"])


# TODO:
def _test_edit_event_in_timelinev(qtbot, pp, qmlScene, personProps, person):

    event = Event(description="here we are", dateTime=util.Date(2003, 5, 11))
    event.setParent(person)
    pp.show([person])
    # activate(pp)

    pp.ui.tabWidget.setCurrentIndex(1)
    pp.clickTableViewItem(pp.ui.timelineView, "here we are", column=3)

    pp.mouseClick(pp.ui.editEventButton, Qt.LeftButton)
    assert pp.eventProperties.isShown()

    runEventProperties(pp.eventProperties.ui, personProps)
    assertEventProperties(event, personProps)

    # TODO: Add test tags
