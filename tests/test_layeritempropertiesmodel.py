import pytest
from pkdiagram import *


@pytest.fixture
def layerItemStuff():
    scene = Scene()
    def addLayer():
        name = util.newNameOf(scene.layers(), tmpl='View %i', key=lambda x: x.name())
        layer = Layer(name=name)
        scene.addItem(layer)
    addLayer()
    addLayer()
    addLayer()
    addLayer()
    callout = Callout(layers=[l.id for i, l in enumerate(scene.layers()) if i in (1, 3)])
    scene.addItem(callout)
    model = LayerItemLayersModel()
    model.scene = scene
    model.items = [callout]
    return scene, callout, model


def test_layer_model_init(layerItemStuff):
    scene, callout, model = layerItemStuff

    assert model.data(model.index(0, 0)) == 'View 1'
    assert model.data(model.index(1, 0)) == 'View 2'
    assert model.data(model.index(2, 0)) == 'View 3'
    assert model.data(model.index(3, 0)) == 'View 4'
    
    assert model.data(model.index(0, 0), model.NameRole) == 'View 1'
    assert model.data(model.index(1, 0), model.NameRole) == 'View 2'
    assert model.data(model.index(2, 0), model.NameRole) == 'View 3'
    assert model.data(model.index(3, 0), model.NameRole) == 'View 4'
    
    scene.query1(name='View 2').setActive(True)
    scene.query1(name='View 4').setActive(True)

    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.Unchecked
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.Checked
    assert model.data(model.index(2, 0), model.ActiveRole) == Qt.Unchecked
    assert model.data(model.index(3, 0), model.ActiveRole) == Qt.Checked


def test_resort_on_scene_resort(layerItemStuff):
    scene, callout, model = layerItemStuff
    layerModel = SceneLayerModel()
    layerModel.scene = scene
    layerModel.moveLayer(1, 3)
    assert model.data(model.index(0, 0), model.NameRole) == 'View 1'
    assert model.data(model.index(1, 0), model.NameRole) == 'View 3'
    assert model.data(model.index(2, 0), model.NameRole) == 'View 4'
    assert model.data(model.index(3, 0), model.NameRole) == 'View 2'


def test_set_item_layer_active(layerItemStuff):
    scene, callout, model = layerItemStuff

    dataChanged = util.Condition()
    model.dataChanged.connect(dataChanged)
    assert dataChanged.callCount == 0
    assert scene.layers()[0].id not in callout.layers()
    
    model.setData(model.index(0, 0), True, model.ActiveRole)
    assert dataChanged.callCount == 1
    assert dataChanged.callArgs[0][0].row() == 0
    assert dataChanged.callArgs[0][0].column() == 0
    assert dataChanged.callArgs[0][2][0] == model.ActiveRole
    assert scene.layers()[0].id in callout.layers()


