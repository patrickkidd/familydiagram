import pytest

from pkdiagram.pyqt import Qt, QDateTime, QApplication
from pkdiagram import util
from pkdiagram.scene import EventKind, Person, Marriage, Event, Scene, Emotion
from pkdiagram.views import QmlDrawer


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
        "color": "#3c3c3c",
    }


@pytest.fixture
def view(qtbot, qmlEngine, scene):
    qmlEngine.setScene(scene)
    view = QmlDrawer(
        qmlEngine, "qml/EventPropertiesDrawer.qml", propSheetModel="eventModel"
    )
    view.checkInitQml()
    view.eventModel = view.rootProp("eventModel")
    view.resize(600, 800)
    view.show()
    qtbot.addWidget(view)
    qtbot.waitActive(view)

    yield view

    view.hide()
    view.deinit()
    scene.deinit()


def runEventProperties(view, props, personName=None, updates={}):

    props = dict(props)
    props.update(updates)

    resetFocus = False
    returnToFinish = False
    if personName:
        view.clickComboBoxItem("nameBox", personName)
        opened = view.itemProp("nameBox", "opened")
        if opened:
            view.findItem("nameBox").close()
        assert view.itemProp("nameBox", "currentText") == personName

    nodalBox = view.rootProp("nodalBox")
    includeOnDiagramBox = view.rootProp("includeOnDiagramBox")
    eventNotesEdit = view.rootProp("eventNotesEdit")

    # # This fails if after dateButtons for some reason. Hard to debug
    # if props["nodal"] != nodalBox.property("checkState"):
    #     view.mouseClickItem(nodalBox)

    view.focusItem("dateButtons.dateTextInput")
    view.keyClick("dateButtons.dateTextInput", Qt.Key_Backspace)
    view.keyClicks(
        "dateButtons.dateTextInput",
        util.dateString(props["dateTime"]),
        resetFocus=resetFocus,
        returnToFinish=returnToFinish,
    )

    view.focusItem("dateButtons.timeTextInput")
    view.keyClick("dateButtons.timeTextInput", Qt.Key_Backspace)
    view.keyClicks(
        "dateButtons.timeTextInput",
        util.timeString(props["dateTime"]),
        resetFocus=resetFocus,
        returnToFinish=returnToFinish,
    )

    # if props['unsure'] != view.itemProp('dateButtons', 'unsure'):
    #     view.mouseClick('dateButtons.unsureBox')
    view.keyClicks(
        "descriptionEdit",
        props["description"],
        resetFocus=resetFocus,
        returnToFinish=returnToFinish,
    )
    view.keyClicks(
        "locationEdit",
        props["location"],
        resetFocus=resetFocus,
        returnToFinish=returnToFinish,
    )

    view.clickTabBarButton("tabBar", 1)
    eventNotesEdit.selectAll()
    view.keyClicksItem(eventNotesEdit, props["notes"])

    colorBox = view.rootProp("colorBox")
    view.clickComboBoxItem(colorBox, props["color"])
    view.mouseClick("event_doneButton", Qt.LeftButton)


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
    assert event.color() == props["color"]


def test_init_single(scene, view, eventProps):
    person = Person()
    event = Event(person, **eventProps)
    scene.addItem(person)
    view.eventModel.items = [event]

    props = eventProps
    assert view.itemProp("dateButtons", "dateTime") == props["dateTime"]
    # assert view.itemProp('dateButtons', 'unsure') == props['unsure']
    assert view.itemProp("descriptionEdit", "text") == props["description"]
    assert view.itemProp("locationEdit", "text") == props["location"]
    # assert nodalBox.property("checkState") == props["nodal"]
    assert view.itemProp("notesEdit", "text") == props["notes"]


def test_init_single_emotion(scene, view, eventProps):
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
    view.eventModel.items = [conflict.startEvent]
    assert view.eventModel.parentName == "Person A & Person B"
    assert view.eventModel.parentIsEmotion == True
    assert view.itemProp("readOnlyNameBox", "visible") == True
    assert view.itemProp("readOnlyNameBox", "currentText") == "Person A & Person B"


def test_init_multiple_same(scene, view, eventProps):
    nodalBox = view.rootProp("nodalBox")
    event1 = Event()
    event2 = Event()
    event1.setProperties(**eventProps)
    event2.setProperties(**eventProps)
    scene.addItems(event1, event2)
    view.eventModel.items = [event1, event2]

    props = eventProps
    assert view.itemProp("dateButtons", "dateTime") == props["dateTime"]
    # assert view.itemProp('dateButtons', 'unsure') == props['unsure']
    assert view.itemProp("descriptionEdit", "text") == props["description"]
    assert view.itemProp("locationEdit", "text") == props["location"]
    # assert nodalBox.property("checkState") == props["nodal"]
    assert view.itemProp("notesEdit", "text") == props["notes"]


