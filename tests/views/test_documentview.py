import os.path, datetime
import logging
import itertools

import pytest, mock

from pkdiagram import (
    util,
    Scene,
    Session,
    Person,
    DocumentView,
    TagsModel,
    Layer,
    Event,
    DocumentView,
)
from pkdiagram.objects import Emotion
from pkdiagram.mainwindow_form import Ui_MainWindow
from pkdiagram.documentview import RightDrawerView
from pkdiagram.pyqt import (
    Qt,
    QWidget,
    QMainWindow,
    QPointF,
    QApplication,
    QDateTime,
    QItemSelection,
    QItemSelectionModel,
)

pytestmark = [
    pytest.mark.component("DocumentView"),
    pytest.mark.depends_on(
        "Session",
        "TimelineModel",
        "SearchModel",
        "SceneModel",
        "AccessRightsModel",
        "CaseProperties",
    ),
]


##
## TODO: view.onAddEvent from personprops|quick -add
## TODO: add emotion dialog
##


_log = logging.getLogger(__name__)


@pytest.fixture
def dv(test_session, test_activation, qtbot):
    # A mainwindow that only has the ui elements and actions required for DocumentView and View.
    mw = QMainWindow()
    mw.ui = Ui_MainWindow()
    mw.ui.setupUi(mw)

    session = Session()
    w = DocumentView(mw, session)
    w.init()
    mw.setCentralWidget(w)
    # dv.view.itemToolBar.setFocus(Qt.MouseFocusReason)

    w.session.init(sessionData=test_session.account_editor_dict())

    w.setScene(Scene())  # leave empty
    mw.resize(800, 800)
    mw.show()
    qtbot.addWidget(w)
    qtbot.waitActive(w)

    yield w

    w.setScene(None)
    w.hide()
    w.deinit()


@pytest.mark.parametrize("editorMode", [True, False])
def test_editorMode_enabled(qtbot, dv, editorMode):
    dv.controller.onEditorMode(editorMode)
    qtbot.mouseClick(dv.view.rightToolBar.settingsButton, Qt.LeftButton)
    assert dv.caseProps.itemProp("variablesBox", "visible") == editorMode


def test_set_item_mode(qtbot, dv):
    # Hack - couldn't figure out how to get anythign to focus with QT_QPA_PLATFORM=offscreen
    with mock.patch.object(QApplication, "focusWidget", return_value=dv.view):
        dv.controller.updateActions()

    for buttonName, itemMode in (
        ("maleButton", util.ITEM_MALE),
        ("femaleButton", util.ITEM_FEMALE),
        ("marriageButton", util.ITEM_MARRY),
        ("childButton", util.ITEM_CHILD),
        ("pencilButton", util.ITEM_PENCIL),
        ("fusionButton", util.ITEM_FUSION),
        ("cutoffButton", util.ITEM_CUTOFF),
        ("conflictButton", util.ITEM_CONFLICT),
        ("projectionButton", util.ITEM_PROJECTION),
        ("distanceButton", util.ITEM_DISTANCE),
        ("towardButton", util.ITEM_TOWARD),
        ("awayButton", util.ITEM_AWAY),
        ("definedSelfButton", util.ITEM_DEFINED_SELF),
        ("calloutButton", util.ITEM_CALLOUT),
        ("reciprocityButton", util.ITEM_RECIPROCITY),
        ("insideButton", util.ITEM_INSIDE),
        ("outsideButton", util.ITEM_OUTSIDE),
        # ('actionMale', util.ITEM_ERASER),
    ):
        button = dv.view.itemToolBar.findChild(QWidget, buttonName)
        assert button, f"Could not find {buttonName}."

        qtbot.mouseClick(button, Qt.LeftButton)
        assert (
            dv.scene.itemMode() == itemMode
        ), f"{buttonName} did not enable its item mode."


def test_add_person(qtbot, dv):
    assert dv.view.noItemsCTALabel.isVisible() == True
    dv.scene.setItemMode(util.ITEM_MALE)
    qtbot.mouseClick(
        dv.view.viewport(), Qt.LeftButton, Qt.NoModifier, dv.view.rect().center()
    )
    assert len(dv.scene.people()) == 1
    assert dv.scene.query1(gender="male")
    assert dv.view.noItemsCTALabel.isVisible() == False


