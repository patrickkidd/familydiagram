import os.path, datetime
import logging
import itertools
import pickle
import json
import contextlib

import pytest
from mock import patch, MagicMock

from btcopilot.schema import EventKind, RelationshipKind
from pkdiagram.pyqt import (
    Qt,
    QWidget,
    QMainWindow,
    QPointF,
    QApplication,
    QDateTime,
    QItemSelection,
    QItemSelectionModel,
    QPrinter,
    QDialog,
    QMessageBox,
    QRect,
)
from pkdiagram import util
from pkdiagram.scene import (
    Scene,
    Person,
    Layer,
    Event,
    Emotion,
    Marriage,
    Callout,
    ItemMode,
    Event,
)
from pkdiagram.documentview import DocumentView, DocumentController, RightDrawerView
from pkdiagram.mainwindow.mainwindow_form import Ui_MainWindow
from pkdiagram.app import Session
from pkdiagram.widgets import QmlWidgetHelper

from pkdiagram.tests.widgets import TestActiveListEdit
from pkdiagram.tests.views.eventform.testeventform import TestEventForm

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
def dv(test_session, test_activation, qtbot, scene):
    # A mainwindow that only has the ui elements and actions required for DocumentView and View.
    mw = QMainWindow()
    mw.ui = Ui_MainWindow()
    mw.ui.setupUi(mw)

    session = Session()
    w = DocumentView(mw, session)
    w.init()
    w.__mw = mw
    mw.setCentralWidget(w)
    # dv.view.itemToolBar.setFocus(Qt.MouseFocusReason)

    w.session.init(sessionData=test_session.account_editor_dict())

    w.setScene(scene)  # leave empty
    mw.resize(800, 800)
    mw.show()
    qtbot.addWidget(w)
    qtbot.waitActive(w)

    yield w

    w.setScene(None)
    mw.hide()
    w.deinit()
    mw = None


@pytest.mark.parametrize("readOnly", [True, False])
def test_readOnly(qtbot, dv, readOnly):
    dv.setScene(Scene(readOnly=readOnly))
    assert dv.view.rightToolBar.addAnythingButton.isVisible() == bool(not readOnly)


@pytest.mark.parametrize("editorMode", [True, False])
def test_editorMode_enabled(qtbot, dv, editorMode):
    dv.controller.onEditorMode(editorMode)
    qtbot.mouseClick(dv.view.rightToolBar.settingsButton, Qt.LeftButton)
    assert dv.caseProps.itemProp("variablesBox", "visible") == editorMode