def test_init_multiple_different(scene, view):
    """Test that fields with different values have proper defaults."""
    nodalBox = view.rootProp("nodalBox")
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
    scene.addItems(event1, event2)
    view.eventModel.items = [event1, event2]

    assert view.itemProp("dateButtons", "dateTime") == QDateTime()
    # assert view.itemProp('dateButtons', 'unsure') == Qt.PartiallyChecked
    assert view.itemProp("descriptionEdit", "text") == ""
    assert view.itemProp("locationEdit", "text") == ""
    # assert nodalBox.property("checkState") == Qt.PartiallyChecked
    assert view.itemProp("notesEdit", "text") == ""


@pytest.mark.parametrize(
    "eventDates",
    [
        [util.Date(2000, 1, 2, 3, 4, 5)],
        [util.Date(2001, 1, 2, 3, 4, 5), util.Date(2010, 1, 2, 3, 4, 5)],
    ],
)
def test_set_fields(qtbot, scene, view, eventDates):

    DATETIME = util.Date(2000, 4, 21, 3, 4)
    DESCRIPTION = "Something happened"
    LOCATION = "Somewhere, US"
    NOTES = """here
we
are again."""
    COLOR = "#3c3c3c"

    dateTextInput = view.rootProp("dateTextInput")
    timeTextInput = view.rootProp("timeTextInput")
    notesEdit = view.rootProp("notesEdit")
    descriptionEdit = view.rootProp("descriptionEdit")
    locationEdit = view.rootProp("locationEdit")
    colorBox = view.rootProp("colorBox")

    person = Person()
    events = [
        Event(person, description=f"event {i}", dateTime=date)
        for i, date in enumerate(eventDates)
    ]
    scene.addItem(person)
    view.eventModel.items = events
    qtbot.waitActive(view)

    view.keyClicksItem(dateTextInput, "\b" + util.dateString(DATETIME))
    view.keyClicksItem(timeTextInput, "\b" + util.timeString(DATETIME))
    view.keyClicksItem(descriptionEdit, "\b" + DESCRIPTION)
    view.keyClicksItem(locationEdit, "\b" + LOCATION)
    view.clickComboBoxItem(colorBox, COLOR)
    view.setCurrentTab("notes")
    # QApplication.instance().exec()
    notesEdit.selectAll()
    view.keyClicksItem(notesEdit, "\b" + NOTES, returnToFinish=False)

    assert set(x.description() for x in events) == {DESCRIPTION}
    assert set(x.dateTime() for x in events) == {DATETIME}
    assert set(x.location() for x in events) == {LOCATION}
    assert set(x.notes() for x in events) == {NOTES}
    assert set(x.color() for x in events) == {COLOR}


def test_readOnlyFields(view, qmlEngine):
    scene = Scene(readOnly=True)
    event = Event(description="here we are", uniqueId="blah")
    qmlEngine.setScene(scene)
    view.show(event)
    assert view.findItem("descriptionEdit").property("enabled") == False
    assert view.findItem("nameBox").property("enabled") == False

    # TODO: test more read only fields


def __test_tabs_disabled(qtbot, view):
    ui = view.ui
    events = [Event(), Event()]
    view.show(events)
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

    view.hide()
    view.show(events[0])
    assert ui.tabWidget.currentIndex() == 0
    assert ui.documentsView.isEnabled()


# def test_tabKeys(qtbot, view):
#     ui = view.ui
#     event = initEvent()
#     view.show(event)

#     assert ui.tabWidget.currentIndex() == 0

#     qtbot.keyClick(view, Qt.Key_BracketRight, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 1

#     qtbot.keyClick(view, Qt.Key_BracketRight, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 2

#     qtbot.keyClick(view, Qt.Key_BracketRight, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 3

#     qtbot.keyClick(view, Qt.Key_BracketLeft, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 2

#     qtbot.keyClick(view, Qt.Key_BracketLeft, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 1

#     qtbot.keyClick(view, Qt.Key_BracketLeft, Qt.ShiftModifier)
#     assert ui.tabWidget.currentIndex() == 0


