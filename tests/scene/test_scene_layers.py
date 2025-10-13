import os, os.path, pickle

import pytest

from pkdiagram.pyqt import Qt, QGraphicsView, QPointF, QRectF, QDateTime
from pkdiagram import util
from pkdiagram.scene import (
    Scene,
    Item,
    Person,
    Marriage,
    Emotion,
    Event,
    MultipleBirth,
    Layer,
    EventKind,
)
from pkdiagram.models import SceneLayerModel

pytestmark = [
    pytest.mark.component("Scene"),
    pytest.mark.depends_on("Item"),
]


def test_new_persons_get_current_layers():

    s = Scene()
    layer1 = Layer()
    s.addItem(layer1)
    p1 = Person(name="p1")
    assert p1.layers() == []

    layer1.setActive(True)
    assert layer1.id not in p1.layers()

    p2 = Person(name="p2")
    s.addItem(p2)
    assert p1.layers() == []
    assert p2.layers() == [layer1.id]

    layer2 = Layer(active=True)
    s.addItem(layer2)
    assert p1.layers() == []
    assert p2.layers() == [layer1.id]

    p3 = Person(name="p3")
    s.addItem(p3)
    assert p1.layers() == []
    assert p2.layers() == [layer1.id]
    assert p3.layers() == [layer1.id, layer2.id]

    layer1.setActive(False)
    p4 = Person(name="p4")
    s.addItem(p4)
    assert p1.layers() == []
    assert p2.layers() == [layer1.id]
    assert p3.layers() == [layer1.id, layer2.id]
    assert p4.layers() == [layer2.id]


def test_hasActiveLayers():
    scene = Scene()
    assert scene.hasActiveLayers == False

    layer = Layer(active=True)
    scene.addItem(layer)
    assert scene.hasActiveLayers == True

    layer.setActive(False)
    assert scene.hasActiveLayers == False


def test_layers():
    scene = Scene()
    layer1 = Layer(name="View 1", internal=True)
    layer2 = Layer(name="View 2", internal=True)
    layer3 = Layer(name="View 3")
    scene.addItems(layer1, layer2, layer3)
    assert scene.layers() == [layer1, layer2, layer3]


def test_layers_onlyInternal():
    scene = Scene()
    layer1 = Layer(name="View 1", internal=True)
    layer2 = Layer(name="View 2", internal=True)
    layer3 = Layer(name="View 3")
    scene.addItems(layer1, layer2, layer3)
    assert set(scene.layers(onlyInternal=True)) == set([layer1, layer2])


def test_layers_includeInternal():
    scene = Scene()
    layer1 = Layer(name="View 1", internal=True)
    layer2 = Layer(name="View 2", internal=True)
    layer3 = Layer(name="View 3")
    scene.addItems(layer1, layer2, layer3)
    assert set(scene.layers(includeInternal=False)) == set([layer3])


