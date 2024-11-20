import pytest
from pkdiagram.scene import commands
from pkdiagram.pyqt import Qt, QDateTime
from pkdiagram import (
    util,
    EventKind,
    Person,
    Marriage,
    Event,
    Scene,
    SceneModel,
    Emotion,
)
from pkdiagram.widgets.qml.qmldrawer import QmlDrawer


## TODO: test personBox works for adding event to person


@pytest.fixture
def eventProps():
    """Could even rotate these just for fun."""
    return {
        "dateTime": util.Date(2000, 4, 21, 3, 4),
        # 'unsure': Qt.Checked,
        "description": "Something happened",
        "nodal": Qt.Checked,
        "notes": "It was really intense but came and went",
        "location": "Anchorage, AK",
        "includeOnDiagram": Qt.Checked,
    }


@pytest.fixture
def event(eventProps):
    event = Event()
    for key, value in eventProps.items():
        event.prop(key).set(value)
    return event


@pytest.fixture
def ep(qtbot, qmlEngine):
    scene = Scene()
    qmlEngine.setScene(scene)
    ep = QmlDrawer(
        qmlEngine, "qml/EventPropertiesDrawer.qml", propSheetModel="eventModel"
    )
    ep.checkInitQml()
    ep.show()
    ep.eventModel = ep.rootProp("eventModel")
    qtbot.addWidget(ep)
    qtbot.waitActive(ep)

    yield ep

    ep.hide()
    ep.deinit()
    scene.deinit()


def runEventProperties(ep, props, personName=None, updates={}):

    props = dict(props)
    props.update(updates)

    resetFocus = False
    returnToFinish = False
    if personName:
        ep.clickComboBoxItem("nameBox", personName)
        opened = ep.itemProp("nameBox", "opened")
        if opened:
            ep.findItem("nameBox").close()
        assert ep.itemProp("nameBox", "currentText") == personName

    nodalBox = ep.rootProp("nodalBox")

    # # This fails if after dateButtons for some reason. Hard to debug
    # if props["nodal"] != nodalBox.property("checkState"):
    #     ep.mouseClickItem(nodalBox)

    if props["includeOnDiagram"] != ep.itemProp("includeOnDiagramBox", "checkState"):
        ep.mouseClick("includeOnDiagramBox")

    ep.focusItem("dateButtons.dateTextInput")
    ep.keyClick("dateButtons.dateTextInput", Qt.Key_Backspace)
    ep.keyClicks(
        "dateButtons.dateTextInput",
        util.dateString(props["dateTime"]),
        resetFocus=resetFocus,
        returnToFinish=returnToFinish,
    )

    ep.focusItem("dateButtons.timeTextInput")
    ep.keyClick("dateButtons.timeTextInput", Qt.Key_Backspace)
    ep.keyClicks(
        "dateButtons.timeTextInput",
        util.timeString(props["dateTime"]),
        resetFocus=resetFocus,
        returnToFinish=returnToFinish,
    )

    # if props['unsure'] != ep.itemProp('dateButtons', 'unsure'):
    #     ep.mouseClick('dateButtons.unsureBox')
    ep.keyClicks(
        "descriptionEdit",
        props["description"],
        resetFocus=resetFocus,
        returnToFinish=returnToFinish,
    )
    ep.keyClicks(
        "locationEdit",
        props["location"],
        resetFocus=resetFocus,
        returnToFinish=returnToFinish,
    )
    ep.clickTabBarButton("tabBar", 2)
    ep.findItem("eventNotesEdit").selectAll()
    ep.keyClicks(
        "eventNotesEdit",
        props["notes"],
        resetFocus=resetFocus,
        returnToFinish=returnToFinish,
    )
    ep.mouseClick("event_doneButton", Qt.LeftButton)


def assertEventProperties(event, props, updates={}, personName=None):
    assert event is not None
    props = dict(props)
    props.update(updates)
    if personName is not None:
        assert event.parentName() == personName
    assert event.description() == props["description"]
    assert event.dateTime() == props["dateTime"]
    # assert event.unsure() == (props['unsure'] == Qt.Checked)
    assert event.location() == props["location"]
    # assert event.nodal() == (props["nodal"] == Qt.Checked)
    if event.parent and event.parent.isMarriage:
        assert event.includeOnDiagram() == (props["includeOnDiagram"] == Qt.Checked)
    assert event.notes().strip() == props["notes"]


def test_init_single(ep, eventProps):
    nodalBox = ep.rootProp("nodalBox")
    scene = Scene()
    person = Person()
    event = Event(parent=person, **eventProps)
    scene.addItem(event)
    ep.eventModel.items = [event]

    props = eventProps
    assert ep.itemProp("dateButtons", "dateTime") == props["dateTime"]
    # assert ep.itemProp('dateButtons', 'unsure') == props['unsure']
    assert ep.itemProp("descriptionEdit", "text") == props["description"]
    assert ep.itemProp("locationEdit", "text") == props["location"]
    # assert nodalBox.property("checkState") == props["nodal"]
    assert ep.itemProp("eventNotesEdit", "text") == props["notes"]


