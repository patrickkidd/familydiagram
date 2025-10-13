import pytest

from pkdiagram.pyqt import QPointF
from pkdiagram import util
from pkdiagram.scene import Scene, Layer, PathItem, Person, Property, Callout


pytestmark = [pytest.mark.component("Layer")]


def test_scene_layersForPerson(scene):
    layer1, layer2, person = scene.addItems(Layer(), Layer(), Person())
    assert scene.layersForPerson(person) == []

    person.setLayers([layer1.id])
    assert scene.layersForPerson(person) == [layer1]

    person.setLayers([layer1.id, layer2.id])
    assert scene.layersForPerson(person) == [layer1, layer2]


def test_layer_shows_hides_person(scene):
    layer1, layer2, person = scene.addItems(Layer(), Layer(), Person())
    assert person.isVisible() == True

    person.setLayers([layer1.id])
    assert scene.activeLayers() == []
    assert person.isVisible() == True

    layer2.setActive(True)
    assert person.isVisible() == False

    layer1.setActive(True)
    assert person.isVisible() == True

    layer2.setActive(False)
    assert person.isVisible() == True

    layer1.setActive(False)
    assert scene.activeLayers() == []
    assert person.isVisible() == True


def test_add_layers_retain_order(scene):
    scene.addItems(
        Layer(name="View 1"),
        Layer(name="View 2"),
        Layer(name="View 3"),
        Layer(name="View 4"),
    )

    assert scene.query1(name="View 1").order() == 0
    assert scene.query1(name="View 2").order() == 1
    assert scene.query1(name="View 3").order() == 2
    assert scene.query1(name="View 4").order() == 3


def test_layerOrderChanged(scene):
    scene.addItems(
        Layer(name="View 1"),
        Layer(name="View 2"),
        Layer(name="View 3"),
        Layer(name="View 4"),
    )
    layerOrderChanged = util.Condition(scene.layerOrderChanged)

    scene.resortLayersFromOrder()  # noop
    assert layerOrderChanged.callCount == 0

    scene.query1(name="View 2").setOrder(10)  # way above
    scene.resortLayersFromOrder()
    assert layerOrderChanged.callCount == 1


def test_scene_signals(scene):
    onLayerAdded = util.Condition()
    scene.layerAdded[Layer].connect(onLayerAdded)
    onLayerChanged = util.Condition()
    scene.layerChanged[Property].connect(onLayerChanged)
    onLayerRemoved = util.Condition()
    scene.layerRemoved[Layer].connect(onLayerRemoved)

    # add
    for i in range(3):
        layer = scene.addItem(Layer())
        assert onLayerAdded.callCount == i + 1
        assert onLayerAdded.lastCallArgs == (layer,)
    assert len(scene.layers()) == 3
    assert onLayerAdded.callCount == 3
    assert onLayerChanged.callCount == 0
    assert onLayerRemoved.callCount == 0

    # change
    for i in range(3):
        layer = scene.layers()[i]
        name = "here %i" % i
        layer.setName(name)
        prop = layer.prop("name")
        assert onLayerChanged.callCount == i + 1
        assert onLayerChanged.lastCallArgs == (prop,)
    assert onLayerAdded.callCount == 3
    assert onLayerChanged.callCount == 3
    assert onLayerRemoved.callCount == 0

    # remove
    for i in range(3):
        layer = scene.layers()[-1]
        scene.removeItem(layer)
        assert onLayerRemoved.callCount == i + 1
        assert onLayerRemoved.lastCallArgs == (layer,)
    assert onLayerAdded.callCount == 3
    assert onLayerChanged.callCount == 3
    assert onLayerRemoved.callCount == 3


def test_undo_commands(scene):
    """Test merging multiple undo commands values."""
    person1, person2 = scene.addItems(Person(name="p1"), Person(name="p2"))

    layer = scene.addItem(Layer(name="View 1"))
    layer.setActive(True)

    with scene.macro("Set color first time"):
        person1.setColor("#ABCABC", undo=True)
        person2.setColor("#DEFDEF", undo=True)

    with scene.macro("Set color second time"):
        person1.setColor("#123123", undo=True)
        person2.setColor("#456456", undo=True)

    assert person1.color() == "#123123"
    assert person2.color() == "#456456"

    scene.undo()
    assert person1.color() == "#ABCABC"
    assert person2.color() == "#DEFDEF"

    scene.undo()
    assert person1.color() == None
    assert person2.color() == None


