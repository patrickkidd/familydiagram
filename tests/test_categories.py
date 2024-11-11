import pytest

from pkdiagram import Scene
from pkdiagram.objects import Layer, Person, Event, Callout
from pkdiagram.models import CategoriesModel, SearchModel
from pkdiagram.pyqt import Qt


@pytest.fixture(autouse=True)
def _init(qApp):
    yield


@pytest.fixture
def model():
    scene = Scene()
    categoriesModel = CategoriesModel()
    categoriesModel.scene = scene
    yield categoriesModel


def test_add_category(model):
    CATEGORY_NAME = model.NEW_NAME_TMPL % 1

    model.addRow()
    assert model.rowCount() == 1
    assert model.data(model.index(0)) == CATEGORY_NAME
    assert model.scene.tags() == [CATEGORY_NAME]
    assert [x.name() for x in model.scene.layers()] == [CATEGORY_NAME]


def test_add_category_when_tag_exists_with_template_name(model):
    TAG_NAME = model.NEW_NAME_TMPL % 1
    CATEGORY_NAME = model.NEW_NAME_TMPL % 2

    model.scene.addTag(TAG_NAME)
    model.addRow()
    assert model.rowCount() == 1
    assert model.data(model.index(0)) == CATEGORY_NAME
    assert model.scene.tags() == [TAG_NAME, CATEGORY_NAME]
    assert len(model.scene.layers()) == 1
    assert model.scene.layers()[0].name() == CATEGORY_NAME


def test_add_category_when_layer_exists_with_template_name(model):
    LAYER_NAME = model.NEW_NAME_TMPL % 1
    CATEGORY_NAME = model.NEW_NAME_TMPL % 2

    model.scene.addItem(Layer(name=LAYER_NAME))
    model.addRow()
    assert model.rowCount() == 1
    assert model.data(model.index(0)) == CATEGORY_NAME
    assert model.scene.tags() == [CATEGORY_NAME]
    assert len(model.scene.layers()) == 2
    assert model.scene.layers()[0].name() == LAYER_NAME
    assert model.scene.layers()[1].name() == CATEGORY_NAME


def test_rename_category(model):
    NEW_NAME = "Renamed Category"

    model.addRow()
    model.setData(model.index(0), NEW_NAME)
    assert model.data(model.index(0)) == NEW_NAME
    assert model.scene.tags() == [NEW_NAME]
    assert [x.name() for x in model.scene.layers()] == [NEW_NAME]


def test_rename_category_when_category_exists_with_same(qtbot, model):
    CATEGORY_NAME = model.NEW_NAME_TMPL % 1

    model.addRow()
    model.addRow()
    qtbot.clickOkAfter(
        lambda: model.setData(model.index(1), CATEGORY_NAME),
        text=model.S_CATEGORY_EXISTS_WITH_NAME.format(name=CATEGORY_NAME),
    )


def test_rename_category_when_tag_exists_with_same(qtbot, model):
    TAG_NAME = "Some Tag"

    model.scene.addTag(TAG_NAME)
    model.addRow()
    qtbot.clickOkAfter(
        lambda: model.setData(model.index(0), TAG_NAME),
        text=model.S_TAG_EXISTS_WITH_NAME.format(name=TAG_NAME),
    )


def test_rename_category_when_layer_exists_with_same(qtbot, model):
    LAYER_NAME = "Some Layer"

    model.scene.addItem(Layer(name=LAYER_NAME))
    model.addRow()
    qtbot.clickOkAfter(
        lambda: model.setData(model.index(0), LAYER_NAME),
        text=model.S_LAYER_EXISTS_WITH_NAME.format(name=LAYER_NAME),
    )


def test_delete_category(qtbot, model):
    model.addRow()

    qtbot.clickYesAfter(
        lambda: model.removeRow(0),
        text=model.S_CONFIRM_DELETE_VIEW,
    )
    assert model.rowCount() == 0
    assert model.scene.tags() == []
    assert model.scene.layers() == []


def test_delete_category_with_layerItems_and_events(qtbot, model):
    model.addRow()
    layer = model.scene.layers()[0]
    person = Person(name="Hey", tags=model.scene.tags())
    person.setLayers([layer.id])
    event = Event(person, tags=model.scene.tags())
    callout = Callout(layers=[layer.id])
    model.scene.addItems(person, event, callout)

    qtbot.clickYesAfter(
        lambda: model.removeRow(0),
        text=model.S_CONFIRM_DELETE_CATEGORY.format(nItems=1, nEvents=1),
    )
    assert model.rowCount() == 0
    assert model.scene.tags() == []
    assert model.scene.layers() == []


def test_model_reflects_similar_tag_and_layer(model):
    NAME = "Something"

    model.scene.addItem(Layer(name=NAME))
    model.scene.addTag(NAME)
    assert model.rowCount() == 1
    assert model.scene.tags() == [NAME]
    assert [x.name() for x in model.scene.layers()] == [NAME]


def test_delete_category_tag_from_scene(model):
    NAME = model.NEW_NAME_TMPL % 1

    model.addRow()
    model.scene.removeTag(NAME)
    assert model.rowCount() == 0


def test_delete_category_layer_from_scene(model):
    model.addRow()
    model.scene.removeItem(model.scene.layers()[0])
    assert model.rowCount() == 0


def test_set_category_active_when_tag_is_already_active(model):
    NAME = model.NEW_NAME_TMPL % 1

    # searchModel = SearchModel()
    # searchModel.scene = model.scene

    model.addRow()
    searchModel.setTags([NAME])
    model.setData(model.index(0), Qt.CheckState.Checked, model.ActiveRole)
    assert model.data(model.index(0), model.ActiveRole) == Qt.CheckState.Checked
    assert searchModel.tags == [NAME]


def test_set_category_active_when_layer_is_already_active(model):
    NAME = model.NEW_NAME_TMPL % 1

    searchModel = SearchModel()
    searchModel.scene = model.scene

    model.addRow()
    model.scene.addItem(Layer(name=NAME))
    model.setData(model.index(0), Qt.CheckState.Checked, model.ActiveRole)
    assert model.data(model.index(0), model.ActiveRole) == Qt.CheckState.Checked
    assert model.scene.layers()[0].active() == True
    assert searchModel.tags == [NAME]