def test_init_single_emotion(ep, eventProps):
    scene = Scene()
    personA = Person(name="Person A")
    personB = Person(name="Person B")
    conflict = Emotion(
        kind=util.ITEM_CONFLICT,
        personA=personA,
        personB=personB,
        startDate=util.Date(2001, 2, 3),
        endDate=util.Date(2001, 2, 5),
    )
    scene.addItems(personA, personB, conflict)
    ep.eventModel.items = [conflict.startEvent]
    assert ep.eventModel.parentName == "Person A & Person B"
    assert ep.eventModel.parentIsEmotion == True
    assert ep.itemProp("readOnlyNameBox", "visible") == True
    assert ep.itemProp("readOnlyNameBox", "currentText") == "Person A & Person B"


def test_init_multiple_same(ep, event, eventProps):
    nodalBox = ep.rootProp("nodalBox")
    event1 = Event()
    event2 = Event()
    event1.setProperties(**eventProps)
    event2.setProperties(**eventProps)
    ep.eventModel.items = [event1, event2]

    props = eventProps
    assert ep.itemProp("dateButtons", "dateTime") == props["dateTime"]
    # assert ep.itemProp('dateButtons', 'unsure') == props['unsure']
    assert ep.itemProp("descriptionEdit", "text") == props["description"]
    assert ep.itemProp("locationEdit", "text") == props["location"]
    # assert nodalBox.property("checkState") == props["nodal"]
    assert ep.itemProp("eventNotesEdit", "text") == props["notes"]


def test_init_multiple_different(ep, event):
    """Test that fields with different values have proper defaults."""
    nodalBox = ep.rootProp("nodalBox")
    event1 = Event(
        description="Some Event 1",
        unsure=True,
        dateTime=util.Date(2001, 5, 20),
        nodal=False,
        notes="Some notes I had 1",
        location="Seward, AK",
    )
    event2 = Event(
        description="Some Event 2",
        unsure=False,
        dateTime=util.Date(2000, 4, 19),
        nodal=True,
        notes="Some notes I had 2",
        location="Anchorage, AK",
    )
    ep.eventModel.items = [event1, event2]

    assert ep.itemProp("dateButtons", "dateTime") == QDateTime()
    # assert ep.itemProp('dateButtons', 'unsure') == Qt.PartiallyChecked
    assert ep.itemProp("descriptionEdit", "text") == ""
    assert ep.itemProp("locationEdit", "text") == ""
    # assert nodalBox.property("checkState") == Qt.PartiallyChecked
    assert ep.itemProp("eventNotesEdit", "text") == ""


def test_edit_single(qtbot, ep, eventProps):
    event = Event(
        description="here we are",
        dateTime=util.Date(2000, 1, 2, 3, 4, 5),  # new date entry clears time too
    )
    ep.eventModel.items = [event]
    qtbot.waitActive(ep)

    runEventProperties(ep, eventProps)
    assertEventProperties(event, eventProps)


def test_edit_multiple(qtbot, ep, eventProps):
    event1 = Event(
        description="Some Event 1",
        unsure=True,
        dateTime=util.Date(2001, 5, 20),
        nodal=False,
        notes="Some notes I had 1",
        location="Seward, AK",
    )
    event2 = Event(
        description="Some Event 2",
        unsure=False,
        dateTime=util.Date(2000, 4, 19),
        nodal=True,
        notes="Some notes I had 2",
        location="Anchorage, AK",
    )
    ep.eventModel.items = [event1, event2]
    qtbot.waitActive(ep)

    runEventProperties(ep, eventProps)
    assertEventProperties(event1, eventProps)
    assertEventProperties(event2, eventProps)


def test_readOnlyFields(ep, qmlEngine):
    scene = Scene(readOnly=True)
    event = Event(description="here we are", uniqueId="blah")
    qmlEngine.setScene(scene)
    ep.show(event)
    assert ep.findItem("descriptionEdit").property("enabled") == False
    assert ep.findItem("nameBox").property("enabled") == False

    # TODO: test more read only fields


def __test_tabs_disabled(qtbot, ep):
    ui = ep.ui
    events = [Event(), Event()]
    ep.show(events)
    assert ui.tabWidget.currentIndex() == 0
    assert not ui.documentsView.isEnabled()

    # just to be able to test if it switches back after...
    qtbot.mouseClick(
        ui.tabWidget.tabBar(),
        Qt.LeftButton,
        Qt.NoModifier,
        ui.tabWidget.tabBar().tabRect(1).center(),
    )
    assert ui.tabWidget.currentIndex() == 1

    ep.hide()
    ep.show(events[0])
    assert ui.tabWidget.currentIndex() == 0
    assert ui.documentsView.isEnabled()


# def test_tabKeys(qtbot, ep):
#     ui = ep.ui
#     event = initEvent()
#     ep.show(event)

#     assert ui.tabWidget.currentIndex() == 0

