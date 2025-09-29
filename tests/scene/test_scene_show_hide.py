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
    LifeChange,
)
from pkdiagram.models import SceneLayerModel

pytestmark = [
    pytest.mark.component("Scene"),
    pytest.mark.depends_on("Item"),
]


def test_hide_emotional_process(simpleScene):
    s = simpleScene

    p1 = s.query1(name="p1")
    p2 = s.query1(name="p2")
    p = s.query1(name="p")

    e1 = Emotion(p1, p2, kind=util.ITEM_CONFLICT)
    s.addItem(e1)
    e2 = Emotion(p2, p1, kind=util.ITEM_PROJECTION)
    s.addItem(e2)
    e3 = Emotion(p1, p, kind=util.ITEM_DISTANCE)
    s.addItem(e3)

    assert e1.isVisible() == True
    assert e2.isVisible() == True
    assert e3.isVisible() == True

    s.setHideEmotionalProcess(True)

    assert e1.isVisible() == False
    assert e2.isVisible() == False
    assert e3.isVisible() == False

    s.setHideEmotionalProcess(False)

    assert e1.isVisible() == True
    assert e2.isVisible() == True
    assert e3.isVisible() == True


def test_hide_names():
    scene = Scene()
    person = Person(name="Person A")
    person.setDiagramNotes(
        """A multi-line
string"""
    )
    person.birthEvent.setDateTime(util.Date(2001, 1, 1))
    scene.addItem(person)
    assert (
        person.detailsText.text()
        == """Person A
b. 01/01/2001
A multi-line
string"""
    )

    scene.setHideNames(True)
    assert (
        person.detailsText.text()
        == """b. 01/01/2001
A multi-line
string"""
    )

    scene.setHideNames(False)
    assert (
        person.detailsText.text()
        == """Person A
b. 01/01/2001
A multi-line
string"""
    )