def test_set_item_mode(qtbot, dv):
    # Hack - couldn't figure out how to get anythign to focus with QT_QPA_PLATFORM=offscreen
    with patch.object(QApplication, "focusWidget", return_value=dv.view):
        dv.controller.updateActions()

    for buttonName, itemMode in (
        ("maleButton", ItemMode.Male),
        ("femaleButton", ItemMode.Female),
        ("marriageButton", ItemMode.Marry),
        ("childButton", ItemMode.Child),
        ("pencilButton", ItemMode.Pencil),
        ("fusionButton", ItemMode.Fusion),
        ("cutoffButton", ItemMode.Cutoff),
        ("conflictButton", ItemMode.Conflict),
        ("projectionButton", ItemMode.Projection),
        ("distanceButton", ItemMode.Distance),
        ("towardButton", ItemMode.Toward),
        ("awayButton", ItemMode.Away),
        ("definedSelfButton", ItemMode.DefinedSelf),
        ("calloutButton", ItemMode.Callout),
        ("reciprocityButton", ItemMode.Reciprocity),
        ("insideButton", ItemMode.Inside),
        ("outsideButton", ItemMode.Outside),
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
    dv.scene.setItemMode(ItemMode.Male)
    qtbot.mouseClick(
        dv.view.viewport(), Qt.LeftButton, Qt.NoModifier, dv.view.rect().center()
    )
    assert len(dv.scene.people()) == 1
    assert dv.scene.query1(gender="male")
    assert dv.view.noItemsCTALabel.isVisible() == False


def test_remove_person(dv, scene):
    person = Person(name="Hey", lastName="You")
    scene.addItem(person)
    assert dv.view.noItemsCTALabel.isVisible() == False

    person.setSelected(True)
    with patch(
        "PyQt5.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes
    ) as question:
        dv.controller.onDelete()
    assert question.call_count == 1
    assert scene.people() == []
    assert dv.view.noItemsCTALabel.isVisible() == True


def test_undo_remove_event(dv, scene):
    person = scene.addItem(Person(name="Hey"))
    event1, event2 = scene.addItems(
        Event(
            EventKind.Shift,
            person,
            description="Event 1",
            dateTime=util.Date(2001, 1, 1),
        ),
        Event(
            EventKind.Shift,
            person,
            description="Event 2",
            dateTime=util.Date(2002, 1, 1),
        ),
    )
    scene.setCurrentDateTime(
        util.Date(2003, 1, 1)
    )  # so the flash happens no matter what
    scene.removeItem(event2, undo=True)
    with patch("pkdiagram.scene.Person.flash") as flash:
        scene.undo()
    assert set(scene.events(onlyDated=True)) == {event2, event1}
    assert flash.call_count == 1
    # and no exceptions form documentview


def test_undo_remove_undated_emotion(dv, scene):
    personA, personB = scene.addItems(Person(name="PersonA"), Person(name="PersonB"))
    event = scene.addItem(
        Event(EventKind.Shift, personA, dateTime=util.Date(2001, 1, 1))
    )
    emotion = scene.addItem(Emotion(RelationshipKind.Conflict, personB, person=personA))
    return
    assert dv.isGraphicalTimelineShown() == True

    scene.removeItem(emotion, undo=True)
    assert dv.isGraphicalTimelineShown() == True

    scene.undo()
    assert dv.isGraphicalTimelineShown() == True


def test_undo_remove_emotion_no_other_events(dv, scene):
    personA, personB = scene.addItems(Person(name="PersonA"), Person(name="PersonB"))
    event = scene.addItem(
        Event(
            EventKind.Shift,
            personA,
            relationship=RelationshipKind.Conflict,
            relationshipTargets=[personB],
            dateTime=util.Date(2002, 1, 1),
        )
    )
    assert dv.isGraphicalTimelineShown() == True

    scene.removeItem(event, undo=True)
    assert dv.isGraphicalTimelineShown() == False

    scene.undo()
    assert dv.isGraphicalTimelineShown() == True


def test_add_callout_from_mouse(qtbot, scene, dv):
    layerItemAdded = util.Condition(scene.layerItemAdded)
    layerItemRemoved = util.Condition(scene.layerItemRemoved)
    scene.addItem(Layer(name="Here we are", active=True))
    scene.setItemMode(ItemMode.Callout)
    qtbot.mouseClick(
        dv.view.viewport(),
        Qt.LeftButton,
        Qt.NoModifier,
        dv.view.viewport().rect().center(),
    )
    assert layerItemAdded.callCount == 1
    assert layerItemAdded.callArgs[0][0].__class__ == Callout
    scene.undo()
    assert layerItemRemoved.callCount == 1
    assert scene.layerItems() == []


def test_add_callout_from_mouse_to_person(qtbot, scene, dv):
    layerItemAdded = util.Condition(scene.layerItemAdded)
    layerItemRemoved = util.Condition(scene.layerItemRemoved)
    layer = Layer(name="Here we are", active=True)
    person = Person(name="Here I am")
    scene.addItems(layer, person)
    scene.setItemMode(ItemMode.Callout)
    person.setSelected(True)
    qtbot.mouseClick(
        dv.view.viewport(),
        Qt.LeftButton,
        Qt.NoModifier,
        dv.view.viewport().rect().center(),
    )
    assert layerItemAdded.callCount == 1
    assert layerItemAdded.callArgs[0][0].__class__ == Callout
    scene.undo()
    assert layerItemRemoved.callCount == 1
    assert scene.layerItems() == []


def test_load_from_file_empty(scene, dv):
    assert dv.view.noItemsCTALabel.isVisible() == True
    # no events yet, so...
    assert dv.ui.actionNext_Event.isEnabled() == False
    assert dv.ui.actionPrevious_Event.isEnabled() == False
    assert dv.isGraphicalTimelineShown() == False


def assert_UIHasAnyEvents(dv, hasEvents: bool):
    assert bool(dv.timelineModel.rowCount()) == hasEvents
    assert dv.ui.actionNext_Event.isEnabled() == hasEvents
    assert dv.ui.actionPrevious_Event.isEnabled() == hasEvents
    assert dv.isGraphicalTimelineShown() == hasEvents


def test_load_from_file_with_people_no_events(scene, dv):
    scene.addItems(Person(name="p1"))
    assert_UIHasAnyEvents(dv, False)


def test_load_from_file_with_people_and_events(scene, dv):
    dv.caseProps.checkInitQml()
    p1, p2 = scene.addItems(Person(name="p1"), Person(name="p2"))
    birth_event = scene.addItem(
        Event(EventKind.Shift, p1, dateTime=util.Date(2001, 1, 1))
    )
    assert_UIHasAnyEvents(dv, True)
    assert dv.view.noItemsCTALabel.isVisible() == False


def test_add_first_event_shows_UI_elements(scene, dv):
    assert_UIHasAnyEvents(dv, False)
    assert dv.view.noItemsCTALabel.isVisible() == True

    person = scene.addItem(Person(name="p1"))
    birth_event = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2001, 1, 1))
    )
    assert_UIHasAnyEvents(dv, True)
    assert dv.view.noItemsCTALabel.isVisible() == False


def test_remove_last_event_hides_UI_elements(scene, dv):
    """
    TimelineModel needs to respond to changes in events, not currentDateTime.
    """
    person = scene.addItem(Person(name="p1"))
    birth_event = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2001, 1, 1))
    )
    scene.setCurrentDateTime(birth_event.dateTime())
    assert_UIHasAnyEvents(dv, True)

    scene.removeItem(birth_event)
    assert_UIHasAnyEvents(dv, False)


def test_remove_last_event(scene, dv):
    assert dv.graphicalTimelineCallout.isVisible() == False

    def _setShowGraphicalTimeline(self, on):
        if on:
            self.graphicalTimelineShim.setFixedHeight(
                util.GRAPHICAL_TIMELINE_SLIDER_HEIGHT
            )
        else:
            self.graphicalTimelineShim.setFixedHeight(0)

    with patch.object(
        DocumentView, "setShowGraphicalTimeline", _setShowGraphicalTimeline
    ):
        person = scene.addItem(Person(name="person"))
        event = scene.addItem(
            Event(EventKind.Shift, person, dateTime=util.Date(2001, 1, 1))
        )
        assert set(x.event for x in dv.timelineModel.timelineRows()) == {event}
        assert_UIHasAnyEvents(dv, True)

        dv.scene.setCurrentDateTime(event.dateTime())
        dv.scene.removeItem(event)
        assert_UIHasAnyEvents(dv, False)


