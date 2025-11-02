import pytest

from pkdiagram import util
from pkdiagram.models import SceneModel
from pkdiagram.scene import Scene, Layer


pytestmark = [
    pytest.mark.component("SceneModel"),
    pytest.mark.depends_on("Scene"),
]


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


def test_eventPropertiesTemplateIndexChanged():
    """
    Punting this to a test so as to avoid to many refactoring changes at once
    """
    scene = Scene()
    model = SceneModel()
    assert model.eventPropertiesTemplateIndex == -1

    model.eventPropertiesTemplateIndex = 2
    assert model.eventPropertiesTemplateIndex == 2

    model.eventPropertiesTemplateIndex = 0
    assert model.eventPropertiesTemplateIndex == 0