def test_remove_person(qtbot, dv):
    person = Person(name="Hey", lastName="You")
    dv.scene.addItem(person)
    assert dv.view.noItemsCTALabel.isVisible() == False

    person.setSelected(True)
    qtbot.clickYesAfter(lambda: dv.controller.onDelete())
    assert dv.scene.people() == []
    assert dv.view.noItemsCTALabel.isVisible() == True


def test_load_from_file_with_people_and_events(dv):
    people = [Person(name="p1"), Person(name="p2")]
    scene = Scene()
    scene.addItems(*people)
    people[0].setBirthDateTime(util.Date(2001, 1, 1))
    dv.setScene(scene)
    assert dv.view.noItemsCTALabel.isVisible() == False
    assert dv.ui.actionNext_Event.isEnabled() == True
    assert dv.ui.actionPrevious_Event.isEnabled() == True


def test_load_from_file_empty(dv):
    scene = Scene()
    dv.setScene(scene)
    assert dv.view.noItemsCTALabel.isVisible() == True
    # no events yet, so...
    assert dv.ui.actionNext_Event.isEnabled() == False
    assert dv.ui.actionPrevious_Event.isEnabled() == False


def test_remove_last_event(qtbot, dv):
    assert dv.graphicalTimelineCallout.isVisible() == False

    def _setShowGraphicalTimeline(self, on):
        if on:
            self.graphicalTimelineShim.setFixedHeight(
                util.GRAPHICAL_TIMELINE_SLIDER_HEIGHT
            )
        else:
            self.graphicalTimelineShim.setFixedHeight(0)

    with mock.patch.object(
        DocumentView, "setShowGraphicalTimeline", _setShowGraphicalTimeline
    ):
        person = dv.scene.addItem(Person(name="person"))
        event = Event(person, dateTime=util.Date(2001, 1, 1))
        assert dv.timelineModel.events() == [event]
        assert dv.graphicalTimelineCallout.isVisible() == True
        assert dv.isGraphicalTimelineShown() == True

        dv.scene.setCurrentDateTime(event.dateTime())
        dv.scene.removeItem(event)
        assert dv.timelineModel.events() == []
        assert dv.graphicalTimelineCallout.isVisible() == False
        assert dv.isGraphicalTimelineShown() == False


def test_inspect_to_person_props_to_hide(qtbot, dv: DocumentView, personProps):
    dv.scene.addItems(Person(name="p1", pos=QPointF(-200, -200)))

    # Single-click select first person
    person = dv.scene.people()[0]
    personPos = dv.view.mapFromScene(person.scenePos())
    qtbot.mouseClick(dv.view.viewport(), Qt.LeftButton, Qt.NoModifier, personPos)
    assert dv.scene.selectedItems() == [person]
    assert dv.currentDrawer == None
    assert dv.personProps.isShown() == False

    # Inspect action
    dv.ui.actionInspect.triggered.emit()
    # qtbot.keyClick(dv.view.viewport(), Qt.Key_I, Qt.ControlModifier)
    assert dv.personProps.isShown() == True
    assert dv.currentDrawer == dv.personProps
    assert dv.personProps.rootProp("personModel").items == [person]

    dv.personProps.qml.rootObject().done.emit()
    person = dv.scene.people()[0]
    assert (
        dv.personProps.rootProp("personModel").items == []
    ), "test drawer did not hide"


