import pytest
import mock

from pkdiagram.pyqt import Qt
from pkdiagram import util, Scene
from pkdiagram.objects import Person, Marriage, Layer
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
    assert set(scene.layers()) == set(x.layer() for x in scene.emotionalUnits())
    assert model.rowCount() == 3
    assert model.data(model.index(0, 0), model.NameRole) == Marriage.itemNameFor(
        *marriages[0].people
    )
    assert model.data(model.index(1, 0), model.NameRole) == Marriage.itemNameFor(
        *marriages[1].people
    )
    assert model.data(model.index(2, 0), model.NameRole) == Marriage.itemNameFor(
        *marriages[2].people
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

    _orig_refresh = model.refresh
    with mock.patch.object(model, "refresh", side_effect=_orig_refresh) as refresh:
        model.setData(model.index(1, 0), True, model.ActiveRole)
    assert refresh.called == False
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.CheckState.Unchecked
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.CheckState.Checked
    assert model.data(model.index(2, 0), model.ActiveRole) == Qt.CheckState.Unchecked
    assert scene.activeLayers() == [marriages[1].emotionalUnit().layer()]


def test_set_inactive():
    scene = Scene()
    model = EmotionalUnitsModel()
    model.scene = scene
    marriages = [
        Marriage(personA=Person(name=f"A-{i}"), personB=Person(name=f"B-{i}"))
        for i in range(3)
    ]
    scene.addItems(*marriages)
    model.setData(model.index(1, 0), Qt.CheckState.Checked, model.ActiveRole)
    model.setData(model.index(1, 0), Qt.CheckState.Unchecked, model.ActiveRole)
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.CheckState.Unchecked
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.CheckState.Unchecked
    assert model.data(model.index(2, 0), model.ActiveRole) == Qt.CheckState.Unchecked
    assert scene.activeLayers() == []


def test_custom_layer_same_name():
    scene = Scene()
    model = EmotionalUnitsModel()
    model.scene = scene
    marriages = [
        Marriage(personA=Person(name=f"A-{i}"), personB=Person(name=f"B-{i}"))
        for i in range(3)
    ]
    layer = Layer(name="Some Layer")
    scene.addItem(layer)
    scene.addItems(*marriages)
    assert model.rowCount() == 3
    assert len(scene.layers()) == 4
    model.setData(model.index(1, 0), True, model.ActiveRole)
    assert layer.active() == False
    assert scene.activeLayers() == [marriages[1].emotionalUnit().layer()]
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.CheckState.Unchecked
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.CheckState.Checked
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.CheckState.Unchecked