def test_inspect_to_person_props_to_hide(qtbot, scene, dv: DocumentView):
    scene.addItems(Person(name="p1", pos=QPointF(-200, -200)))

    # Single-click select first person
    person = scene.people()[0]
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


def test_inspect_events_from_graphical_timeline(qtbot, scene, dv: DocumentView):
    dv.setCurrentDrawer(dv.caseProps)
    # dv.caseProps.checkInitQml()
    person = scene.addItem(Person(name="person"))
    event_1, event_2 = scene.addItems(
        Event(
            EventKind.Shift,
            person,
            description="Event 1",
            dateTime=util.Date(2001, 1, 1),
        ),
        Event(
            EventKind.Shift,
            person,
            description="Event 2",
            dateTime=util.Date(2002, 1, 1),
        ),
    )
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
    assert dv.currentDrawer == dv.eventFormDrawer
    assert set(dv.eventFormDrawer.eventForm._events) == {event_1, event_2}


def test_inspect_new_emotion_via_click_select(qtbot, scene, dv: DocumentView):
    personA, personB = scene.addItems(Person(name="PersonA"), Person(name="PersonB"))
    personA.setItemPos(QPointF(-200, -200))
    personB.setItemPos(QPointF(200, 200))
    emotion1, emotion2 = scene.addItems(
        Emotion(RelationshipKind.Conflict, personB, person=personA),
        Emotion(RelationshipKind.Projection, personB, person=personA),
    )
    emotion1.setSelected(True)
    dv.controller.onInspect()
    assert dv.currentDrawer == dv.emotionProps
    assert dv.emotionProps.rootProp("emotionModel").items == [emotion1]

    qtbot.mouseClick(
        dv.view.viewport(),
        Qt.LeftButton,
        Qt.NoModifier,
        dv.view.mapFromScene(emotion2.sceneBoundingRect().center()),
    )
    assert emotion1.isSelected() == False
    assert emotion2.isSelected() == True
    assert dv.currentDrawer == dv.emotionProps
    assert dv.emotionProps.rootProp("emotionModel").items == [emotion2]


def test_inspect_emotion_from_eventform(scene, dv: DocumentView):
    personA, personB = scene.addItems(Person(name="personA"), Person(name="personB"))
    event = scene.addItem(
        Event(
            person=personA,
            kind=EventKind.Shift,
            relationship=RelationshipKind.Conflict,
            relationshipTargets=personB,
            color="#ff0000",
            intensity=5,
            notes="Some notes",
        )
    )
    emotions = scene.emotionsFor(event)
    dv.controller.inspectEvents([event])
    assert dv.currentDrawer == dv.eventFormDrawer

    inspectEmotionsButton = dv.eventFormDrawer.rootProp("inspectEmotionButton")
    dv.eventFormDrawer.mouseClick(inspectEmotionsButton)
    assert dv.currentDrawer == dv.emotionProps
    assert dv.emotionProps.getPropSheetModel().items == emotions


def test_change_graphical_timeline_selection_hides_event_props(scene, dv):
    dv.caseProps.checkInitQml()
    personA, personB = scene.addItems(Person(name="PersonA"), Person(name="PersonB"))
    event_1, event_2 = scene.addItems(
        Event(EventKind.Shift, personA, dateTime=util.Date(2001, 1, 1)),
        Event(EventKind.Shift, personB, dateTime=util.Date(2002, 1, 1)),
    )
    dv.timelineSelectionModel.select(
        QItemSelection(
            dv.timelineModel.indexForEvent(event_1),
            dv.timelineModel.indexForEvent(event_2),
        ),
        QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
    )
    dv.setCurrentDrawer(dv.caseProps)
    dv.caseProps.qml.setFocus(True)
    dv.controller.onInspect()
    assert dv.currentDrawer == dv.eventFormDrawer

    dv.setShowGraphicalTimeline(True)
    dv.graphicalTimelineView.timeline.canvas.selectRowsInRect(QRect())
    assert dv.currentDrawer == dv.eventFormDrawer


def test_edit_datetime_in_event_props_doesnt_hide_event_props(scene, dv):
    dv.caseProps.checkInitQml()
    personA, personB = scene.addItems(Person(name="PersonA"), Person(name="PersonB"))
    event_1, event_2 = scene.addItems(
        Event(EventKind.Shift, personA, dateTime=util.Date(2001, 1, 1)),
        Event(EventKind.Shift, personB, dateTime=util.Date(2002, 1, 1)),
    )
    dv.caseProps.qml.setFocus(True)
    dv.timelineSelectionModel.select(
        QItemSelection(
            dv.timelineModel.indexForEvent(event_1),
            dv.timelineModel.indexForEvent(event_2),
        ),
        QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
    )
    dv.setCurrentDrawer(dv.caseProps)
    dv.caseProps.qml.setFocus(True)
    dv.controller.onInspect()
    assert dv.currentDrawer == dv.eventFormDrawer

    TestEventForm(dv.eventFormDrawer).set_startDateTime(util.Date(2000, 1, 1))
    assert dv.currentDrawer == dv.eventFormDrawer


