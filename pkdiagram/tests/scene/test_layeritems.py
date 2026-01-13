import pytest

from pkdiagram.pyqt import QPointF, QRectF
from pkdiagram import util
from pkdiagram.scene import Scene, Layer, Callout, LayerLabel

pytestmark = [pytest.mark.component("LayerItem")]


def test_callout_init_pos():
    scene = Scene()
    layer = Layer(active=True)
    scene.addItem(layer)  # need id for Callout ctor
    callout = Callout(layers=[layer.id], itemPos=QPointF(10, 10))
    scene.addItem(callout)
    assert callout.pos() == callout.itemPos()

    # layer.setActive(True)
    # layer.setItemProperty(callout.id,
    # assert callout.pos() == callout.itemPos()

    # callout.setPos(QPointF(10, 10))
    # assert callout.pos() == QPointF(10, 10)
    # assert callout.itemPos() == QPointF(10, 10)


def test_layeritems_init_when_saved_without_active_layers():
    scene = Scene()
    layer = Layer(active=True)
    scene.addItem(layer)  # need id for Callout ctor
    callout = Callout(layers=[layer.id], itemPos=QPointF(10, 10))
    scene.addItem(callout)
    chunk = {}
    layer.setActive(False)
    scene.write(chunk)

    scene = Scene()
    scene.read(chunk)
    callout = scene.find(types=Callout)[0]
    layer = scene.find(types=Layer)[0]
    layer.setActive(True)
    assert callout.pos() == callout.itemPos()  # was initializing to QPointF()


def test_parentRequestsToShowForLayers():
    scene = Scene()
    layer = Layer(name="View 1")
    scene.addItem(layer)  # add first so another one is not automatically added.
    callout = Callout(layers=[layer.id])
    scene.addItem(callout)
    assert callout.isVisible() == False
    assert callout.shouldShowForLayers([layer]) == True

    layer.setActive(True)
    assert callout.isVisible() == True
    assert callout.shouldShowForLayers([layer]) == True

    layer.setActive(False)
    assert callout.isVisible() == False
    assert callout.shouldShowForLayers([layer]) == True


def test_Callout_layeredSceneBoundingRect():
    scene = Scene()
    layer = Layer(name="View 1")
    scene.addItem(layer)  # add first so another one is not automatically added.
    callout = Callout(layers=[layer.id])
    scene.addItem(callout)
    assert callout.layeredSceneBoundingRect([], []) == QRectF()
    assert callout.layeredSceneBoundingRect([layer], []) == (
        callout.sceneBoundingRect() | callout.childrenBoundingRect()
    )


def test_Callout_no_default_itemPos():
    scene = Scene()
    layer = Layer(name="View 1")
    scene.addItem(layer)  # add first so another one is not automatically added.
    callout = Callout(layers=[layer.id])
    scene.addItem(callout)
    assert callout.pos() == QPointF()

    layer.setActive(True)
    assert callout.pos() == QPointF()

    callout.setItemPos(QPointF(100, 100))
    assert callout.pos() == QPointF(100, 100)
    assert callout.itemPos() == QPointF(100, 100)

    layer.setActive(False)
    assert callout.pos() == QPointF(100, 100)


def test_layerlabel_uses_big_font():
    label = LayerLabel(text="Test")
    assert label._textItem.font() == util.DETAILS_BIG_FONT


def test_layerlabel_text():
    label = LayerLabel(text="Hello")
    assert label.text() == "Hello"
    label.setText("World")
    assert label.text() == "World"


def test_layerlabel_visibility_follows_layer():
    scene = Scene()
    layer = Layer(name="View 1", active=True)
    scene.addItem(layer)
    label = LayerLabel(text="Test")
    scene.addItem(label)
    label.setLayers([layer.id])
    assert label.isVisible() is True

    layer.setActive(False)
    assert label.isVisible() is False

    layer.setActive(True)
    assert label.isVisible() is True


def test_layerlabel_no_zoom_hiding():
    scene = Scene()
    layer = Layer(name="View 1", active=True)
    scene.addItem(layer)
    label = LayerLabel(text="Test")
    scene.addItem(label)
    label.setLayers([layer.id])
    assert label.isVisible() is True
    assert not hasattr(label, "onVisibleSizeChanged")
