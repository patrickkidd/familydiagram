import pytest

from pkdiagram.pyqt import (
    Qt,
    QPoint,
    QDate,
    QDateTime,
    QRect,
    QItemSelectionModel,
)
from pkdiagram import util
from pkdiagram.scene import Scene, Event, Person
from pkdiagram.models import SearchModel, TimelineModel
from pkdiagram.documentview import GraphicalTimelineView

pytestmark = [
    pytest.mark.component("GraphicalTimelineView"),
    pytest.mark.depends_on("TimelineModel"),
]


@pytest.fixture
def create_gtv(scene, qtbot):

    created = []

    def _create_gtv():
        nonlocal created

        folks = (
            Person(name=f"person_{i}", birthDateTime=QDateTime(QDate(2000 + i, 1, 1)))
            for i in range(5)
        )
        scene.addItems(*folks)
        searchModel = SearchModel()
        searchModel.scene = scene
        timelineModel = TimelineModel()
        timelineModel.scene = scene
        timelineModel.items = [scene]
        selectionModel = QItemSelectionModel(timelineModel)
        gtv = GraphicalTimelineView(searchModel, selectionModel)
        gtv.resize(800, 600)
        gtv.show()
        gtv.setScene(scene)
        qtbot.addWidget(gtv)
        qtbot.waitActive(gtv)

        created.append(gtv)
        return gtv

    yield _create_gtv

    for gtv in created:
        gtv.setScene(None)
        gtv.hide()


def test_is_slider_multiple_tags(scene, create_gtv):

    TAG_1 = "Tag 1"
    TAG_2 = "Tag 2"

    gtv = create_gtv()
    canvas = gtv.timeline.canvas
    canvas.setIsSlider(False)
    canvas._searchModel.tags = [TAG_1, TAG_2]

    person = Person()
    event1 = Event(
        parent=person,
        loggedDateTime=util.Date(2000, 1, 10),
        dateTime=util.Date(1900, 1, 1),
        description="item1",
        tags=[TAG_1],
    )
    event2 = Event(
        parent=person,
        loggedDateTime=util.Date(2000, 2, 10),
        dateTime=util.Date(1900, 1, 1),
        description="item2",
        tags=[TAG_2],
    )
    event3 = Event(
        parent=person,
        loggedDateTime=util.Date(2000, 3, 10),
        dateTime=util.Date(1900, 1, 1),
        description="item3",
    )
    scene.addItems(person)


def test_scene_setCurrentDate_from_graphical_timeline_click(qtbot, scene, create_gtv):
    gtv = create_gtv()
    assert len(scene.people()) > 0  # otherwise will get a false positive
    pos = QPoint(
        int(gtv.timeline.canvas.width() / 3), int(gtv.height() / 3)
    )  # sort of 1/3 upper left
    date = gtv.timeline.canvas._dateTimeForPoint(
        pos
    ).date()  # lose time precision for easier equality
    qtbot.mouseClick(gtv.timeline.canvas, Qt.LeftButton, Qt.NoModifier, pos)
    assert scene.currentDateTime().date() == date


# @pytest.mark.parametrize("sullivanianTime", [True, False])
def test_rubber_band_select_events(qtbot, scene, create_gtv):
    TAG_1 = "Tag 1"
    TAG_2 = "Tag 2"

    gtv = create_gtv()
    gtv.searchModel.tags = [TAG_1, TAG_2]
    canvas = gtv.timeline.canvas
    canvas.setIsSlider(False)
    timelineModel = gtv.timelineModel
    selectionModel = gtv.selectionModel
    selectionModel.setModel(timelineModel)
    selectionChanged = util.Condition(selectionModel.selectionChanged)

    for i, person in enumerate(scene.people()):
        if i % 2 == 0:
            person.birthEvent.setTags([TAG_1])
        else:
            person.birthEvent.setTags([TAG_2])

    person_2 = scene.query1(name="person_2")
    person_3 = scene.query1(name="person_3")

    # Contain the list of events in each selection to avoid segfault on deleted
    # QItemSelection after signal emit()
    events_for_selectionChanged = []

    def _onSelectionChanged():
        events = set(
            timelineModel.eventForRow(index.row())
            for index in selectionModel.selectedIndexes()
        )
        events_for_selectionChanged.append(events)

    selectionModel.selectionChanged.connect(_onSelectionChanged)

    upperLeft = QPoint(272, 220)
    lowerRight = QPoint(498, 517)
    delta = lowerRight - upperLeft
    drag_1 = upperLeft + delta * 0.05
    drag_2 = upperLeft + delta * 0.65
    drag_naught = upperLeft + QPoint(-100, -100)
    assert canvas._rubberBand.isVisible() == False

    # QApplication.instance().exec_()

    qtbot.mousePress(
        canvas,
        Qt.MouseButton.LeftButton,
        pos=upperLeft,
    )
    assert canvas._rubberBand.isVisible() == True
    assert len(events_for_selectionChanged) == 0

    qtbot.mouseMove(canvas, pos=drag_1)
    assert canvas._rubberBand.isVisible() == True
    assert canvas._rubberBand.geometry() == QRect(upperLeft, drag_1)
    assert len(events_for_selectionChanged) == 0

    qtbot.mouseMove(canvas, pos=drag_2)
    assert canvas._rubberBand.isVisible() == True
    assert canvas._rubberBand.geometry() == QRect(upperLeft, drag_2)
    assert len(events_for_selectionChanged) == 1
    assert events_for_selectionChanged[0] == {person_2.birthEvent}

    qtbot.mouseMove(canvas, pos=lowerRight)
    assert canvas._rubberBand.isVisible() == True
    assert canvas._rubberBand.geometry() == QRect(upperLeft, lowerRight)
    assert len(events_for_selectionChanged) == 2
    assert events_for_selectionChanged[1] == {
        person_3.birthEvent,
        person_2.birthEvent,
    }

    qtbot.mouseMove(canvas, pos=drag_naught)
    assert canvas._rubberBand.isVisible() == True
    assert canvas._rubberBand.geometry() == QRect(upperLeft, drag_naught).normalized()
    assert len(events_for_selectionChanged) == 3
    assert events_for_selectionChanged[2] == set()

    qtbot.mouseRelease(
        canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier
    )
    assert canvas._rubberBand.isVisible() == False
    assert len(events_for_selectionChanged) == 3
