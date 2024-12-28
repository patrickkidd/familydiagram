import os, os.path, pickle

import pytest

from pkdiagram.pyqt import Qt, QGraphicsView, QPointF, QRectF, QDateTime
from pkdiagram import util
from pkdiagram.scene import (
    Scene,
    Item,
    Person,
    Marriage,
    Emotion,
    Event,
    MultipleBirth,
    Layer,
    EventKind,
)
from pkdiagram.models import SceneLayerModel

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
    person = Person(name="p1", birthDateTime=util.Date(2001, 1, 1))
    scene = Scene()
    scene.addItem(person)
    assert scene.currentDateTime() == person.birthDateTime()

    person.birthEvent.prop("dateTime").reset()
    assert scene.currentDateTime() == QDateTime()
