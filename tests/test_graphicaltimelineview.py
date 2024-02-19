import pytest
from pkdiagram.pyqt import Qt, QPoint, QDate, QDateTime
from pkdiagram import (
    util,
    GraphicalTimelineView,
    GraphicalTimelineCanvas,
    Scene,
    Event,
    Person,
)


@pytest.fixture
def create_gtv(qtbot):

    created = []

    def _create_gtv():
        nonlocal created

        scene = Scene()
        folks = (
            Person(birthDateTime=QDateTime(QDate(2000 + i, 1, 1))) for i in range(5)
        )
        scene.addItems(*folks)
        gtv = GraphicalTimelineView()
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


def test_is_slider_multiple_tags(create_gtv):

    TAG_1 = "Tag 1"
    TAG_2 = "Tag 2"

    gtv = create_gtv()
    canvas = gtv.timeline.canvas
    canvas.setIsSlider(False)
    canvas.scene.searchModel.tags = [TAG_1, TAG_2]

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
    canvas.scene.addItems(person, event1, event2, event3)


def test_scene_setCurrentDate_from_graphical_timeline_click(qtbot, create_gtv):
    gtv = create_gtv()
    assert len(gtv.scene.people()) > 0  # otherwise will get a false positive
    pos = QPoint(
        int(gtv.timeline.canvas.width() / 3), int(gtv.height() / 3)
    )  # sort of 1/3 upper left
    date = gtv.timeline.canvas._dateTimeForPoint(
        pos
    ).date()  # lose time precision for easier equality
    qtbot.mouseClick(gtv.timeline.canvas, Qt.LeftButton, Qt.NoModifier, pos)
    assert gtv.scene.currentDateTime().date() == date
