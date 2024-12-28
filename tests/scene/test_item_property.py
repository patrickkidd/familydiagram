import pytest

from pkdiagram.scene import Scene, Item

pytestmark = [pytest.mark.component("Item")]


@pytest.fixture
def scene(qApp):
    _scene = Scene()
    yield _scene
    _scene.deinit()


class MyItem(Item):
    Item.registerProperties(({"attr": "num", "default": -1},))


@pytest.mark.parametrize("undo", [False, True])
def test_property_setter(scene, undo):
    item = MyItem(num=123)
    scene.addItem(item)
    assert item.num() == 123

    item.setNum(456, undo=undo)
    assert item.num() == 456

    item.setNum(789, undo=undo)
    assert item.num() == 789


def test_property_set_with_undo(scene):
    item = MyItem(num=123)
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
    item = MyItem(num=123)
    scene.addItem(item)
    assert item.num() == 123

    item.prop("num").reset(undo=undo)
    assert item.num() == -1


def test_property_reset_with_undo(scene):
    item = MyItem(num=123)
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
