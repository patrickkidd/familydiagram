from pkdiagram import util, Scene
from pkdiagram.objects import EmotionalUnit, Marriage, Person, Layer


def test_add_marriage():
    scene = Scene()
    layerAdded = util.Condition(scene.layerAdded)
    marriage = Marriage(personA=Person(name="A"), personB=Person(name="B"))
    personA, personB = marriage.people
    scene.addItem(marriage)
    assert len(scene.emotionalUnits()) == 1
    emotionalUnit = scene.emotionalUnits()[0]
    assert set(personA.layers() + personB.layers()) == {emotionalUnit.layer().id}
    assert emotionalUnit.marriage() is marriage
    assert layerAdded.callCount == 1
    assert len(scene.layers()) == 1
    assert scene.layers()[0].name() == None


def test_remove_marriage():
    scene = Scene()
    layerRemoved = util.Condition(scene.layerRemoved)
    marriage = Marriage(personA=Person(name="A"), personB=Person(name="B"))
    personA, personB = marriage.people
    scene.addItem(marriage)
    scene.removeItem(marriage)
    assert scene.emotionalUnits() == []
    assert layerRemoved.callCount == 1
    assert scene.layers() == []
    assert set(personA.layers() + personB.layers()) == set()


def test_ignores_custom_layers():
    CUSTOM_NAME = "My Layer"

    scene = Scene()
    layerAdded = util.Condition(scene.layerAdded)
    layer = Layer(name=CUSTOM_NAME)
    scene.addItem(layer)
    assert layerAdded.callCount == 1

    marriage = Marriage(personA=Person(name="A"), personB=Person(name="B"))
    scene.addItem(marriage)
    assert layerAdded.callCount == 2
    assert len(scene.layers()) == 2
    assert sum(1 for x in scene.layers() if not x.internal()) == 1


def test_sort():
    scene = Scene()
    marriage_1 = Marriage(
        personA=Person(name="A", birthDateTime=util.Date(2001, 1, 1)),
        personB=Person(name="B"),
    )
    marriage_2 = Marriage(
        personA=Person(name="B"),
        personB=Person(name="C", birthDateTime=util.Date(2000, 1, 1)),
    )
    scene.addItems(marriage_1, marriage_2)
    emotionalUnit_1 = scene.emotionalUnitFor(marriage_1)
    emotionalUnit_2 = scene.emotionalUnitFor(marriage_2)
    assert emotionalUnit_2 < emotionalUnit_1
