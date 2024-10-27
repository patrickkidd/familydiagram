import pytest
from pkdiagram.pyqt import Qt
from pkdiagram import util, Scene, TagsModel, Item, Layer


def test_init_deinit():
    model = TagsModel()
    assert model.rowCount() == 0

    scene = Scene(tags=["here", "we", "are"])
    model.scene = scene
    assert model.rowCount() == 3

    item1 = Item(tags=["here", "we"])
    item2 = Item(tags=["here"])
    model.items = [item1, item2]
    assert model.data(model.index(0, 0)) == "are"
    assert model.data(model.index(1, 0)) == "here"
    assert model.data(model.index(2, 0)) == "we"
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.Unchecked  # are
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.Checked  # here
    assert model.data(model.index(2, 0), model.ActiveRole) == Qt.PartiallyChecked  # we

    model.resetItems()
    assert model.rowCount() == 3
    # should not change item tags
    assert item1.tags() == ["here", "we"]
    assert item2.tags() == ["here"]

    model.resetScene()
    assert model.rowCount() == 0
    with pytest.raises(KeyError):
        model.data(model.index(0, 0))


def test_add_tag():
    scene = Scene()
    model = TagsModel()
    model.scene = scene
    item1 = Item()
    item2 = Item()
    model.items = [item1, item2]
    assert model.rowCount() == 0

    modelReset = util.Condition()
    model.modelReset.connect(modelReset)

    model.addRow()
    assert modelReset.callCount == 1
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0)) == model.NEW_NAME_TMPL % 1


def test_remove_tag(qtbot):
    model = TagsModel()
    scene = Scene(tags=["here", "we", "are"])
    model.scene = scene
    item1 = Item(tags=["here", "we"])
    item2 = Item(tags=["here"])
    model.items = [item1, item2]

    modelReset = util.Condition()
    model.modelReset.connect(modelReset)

    qtbot.clickYesAfter(lambda: model.removeTag(1))
    assert modelReset.callCount == 1
    assert model.rowCount() == 2
    assert model.data(model.index(0, 0)) == "are"
    assert model.data(model.index(0, 0), model.ActiveRole) == Qt.Unchecked
    assert model.data(model.index(1, 0)) == "we"
    assert model.data(model.index(1, 0), model.ActiveRole) == Qt.PartiallyChecked


def test_rename_tag_retains_tag_on_items():

    s = Scene()
    s.setTags(["aaa", "ccc", "ddd"])
    item = Item()
    s.addItem(item)
    item.setTags(["ddd"])

    model = TagsModel()
    model.items = [item]
    model.scene = s
    assert model.data(model.index(2, 0), model.NameRole) == "ddd"

    dataChanged = util.Condition()
    model.dataChanged.connect(dataChanged)
    modelReset = util.Condition()
    model.modelReset.connect(modelReset)

    model.setData(model.index(2, 0), "bbb", model.NameRole)

    assert s.tags() == ["aaa", "bbb", "ccc"]
    assert item.tags() == ["bbb"]
    assert modelReset.callCount == 1
    assert dataChanged.callCount == 0


def test_set_active():
    scene = Scene()
    model = TagsModel()
    model.scene = scene
    item1 = Item()
    item2 = Item()
    model.items = [item1, item2]

    scene.setTags(["here", "we", "are"])
    assert item1.tags() == []
    assert item2.tags() == []

    def set(row, value):
        assert model.setData(model.index(row, 0), value, model.ActiveRole) is True

    set(0, True)
    assert item1.tags() == ["are"]
    assert item2.tags() == ["are"]

    set(2, True)
    assert item1.tags() == ["are", "we"]
    assert item2.tags() == ["are", "we"]

    set(0, False)
    assert item1.tags() == ["we"]
    assert item2.tags() == ["we"]

    set(2, False)
    assert item1.tags() == []
    assert item2.tags() == []


def test_set_active_SearchModel():
    scene = Scene()
    model = TagsModel()
    model.scene = scene
    model.items = [scene]

    scene.setTags(["here", "we", "are"])

    def set(row, value):
        assert model.setData(model.index(row, 0), value, model.ActiveRole) is True

    set(0, True)
    assert scene.searchModel.tags == ["are"]

    set(2, True)
    assert scene.searchModel.tags == ["are", "we"]

    set(0, False)
    assert scene.searchModel.tags == ["we"]

    set(2, False)
    assert scene.searchModel.tags == []
