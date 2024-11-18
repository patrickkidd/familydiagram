from pkdiagram import util, Scene
from pkdiagram.objects import EmotionalUnit, Marriage, Person, Layer


def _add_unit(scene: Scene, children=True):
    personA, personB = Person(name="A"), Person(name="B")
    scene.addItems(personA, personB)
    marriage = Marriage(personA=personA, personB=personB)
    scene.addItem(marriage)
    if children:
        child_1 = Person(name="C")
        child_2 = Person(name="D")
        scene.addItems(child_1, child_2)
        child_1.setParents(marriage)
        child_2.setParents(marriage)
    return marriage


def test_add_marriage():
    scene = Scene()
    layerAdded = util.Condition(scene.layerAdded)
    marriage = _add_unit(scene, children=False)
    personA, personB = marriage.people
    emotionalUnit = marriage.emotionalUnit()
    assert set(personA.layers() + personB.layers()) == {emotionalUnit.layer().id}
    assert emotionalUnit.marriage() is marriage
    assert layerAdded.callCount == 1
    assert len(scene.layers()) == 1
    assert emotionalUnit.layer().name() == None
    assert personA._layers == [emotionalUnit.layer()]
    assert personB._layers == [emotionalUnit.layer()]


def test_add_children():
    scene = Scene()
    marriage = _add_unit(scene)
    personA, personB = marriage.people
    child_1, child_2 = marriage.children
    emotionalUnit = marriage.emotionalUnit()
    layer = emotionalUnit.layer()
    assert set(emotionalUnit.people()) == {personA, personB, child_1, child_2}
    assert set(
        personA.layers() + personB.layers() + child_1.layers() + child_2.layers()
    ) == {layer.id}
    assert personA._layers == [layer]
    assert personB._layers == [layer]
    assert child_1._layers == [layer]
    assert child_2._layers == [layer]


def test_remove_marriage():
    scene = Scene()
    layerRemoved = util.Condition(scene.layerRemoved)
    marriage = _add_unit(scene, children=False)
    personA, personB = marriage.people
    scene.removeItem(marriage)
    assert scene.emotionalUnits() == []
    assert layerRemoved.callCount == 1
    assert scene.layers() == []
    assert set(personA.layers() + personB.layers()) == set()
    assert personA._layers == []
    assert personB._layers == []


def test_remove_people():
    scene = Scene()
    marriage = _add_unit(scene)
    personA, personB = marriage.people
    child_1, child_2 = marriage.children
    assert marriage.emotionalUnit().people() == [personA, personB, child_1, child_2]

    child_1.setParents(None)
    assert marriage.emotionalUnit().people() == [personA, personB, child_2]
    assert child_1.layers() == []

    personA._onRemoveMarriage(marriage)
    child_2.setParents(None)
    scene.removeItem(marriage)
    assert scene.emotionalUnits() == []
    assert personA.layers() == []
    assert personB.layers() == []
    assert child_1.layers() == []
    assert child_2.layers() == []
    assert personA._layers == []
    assert personB._layers == []
    assert child_1._layers == []
    assert child_2._layers == []


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
    emotionalUnit_1 = marriage_1.emotionalUnit()
    emotionalUnit_2 = marriage_2.emotionalUnit()
    assert emotionalUnit_2 < emotionalUnit_1


def test_read_write_batching():
    scene = Scene()
    marriage = _add_unit(scene)
    data = {}
    scene.write(data)

    scene = Scene()
    scene.read(data)
    marriage = scene.marriages()[0]
    personA, personB = marriage.people
    child_1, child_2 = marriage.children
    layer = marriage.emotionalUnit().layer()
    assert len(scene.emotionalUnits()) == 1
    assert set(x.id for x in marriage.emotionalUnit().people()) == {
        personA.id,
        personB.id,
        child_1.id,
        child_2.id,
    }
    assert set(
        personA.layers() + personB.layers() + child_1.layers() + child_2.layers()
    ) == {layer.id}
    assert personA._layers == [layer]
    assert personB._layers == [layer]
    assert child_1._layers == [layer]
    assert child_2._layers == [layer]
