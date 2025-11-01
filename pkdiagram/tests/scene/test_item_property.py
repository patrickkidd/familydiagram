import enum

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


_lastNum = 0


def someDefault() -> int:
    global _lastNum
    _lastNum += 1
    return _lastNum


class MyCallableDefaultItem(Item):
    Item.registerProperties([{"attr": "num", "type": int, "default": someDefault}])


def test_default_is_callable(scene):

    item1 = scene.addItem(MyCallableDefaultItem())
    assert item1.num() == 1

    item2 = scene.addItem(MyCallableDefaultItem())
    assert item2.num() == 2


@pytest.mark.parametrize("undo", [False, True])
def test_property_setter(scene, undo):
    item = scene.addItem(MyNumItem(num=123))
    assert item.num() == 123

    item.setNum(456, undo=undo)
    assert item.num() == 456

    item.setNum(789, undo=undo)
    assert item.num() == 789


def test_property_set_with_undo(scene):
    item = scene.addItem(MyNumItem(num=123))
    assert item.num() == 123

    item.setNum(456, undo=True)  # 1
    assert item.num() == 456

    scene.undo()  # 0
    assert item.num() == 123

    scene.redo()  # 1
    assert item.num() == 456


@pytest.mark.parametrize("undo", [False, True])
def test_property_resetter(scene, undo):
    item = scene.addItem(MyNumItem(num=123))
    assert item.num() == 123

    item.prop("num").reset(undo=undo)
    assert item.num() == -1


def test_property_reset_with_undo(scene):
    item = scene.addItem(MyNumItem(num=123))
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


class MyKind(enum.StrEnum):
    One = "one"
    Two = "two"


class MyEnumItem(Item):
    Item.registerProperties(({"attr": "kind", "type": MyKind},))


def test_set_enum():
    item = MyEnumItem()
    item.setKind(MyKind.One)
    assert item.kind() == MyKind.One

    item.setKind(MyKind.Two)
    assert item.kind() == MyKind.Two

    with pytest.raises(ValueError):
        item.setKind("three")