def test_person_props(scene):
    layer, person = scene.addItems(Layer(), Person())

    # layer on
    layer.setActive(True)
    assert scene.activeLayers() == [layer]

    # set props
    person.setColor("#FF0000")
    assert person.color() == "#FF0000"

    # layer off
    layer.setActive(False)
    assert scene.activeLayers() == []
    assert person.color() == None

    # layer back on
    layer.setActive(True)
    assert scene.activeLayers() == [layer]
    assert person.color() == "#FF0000"


def test_person_pen_multiple_layers(scene):
    layer1, layer2 = scene.addItems(Layer(), Layer())
    person = scene.addItem(Person())

    # default color, i.e. what layer2 should match
    assert person.pen().color() == util.PEN.color()

    # set color on layer1
    layer1.setActive(True)
    person.setColor("#FF0000")
    assert person.pen().color().name() == "#ff0000"

    layer1.setActive(False)
    layer2.setActive(True)
    assert person.pen().color() == util.PEN.color()

    layer2.setActive(False)
    assert scene.activeLayers() == []
    assert person.pen().color() == util.PEN.color()


def test_same_value_multiple_layers(scene):
    """Property._value was caching the set value from the previous layer, preventing the next layer to set it."""

    person = scene.addItem(Person())
    layer1, layer2 = scene.addItems(Layer(name="layer1"), Layer(name="layer2"))

    # default
    assert person.itemOpacity() is None

    layer1.setActive(True)
    person.setItemOpacity(0.1)
    x, ok = layer1.getItemProperty(person.id, "itemOpacity")
    assert ok
    assert x == 0.1
    assert person.itemOpacity() == 0.1

    layer1.setActive(False)
    layer2.setActive(True)
    person.setItemOpacity(0.1)
    x, ok = layer2.getItemProperty(person.id, "itemOpacity")
    assert ok
    assert x == 0.1
    assert person.itemOpacity() == 0.1

    layer2.setActive(False)
    assert person.itemOpacity() is None


def test_layer_callout(scene):
    layer = scene.addItem(Layer(name="layer"))

    # add
    layer.setActive(True)
    callout = scene.addItem(Callout())
    assert callout.layers() == [layer.id]
    assert callout.scene() == scene
    assert callout.isVisible()
    assert callout.opacity() == 1.0

    # hide
    layer.setActive(False)
    assert not callout.isVisible()
    assert callout.opacity() == 0.0

    # show
    layer.setActive(True)
    assert callout.isVisible()
    assert callout.opacity() == 1.0


def test_add_default_layer_with_first_LayerItem(scene):
    assert scene.layers(includeInternal=False) == []

    callout = scene.addItem(Callout())
    assert len(scene.layers(includeInternal=False)) == 1
    assert callout.layers() == [scene.layers(includeInternal=False)[0].id]


def test_write_read_active_layer_items(scene):
    layer, personA, personB = scene.addItems(
        Layer(active=True), Person(name="personA"), Person(name="personB")
    )
    personB.setLayers([layer.id])
    assert scene.query1(name="personA").isVisible() == False
    assert scene.query1(name="personB").isVisible() == True
    data = {}
    scene.write(data)

    scene = Scene()
    scene.read(data)
    assert len(scene.find(types=Layer)) == 1
    assert len(scene.find(types=Person)) == 2
    assert scene.find(types=Layer)[0].active() == True
    assert scene.query1(name="personA").isVisible() == False
    assert scene.query1(name="personB").isVisible() == True