def test_set_different_item_layer_active_but_enforce_min_one_layer(layerItemStuff):
    """ Set layers on multiple LayerItems when LayerItems have different layers set. """
    scene, callout, model = layerItemStuff
    callout.setLayers([l.id for i, l in enumerate(scene.layers()) if i in (0, 1)])

    callout2 = Callout(layers=[l.id for i, l in enumerate(scene.layers()) if i == 0])
    scene.addItem(callout2)
    model.items = [callout, callout2]
    dataChanged = util.Condition()
    model.dataChanged.connect(dataChanged)
    assert dataChanged.callCount == 0
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.Checked             # [True, True]
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.PartiallyChecked    # [True, False]
    assert model.data(model.index(2, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]
    assert model.data(model.index(3, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]

    # should not unset layer 0 on callout2 b/c min one layer
    model.setData(model.index(0, 0), Qt.Unchecked, model.ActiveRole)
    assert dataChanged.callCount == 1
    assert dataChanged.callArgs[0][0].row() == 0
    assert dataChanged.callArgs[0][0].column() == 0
    assert dataChanged.callArgs[0][2][0] == model.ActiveRole
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.PartiallyChecked    # [False, True] -- callout2 remains
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.PartiallyChecked    # [True, False]
    assert model.data(model.index(2, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]
    assert model.data(model.index(3, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]
    
    # should not unset layer 1 on callout b/c min one layer
    model.setData(model.index(1, 0), Qt.Unchecked, model.ActiveRole)
    assert dataChanged.callCount == 2
    assert dataChanged.callArgs[1][0].row() == 1
    assert dataChanged.callArgs[1][0].column() == 0
    assert dataChanged.callArgs[1][2][0] == model.ActiveRole
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.PartiallyChecked    # [False, True] -- callout2 remains
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.PartiallyChecked    # [True, False]
    assert model.data(model.index(2, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]
    assert model.data(model.index(3, 0), model.ActiveRole) == Qt.Unchecked             # [False, False]
    

def test_set_different_item_layer_active(layerItemStuff):
    """ Set layers on multiple LayerItems when LayerItems have different layers set. """
    scene, callout, model = layerItemStuff

    callout2 = Callout(layers=[l.id for i, l in enumerate(scene.layers()) if i in (0, 3)])
    scene.addItem(callout2)
    model.items = [callout, callout2]
    dataChanged = util.Condition()
    model.dataChanged.connect(dataChanged)
    assert dataChanged.callCount == 0
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.PartiallyChecked    # [False, True]
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.PartiallyChecked    # [True, False]
    assert model.data(model.index(2, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]
    assert model.data(model.index(3, 0), model.ActiveRole) == Qt.Checked             # [True, True]

    model.setData(model.index(0, 0), Qt.Checked, model.ActiveRole)
    assert dataChanged.callCount == 1
    assert dataChanged.callArgs[0][0].row() == 0
    assert dataChanged.callArgs[0][0].column() == 0
    assert dataChanged.callArgs[0][2][0] == model.ActiveRole
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.Checked             # [True, True]
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.PartiallyChecked    # [True, False]
    assert model.data(model.index(2, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]
    assert model.data(model.index(3, 0), model.ActiveRole) == Qt.Checked             # [True, True]
    
    model.setData(model.index(0, 0), Qt.Unchecked, model.ActiveRole)
    assert dataChanged.callCount == 2 
    assert dataChanged.callArgs[1][0].row() == 0
    assert dataChanged.callArgs[1][0].column() == 0
    assert dataChanged.callArgs[1][2][0] == model.ActiveRole
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.PartiallyChecked    # [True, False]
    assert model.data(model.index(2, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]
    assert model.data(model.index(3, 0), model.ActiveRole) == Qt.Checked             # [True, True]

    model.setData(model.index(1, 0), Qt.Checked, model.ActiveRole)
    assert dataChanged.callCount == 3 
    assert dataChanged.callArgs[2][0].row() == 1
    assert dataChanged.callArgs[2][0].column() == 0
    assert dataChanged.callArgs[2][2][0] == model.ActiveRole
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.Checked             # [True, True]
    assert model.data(model.index(2, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]
    assert model.data(model.index(3, 0), model.ActiveRole) == Qt.Checked             # [True, True]

    model.setData(model.index(3, 0), Qt.Unchecked, model.ActiveRole)
    assert dataChanged.callCount == 4
    assert dataChanged.callArgs[3][0].row() == 3
    assert dataChanged.callArgs[3][0].column() == 0
    assert dataChanged.callArgs[3][2][0] == model.ActiveRole
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.Checked             # [True, True]
    assert model.data(model.index(2, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]
    assert model.data(model.index(3, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]

    # shouldn't emit if values are the same
    model.setData(model.index(3, 0), Qt.Unchecked, model.ActiveRole)
    assert dataChanged.callCount == 4
    assert dataChanged.callArgs[3][0].row() == 3
    assert dataChanged.callArgs[3][0].column() == 0
    assert dataChanged.callArgs[3][2][0] == model.ActiveRole
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.Checked             # [True, True]
    assert model.data(model.index(2, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]
    assert model.data(model.index(3, 0), model.ActiveRole) == Qt.Unchecked           # [False, False]


def test_set_layer_on_person():
    model = LayerItemLayersModel()
    scene = Scene()
    person = Person(name='You')
    layer1 = Layer(name='View 1')
    layer2 = Layer(name='View 2')
    layer3 = Layer(name='View 3')
    scene.addItems(layer1, layer2, layer3)
    model.scene = scene
    model.items = [person]

    assert layer1.active() == False
    assert layer2.active() == False
    assert layer3.active() == False

    def set(row, value):
        assert model.setData(model.index(row, 0), value, model.ActiveRole) is True

    set(0, True)
    assert layer1.id in person.layers()
    assert layer2.id not in person.layers()
    assert layer3.id not in person.layers()
    
    set(2, True)
    assert layer1.id in person.layers()
    assert layer2.id not in person.layers()
    assert layer3.id in person.layers()
        
    set(0, False)
    assert layer1.id not in person.layers()
    assert layer2.id not in person.layers()
    assert layer3.id in person.layers()
    
    set(2, False)
    assert layer1.id not in person.layers()
    assert layer2.id not in person.layers()
    assert layer3.id not in person.layers()