@pytest.mark.skip("Couldn't get the correct bounding rect for the event delegate")
def test_delete_event_from_timeline_via_keyboard_shortcut(qtbot, scene, dv):
    """
    - Start with an event for a person.
    - Show the timeline view
    - Click to select the event
    - Trigger the deleteAction via its keyboard shortcut
    - Assert that the user was prompted to confirm deletion
    - Assert that the event was deleted
    """

    person = scene.addItem(Person(name="TestPerson"))
    event = scene.addItem(
        Event(
            EventKind.Shift,
            person,
            description="Event to Delete",
            dateTime=util.Date(2001, 1, 1),
        )
    )
    assert scene.events() == [event]

    dv.setCurrentDrawer(dv.caseProps)
    dv.caseProps.checkInitQml()
    assert dv.ui.actionDelete.isEnabled() == False

    row_y = util.QML_ITEM_HEIGHT + (util.QML_ITEM_HEIGHT // 2)
    eventCenter = QPointF(50, row_y)

    dv.caseProps.clickTimelineViewItem(
        dv.caseProps.rootProp("timelineView"),
        event.description(),
        column=3,
    )
    # qtbot.mouseClick(
    #     dv.caseProps.qml, Qt.LeftButton, Qt.NoModifier, eventCenter.toPoint()
    # )
    # dv.controller.updateActions()
    assert dv.ui.actionDelete.isEnabled() == True

    with patch(
        "PyQt5.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes
    ) as mock_question:
        qtbot.keyPress(
            dv.caseProps.qml, Qt.Key.Key_Delete, Qt.KeyboardModifier.ControlModifier
        )
    assert mock_question.call_count >= 1, "Delete key did not trigger delete action"
    assert scene.events() == []


def test_load_reload(qtbot, dv):
    dv.caseProps.checkInitQml()
    dv.searchDialog.checkInitQml()

    dv.searchModel.tags = ["blah"]
    dv.searchModel.description = "Some description"
    assert dv.searchDialog.itemProp("descriptionEdit", "text") == "Some description"
    dv.graphicalTimelineView.timeline.zoomAbsolute(1.5)
    assert dv.graphicalTimelineView.timeline.scaleFactor == 1.5
    qtbot.mouseClick(dv.view.rightToolBar.timelineButton, Qt.LeftButton)
    assert dv.currentDrawer == dv.caseProps

    dv.setScene(Scene(items=[]))
    assert dv.searchModel.tags == []
    assert dv.searchDialog.itemProp("descriptionEdit", "text") == ""
    assert dv.graphicalTimelineView.timeline.scaleFactor == 1.0
    assert dv.graphicalTimelineView.lastScaleFactor == 1.0
    assert dv.view.rightToolBar.timelineButton.isChecked() == False
    assert dv.currentDrawer == None


def test_prevTaggedDateTime(scene, dv):
    person = scene.addItem(Person())
    event = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2001, 1, 1))
    )
    scene.setCurrentDateTime(util.Date(2002, 1, 1))
    dv.controller.onPrevEvent()
    assert scene.currentDateTime() == util.Date(2001, 1, 1)


def test_nextTaggedDateTime(scene, dv):
    person = scene.addItem(Person())
    event = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 1))
    )
    scene.setCurrentDateTime(util.Date(1990, 1, 1))
    dv.controller.onNextEvent()
    assert scene.currentDateTime() == util.Date(2000, 1, 1)


def test_toggle_search_tag_via_model(scene, dv):
    """Was bombing on setCurrentDate."""
    person = scene.addItem(Person())
    birth_event, event_1, event_2, event_3 = scene.addItems(
        Event(EventKind.Shift, person, dateTime=util.Date(2001, 1, 1)),
        Event(EventKind.Shift, person, dateTime=util.Date(2002, 1, 1), tags=["you"]),
        Event(EventKind.Shift, person, dateTime=util.Date(2002, 1, 1), tags=["you"]),
        Event(EventKind.Shift, person, dateTime=util.Date(2003, 1, 1), tags=["you"]),
    )
    scene.setTags(["here", "you", "are"])

    dv.ui.actionFind.trigger()
    tagsEdit = dv.searchDialog.rootProp("tagsEdit")
    propsPage = dv.searchDialog.rootProp("propsPage")
    QmlWidgetHelper.scrollChildToVisible(propsPage, tagsEdit)
    tagsEdit_list = TestActiveListEdit(
        dv.searchDialog, dv.searchDialog.qml.rootObject().property("tagsEdit")
    )
    tagsEdit_list.clickActiveBox("you")

    assert scene.currentDateTime() == event_1.dateTime()
    # Ensure callout updates
    assert dv.graphicalTimelineCallout.events[0].dateTime() == event_1.dateTime()


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
    assert dv.scene.activeLayers() == []

    tag = None
    for action in dv.ui.menuLayers.actions():
        if action.isCheckable():
            tag = action.data()
            action.setChecked(True)
            break
    assert dv.scene.activeLayers() == [layer]


def test_emotional_unit_no_menu_actions(dv):
    personA, personB = Person(name="A"), Person(name="B")
    marriage_1 = Marriage(personA, personB)
    dv.scene.addItems(personA, personB, marriage_1)
    assert [x.data() for x in dv.ui.menuLayers.actions() if x.data()] == []


def test_search_show(dv):
    dv.ui.actionFind.trigger()
    assert dv.searchDialog.isShown() == True
    assert dv.searchDialog.isVisible() == True