def test_empty_strings_reset_props(view, eventProps):
    person = Person(name="Me")
    event = Event(parent=person, description="here we are")
    event.setProperties(**eventProps)
    scene = Scene()
    scene.addItem(person)
    view.show(event)

    assert view.qmlEngine().sceneModel.readOnly == False

    # clear all fields possible
    # view.keyClicksClear('dateButtons.dateTextInput')
    view.keyClicksClear("descriptionEdit")
    view.keyClicksClear("locationEdit")
    view.clickTabBarButton("tabBar", 1)
    view.keyClicksClear("notesEdit")

    # assert view.findItem('dateButtons.dateTextInput').property('text') == ''

    eventModel = view.rootProp("eventModel")
    # assert eventModel.dateTime == eventModel.defaultFor('dateTime')
    assert eventModel.description == eventModel.defaultFor("description")
    assert eventModel.location == eventModel.defaultFor("location")
    assert eventModel.notes == eventModel.defaultFor("notes")


def test_set_uniqueId_with_description(qtbot, scene, view):
    personA, personB = Person(), Person()
    marriage = Marriage(personA=personA, personB=personB)
    event = Event(
        parent=marriage, description="here we are", dateTime=util.Date(1900, 1, 1)
    )
    scene.addItems(personA, personB, marriage)
    view.eventModel.items = [event]
    qtbot.waitActive(view)

    view.clickComboBoxItem("uniqueIdBox", "Separated")
    assert event.uniqueId() == EventKind.Separated.value
    assert event.description() == "Separated"
    # qtbot.clickYesAfter(lambda: view.clickComboBoxItem('uniqueIdBox', 'Separated'))


def test_reset_summary_on_reset_uniqueId(qtbot, view, scene):
    personA, personB = Person(), Person()
    marriage = Marriage(personA=personA, personB=personB)
    married = Event(
        parent=marriage,
        uniqueId=EventKind.Married.value,
        dateTime=util.Date(1900, 1, 1),
    )
    scene.addItems(marriage)
    view.eventModel.items = [married]
    qtbot.waitActive(view)
    assert married.uniqueId() == EventKind.Married.value
    assert married.description() == "Married"
    assert view.itemProp("uniqueIdBox", "currentText") == "Married"

    view.mouseClick("resetUniqueIdButton")
    assert married.uniqueId() == None
    assert married.description() == None
    assert view.itemProp("uniqueIdBox", "currentText") == ""


def test_uniqueId_undo_redo(qtbot, view):
    scene = view.rootModel().scene
    personA, personB = Person(), Person()
    marriage = Marriage(personA=personA, personB=personB)
    married = Event(
        parent=marriage,
        uniqueId=EventKind.Married.value,
        dateTime=util.Date(1900, 1, 1),
    )
    scene.addItems(personA, personB, marriage)
    view.eventModel.items = [married]
    qtbot.waitActive(view)
    view.mouseClick("resetUniqueIdButton")
    assert married.uniqueId() == None
    assert married.description() == None
    assert view.itemProp("uniqueIdBox", "currentText") == ""

    scene.undo()
    assert married.uniqueId() == EventKind.Married.value
    assert married.description() == "Married"
    assert view.itemProp("uniqueIdBox", "currentText") == "Married"


def test_uniqueId_undo_redo_custom_event(qtbot, view, scene):
    personA, personB = Person(), Person()
    marriage = Marriage(personA=personA, personB=personB)
    event = Event(
        parent=marriage, description="Initial", dateTime=util.Date(1900, 1, 1)
    )
    scene.addItems(personA, personB, marriage)
    view.eventModel.items = [event]
    qtbot.waitActive(view)
    assert event.uniqueId() == None
    assert event.description() == "Initial"
    assert view.itemProp("uniqueIdBox", "currentText") == ""
    assert view.itemProp("uniqueIdBox", "currentIndex") == -1
    assert view.itemProp("descriptionEdit", "text") == "Initial"

    view.clickComboBoxItem("uniqueIdBox", "Separated")
    assert event.uniqueId() == EventKind.Separated.value
    assert event.description() == "Separated"
    assert view.itemProp("descriptionEdit", "text") == "Separated"

    scene.undo()
    assert event.uniqueId() == None
    assert event.description() == "Initial"
    assert view.itemProp("uniqueIdBox", "currentText") == ""
    assert view.itemProp("uniqueIdBox", "currentIndex") == -1
    assert view.itemProp("descriptionEdit", "text") == "Initial"

    scene.redo()
    assert event.uniqueId() == EventKind.Separated.value
    assert event.description() == "Separated"
    assert view.itemProp("descriptionEdit", "text") == "Separated"