def test_layered_properties(scene):
    """Ensure correct layered prop updates for marriage+marriage-indicators."""
    male, female = scene.addItems(
        Person(name="Male", kind="male"), Person(name="Female", kind="female")
    )
    marriage = scene.addItem(Marriage(personA=male, personB=female))
    divorcedEvent = scene.addItem(
        Event(
            EventKind.Divorced,
            person=male,
            spouse=female,
            dateTime=util.Date(1900, 1, 1),
        )
    )
    layer = scene.addItem(Layer(name="View 1"))
    #
    unlayered = {
        "male": QPointF(-100, -50),
        "maleDetails": QPointF(100, 100),
        "female": QPointF(100, -50),
        "femaleDetails": QPointF(-100, -200),
        "marriageSep": QPointF(100, 0),
        "marriageDetails": QPointF(-25, 0),
    }
    layered = {
        "male": QPointF(-200, -150),
        "maleDetails": QPointF(-100, -100),
        "female": QPointF(100, 50),
        "femaleDetails": QPointF(100, 200),
        "marriageSep": QPointF(100, 0),
        "marriageDetails": QPointF(25, -100),
    }
    # layered
    layer.setItemProperty(male.id, "itemPos", layered["male"])
    layer.setItemProperty(male.detailsText.id, "itemPos", layered["maleDetails"])
    layer.setItemProperty(female.id, "itemPos", layered["female"])
    layer.setItemProperty(female.detailsText.id, "itemPos", layered["femaleDetails"])
    layer.setItemProperty(
        marriage.detailsText.id, "itemPos", layered["marriageDetails"]
    )
    layer.setItemProperty(
        marriage.separationIndicator.id, "itemPos", layered["marriageSep"]
    )
    # unlayered
    male.setItemPos(unlayered["male"], undo=False)
    male.detailsText.setItemPos(unlayered["maleDetails"], undo=False)
    female.setItemPos(unlayered["female"], undo=False)
    female.detailsText.setItemPos(unlayered["femaleDetails"], undo=False)
    # marriage.setDivorced(True, undo=False)
    marriage.separationIndicator.setItemPos(unlayered["marriageSep"], undo=False)
    marriage.detailsText.setItemPos(unlayered["marriageDetails"], undo=False)

    assert male.pos() == unlayered["male"]
    assert male.detailsText.pos() == unlayered["maleDetails"]
    assert female.pos() == unlayered["female"]
    assert female.detailsText.pos() == unlayered["femaleDetails"]
    assert marriage.detailsText.pos() == unlayered["marriageDetails"]
    assert marriage.separationIndicator.pos() == unlayered["marriageSep"]

    layer.setActive(True)
    assert male.pos() == layered["male"]
    assert male.detailsText.pos() == layered["maleDetails"]
    assert female.pos() == layered["female"]
    assert female.detailsText.pos() == layered["femaleDetails"]
    assert marriage.detailsText.pos() == layered["marriageDetails"]
    assert marriage.separationIndicator.pos() == layered["marriageSep"]

    layer.setActive(False)
    assert male.pos() == unlayered["male"]
    assert male.detailsText.pos() == unlayered["maleDetails"]
    assert female.pos() == unlayered["female"]
    assert female.detailsText.pos() == unlayered["femaleDetails"]
    assert marriage.detailsText.pos() == unlayered["marriageDetails"]
    assert marriage.separationIndicator.pos() == unlayered["marriageSep"]

    layer.resetItemProperty(male.prop("itemPos"))
    layer.resetItemProperty(male.detailsText.prop("itemPos"))
    layer.resetItemProperty(female.prop("itemPos"))
    layer.resetItemProperty(female.detailsText.prop("itemPos"))
    layer.resetItemProperty(marriage.detailsText.prop("itemPos"))
    layer.resetItemProperty(marriage.separationIndicator.prop("itemPos"))
    layer.setActive(True)
    assert male.pos() == unlayered["male"]
    assert male.detailsText.pos() == unlayered["maleDetails"]
    assert female.pos() == unlayered["female"]
    assert female.detailsText.pos() == unlayered["femaleDetails"]
    assert marriage.detailsText.pos() == unlayered["marriageDetails"]
    assert marriage.separationIndicator.pos() == unlayered["marriageSep"]


def test_undo_add_remove_layered_item_props(qtbot, scene):
    male, female = scene.addItems(
        Person(name="Female", kind="female"), Person(name="Male", kind="male")
    )
    marriage = scene.addItem(Marriage(male, female))
    divorcedEvent = scene.addItem(
        Event(
            EventKind.Divorced,
            male,
            target=female,
            dateTime=util.Date(1900, 1, 1),
        )
    )
    layer = scene.addItem(Layer(name="View 1"))
    #
    unlayered = {
        "male": QPointF(-100, -50),
        "maleDetails": QPointF(100, 100),
        "female": QPointF(100, -50),
        "femaleDetails": QPointF(-100, -200),
        "marriageSep": QPointF(100, 0),
        "marriageDetails": QPointF(-25, 0),
    }
    layered = {
        "male": QPointF(-200, -150),
        "maleDetails": QPointF(-100, -100),
        "female": QPointF(100, 50),
        "femaleDetails": QPointF(100, 200),
        "marriageSep": QPointF(100, 0),
        "marriageDetails": QPointF(25, -100),
    }
    # layered
    layer.setItemProperty(male.id, "itemPos", layered["male"])
    layer.setItemProperty(male.detailsText.id, "itemPos", layered["maleDetails"])
    layer.setItemProperty(female.id, "itemPos", layered["female"])
    layer.setItemProperty(female.detailsText.id, "itemPos", layered["femaleDetails"])
    layer.setItemProperty(
        marriage.detailsText.id, "itemPos", layered["marriageDetails"]
    )
    layer.setItemProperty(
        marriage.separationIndicator.id, "itemPos", layered["marriageSep"]
    )
    # unlayered
    male.setItemPos(unlayered["male"], undo=False)
    male.detailsText.setItemPos(unlayered["maleDetails"], undo=False)
    female.setItemPos(unlayered["female"], undo=False)
    female.detailsText.setItemPos(unlayered["femaleDetails"], undo=False)
    # marriage.setDivorced(True, undo=False)
    marriage.separationIndicator.setItemPos(unlayered["marriageSep"], undo=False)
    marriage.detailsText.setItemPos(unlayered["marriageDetails"], undo=False)
    assert len(scene.items()) == 24

    scene.selectAll()
    qtbot.clickYesAfter(lambda: scene.removeSelection())
    assert len(scene.items()) == 0

    scene.undo()
    assert len(scene.items()) == 24

    scene.redo()
    assert len(scene.items()) == 0


