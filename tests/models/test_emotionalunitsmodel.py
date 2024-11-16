import pytest
from pkdiagram import util, Scene
from pkdiagram.objects import Person, Marriage
from pkdiagram.models import EmotionalUnitsModel


def test_read():
    scene = Scene()
    model = EmotionalUnitsModel()
    model.scene = scene
    marriages = [
        Marriage(personA=Person(name=f"A-{i}"), personB=Person(name=f"B-{i}"))
        for i in range(3)
    ]
    scene.addItems(*marriages)
    assert set(x.name() for x in scene.layers()) == set(
        Marriage.itemNameFor(x) for x in marriages
    )
    assert model.rowCount() == 3
    assert model.data(model.index(0, 0), model.NameRole) == Marriage.itemNameFor(
        marriages[0]
    )
    assert model.data(model.index(1, 0), model.NameRole) == Marriage.itemNameFor(
        marriages[1]
    )
    assert model.data(model.index(2, 0), model.NameRole) == Marriage.itemNameFor(
        marriages[2]
    )


def test_set_active():
    scene = Scene()
    model = EmotionalUnitsModel()
    model.scene = scene
    marriages = [
        Marriage(personA=Person(name=f"A-{i}"), personB=Person(name=f"B-{i}"))
        for i in range(3)
    ]
    scene.addItems(*marriages)
    model.setData(model.index(1, 0), True, model.ActiveRole)
    assert model.data(model.index(0, 0), model.ActiveRole) == False
    assert model.data(model.index(1, 0), model.ActiveRole) == True
    assert model.data(model.index(0, 0), model.ActiveRole) == False
    assert scene.activeLayers() == [
        x.id for x in scene.layers() if x.name() == Marriage.itemNameFor(marriages[1])
    ]


def test_custom_layer_same_name():
    scene = Scene()
    model = EmotionalUnitsModel()
    model.scene = scene
    marriages = [
        Marriage(personA=Person(name=f"A-{i}"), personB=Person(name=f"B-{i}"))
        for i in range(3)
    ]
    layer = scene.addLayer(name=Marriage.itemNameFor(marriages[1]))
    scene.addItem(layer)
    scene.addItems(*marriages)
    assert model.rowCount() == 3
    assert len(scene.layers()) == 4
    model.setData(model.index(1, 0), True, model.ActiveRole)
    assert layer.active() == False
    assert scene.activeLayers() == [scene.layerForMarriage(marriages[1])]

    assert model.data(model.index(0, 0), model.ActiveRole) == False
    assert model.data(model.index(1, 0), model.ActiveRole) == True
    assert model.data(model.index(0, 0), model.ActiveRole) == False
    assert scene.activeLayers() == [
        x.id for x in scene.layers() if x.name() == Marriage.itemNameFor(marriages[1])
    ]