def test_remove_layers_with_layerItems(scene):
    layer1, layer2 = scene.addItems(Layer(), Layer())

    assert scene.activeLayers() == []

    layer1.setActive(True)
    callout1 = scene.addItem(Callout())  # layer1, layer2

    layer1.setActive(False)
    layer2.setActive(True)
    callout2 = scene.addItem(Callout())  # layer2

    layer1.setActive(True)
    callout3 = scene.addItem(Callout())  # layer1, layer2

    scene.removeItem(layer1, undo=True)
    assert not (layer1 in scene.layers())
    assert not (callout1 in scene.layerItems())
    assert callout2 in scene.layerItems()
    assert callout3 in scene.layerItems()
    assert callout1.layers() == []
    assert callout2.layers() == [layer2.id]
    assert callout3.layers() == [layer2.id]

    scene.undo()
    assert layer1 in scene.layers()
    assert callout1 in scene.layerItems()
    assert callout2 in scene.layerItems()
    assert callout3 in scene.layerItems()
    assert callout1.layers() == [layer1.id]
    assert callout2.layers() == [layer2.id]
    assert sorted(callout3.layers()) == [layer1.id, layer2.id]

    ##

    scene.removeItem(layer2, undo=True)
    assert not (layer2 in scene.layers())
    assert callout1 in scene.layerItems()
    assert not (callout2 in scene.layerItems())
    assert callout3 in scene.layerItems()
    assert callout1.layers() == [layer1.id]
    assert callout2.layers() == []
    assert callout3.layers() == [layer1.id]

    scene.undo()
    assert layer2 in scene.layers()
    assert callout1 in scene.layerItems()
    assert callout2 in scene.layerItems()
    assert callout3 in scene.layerItems()
    assert callout1.layers() == [layer1.id]
    assert callout2.layers() == [layer2.id]
    assert sorted(callout3.layers()) == [layer1.id, layer2.id]

    ##

    with scene.macro("Remove layer items"):
        scene.removeItem(layer1, undo=True)
        scene.removeItem(layer2, undo=True)
    assert not (layer1 in scene.layers())
    assert not (layer2 in scene.layers())
    assert not (callout1 in scene.layerItems())
    assert not (callout2 in scene.layerItems())
    assert not (callout3 in scene.layerItems())
    assert callout1.layers() == []
    assert callout2.layers() == []
    assert callout3.layers() == []

    scene.undo()
    assert layer1 in scene.layers()
    assert layer2 in scene.layers()
    assert callout1 in scene.layerItems()
    assert callout2 in scene.layerItems()
    assert callout3 in scene.layerItems()
    assert callout1.layers() == [layer1.id]
    assert callout2.layers() == [layer2.id]
    assert sorted(callout3.layers()) == [layer1.id, layer2.id]


class LayeredPathItem(PathItem):

    PathItem.registerProperties(({"attr": "something", "layered": True},))


def test_delete_layer_prop_with_items(qtbot, scene):
    layer, item = scene.addItems(Layer(active=True), LayeredPathItem())
    item.setFlag(item.ItemIsSelectable, True)
    item.setSomething("here", undo=True)  # 0
    value, ok = layer.getItemProperty(item.id, "something")
    assert ok == True
    assert value == "here"
    assert len(layer.itemProperties().items()) == 1

    item.setSelected(True)
    qtbot.clickYesAfter(lambda: scene.removeSelection())  # 1
    value, ok = layer.getItemProperty(item.id, "something")
    assert ok == False
    assert value == None
    assert len(layer.itemProperties().items()) == 0

    scene.undo()  # 0
    value, ok = layer.getItemProperty(item.id, "something")
    assert ok == True
    assert value == "here"
    assert len(layer.itemProperties().items()) == 1