def test_inspect_events_from_graphical_timeline(qtbot, dv: DocumentView):
    person = Person(name="person")
    event_2 = Event(person, description="Event 2", dateTime=util.Date(2002, 1, 1))
    event_1 = Event(person, description="Event 1", dateTime=util.Date(2001, 1, 1))
    dv.scene.addItem(person)
    dv.timelineSelectionModel.select(
        QItemSelection(
            dv.timelineModel.indexForEvent(event_1),
            dv.timelineModel.indexForEvent(event_2),
        ),
        QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
    )
    assert dv.graphicalTimelineView.inspectButton.isVisible()
    dv.graphicalTimelineView.timeline.setFocus(True)
    qtbot.mouseClick(dv.graphicalTimelineView.inspectButton, Qt.LeftButton)
    # dv.ui.actionInspect.triggered.emit()
    assert dv.currentDrawer == dv.caseProps
    assert dv.caseProps.currentTab() == RightDrawerView.Timeline.value
    assert set(
        dv.caseProps.qml.rootObject()
        .property("eventProperties")
        .property("eventModel")
        .items
    ) == {event_1, event_2}


def test_load_reload_clears_SearchModel(dv):
    dv.caseProps.checkInitQml()

    dv.searchModel.tags = ["blah"]
    dv.caseProps.setItemProp(
        "timelineSearch.descriptionEdit", "text", "Some description"
    )
    assert (
        dv.caseProps.itemProp("timelineSearch.descriptionEdit", "text")
        == "Some description"
    )

    dv.setScene(Scene(items=[]))
    assert dv.searchModel.tags == []
    assert dv.caseProps.itemProp("timelineSearch.descriptionEdit", "text") == ""


def test_prevTaggedDateTime(dv):
    person = Person()
    person.birthEvent.setDateTime(util.Date(2001, 1, 1))
    dv.scene.addItem(person)
    dv.scene.setCurrentDateTime(util.Date(2002, 1, 1))
    dv.controller.onPrevEvent()
    assert dv.scene.currentDateTime() == util.Date(2001, 1, 1)


def test_nextTaggedDateTime(dv):
    person = Person()
    person.birthEvent.setDateTime(util.Date(2000, 1, 1))
    dv.scene.addItem(person)
    dv.scene.setCurrentDateTime(util.Date(1990, 1, 1))
    dv.controller.onNextEvent()
    assert dv.scene.currentDateTime() == util.Date(2000, 1, 1)


def test_toggle_search_tag_via_model(dv):
    """Was bombing on setCurrentDate."""
    dv.scene.setTags(["here", "you", "are"])
    searchView = dv.caseProps.findItem("timelineSearch")
    for tagsModel in searchView.findChildren(TagsModel):
        if tagsModel.items == [dv.scene]:
            tagsModel.setData(tagsModel.index(0, 0), True, role=tagsModel.ActiveRole)


def test_toggle_search_tag_via_action(dv):
    dv.scene.setTags(["here", "you", "are"])
    assert dv.searchModel.tags == []

    tag = None
    for action in dv.ui.menuTags.actions():
        if action.isCheckable():
            tag = action.data()
            action.setChecked(True)
            break
    assert dv.searchModel.tags == [tag]


def test_deselect_all_tags(dv):
    dv.scene.setTags(["here", "you", "are"])
    dv.searchModel.tags = ["you"]
    dv.ui.actionDeselect_All_Tags.trigger()
    assert dv.searchModel.tags == []
    for action in dv.ui.menuTags.actions():
        if action.isCheckable():  # skip deselect all action
            assert action.isChecked() == False


def test_toggle_search_layer_via_action(dv):
    layer = Layer(name="View 1")
    dv.scene.addItem(layer)
    searchView = dv.caseProps.findItem("timelineSearch")
    assert dv.scene.activeLayers() == []

    tag = None
    for action in dv.ui.menuLayers.actions():
        if action.isCheckable():
            tag = action.data()
            action.setChecked(True)
            break
    assert dv.scene.activeLayers() == [layer]


def test_deselect_all_layers(dv):
    layer = Layer(name="View 1")
    dv.scene.addItem(layer)
    layer.setActive(True)
    dv.ui.actionDeselect_All_Tags.trigger()
    assert dv.scene.activeLayers() == [layer]

    for action in dv.ui.menuLayers.actions():
        if action.isCheckable():  # skip deselect all action
            action.setChecked(False)
            break
    assert dv.scene.activeLayers() == []


