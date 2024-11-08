import pytest
from pkdiagram.pyqt import Qt
from pkdiagram import util, Scene, SceneLayerModel, Layer, Person


pytestmark = [
    pytest.mark.component("SceneLayerModel"),
    pytest.mark.depends_on("Scene", "Layer"),
]


def test_init_deinit():
    model = SceneLayerModel()
    assert model.rowCount() == 0

    scene = Scene()
    layer1 = Layer(name="View 1")
    layer2 = Layer(name="View 2", active=True)
    layer3 = Layer(name="View 3", active=True)
    scene.addItems(layer1, layer2, layer3)
    model.scene = scene
    assert model.rowCount() == 3
    assert model.data(model.index(0, 0), model.IdRole) == layer1.id
    assert model.data(model.index(1, 0), model.IdRole) == layer2.id
    assert model.data(model.index(2, 0), model.IdRole) == layer3.id
    assert model.data(model.index(0, 0)) == "View 1"
    assert model.data(model.index(1, 0)) == "View 2"
    assert model.data(model.index(2, 0)) == "View 3"
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.Unchecked
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.Checked
    assert model.data(model.index(2, 0), model.ActiveRole) == Qt.Checked

    model.resetScene()
    assert model.rowCount() == 0
    with pytest.raises(IndexError):
        model.data(model.index(0, 0))


def test_add_layer_sceneModel():
    scene = Scene()
    model = SceneLayerModel()
    model.scene = scene
    rowsInserted = util.Condition()
    model.rowsInserted.connect(rowsInserted)
    model.addRow()
    assert rowsInserted.callCount == 1
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0)) == (model.NEW_NAME_TMPL % 1)

    model.addRow()
    assert rowsInserted.callCount == 2
    assert model.rowCount() == 2
    assert model.data(model.index(1, 0)) == (model.NEW_NAME_TMPL % 2)


def test_add_layer_personModel():
    scene = Scene()
    person = Person(name="You")
    model = SceneLayerModel()
    model.scene = scene
    model.items = [person]
    rowsInserted = util.Condition()
    model.rowsInserted.connect(rowsInserted)
    model.addRow()
    assert rowsInserted.callCount == 1
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0)) == (model.NEW_NAME_TMPL % 1)

    model.addRow()
    assert rowsInserted.callCount == 2
    assert model.rowCount() == 2
    assert model.data(model.index(1, 0)) == (model.NEW_NAME_TMPL % 2)


def test_remove_layer(qtbot):
    model = SceneLayerModel()
    scene = Scene()
    model.scene = scene
    model.addRow()
    model.addRow()
    rowsRemoved = util.Condition()
    model.rowsRemoved.connect(rowsRemoved)
    qtbot.clickYesAfter(lambda: model.removeRow(0))

    assert rowsRemoved.callCount == 1
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0)) == (model.NEW_NAME_TMPL % 2)
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.Unchecked


def test_set_active_sceneModel():
    model = SceneLayerModel()
    scene = Scene()
    layer1 = Layer(name="View 1")
    layer2 = Layer(name="View 2")
    layer3 = Layer(name="View 3")
    scene.addItems(layer1, layer2, layer3)
    model.scene = scene
    model.items = [scene]

    assert layer1.active() == False
    assert layer2.active() == False
    assert layer3.active() == False

    def set(row, value):
        assert model.setData(model.index(row, 0), value, model.ActiveRole) is True

    set(0, True)
    assert layer1.active() == True
    assert layer2.active() == False
    assert layer2.active() == False

    set(2, True)
    assert layer1.active() == True
    assert layer2.active() == False
    assert layer3.active() == True

    set(0, False)
    assert layer1.active() == False
    assert layer2.active() == False
    assert layer3.active() == True

    set(2, False)
    assert layer1.active() == False
    assert layer2.active() == False
    assert layer3.active() == False


def test_moveLayer():
    scene = Scene()
    model = SceneLayerModel()
    layer0 = Layer(name="View 0")
    layer1 = Layer(name="View 1")
    layer2 = Layer(name="View 2")
    scene.addItems(layer0, layer1, layer2)
    model.scene = scene

    assert layer0.order() == 0
    assert layer1.order() == 1
    assert layer2.order() == 2

    model.moveLayer(2, 1)
    assert layer0.order() == 0
    assert layer1.order() == 2
    assert layer2.order() == 1

    model.moveLayer(0, 2)
    assert layer0.order() == 2
    assert layer1.order() == 1
    assert layer2.order() == 0
    assert scene.layers() == [layer2, layer1, layer0]

    # test reload file after reordering layers

    data = {}
    scene.write(data)
    scene2 = Scene()
    scene2.read(data)

    _layer0 = scene2.query1(name="View 0")
    _layer1 = scene2.query1(name="View 1")
    _layer2 = scene2.query1(name="View 2")
    assert _layer0.order() == 2
    assert _layer1.order() == 1
    assert _layer2.order() == 0
    assert scene2.layers() == [_layer2, _layer1, _layer0]
