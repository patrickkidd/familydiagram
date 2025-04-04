import mock

from pkdiagram.pyqt import Qt
from pkdiagram import util
from pkdiagram.scene import Scene
from pkdiagram.models import SceneVariablesModel


def test_init_deinit(scene):
    model = SceneVariablesModel()
    assert model.rowCount() == 0

    scene.addEventProperty("Var 1")
    scene.addEventProperty("Var 2")
    model.scene = scene
    assert model.rowCount() == 2

    assert model.data(model.index(0, 0), Qt.DisplayRole) == "Var 1"
    assert model.data(model.index(1, 0), Qt.DisplayRole) == "Var 2"

    model.resetScene()
    assert model.rowCount() == 0


def test_add_var(scene):
    model = SceneVariablesModel()
    model.scene = scene
    assert model.rowCount() == 0

    modelReset = util.Condition()
    model.modelReset.connect(modelReset)

    model.addRow()
    assert modelReset.callCount == 1
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), Qt.DisplayRole) == model.NEW_NAME_TMPL % 1


def test_remove_var(scene):
    model = SceneVariablesModel()
    scene.addEventProperty("Var 1")
    scene.addEventProperty("Var 2")
    scene.addEventProperty("Var 3")
    model.scene = scene
    assert model.rowCount() == 3

    model.removeRow(1)
    assert model.rowCount() == 2
    assert model.data(model.index(0, 0), Qt.DisplayRole) == "Var 1"
    assert model.data(model.index(1, 0), Qt.DisplayRole) == "Var 3"


def test_rename_var(scene):
    scene.addEventProperty("Var 1")
    model = SceneVariablesModel()
    model.scene = scene
    with mock.patch.object(Scene, "renameEventProperty") as renameEventProperty:
        model.setData(model.index(0, 0), "Var 2", Qt.EditRole)
    renameEventProperty.assert_called_once_with("Var 1", "Var 2", undo=True)