@pytest.mark.skip("Couldn't get person to be selected on mouse click")
def test_retain_tab_between_selections(qtbot, mw, test_session):
    # _init_mw(mw, test_session)
    personA, personB = Person(), Person(kind="female")
    conflict = Emotion(personA=personA, personB=personB, kind=util.ITEM_CONFLICT)
    mw.scene.addItems(personA, personB, conflict)
    personA.setPos(-100, 0)
    personB.setPos(100, 0)
    assert mw.documentView.emotionProps.isVisible() == False
    assert mw.documentView.emotionProps.currentTab() == "item"

    conflict.setSelected(True)
    qtbot.keyClick(mw, Qt.Key_M, Qt.ShiftModifier | Qt.ControlModifier)
    assert mw.documentView.emotionProps.isVisible() == True
    assert mw.documentView.emotionProps.currentTab() == "meta"

    personA_pos = mw.documentView.view.mapFromScene(personA.pos())
    qtbot.mouseClick(mw.documentView.view, Qt.LeftButton, Qt.NoModifier, personA_pos)
    assert personA.isSelected() == False
    assert conflict.isSelected() == True
    assert mw.documentView.personProps.isVisible() == True
    assert mw.documentView.personProps.currentTab() == "meta"


def test_show_search_view_from_graphical_timeline(qtbot, dv: DocumentView):
    qtbot.mouseClick(dv.graphicalTimelineView.searchButton, Qt.LeftButton)
    assert dv.currentDrawer == dv.caseProps
    assert dv.caseProps.currentTab() == "search"


def test_show_events_from_timeline_callout(qtbot, dv: DocumentView):
    person = dv.scene.addItem(Person(name="person"))
    dv.scene.setCurrentDateTime(util.Date(2001, 1, 1))
    ensureVisAnimation = dv.caseProps.findItem("ensureVisAnimation")
    ensureVisAnimation_finished = util.Condition(ensureVisAnimation.finished)
    ensureVisibleSet = util.Condition(
        dv.caseProps.findItem("caseProps_timelineView").ensureVisibleSet
    )
    with dv.scene.batchAddRemoveItems():
        events = [
            Event(
                parent=person,
                dateTime=util.Date(2000 + i, 1, 1),
                description=f"Event {i}",
            )
            for i in range(100)
        ]
    DATETIME = events[50].dateTime()
    dv.scene.setCurrentDateTime(DATETIME)
    # dv.onNextEvent()
    # dv.onNextEvent()
    assert dv.scene.currentDateTime() == DATETIME
    qtbot.mouseClick(dv.graphicalTimelineCallout, Qt.LeftButton)
    firstRow = dv.timelineModel.firstRowForDateTime(DATETIME)
    assert dv.currentDrawer == dv.caseProps
    assert dv.caseProps.currentTab() == "timeline"
    assert ensureVisAnimation_finished.wait() == True
    assert ensureVisibleSet.wait() == True
    assert ensureVisibleSet.callArgs[0][0] == util.QML_ITEM_HEIGHT * firstRow
    # contentY was still zero after set and table not updated visually, but then
    # would jump there on first scroll. Suggests qml bug.
    #
    # assert ( dv.caseProps.itemProp("caseProps_timelineView.table", "contentY")
    #     == util.QML_ITEM_HEIGHT * firstRow )


def test_nextTaggedDate_prevTaggedDateTime(dv: DocumentView):
    scene = dv.scene
    scene.replaceEventProperties(["Var 1", "Var 2"])
    person1 = Person()
    person1.setBirthDateTime(util.Date(2000, 1, 1))  # 0
    scene.addItem(person1)
    event1 = Event(parent=person1, dateTime=util.Date(2001, 1, 1))  # 1
    event1.dynamicProperty("var-1").set("One")
    event2 = Event(parent=person1, dateTime=util.Date(2002, 1, 1))  # 2
    event3 = Event(parent=person1, dateTime=util.Date(2003, 1, 1))  # 3
    event3.dynamicProperty("var-2").set("Two")
    scene.setCurrentDateTime(person1.birthDateTime())  # 0
    dv.controller.onNextEvent()  # 1
    assert scene.currentDateTime() == event1.dateTime()

    dv.controller.onNextEvent()  # 2
    assert scene.currentDateTime() == event2.dateTime()

    dv.controller.onNextEvent()  # 3
    assert scene.currentDateTime() == event3.dateTime()

    dv.controller.onPrevEvent()  # 2
    assert scene.currentDateTime() == event2.dateTime()

    dv.controller.onPrevEvent()  # 1
    assert scene.currentDateTime() == event1.dateTime()

    dv.controller.onPrevEvent()  # 0
    assert scene.currentDateTime() == person1.birthDateTime()


