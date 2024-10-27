import pytest

from pkdiagram import Scene
from pkdiagram.objects import Layer
from pkdiagram.models import CategoriesModel
from pkdiagram.pyqt import Qt


@pytest.fixture(autouse=True)
def _init(qApp):
    yield


@pytest.fixture
def model():
    scene = Scene()
    _model = CategoriesModel()
    _model.scene = scene
    yield _model


def test_add_category(model):
    model.addRow()
    assert model.rowCount() == 1
    assert model.data(model.index(0), model.NameRole) == "Category 0"
    assert model.scene.tags() == ["Category 0"]
    assert [x.name() for x in model.scene.layers()] == ["Category 0"]


def test_add_category(model):
    model.addRow()
    assert model.rowCount() == 1
    assert model.data(model.index(0), model.NameRole) == "Category 0"
    assert model.scene.tags() == ["Category 0"]
    assert [x.name() for x in model.scene.layers()] == ["Category 0"]


def test_add_category_when_tag_exists_with_template_name(model):
    NAME = model.NEW_NAME_TMPL % 0

    model.scene.addTag(NAME)
    model.addRow()
    assert model.rowCount() == 1
    assert model.data(model.index(0), model.NameRole) == "Category 1"
    assert model.scene.tags() == ["Category 0", "Category 1"]
    assert len(model.layers()) == 1
    assert model.layers()[0].name() == "Category 1"


def test_add_category_when_layer_exists_with_template_name(model):
    NAME = model.NEW_NAME_TMPL % 0

    model.scene.addItem(Layer(name=NAME))
    model.addRow()
    assert model.rowCount() == 1
    assert model.data(model.index(0), model.NameRole) == "Category 1"
    assert model.scene.tags() == "Category 1"
    assert len(model.layers()) == 2
    assert model.layers()[0].name() == ["Category 0", "Category 1"]


def test_rename_category(model):
    NEW_NAME = "Renamed Category"

    model.addRow()
    model.setData(model.index(0), NEW_NAME, model.NameRole)
    assert model.data(model.index(0), model.NameRole) == NEW_NAME
    assert model.scene.tags() == [NEW_NAME]
    assert [x.name() for x in model.scene.layers()] == [NEW_NAME]


def test_rename_category_when_tag_exists_with_same(qtbot, model):
    TAG_NAME = "Some Tag"
    CATEGORY_NAME = model.NEW_NAME_TMPL % 0

    model.scene.addTag(TAG_NAME)
    model.addRow()
    qtbot.clickOkAfter(lambda: model.setData(model.index(0), TAG_NAME, model.NameRole))
    assert model.data(model.index(0), model.NameRole) == CATEGORY_NAME
    assert model.scene.tags() == [CATEGORY_NAME]
    assert [x.name() for x in model.scene.layers()] == [CATEGORY_NAME]


def test_rename_category_when_layer_exists_with_same(qtbot, model):
    LAYER_NAME = "Some Layer"
    CATEGORY_NAME = model.NEW_NAME_TMPL % 0

    model.scene.addItem(Layer(name=LAYER_NAME))
    model.addRow()
    qtbot.clickOkAfter(
        lambda: model.setData(model.index(0), LAYER_NAME, model.NameRole)
    )
    assert model.data(model.index(0), model.NameRole) == CATEGORY_NAME
    assert model.scene.tags() == [CATEGORY_NAME]
    assert [x.name() for x in model.scene.layers()] == [CATEGORY_NAME]


def test_delete_category(model):
    model.addRow()
    assert model.rowCount() == 1
    model.removeRow(0)
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
    NAME = model.NEW_NAME_TMPL % 0

    model.addRow()
    model.scene.removeTag("Category 0")
    assert model.rowCount() == 0


def test_delete_category_layer_from_scene(model):
    NAME = model.NEW_NAME_TMPL % 0

    model.addRow()
    model.scene.removeItem(model.scene.layers()[0])
    assert model.rowCount() == 0


def test_set_category_active_when_tag_is_already_active(model):
    NAME = model.NEW_NAME_TMPL % 0

    model.addRow()
    model.scene.searchModel.setTags([NAME])
    model.setData(model.index(0), Qt.CheckState.Checked, model.ActiveRole)
    assert model.data(model.index(0), model.ActiveRole) is Qt.CheckState.Checked
    assert model.scene.searchModel.tags() == [NAME]


def test_set_category_active_when_layer_is_already_active(model):
    NAME = model.NEW_NAME_TMPL % 0

    model.addRow()
    model.scene.addItem(Layer(name=NAME))
    model.setData(model.index(0), Qt.CheckState.Checked, model.ActiveRole)
    assert model.data(model.index(0), model.ActiveRole) is Qt.CheckState.Checked
    assert model.scene.searchModel.tags() == [NAME]