#     qtbot.keyClick(ep, Qt.Key_BracketRight, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 1

#     qtbot.keyClick(ep, Qt.Key_BracketRight, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 2

#     qtbot.keyClick(ep, Qt.Key_BracketRight, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 3

#     qtbot.keyClick(ep, Qt.Key_BracketLeft, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 2

#     qtbot.keyClick(ep, Qt.Key_BracketLeft, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 1

#     qtbot.keyClick(ep, Qt.Key_BracketLeft, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 0


def test_empty_strings_reset_props(qtbot, ep, event, qmlEngine):
    person = Person(name="Me")
    event.setParent(person)
    scene = Scene()
    scene.addItem(person)
    ep.setScene(scene)
    qmlEngine.setScene(scene)
    ep.show(event)

    assert qmlEngine.sceneModel.readOnly == False

    # clear all fields possible
    # ep.keyClicksClear('dateButtons.dateTextInput')
    ep.keyClicksClear("descriptionEdit")
    ep.keyClicksClear("locationEdit")
    ep.clickTabBarButton("tabBar", 1)
    ep.keyClicksClear("eventNotesEdit")

    # assert ep.findItem('dateButtons.dateTextInput').property('text') == ''

    eventModel = ep.rootProp("eventModel")
    # assert eventModel.dateTime == eventModel.defaultFor('dateTime')
    assert eventModel.description == eventModel.defaultFor("description")
    assert eventModel.location == eventModel.defaultFor("location")
    assert eventModel.notes == eventModel.defaultFor("notes")


def test_set_uniqueId_with_description(qtbot, ep):
    personA, personB = Person(), Person()
    marriage = Marriage(personA=personA, personB=personB)
    event = Event(
        parent=marriage, description="here we are", dateTime=util.Date(1900, 1, 1)
    )
    ep.eventModel.items = [event]
    qtbot.waitActive(ep)

    ep.clickComboBoxItem("uniqueIdBox", "Separated")
    assert event.uniqueId() == EventKind.Separated.value
    assert event.description() == "Separated"
    # qtbot.clickYesAfter(lambda: ep.clickComboBoxItem('uniqueIdBox', 'Separated'))


def test_reset_description_on_reset_uniqueId(qtbot, ep):
    personA, personB = Person(), Person()
    marriage = Marriage(personA=personA, personB=personB)
    married = Event(
        parent=marriage,
        uniqueId=EventKind.Married.value,
        dateTime=util.Date(1900, 1, 1),
    )
    ep.eventModel.items = [married]
    qtbot.waitActive(ep)
    assert married.uniqueId() == EventKind.Married.value
    assert married.description() == "Married"
    assert ep.itemProp("uniqueIdBox", "currentText") == "Married"

    ep.mouseClick("resetUniqueIdButton")
    assert married.uniqueId() == None
    assert married.description() == None
    assert ep.itemProp("uniqueIdBox", "currentText") == ""


def test_uniqueId_undo_redo(qtbot, ep):
    personA, personB = Person(), Person()
    marriage = Marriage(personA=personA, personB=personB)
    married = Event(
        parent=marriage,
        uniqueId=EventKind.Married.value,
        dateTime=util.Date(1900, 1, 1),
    )
    ep.eventModel.items = [married]
    qtbot.waitActive(ep)
    ep.mouseClick("resetUniqueIdButton")
    assert married.uniqueId() == None
    assert married.description() == None
    assert ep.itemProp("uniqueIdBox", "currentText") == ""

    commands.stack().undo()
    assert married.uniqueId() == EventKind.Married.value
    assert married.description() == "Married"
    assert ep.itemProp("uniqueIdBox", "currentText") == "Married"


def test_uniqueId_undo_redo_custom_event(qtbot, ep):
    personA, personB = Person(), Person()
    marriage = Marriage(personA=personA, personB=personB)
    event = Event(
        parent=marriage, description="Something", dateTime=util.Date(1900, 1, 1)
    )
    ep.eventModel.items = [event]
    qtbot.waitActive(ep)
    assert event.uniqueId() == None
    assert event.description() == "Something"
    assert ep.itemProp("uniqueIdBox", "currentText") == ""
    assert ep.itemProp("uniqueIdBox", "currentIndex") == -1
    assert ep.itemProp("descriptionEdit", "text") == "Something"

    ep.clickComboBoxItem("uniqueIdBox", "Separated")
    assert event.uniqueId() == EventKind.Separated.value
    assert event.description() == "Separated"
    assert ep.itemProp("descriptionEdit", "text") == "Separated"

    commands.stack().undo()
    assert event.uniqueId() == None
    assert event.description() == "Something"
    assert ep.itemProp("uniqueIdBox", "currentText") == ""
    assert ep.itemProp("uniqueIdBox", "currentIndex") == -1
    assert ep.itemProp("descriptionEdit", "text") == "Something"

    commands.stack().redo()
    assert event.uniqueId() == EventKind.Separated.value
    assert event.description() == "Separated"
    assert ep.itemProp("descriptionEdit", "text") == "Separated"