def test_nextTaggedDate_uses_search_tags(dv: DocumentView):
    scene = dv.scene
    tags = ["test"]

    person1 = Person()
    person1.setBirthDateTime(util.Date(1980, 1, 1))
    person2 = Person()
    person2.setBirthDateTime(util.Date(1990, 2, 2))
    person3 = Person()
    person3.setBirthDateTime(util.Date(2000, 3, 3))
    scene.addItem(person1)
    scene.addItem(person2)
    scene.addItem(person3)

    # test first before setting tags

    scene.setCurrentDateTime(person1.birthDateTime())
    assert scene.currentDateTime() == person1.birthDateTime()

    dv.controller.onPrevEvent()  # noop
    assert scene.currentDateTime() == person1.birthDateTime()

    dv.controller.onNextEvent()
    assert scene.currentDateTime() == person2.birthDateTime()

    dv.controller.onNextEvent()
    assert scene.currentDateTime() == person3.birthDateTime()

    dv.controller.onNextEvent()  # noop
    assert scene.currentDateTime() == person3.birthDateTime()

    # then test after setting tags
    person1.birthEvent.setTags(tags)
    person3.birthEvent.setTags(tags)
    dv.searchModel.setTags(tags)

    taggedEvents = [e for e in scene.events() if e.hasTags(tags)]
    scene.setCurrentDateTime(taggedEvents[0].dateTime())
    assert scene.currentDateTime() == person1.birthDateTime()

    dv.controller.onPrevEvent()  # noop
    assert scene.currentDateTime() == person1.birthDateTime()

    dv.controller.onNextEvent()  # skip person 2 for tags
    assert scene.currentDateTime() == person3.birthDateTime()

    dv.controller.onNextEvent()  # noop
    assert scene.currentDateTime() == person3.birthDateTime()


def test_nextTaggedDate_uses_searchModel(dv: DocumentView):
    scene = dv.scene
    tags = ["test"]

    person1 = Person(name="One")
    person1.setBirthDateTime(util.Date(1980, 1, 1))
    person2 = Person(name="Two")
    person2.setBirthDateTime(util.Date(1990, 2, 2))
    person3 = Person(name="Three")
    person3.setBirthDateTime(util.Date(2000, 3, 3))
    scene.addItem(person1)
    scene.addItem(person2)
    scene.addItem(person3)

    # test first before setting tags

    scene.setCurrentDateTime(person1.birthDateTime())
    assert scene.currentDateTime() == person1.birthDateTime()

    dv.controller.onPrevEvent()  # noop
    assert scene.currentDateTime() == person1.birthDateTime()

    dv.controller.onNextEvent()
    assert scene.currentDateTime() == person2.birthDateTime()

    dv.controller.onNextEvent()
    assert scene.currentDateTime() == person3.birthDateTime()

    dv.controller.onNextEvent()  # noop
    assert scene.currentDateTime() == person3.birthDateTime()

    # then test after setting tags
    person1.birthEvent.setTags(tags)
    person3.birthEvent.setTags(tags)
    dv.searchModel.setTags(tags)

    taggedEvents = [e for e in scene.events() if e.hasTags(tags)]
    scene.setCurrentDateTime(taggedEvents[0].dateTime())
    assert scene.currentDateTime() == person1.birthDateTime()

    dv.controller.onPrevEvent()  # noop
    assert scene.currentDateTime() == person1.birthDateTime()

    dv.controller.onNextEvent()  # skip person 2 for tags
    assert scene.currentDateTime() == person3.birthDateTime()

    dv.controller.onNextEvent()  # noop
    assert scene.currentDateTime() == person3.birthDateTime()

    dv.controller.onPrevEvent()
    assert scene.currentDateTime() == person1.birthDateTime()

    dv.controller.onPrevEvent()  # noop
    assert scene.currentDateTime() == person1.birthDateTime()


