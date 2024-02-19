from pkdiagram import util, Scene, SceneModel, Layer


def test_sceneChanged():
    scene = Scene()
    model = SceneModel()
    sceneChanged = util.Condition()
    model.sceneChanged.connect(sceneChanged)
    model.scene = scene
    assert sceneChanged.callCount == 1
    assert sceneChanged.callArgs[0][0] == scene


def test_hasActiveLayers():
    scene = Scene()
    model = SceneModel()
    model.scene = scene
    assert model.hasActiveLayers == scene.hasActiveLayers

    layer = Layer(active=True)
    scene.addItem(layer)
    assert model.hasActiveLayers == scene.hasActiveLayers

    layer.setActive(False)
    assert model.hasActiveLayers == scene.hasActiveLayers


def __test_valid_props():
    scene = Scene()
    model = SceneModel()
    model.scene = scene

    attrs = model.classProperties(SceneModel)
    for kwargs in attrs:
        attr = kwargs["attr"]
        Debug(attr, model.get(attr))