@pytest.mark.parametrize("bothUnits", [True, False])
def test_search_show_emotional_unit(dv, bothUnits):
    personA, personB = Person(name="A"), Person(name="B")
    marriage_1 = Marriage(personA, personB)
    personC, personD = Person(name="C"), Person(name="D")
    marriage_2 = Marriage(personC, personD)
    dv.scene.addItems(personA, personB, personC, personD)
    dv.scene.addItems(marriage_1, marriage_2)
    child_1, child_2, child_3, child_4 = (
        Person(name="E"),
        Person(name="F"),
        Person(name="G"),
        Person(name="H"),
    )
    dv.scene.addItems(child_1, child_2, child_3, child_4)
    child_1.setParents(marriage_1)
    child_2.setParents(marriage_1)
    child_3.setParents(marriage_2)
    child_4.setParents(marriage_2)
    dv.scene.addItems(child_1, child_2, child_3, child_4)

    dv.ui.actionFind.trigger()

    propsPage = dv.searchDialog.rootProp("propsPage")
    emotionalUnitsEdit = dv.searchDialog.qml.rootObject().property("emotionalUnitsEdit")
    QmlWidgetHelper.scrollChildToVisible(propsPage, emotionalUnitsEdit)

    emotionalUnitsEdit_list = TestActiveListEdit(dv.searchDialog, emotionalUnitsEdit)
    emotionalUnitsEdit_list.clickActiveBox(marriage_1.itemName())
    if bothUnits:
        emotionalUnitsEdit_list.clickActiveBox(marriage_2.itemName())
        QApplication.processEvents()
    if bothUnits:
        assert (
            dv.view.hiddenItemsLabel.text()
            == f"Emotional Units: {marriage_1.emotionalUnit().name()}, {marriage_2.emotionalUnit().name()}"
        )
    else:
        assert (
            dv.view.hiddenItemsLabel.text()
            == f"Emotional Unit: {marriage_1.emotionalUnit().name()} (Hiding 4 people)"
        )
    assert personA.isVisible() == True
    assert personB.isVisible() == True
    assert child_1.isVisible() == True
    assert child_2.isVisible() == True
    assert personC.isVisible() == bothUnits
    assert personD.isVisible() == bothUnits
    assert child_3.isVisible() == bothUnits
    assert child_4.isVisible() == bothUnits
    # TODO: verify QActions checked for layers
    for action in dv.ui.menuLayers.actions():
        assert action.isChecked() == False, f"{action.text()} should be unchecked"


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
    conflict = Emotion(RelationshipKind.Conflict, personB, person=personA)
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


def test_show_graphical_timeline(qtbot, scene, dv: DocumentView):
    assert dv.isGraphicalTimelineShown() == False
    person = scene.addItem(Person(name="person"))
    scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 1, 1)))
    assert dv.scene.currentDateTime() == util.Date(2001, 1, 1)
    assert dv.isGraphicalTimelineShown() == True
    assert dv.graphicalTimelineCallout.isVisible() == True

    qtbot.mouseClick(dv.graphicalTimelineView.expandButton)
    assert dv.isGraphicalTimelineShown() == True
    assert dv.graphicalTimelineCallout.isVisible() == False


def test_show_search_view_from_graphical_timeline(qtbot, dv: DocumentView):
    was_currentDrawer = dv.currentDrawer
    qtbot.mouseClick(dv.graphicalTimelineView.searchButton, Qt.LeftButton)
    assert dv.currentDrawer == was_currentDrawer
    assert dv.searchDialog.isVisible() == True


def test_show_events_from_timeline_callout(qtbot, scene, dv: DocumentView):
    person = scene.addItem(Person(name="person"))
    events = scene.addItems(
        *[
            Event(
                EventKind.Shift,
                person,
                dateTime=util.Date(2000 + i, 1, 1),
                description=f"Event {i}",
            )
            for i in range(100)
        ]
    )
    scene.setCurrentDateTime(util.Date(2001, 1, 1))
    ensureVisAnimation = dv.caseProps.findItem("ensureVisAnimation")
    ensureVisAnimation_finished = util.Condition(ensureVisAnimation.finished)
    ensureVisibleSet = util.Condition(
        dv.caseProps.rootProp("timelineView").ensureVisibleSet
    )
    DATETIME = events[50].dateTime()
    scene.setCurrentDateTime(DATETIME)
    # dv.onNextEvent()
    # dv.onNextEvent()
    assert scene.currentDateTime() == DATETIME
    qtbot.mouseClick(dv.graphicalTimelineCallout, Qt.LeftButton)
    firstRow, lastRow = dv.timelineModel.firstAndLastRowsForDateTime(DATETIME)
    assert dv.currentDrawer == dv.caseProps
    assert dv.caseProps.currentTab() == RightDrawerView.Timeline.value
    assert ensureVisAnimation_finished.wait() == True
    assert ensureVisibleSet.wait() == True
    assert ensureVisibleSet.callArgs[0][0] == util.QML_ITEM_HEIGHT * (firstRow - 1)
    # contentY was still zero after set and table not updated visually, but then
    # would jump there on first scroll. Suggests qml bug.
    #
    # assert ( dv.caseProps.itemProp("caseProps_timelineView.table", "contentY")
    #     == util.QML_ITEM_HEIGHT * firstRow )


def test_nextTaggedDate_prevTaggedDateTime(scene, dv: DocumentView):
    scene.replaceEventProperties(["Var 1", "Var 2"])
    person1 = scene.addItem(Person())
    birth_event, event1, event2, event3 = scene.addItems(
        Event(EventKind.Shift, person1, dateTime=util.Date(2000, 1, 1)),  # 0
        Event(EventKind.Shift, person1, dateTime=util.Date(2001, 1, 1)),  # 1
        Event(EventKind.Shift, person1, dateTime=util.Date(2002, 1, 1)),  # 2
        Event(EventKind.Shift, person1, dateTime=util.Date(2003, 1, 1)),  # 3
    )
    event1.dynamicProperty("var-1").set("One")
    event3.dynamicProperty("var-2").set("Two")
    scene.setCurrentDateTime(birth_event.dateTime())  # 0
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
    assert scene.currentDateTime() == birth_event.dateTime()


