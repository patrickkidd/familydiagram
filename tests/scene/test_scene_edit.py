import os.path

import pytest

from pkdiagram.pyqt import Qt, QGraphicsView, QDateTime, QPoint
from pkdiagram import util
from pkdiagram.scene import Scene, Item, Person, Event, EventKind


class View(QGraphicsView):
    def getVisibleSceneScaleRatio(self):
        return 1.0


pytestmark = [
    pytest.mark.component("Scene"),
    pytest.mark.depends_on("Item"),
]


def test_renameTag():
    scene = Scene()
    scene.setTags(["aaa", "ccc", "ddd"])
    item = Item()
    scene.addItem(item)
    item.setTags(["ddd"])
    assert item.tags() == ["ddd"]

    scene.renameTag("ddd", "bbb")
    assert scene.tags() == ["aaa", "bbb", "ccc"]
    assert item.tags() == ["bbb"]


def test_reset_last_event_resets_currentDateTime():
    scene = Scene()
    person = scene.addItem(Person(name="p1"))
    birthEvent = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2001, 1, 1))
    )
    assert scene.currentDateTime() == birthEvent.dateTime()

    birthEvent.prop("dateTime").reset()
    assert scene.currentDateTime() == QDateTime()


def test_click_on_pathitem_doesnt_add_undo_command(qtbot, scene):
    person = Person(name="p1")
    scene.addItem(person)

    view = View()
    view.setScene(scene)
    qtbot.addWidget(view)
    qtbot.waitActive(view)
    view.show()
    assert scene.stack().count() == 0

    qtbot.mouseClick(
        view.viewport(),
        Qt.LeftButton,
        Qt.NoModifier,
        view.mapFromScene(person.sceneBoundingRect().center()),
    )
    assert person.isSelected() == True
    assert scene.stack().count() == 0


def test_drag_pathitem_undo(qtbot, scene):
    person = Person(name="p1")
    scene.addItem(person)

    view = View()
    view.setScene(scene)
    qtbot.addWidget(view)
    qtbot.waitActive(view)
    view.show()
    assert scene.stack().count() == 0

    qtbot.mousePress(
        view.viewport(),
        Qt.LeftButton,
        Qt.NoModifier,
        view.mapFromScene(person.sceneBoundingRect().center()),
    )
    person.setPos(QPoint(100, 100))
    qtbot.mouseRelease(
        view.viewport(),
        Qt.LeftButton,
        Qt.NoModifier,
        view.mapFromScene(person.sceneBoundingRect().center()) + QPoint(10, 10),
    )
    assert person.isSelected() == True
    assert scene.stack().count() == 1


@pytest.mark.parametrize("undo", [True, False])
def test_rename_timeline_property(scene, undo):
    scene.addEventProperty("Var 1")
    scene.renameEventProperty("Var 1", "Var 2", undo=undo)
    assert scene.eventProperties()[0]["name"] == "Var 2"


@pytest.mark.parametrize("undo", [True, False])
def test_rename_timeline_property(scene, undo):
    scene.addEventProperty("Var 1")
    scene.addEventProperty("Var 2")
    scene.replaceEventProperties(util.PAPERO_MODEL, undo=undo)
    assert [x["name"] for x in scene.eventProperties()] == util.PAPERO_MODEL
