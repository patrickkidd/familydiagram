import pytest

from pkdiagram.pyqt import QGraphicsView
from pkdiagram import util
from pkdiagram.scene import Callout, Property

@pytest.fixture
def view(qtbot, scene):
    view = QGraphicsView()
    view.setScene(scene)
    view.show()
    view.resize(800, 600)
    qtbot.addWidget(view)
    qtbot.waitActive(view)

    yield view

    view.hide()


@pytest.fixture
def callout(scene):
    item = Callout()
    scene.addItem(item)
    yield item


def test_edit_text(qtbot, view, scene, callout):
    layerItemChanged = util.Condition(scene.layerItemChanged[Property])
    assert scene.stack().index() == 0
    assert callout.text() == ""

    TEXT = "Hello, World!"

    qtbot.mouseDClickGraphicsItem(view, callout)
    assert callout.textItem.hasFocus() == True

    qtbot.keyClicks(view, TEXT)
    callout.textItem.clearFocus()
    assert layerItemChanged.callCount == 1
    assert layerItemChanged.callArgs[0][0] == callout.prop('text')
    assert callout.text() == TEXT
