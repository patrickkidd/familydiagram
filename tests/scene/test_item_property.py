import pytest

from pkdiagram.scene import Scene, Item, Layer

pytestmark = [pytest.mark.component("Item")]


@pytest.fixture
def scene(qApp):
    _scene = Scene()
    yield _scene
    _scene.deinit()


class MyNumItem(Item):
    Item.registerProperties(({"attr": "num", "default": -1},))


@pytest.mark.parametrize("undo", [False, True])
def test_property_setter(scene, undo):
    item = MyNumItem(num=123)
    scene.addItem(item)
    assert item.num() == 123

    item.setNum(456, undo=undo)
    assert item.num() == 456

    item.setNum(789, undo=undo)
    assert item.num() == 789


def test_property_set_with_undo(scene):
    item = MyNumItem(num=123)
    scene.addItem(item)
    assert item.num() == 123

    item.setNum(456, undo=True)  # 1
    assert item.num() == 456

    scene.undo()  # 0
    assert item.num() == 123

    scene.redo()  # 1
    assert item.num() == 456


@pytest.mark.parametrize("undo", [False, True])
def test_property_resetter(scene, undo):
    item = MyNumItem(num=123)
    scene.addItem(item)
    assert item.num() == 123

    item.prop("num").reset(undo=undo)
    assert item.num() == -1


def test_property_reset_with_undo(scene):
    item = MyNumItem(num=123)
    scene.addItem(item)
    assert item.num() == 123  # 0

    item.prop("num").reset(undo=True)  # 1
    assert item.num() == -1

    scene.undo()  # 0
    assert item.num() == 123

    scene.undo()  # 0
    assert item.num() == 123

    scene.redo()  # 1
    assert item.num() == -1


class MyNumItemLayered(Item):
    Item.registerProperties(({"attr": "num", "default": -1, "layered": True},))


def test_property_layered_reset_with_undo(scene):
    item = MyNumItemLayered()
    layer = Layer()
    scene.addItems(item, layer)
    layer.setActive(True)

    item.setNum(123)
    assert item.num() == 123  # 0
    assert item.prop("num").isUsingLayer() == True
    assert layer.getItemProperty(item.id, "num") == (123, True)

    item.prop("num").reset(undo=True)  # 1
    assert item.num() == -1

    scene.undo()  # 0
    assert item.num() == 123

    scene.undo()  # 0
    assert item.num() == 123

    scene.redo()  # 1
    assert item.num() == -1
