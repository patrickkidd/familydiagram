import os.path, datetime
import logging
import pytest, mock
from conftest import setPersonProperties, assertPersonProperties
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
from pkdiagram.mainwindow_form import Ui_MainWindow
from pkdiagram.pyqt import (
    Qt,
    QWidget,
    QMainWindow,
    QPointF,
    QTest,
    QApplication,
    QEventLoop,
)


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
    mw.resize(800, 600)
    mw.show()
    qtbot.addWidget(w)
    qtbot.waitActive(w)

    yield w

    w.setScene(None)
    w.hide()
    w.session.deinit()


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
        assert dv.scene.timelineModel.events() == [event]
        assert dv.graphicalTimelineCallout.isVisible() == True
        assert dv.isGraphicalTimelineShown() == True

        dv.scene.setCurrentDateTime(event.dateTime())
        dv.scene.removeItem(event)
        assert dv.scene.timelineModel.events() == []
        assert dv.graphicalTimelineCallout.isVisible() == False
        assert dv.isGraphicalTimelineShown() == False


def test_set_person_props(qtbot, dv: DocumentView, personProps):
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

    # Edit all fields on person props
    person = dv.scene.people()[0]
    setPersonProperties(dv.personProps, personProps)
    assert dv.personProps.rootProp("personModel").items == [
        person
    ]  # test drawer did not hide
    assertPersonProperties(person, personProps)


def test_load_reload_clears_SearchModel(dv):
    dv.caseProps.checkInitQml()

    dv.scene.searchModel.tags = ["blah"]
    dv.caseProps.setItemProp(
        "timelineSearch.descriptionEdit", "text", "Some description"
    )
    assert (
        dv.caseProps.itemProp("timelineSearch.descriptionEdit", "text")
        == "Some description"
    )

    dv.setScene(Scene(items=[]))
    assert dv.scene.searchModel.tags == []
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
    assert dv.scene.searchModel.tags == []

    tag = None
    for action in dv.ui.menuTags.actions():
        if action.isCheckable():
            tag = action.data()
            action.setChecked(True)
            break
    assert dv.scene.searchModel.tags == [tag]


def test_deselect_all_tags(dv):
    dv.scene.setTags(["here", "you", "are"])
    dv.scene.searchModel.tags = ["you"]
    dv.ui.actionDeselect_All_Tags.trigger()
    assert dv.scene.searchModel.tags == []
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
    _init_mw(mw, test_session)
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


def test_show_search_view_from_graphical_timeline(qtbot, dv):
    qtbot.mouseClick(dv.graphicalTimelineView.searchButton, Qt.LeftButton)
    assert dv.currentDrawer == dv.caseProps
    assert dv.caseProps.currentTab() == "search"


def test_show_events_from_timeline_callout(qtbot, dv):
    person = dv.scene.addItem(Person(name="person"))
    dv.scene.setCurrentDateTime(util.Date(2001, 1, 1))
    ensureVisAnimation = dv.caseProps.findItem("ensureVisAnimation")
    ensureVisAnimation_finished = util.Condition(ensureVisAnimation.finished)
    ensureVisibleSet = util.Condition(
        dv.caseProps.findItem("caseProps_timelineView").ensureVisibleSet
    )
    events = [
        Event(
            parent=person, dateTime=util.Date(2000 + i, 1, 1), description=f"Event {i}"
        )
        for i in range(100)
    ]
    DATETIME = events[50].dateTime()
    dv.scene.setCurrentDateTime(DATETIME)
    # dv.scene.nextTaggedDateTime()
    # dv.scene.nextTaggedDateTime()
    assert dv.scene.currentDateTime() == DATETIME
    qtbot.mouseClick(dv.graphicalTimelineCallout, Qt.LeftButton)
    firstRow = dv.scene.timelineModel.firstRowForDateTime(DATETIME)
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