def test_nextTaggedDate_uses_search_tags(scene, dv: DocumentView):
    tags = ["test"]

    person1, person2, person3 = scene.addItems(Person(), Person(), Person())
    birth1, birth2, birth3 = scene.addItems(
        Event(EventKind.Shift, person1, dateTime=util.Date(1980, 1, 1)),
        Event(EventKind.Shift, person2, dateTime=util.Date(1990, 2, 2)),
        Event(EventKind.Shift, person3, dateTime=util.Date(2000, 3, 3)),
    )

    # test first before setting tags

    scene.setCurrentDateTime(birth1.dateTime())
    assert scene.currentDateTime() == birth1.dateTime()

    dv.controller.onPrevEvent()  # noop
    assert scene.currentDateTime() == birth1.dateTime()

    dv.controller.onNextEvent()
    assert scene.currentDateTime() == birth2.dateTime()

    dv.controller.onNextEvent()
    assert scene.currentDateTime() == birth3.dateTime()

    dv.controller.onNextEvent()  # noop
    assert scene.currentDateTime() == birth3.dateTime()

    # then test after setting tags
    birth1.setTags(tags)
    birth3.setTags(tags)
    dv.searchModel.setTags(tags)

    taggedEvents = [e for e in scene.events() if e.hasTags(tags)]
    scene.setCurrentDateTime(taggedEvents[0].dateTime())
    assert scene.currentDateTime() == birth1.dateTime()

    dv.controller.onPrevEvent()  # noop
    assert scene.currentDateTime() == birth1.dateTime()

    dv.controller.onNextEvent()  # skip person 2 for tags
    assert scene.currentDateTime() == birth3.dateTime()

    dv.controller.onNextEvent()  # noop
    assert scene.currentDateTime() == birth3.dateTime()


def test_nextTaggedDate_uses_searchModel(scene, dv: DocumentView):
    tags = ["test"]

    person1, person2, person3 = scene.addItems(
        Person(name="One"), Person(name="Two"), Person(name="Three")
    )
    birth1, birth2, birth3 = scene.addItems(
        Event(EventKind.Shift, person1, dateTime=util.Date(1980, 1, 1)),
        Event(EventKind.Shift, person2, dateTime=util.Date(1990, 2, 2)),
        Event(EventKind.Shift, person3, dateTime=util.Date(2000, 3, 3)),
    )

    # test first before setting tags

    scene.setCurrentDateTime(birth1.dateTime())
    assert scene.currentDateTime() == birth1.dateTime()

    dv.controller.onPrevEvent()  # noop
    assert scene.currentDateTime() == birth1.dateTime()

    dv.controller.onNextEvent()
    assert scene.currentDateTime() == birth2.dateTime()

    dv.controller.onNextEvent()
    assert scene.currentDateTime() == birth3.dateTime()

    dv.controller.onNextEvent()  # noop
    assert scene.currentDateTime() == birth3.dateTime()

    # then test after setting tags
    birth1.setTags(tags)
    birth3.setTags(tags)
    dv.searchModel.setTags(tags)

    taggedEvents = [e for e in scene.events() if e.hasTags(tags)]
    scene.setCurrentDateTime(taggedEvents[0].dateTime())
    assert scene.currentDateTime() == birth1.dateTime()

    dv.controller.onPrevEvent()  # noop
    assert scene.currentDateTime() == birth1.dateTime()

    dv.controller.onNextEvent()  # skip person 2 for tags
    assert scene.currentDateTime() == birth3.dateTime()

    dv.controller.onNextEvent()  # noop
    assert scene.currentDateTime() == birth3.dateTime()

    dv.controller.onPrevEvent()
    assert scene.currentDateTime() == birth1.dateTime()

    dv.controller.onPrevEvent()  # noop
    assert scene.currentDateTime() == birth1.dateTime()


def test_writePDF(tmp_path, scene, dv: DocumentView):
    FILE_PATH = os.path.join(tmp_path, "test_out.xlsx")

    person = scene.addItem(Person(name="person"))
    event1, event2 = scene.addItems(
        Event(
            EventKind.Shift,
            person,
            datetime=util.Date(2001, 1, 1),
            description="Something happened",
        ),
        Event(
            EventKind.Shift,
            person,
            datetime=util.Date(2002, 1, 1),
            description="Something happened again",
        ),
    )
    dv.controller.writeExcel(FILE_PATH)
    assert os.path.isfile(FILE_PATH) == True


def test_writeJPG(tmp_path, scene, dv: DocumentView):
    FILE_PATH = os.path.join(tmp_path, "test_writeJPG.jpg")

    scene.addItem(Person(name="person"))
    scene.setCurrentDateTime(util.Date(2001, 1, 1))
    dv.controller.writeJPG(FILE_PATH)
    assert os.path.isfile(FILE_PATH) == True


def test_writePNG(tmp_path, scene, dv: DocumentView):
    FILE_PATH = os.path.join(tmp_path, "test_writePNG.png")

    person = scene.addItem(Person(name="person"))
    scene.setCurrentDateTime(util.Date(2001, 1, 1))
    dv.controller.writePNG(FILE_PATH)
    assert os.path.isfile(FILE_PATH) == True


def test_writeExcel(tmp_path, scene, dv: DocumentView):
    FILE_PATH = os.path.join(tmp_path, "test_out.xlsx")

    person = scene.addItem(Person(name="person"))
    event1, event2 = scene.addItems(
        Event(
            EventKind.Shift,
            person,
            datetime=util.Date(2001, 1, 1),
            description="Something happened",
        ),
        Event(
            EventKind.Shift,
            person,
            datetime=util.Date(2002, 1, 1),
            description="Something happened again",
        ),
    )
    dv.controller.writeExcel(FILE_PATH)
    assert os.path.isfile(FILE_PATH) == True


