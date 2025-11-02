import pytest

from pkdiagram.scene import Scene, Item, Person, Marriage, Layer

pytestmark = [pytest.mark.component("Item")]


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
