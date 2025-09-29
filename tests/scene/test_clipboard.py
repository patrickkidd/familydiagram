import pytest

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


pytest.skip(reason="Clipboard not implemented yet", allow_module_level=True)


def _test_copy_paste_twin(simpleScene):
    s = simpleScene
    p1 = s.query1(name="p1")
    p2 = s.query1(name="p2")
    p = s.query1(name="p")

    t1 = Person(name="t1")
    t2 = Person(name="t2")
    s.addItem(t1)
    s.addItem(t2)
    multipleBirth = MultipleBirth(p.parents())
    t1.setParents(multipleBirth=multipleBirth)
    t2.setParents(multipleBirth=multipleBirth)

    t1.setSelected(True)
    s.copy()
    s.paste()


def _test_copy_paste_with_multipleBirth_selected(simpleScene):
    s = simpleScene
    p1 = s.query1(name="p1")
    p2 = s.query1(name="p2")
    p = s.query1(name="p")

    t1 = Person(name="t1")
    t2 = Person(name="t2")
    s.addItem(t1)
    s.addItem(t2)
    multipleBirth = MultipleBirth(p.parents())
    t1.setParents(multipleBirth=multipleBirth)
    t2.setParents(multipleBirth=multipleBirth)

    t1.setSelected(True)
    multipleBirth.setSelected(True)
    s.copy()
    s.paste()