def test_writeExcel_2(tmp_path, scene, dv: DocumentView):
    person1, person2 = scene.addItems(Person(name="p1"), Person(name="p2"))
    kinds = itertools.cycle(
        [
            RelationshipKind.Cutoff,
            RelationshipKind.Conflict,
            RelationshipKind.Projection,
            RelationshipKind.Distance,
            RelationshipKind.Toward,
            RelationshipKind.Away,
            RelationshipKind.DefinedSelf,
            RelationshipKind.Overfunctioning,
            RelationshipKind.Inside,
            RelationshipKind.Outside,
        ]
    )
    iDay = 0
    stride = 2
    firstDate = QDateTime.currentDateTime().addDays(-365 * 5)
    events = []
    for i in range(100):
        for parent in (person1, person2):
            iDay += stride
            dateTime = firstDate.addDays(iDay)
            event = Event(
                EventKind.Shift,
                parent,
                description="Test event %i" % iDay,
                dateTime=dateTime,
            )
            events.append(event)
        iDay += stride
        dateTime = firstDate.addDays(iDay)
        kind = next(kinds)
        event = Event(
            EventKind.Shift,
            person1,
            relationship=kind,
            relationshipTargets=[person2],
            dateTime=dateTime,
        )
        events.append(event)
        # emotion = Emotion(kind, person2, event=event)
    scene.addItems(events)
    # util.printModel(dv.timelineModel)
    filePath = os.path.join(tmp_path, "test.xlsx")
    dv.controller.writeExcel(filePath)


def test_add_emotion_adds_tags(scene, dv: DocumentView):
    person1 = Person()
    person2 = Person()
    scene.addItems(person1, person2)
    dv.searchModel.setTags(["conflict"])
    emotion = Emotion(RelationshipKind.Conflict, person2, person=person1)
    scene.addItem(emotion)
    assert emotion.tags() == ["conflict"]


def test_uploadButton(qtbot, dv: DocumentView):
    uploadToServer = util.Condition(dv.controller.uploadToServer)
    qtbot.mouseClick(dv.view.rightToolBar.settingsButton, Qt.LeftButton)
    dv.caseProps.mouseClick("uploadButton")
    assert uploadToServer.wait() == True
    assert uploadToServer.callCount == 1


def test_show_copilot(qtbot, dv: DocumentView):
    qtbot.mouseClick(dv.view.rightToolBar.copilotButton, Qt.LeftButton)
    copilotView = dv.caseProps.rootProp("copilotView")
    assert copilotView.property("visible") == True


def test_print(dv: DocumentView):
    # Prepare a mock QPrinter instance: native output.
    printer = MagicMock()
    printer.outputFormat.return_value = QPrinter.NativeFormat
    printer.NativeFormat = QPrinter.NativeFormat

    # Patch QPrintDialog to return a dummy dialog with exec() returning QDialog.Accepted.
    dialog = MagicMock()
    dialog.exec.return_value = QDialog.Accepted

    scene = Scene(items=(Person(name="Hey"), Person(name="You")))
    dv.setScene(scene)

    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch(
                DocumentController.__module__ + ".QPrinter",
                return_value=printer,
                NativeFormat=QPrinter.NativeFormat,
            )
        )
        stack.enter_context(
            patch(
                DocumentController.__module__ + ".QPrintDialog",
                return_value=dialog,
            )
        )
        stack.enter_context(
            patch.object(DocumentController, "writeJPG", return_value=None)
        )

        dv.controller.onPrint()
        dv.controller.writeJPG.assert_called_once_with(printer=printer)


def test_write_JSON(tmp_path, scene, dv: DocumentView):
    FILE_PATH = os.path.join(tmp_path, "test_out.json")

    person = scene.addItem(Person(name="person"))
    event1, event2 = scene.addItems(
        Event(
            EventKind.Shift,
            person,
            datetime=util.Date(2001, 1, 1),
            description="Something happened",
        ),
        Event(
            EventKind.Shift,
            person,
            datetime=util.Date(2002, 1, 1),
            description="Something happened again",
        ),
    )
    dv.controller.writeJSON(FILE_PATH)

    # with open(FILE_PATH, "r") as f:
    #     sdata = json.load(f)
    # scene2 = Scene()
    # scene2.read(sdata)
    # assert len(scene2.items()) == 3
    # assert len(scene2.people()) == 1
    # assert len(scene2.events()) == 2
    # assert scene2.people()[0].birthEvent.dateTime() == person.birthEvent.dateTime()
    # assert scene2.events()[0].description() == event1.description()
    # assert scene2.events()[1].description() == event2.description()


def test_add_emotion_via_drag(qtbot, scene, dv: DocumentView):
    personA, personB = scene.addItems(
        Person(name="PersonA", pos=QPointF(-200, -200)),
        Person(name="PersonB", pos=QPointF(200, 200)),
    )
    assert len(scene.emotions()) == 0

    scene.setItemMode(ItemMode.Conflict)

    personA_pos = dv.view.mapFromScene(personA.scenePos())
    personB_pos = dv.view.mapFromScene(personB.scenePos())

    qtbot.mousePress(dv.view.viewport(), Qt.LeftButton, Qt.NoModifier, personA_pos)
    qtbot.mouseMove(dv.view.viewport(), personB_pos)
    qtbot.mouseRelease(dv.view.viewport(), Qt.LeftButton, Qt.NoModifier, personB_pos)

    assert len(scene.emotions()) == 1
    emotion = scene.emotions()[0]
    assert emotion.kind() == RelationshipKind.Conflict
    assert emotion.person() == personA
    assert emotion.target() == personB
    assert emotion.isVisible() == True