def test_store_geometry(qtbot, monkeypatch, scene):
    layer, person = scene.addItems(Layer(), Person())
    layer.setStoreGeometry(False)
    monkeypatch.setattr(scene, "isMovingSomething", lambda: True)

    # Each assert should have all three cases; current visible, no layers, layer.

    person.setItemPosNow(QPointF(100, 100))
    person.setSize(1)
    assert person.itemPos() == QPointF(100, 100)
    assert person.itemPos(forLayers=[]) == QPointF(100, 100)
    assert person.itemPos(forLayers=[layer]) == None
    assert person.size(forLayers=[]) == 1
    assert person.size(forLayers=[layer]) == None

    layer.setActive(True)
    assert person.itemPos() == QPointF(100, 100)
    assert person.itemPos(forLayers=[]) == QPointF(100, 100)
    assert person.itemPos(forLayers=[layer]) == None
    assert person.size() == 1
    assert person.size(forLayers=[]) == 1
    assert person.size(forLayers=[layer]) == None

    person.setItemPos(QPointF(200, 200))
    person.setSize(2)
    assert person.itemPos() == QPointF(200, 200)
    assert person.itemPos(forLayers=[]) == QPointF(200, 200)
    assert person.itemPos(forLayers=[layer]) == None
    assert person.size() == 2
    assert person.size(forLayers=[]) == 2
    assert person.size(forLayers=[layer]) == None

    layer.setStoreGeometry(True)
    assert person.itemPos() == QPointF(200, 200)
    assert person.itemPos(forLayers=[]) == QPointF(200, 200)
    assert person.itemPos(forLayers=[layer]) == None
    assert person.size() == 2
    assert person.size(forLayers=[]) == 2
    assert person.size(forLayers=[layer]) == None

    person.setItemPos(QPointF(300, 300))
    person.setSize(3)
    assert person.itemPos() == QPointF(300, 300)
    assert person.itemPos(forLayers=[]) == QPointF(200, 200)
    assert person.itemPos(forLayers=[layer]) == QPointF(300, 300)
    assert person.size() == 3
    assert person.size(forLayers=[]) == 2
    assert person.size(forLayers=[layer]) == 3

    layer.setActive(False)
    assert person.itemPos() == QPointF(200, 200)
    assert person.itemPos(forLayers=[]) == QPointF(200, 200)
    assert person.itemPos(forLayers=[layer]) == QPointF(300, 300)
    assert person.size() == 2
    assert person.size(forLayers=[]) == 2
    assert person.size(forLayers=[layer]) == 3

    # test values are deleted
    layer.setStoreGeometry(False)
    assert person.itemPos() == QPointF(200, 200)
    assert person.itemPos(forLayers=[]) == QPointF(200, 200)
    assert person.itemPos(forLayers=[layer]) == None
    assert person.size() == 2
    assert person.size(forLayers=[]) == 2
    assert person.size(forLayers=[layer]) == None

    # test values don't change after setting active (ensure values deleted)
    layer.setActive(True)
    assert person.itemPos() == QPointF(200, 200)
    assert person.itemPos(forLayers=[]) == QPointF(200, 200)
    assert person.itemPos(forLayers=[layer]) == None
    assert person.size() == 2
    assert person.size(forLayers=[]) == 2
    assert person.size(forLayers=[layer]) == None

    # test values are not stored in layer, even if layer active
    person.setItemPos(QPointF(400, 400))
    person.setSize(4)
    assert person.itemPos() == QPointF(400, 400)  # value still stored in layer
    assert person.itemPos(forLayers=[]) == QPointF(400, 400)  # new default value
    assert person.itemPos(forLayers=[layer]) == None
    assert person.size() == 4
    assert person.size(forLayers=[]) == 4
    assert (
        person.size(forLayers=[layer]) == None
    )  # should reset layer value when setting default value


def test_dont_store_positions(monkeypatch, scene):
    layer, item = scene.addItems(Layer(), PathItem())
    layer.setStoreGeometry(False)
    monkeypatch.setattr(scene, "isMovingSomething", lambda: True)

    item.setItemPos(QPointF(100, 100))
    assert item.itemPos() == QPointF(100, 100)
    assert item.itemPos(forLayers=[layer]) == None

    layer.setActive(True)
    assert item.itemPos() == QPointF(100, 100)
    assert item.itemPos(forLayers=[layer]) == None

    item.setItemPos(QPointF(200, 200))
    assert item.itemPos() == QPointF(200, 200)
    assert item.itemPos(forLayers=[layer]) == None

    layer.setStoreGeometry(True)
    item.setItemPos(QPointF(300, 300))
    assert item.itemPos() == QPointF(300, 300)
    assert item.itemPos(forLayers=[layer]) == QPointF(300, 300)

    layer.setStoreGeometry(False)
    item.setItemPos(QPointF(400, 400))  # layer still active
    assert item.itemPos() == QPointF(400, 400)
    assert (
        item.itemPos(forLayers=[layer]) == None
    )  # layer value deleted when setting storeGeometry = False

    layer.setStoreGeometry(True)
    item.setItemPos(QPointF(500, 500))  # layer still active
    assert item.itemPos() == QPointF(500, 500)
    assert item.itemPos(forLayers=[layer]) == QPointF(500, 500)

    item.prop("itemPos").reset()
    assert item.itemPos() == QPointF(400, 400)  # value still stored in layer
    assert item.itemPos(forLayers=[layer]) == None  # layer value is cleared now