def test_writePDF(tmp_path, dv: DocumentView):
    FILE_PATH = os.path.join(tmp_path, "test_out.xlsx")

    person = dv.scene.addItem(Person(name="person"))
    Event(person, datetime=util.Date(2001, 1, 1), description="Something happened")
    Event(
        person, datetime=util.Date(2002, 1, 1), description="Something happened again"
    )
    dv.controller.writeExcel(FILE_PATH)
    assert os.path.isfile(FILE_PATH) == True


def test_writeJPG(tmp_path, dv: DocumentView):
    FILE_PATH = os.path.join(tmp_path, "test_writeJPG.jpg")

    dv.scene.addItem(Person(name="person"))
    dv.scene.setCurrentDateTime(util.Date(2001, 1, 1))
    dv.controller.writeJPG(FILE_PATH)
    assert os.path.isfile(FILE_PATH) == True


def test_writePNG(tmp_path, dv: DocumentView):
    FILE_PATH = os.path.join(tmp_path, "test_writePNG.png")

    person = dv.scene.addItem(Person(name="person"))
    dv.scene.setCurrentDateTime(util.Date(2001, 1, 1))
    dv.controller.writePNG(FILE_PATH)
    assert os.path.isfile(FILE_PATH) == True


def test_writeExcel(tmp_path, dv: DocumentView):
    FILE_PATH = os.path.join(tmp_path, "test_out.xlsx")

    person = dv.scene.addItem(Person(name="person"))
    Event(person, datetime=util.Date(2001, 1, 1), description="Something happened")
    Event(
        person, datetime=util.Date(2002, 1, 1), description="Something happened again"
    )
    dv.controller.writeExcel(FILE_PATH)
    assert os.path.isfile(FILE_PATH) == True


def test_writeExcel_2(tmp_path, dv: DocumentView):
    scene = Scene()
    person1, person2 = Person(name="p1"), Person(name="p2")
    scene.addItems(person1, person2)
    kinds = itertools.cycle(
        [
            util.ITEM_CUTOFF,
            util.ITEM_CONFLICT,
            util.ITEM_PROJECTION,
            util.ITEM_DISTANCE,
            util.ITEM_TOWARD,
            util.ITEM_AWAY,
            util.ITEM_DEFINED_SELF,
            util.ITEM_RECIPROCITY,
            util.ITEM_INSIDE,
            util.ITEM_OUTSIDE,
        ]
    )
    iDay = 0
    stride = 2
    firstDate = QDateTime.currentDateTime().addDays(-365 * 5)
    for i in range(100):
        for parent in (person1, person2):
            iDay += stride
            dateTime = firstDate.addDays(iDay)
            Event(parent, description="Test event %i" % iDay, dateTime=dateTime)
        iDay += stride
        dateTime = firstDate.addDays(iDay)
        Emotion(personA=person1, personB=person2, kind=next(kinds), dateTime=dateTime)
    # util.printModel(dv.timelineModel)
    filePath = os.path.join(tmp_path, "test.xlsx")
    dv.controller.writeExcel(filePath)


def test_add_emotion_adds_tags(dv: DocumentView):
    person1, person2 = Person(), Person()
    dv.scene.addItems(person1, person2)
    dv.searchModel.setTags(["conflict"])
    emotion = Emotion(personA=person1, personB=person2, kind=util.ITEM_CONFLICT)
    dv.scene.addItem(emotion)
    assert emotion.tags() == ["conflict"]


def test_uploadButton(qtbot, dv: DocumentView):
    uploadToServer = util.Condition(dv.controller.uploadToServer)
    qtbot.mouseClick(dv.view.rightToolBar.settingsButton, Qt.LeftButton)
    dv.caseProps.scrollSettingsToBottom()
    QApplication.processEvents()  # for scroll to complete
    dv.caseProps.mouseClick("uploadButton")
    assert uploadToServer.wait() == True
    assert uploadToServer.callCount == 1