@pytest.mark.parametrize("hasBirthEvent", [True, False])
def test_personprops_birth_event_button(
    qtbot, scene, dv: DocumentView, hasBirthEvent: bool
):
    person = scene.addItem(Person(name="TestPerson"))
    if hasBirthEvent:
        mother, father = scene.addItems(Person(name="Mother"), Person(name="Father"))
        marriage = Marriage(mother, father)
        scene.addItem(marriage)
        scene.addItem(
            Event(
                EventKind.Birth,
                mother,
                spouse=father,
                child=person,
                dateTime=util.Date(2000, 1, 1),
            )
        )

    person.setSelected(True)
    dv.controller.onInspect()
    assert dv.currentDrawer == dv.personProps

    if hasBirthEvent:
        assert (
            dv.personProps.rootProp("editBirthEventButton").property("text")
            == "→ Edit Birth Event"
        )
    else:
        assert (
            dv.personProps.rootProp("editBirthEventButton").property("text")
            == "→ Add Birth"
        )

    with (
        patch.object(dv.eventFormDrawer, "editEvents") as editEvents,
        patch.object(dv.eventFormDrawer, "addBirthEvent") as addBirthEvent,
    ):
        dv.personProps.qml.rootObject().editBirthEvent.emit()

        if hasBirthEvent:
            assert editEvents.call_count == 1
            assert addBirthEvent.call_count == 0
        else:
            assert addBirthEvent.call_count == 1
            assert editEvents.call_count == 0
            assert addBirthEvent.call_args[0][0] == person


@pytest.mark.parametrize("hasDeathEvent", [True, False])
def test_personprops_death_event_button(qtbot, scene, dv: DocumentView, hasDeathEvent):
    person = scene.addItem(Person(name="TestPerson"))
    if hasDeathEvent:
        scene.addItem(Event(EventKind.Death, person, dateTime=util.Date(2020, 1, 1)))

    person.setSelected(True)
    dv.controller.onInspect()
    assert dv.currentDrawer == dv.personProps

    if hasDeathEvent:
        assert (
            dv.personProps.rootProp("editDeathEventButton").property("visible") == True
        )
        assert (
            dv.personProps.rootProp("editDeathEventButton").property("text")
            == "→ Edit Death Event"
        )
    else:
        assert (
            dv.personProps.rootProp("editDeathEventButton").property("visible") == True
        )

    if hasDeathEvent:
        with (
            patch.object(dv.eventFormDrawer, "editEvents") as editEvents,
            patch.object(dv.eventFormDrawer, "addDeathEvent") as addDeathEvent,
        ):
            dv.personProps.qml.rootObject().editDeathEvent.emit()

            assert editEvents.call_count == 1
            assert addDeathEvent.call_count == 0
    else:
        person.setDeceased(True)
        dv.personProps.rootProp("personModel").refreshProperty("deceased")
        assert (
            dv.personProps.rootProp("editDeathEventButton").property("visible") == True
        )
        assert (
            dv.personProps.rootProp("editDeathEventButton").property("text")
            == "→ Add Death"
        )

        with (
            patch.object(dv.eventFormDrawer, "editEvents") as editEvents,
            patch.object(dv.eventFormDrawer, "addDeathEvent") as addDeathEvent,
        ):
            dv.personProps.qml.rootObject().editDeathEvent.emit()

            assert addDeathEvent.call_count == 1
            assert editEvents.call_count == 0
            assert addDeathEvent.call_args[0][0] == person


@pytest.mark.parametrize("hasBirthEvent", [True, False])
def test_personprops_birth_event_form_state(
    qtbot, scene, dv: DocumentView, hasBirthEvent: bool
):
    """
    Verify that clicking Add Birth/Edit Birth from PersonProperties correctly
    populates the EventForm with the right person in the right field.
    For Add Birth: childPicker should have the selected person (the one being born)
    For Edit Birth: personPicker and spousePicker should have the two parents, childPicker should have the child
    """
    child = scene.addItem(Person(name="TestChild"))
    if hasBirthEvent:
        mother, father = scene.addItems(Person(name="Mother"), Person(name="Father"))
        marriage = Marriage(mother, father)
        scene.addItem(marriage)
        scene.addItem(
            Event(
                EventKind.Birth,
                mother,
                spouse=father,
                child=child,
                dateTime=util.Date(2000, 1, 1),
            )
        )

    child.setSelected(True)
    dv.controller.onInspect()
    assert dv.currentDrawer == dv.personProps

    dv.personProps.qml.rootObject().editBirthEvent.emit()
    assert dv.currentDrawer == dv.eventFormDrawer

    eventForm = dv.eventFormDrawer.eventForm.item
    assert eventForm.property("kind") == EventKind.Birth.value

    childPicker = eventForm.property("childPicker")
    personPicker = eventForm.property("personPicker")
    spousePicker = eventForm.property("spousePicker")

    if hasBirthEvent:
        assert personPicker.property("person") == mother
        assert spousePicker.property("person") == father
        assert childPicker.property("person") == child
    else:
        assert childPicker.property("person") == child
        assert childPicker.property("isSubmitted") == True
        assert personPicker.property("isNewPerson") == True
        assert spousePicker.property("isNewPerson") == True
