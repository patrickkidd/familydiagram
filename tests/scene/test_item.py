import pytest

from pkdiagram.scene import Scene, Item, Person, Marriage, Layer

pytestmark = [pytest.mark.component("Item")]


def test_forward_compat():
    # simulate future version with additional props
    future = Item()
    future.addProperties(
        [{"attr": "here", "default": 101}, {"attr": "there", "default": 202}]
    )
    chunk1 = {}
    future.write(chunk1)
    assert "here" in chunk1
    assert chunk1["here"] == 101
    assert "there" in chunk1
    assert chunk1["there"] == 202

    past = Item()
    past.addProperties(
        [
            {"attr": "here", "default": 10101},
        ]
    )
    past.read(chunk1, None)
    assert past.prop("here") is not None
    assert past.prop("here").get() == 101
    assert past.prop("there") is None

    chunk2 = {}
    past.write(chunk2)
    assert "here" in chunk2
    assert chunk2["here"] == 101
    assert "there" in chunk2
    assert chunk2["there"] == 202


class LayeredItem(Item):

    Item.registerProperties(({"attr": "num", "default": -1, "layered": True},))

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.count = 0
        self.layeredCount = 0

    def onProperty(self, prop):
        if prop.name() == "num":
            if prop.isUsingLayer():
                self.layeredCount += 1
            self.count += 1
        super().onProperty(prop)


def test_hasTags():
    """The basic tags condition test."""
    item = Item(tags=["one"])
    assert item.hasTags([]) == True
    assert item.hasTags(["one"]) == True
    assert item.hasTags(["one", "two"]) == True
    assert item.hasTags(["two"]) == False


def test_addTags():
    item = Item(tags=["one"])
    item.addTags(["one", "two"])
    assert item.tags() == ["one", "two"]

    item.addTags(["two"])
    assert item.tags() == ["one", "two"]

    item.addTags(["three"])
    assert set(item.tags()) == set(["one", "two", "three"])


def test_layered_property():

    scene = Scene()
    item = LayeredItem()
    layer = Layer(name="View 1")
    scene.addItem(item)
    scene.addItem(layer)

    assert item.num() == -1
    assert item.count == 0
    assert item.layeredCount == 0

    item.setNum(1)
    assert item.num() == 1
    assert item.count == 1
    assert item.layeredCount == 0

    layer.setActive(True)
    assert item.num() == 1
    assert item.count == 1
    assert item.layeredCount == 0

    item.prop("num").set(2)
    # item.setNum(2)
    assert item.num() == 2
    assert item.count == 2
    assert item.layeredCount == 1

    layer.setActive(False)
    assert item.num() == 1
    assert item.count == 3
    assert item.layeredCount == 1

    layer.setActive(True)
    assert item.num() == 2
    assert item.count == 4
    assert item.layeredCount == 2

    item.prop("num").reset()
    assert item.num() == 1
    assert item.count == 5
    assert item.layeredCount == 2

    layer.setActive(False)
    assert item.num() == 1
    assert item.count == 5
    assert item.layeredCount == 2


def test_layered_property_undo_redo():
    """SetProperty wasn't working for non-layered properties."""
    scene = Scene()
    item = LayeredItem()
    layer = Layer(name="View 1")
    scene.addItems(layer, item)  # 0
    assert item.num() == -1
    assert item.count == 0
    assert item.layeredCount == 0

    item.setNum(1, undo=True)  # 1
    assert item.num() == 1
    assert item.count == 1
    assert item.layeredCount == 0

    scene.undo()  # 0
    assert item.num() == -1
    assert item.count == 2
    assert item.layeredCount == 0

    scene.redo()  # 1
    assert item.num() == 1
    assert item.count == 3
    assert item.layeredCount == 0


def test_update_frame():
    """Verify that calls are occuring syncronously and that there aren't big redundancies.
    Basically tests the update frame concept.
    """

    personA = Person(name="personA")
    personB = Person(name="personB")
    marriage = Marriage(personA, personB)
    childA = Person(name="childA")
    childA.setParents(marriage)
    scene = Scene()
    scene.addItems(personA, personB, marriage, childA)

    scene.updateAll()
    assert personA._n_updateGeometry == 1
    assert personB._n_updateGeometry == 1
    assert marriage._n_updateGeometry == 1
    assert childA._n_updateGeometry == 1
    assert personA._n_onActiveLayersChanged == 1
    assert personB._n_onActiveLayersChanged == 1
    assert marriage._n_onActiveLayersChanged == 1
    assert childA._n_onActiveLayersChanged == 1

    scene.updateAll()
    assert personA._n_updateGeometry == 1
    assert personB._n_updateGeometry == 1
    assert marriage._n_updateGeometry == 1
    assert childA._n_updateGeometry == 1
    assert personA._n_onActiveLayersChanged == 1
    assert personB._n_onActiveLayersChanged == 1
    assert marriage._n_onActiveLayersChanged == 1
    assert childA._n_onActiveLayersChanged == 1


def test_update_frame_counts():
    """Verify that calls are occuring syncronously and that there aren't big redundancies.
    Basically tests the update frame concept.
    """
    personA = Person(name="personA")
    personB = Person(name="personB")
    marriage = Marriage(personA, personB)
    childA = Person(name="childA")
    childA.setParents(marriage)
    scene = Scene()
    scene.addItems(personA, personB, marriage, childA)

    scene.updateAll()
    assert personA._n_updateGeometry == 1
    assert personB._n_updateGeometry == 1
    assert marriage._n_updateGeometry == 1
    assert childA._n_updateGeometry == 1

    scene.updateAll()
    assert personA._n_updateGeometry == 1
    assert personB._n_updateGeometry == 1
    assert marriage._n_updateGeometry == 1
    assert childA._n_updateGeometry == 1