def test_storeGeometry_dont_reset_LayerItem_pos(monkeypatch, scene):
    layer, item = scene.addItems(Layer(), LayeredPathItem())
    monkeypatch.setattr(scene, "isMovingSomething", lambda: True)

    item.setItemPos(QPointF(100, 100))
    assert item.itemPos() == QPointF(100, 100)
    assert item.itemPos(forLayers=[layer]) == None

    layer.setActive(True)
    layer.setStoreGeometry(True)
    item.setItemPos(QPointF(200, 200))
    assert item.itemPos() == QPointF(200, 200)
    assert item.itemPos(forLayers=[layer]) == QPointF(200, 200)

    layer.setStoreGeometry(False)
    assert item.itemPos() == QPointF(100, 100)
    assert item.itemPos(forLayers=[layer]) == None

    # test no change
    layer.setActive(True)
    assert item.itemPos() == QPointF(100, 100)
    assert item.itemPos(forLayers=[layer]) == None  # redundant, but no biggie


# not sure this makes sense now that setting storeGeometry = False clears geo props in layer
def __test_dont_reset_positions_on_activate_layer(monkeypatch, scene):
    layer, item = scene.addItems(Layer(), PathItem())
    monkeypatch.setattr(scene, "isMovingSomething", lambda: True)
    layer.setStoreGeometry(True)

    item.setPos(QPointF(100, 100))

    layer.setActive(True)
    item.setPos(QPointF(200, 200))

    layer.setStoreGeometry(False)
    layer.setActive(False)
    assert item.itemPos() == QPointF(100, 100)
    assert item.itemPos(forLayers=[layer]) == None

    layer.setActive(True)
    assert item.itemPos() == QPointF(200, 200)
    assert item.itemPos(forLayers=[layer]) == None


def tests_duplicate(scene):
    layer1, item, callout = scene.addItems(Layer(active=True), PathItem(), Callout())
    assert layer1.id in callout.layers()

    layer2 = layer1.clone(scene)
    assert layer2.id in callout.layers()


# def test_internal_and_custom_mutually_exclusive():
#     scene = Scene()
#     customLayer_1, customLayer_2 = Layer(), Layer()
#     internalLayer_1, internalLayer_2 = Layer(internal=True), Layer(internal=True)
#     scene.addItems(customLayer_1, customLayer_2, internalLayer_1, internalLayer_2)

#     # first exclusive selection
#     internalLayer_1.setActive(True)
#     customLayer_1.setActive(True)
#     assert internalLayer_1.active() == False
#     assert internalLayer_2.active() == False
#     assert customLayer_1.active() == True
#     assert customLayer_2.active() == False

#     internalLayer_1.setActive(True)
#     assert internalLayer_1.active() == True
#     assert internalLayer_2.active() == False
#     assert customLayer_1.active() == False
#     assert customLayer_2.active() == False

#     customLayer_2.setActive(True)
#     assert internalLayer_1.active() == False
#     assert internalLayer_2.active() == False
#     assert customLayer_1.active() == False
#     assert customLayer_2.active() == True

#     internalLayer_2.setActive(True)
#     assert internalLayer_1.active() == False
#     assert internalLayer_2.active() == True
#     assert customLayer_1.active() == False
#     assert customLayer_2.active() == False