def test_read_write_layered_props():
    """Item.write was not explicitly requesting non-layered prop values."""
    scene = Scene()
    person = Person()
    layer = Layer(name="View 1", active=True)
    scene.addItems(person, layer)
    person.setLayers([layer.id])
    person.setItemPos(QPointF(10, 10))
    person.setColor("#ff0000")
    #
    data = {}
    scene.write(data)
    scene = Scene()
    scene.read(data)
    assert scene.people()[0].pos() == QPointF(10, 10)
    assert scene.people()[0].color() == "#ff0000"
    assert scene.people()[0].pen().color().name() == "#ff0000"

    scene.layers()[0].setActive(False)
    assert scene.people()[0].color() == None
    assert scene.people()[0].pen().color().name() == util.PEN.color().name()

    scene.layers()[0].setActive(True)
    assert scene.people()[0].color() == "#ff0000"
    assert scene.people()[0].pen().color().name() == "#ff0000"


def test_reset_layered_props():
    """Item.write was not explicitly requesting non-layered prop values."""
    scene = Scene()
    person = Person()
    layer = Layer(name="View 1", active=True, storeGeometry=True)
    scene.addItems(person, layer)
    person.setItemPos(QPointF(10, 10))
    assert layer.active() == True
    assert person.pos() == QPointF(10, 10)

    scene.resetAll()  # was throwing exception in commands.py
    assert person.itemPos() == QPointF()
    assert person.pos() == QPointF()


def test_exclusiveLayerSelection():
    scene = Scene()
    layerModel = SceneLayerModel()
    layerModel.scene = scene
    layerModel.items = [scene]
    layer1 = Layer(name="View 1", active=True)
    layer2 = Layer(name="View 2")
    scene.addItems(layer1, layer2)
    assert layer1.active() == True

    layerModel.setActiveExclusively(1)
    assert layer1.active() == False
    assert layer2.active() == True


def test_layered_setPathItemVisible():
    scene = Scene(exclusiveLayerSelection=True)
    layer1, layer2, layer3, layer4 = scene.addItems(
        Layer(name="View 1"),
        Layer(name="View 2"),
        Layer(name="View 3"),
        Layer(name="View 4"),
    )
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))
    marriage = scene.addItem(Marriage(personA, personB))
    divorcedEvent = scene.addItem(
        Event(
            EventKind.Divorced,
            personA,
            target=personB,
            dateTime=util.Date(1900, 1, 1),
        )
    )
    personA.setLayers([layer2.id, layer4.id])
    personB.setLayers([layer3.id])
    layerModel = SceneLayerModel()
    layerModel.scene = scene
    layerModel.items = [scene]
    OPACITY = 0.1
    personA.setItemOpacity(OPACITY, forLayers=[layer2, layer4])

    assert personA.opacity() == 1.0
    assert personB.opacity() == 1.0
    assert marriage.opacity() == 1.0
    assert personA.isVisible() == True
    assert personB.isVisible() == True
    assert marriage.isVisible() == True

    layerModel.setActiveExclusively(0)
    assert personA.opacity() == 0.0
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == False
    assert personB.isVisible() == False
    assert marriage.isVisible() == False

    # deemphasis and other marriage-person hidden should not show marriage
    layerModel.setActiveExclusively(1)
    assert personA.opacity() == OPACITY
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert marriage.isVisible() == False

    layerModel.setActiveExclusively(2)
    assert personA.opacity() == 0.0
    assert personB.opacity() == 1.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == False
    assert personB.isVisible() == True
    assert marriage.isVisible() == False

    # deemphasis and other marriage-person hidden should not show marriage
    layerModel.setActiveExclusively(3)
    assert personA.opacity() == OPACITY
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert marriage.isVisible() == False

    layerModel.setActiveExclusively(1)
    assert personA.opacity() == OPACITY
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert marriage.isVisible() == False


def test_layered_setPathItemVisible_2():
    scene = Scene(exclusiveLayerSelection=True)
    layer1, layer2 = scene.addItems(Layer(name="View 1"), Layer(name="View 2"))
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))
    marriage = scene.addItem(Marriage(personA, personB))
    divorcedEvent = scene.addItem(
        Event(
            EventKind.Divorced,
            personA,
            target=personB,
            dateTime=util.Date(1900, 1, 1),
        )
    )
    personA.setLayers([layer1.id, layer2.id])
    layerModel = SceneLayerModel()
    layerModel.scene = scene
    layerModel.items = [scene]
    OPACITY = 0.1
    personA.setItemOpacity(OPACITY, forLayers=[layer2])

    # Only personA shown, and at full opacity
    layerModel.setActiveExclusively(0)
    assert personA.opacity() == 1.0
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert marriage.isVisible() == False

    # Only personA shown, and at partial opacity
    layerModel.setActiveExclusively(1)
    assert personA.opacity() == OPACITY
    assert personB.opacity() == 0.0
    assert marriage.opacity() == 0.0
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert marriage.isVisible() == False
