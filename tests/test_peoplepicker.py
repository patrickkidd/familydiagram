import pytest
from pkdiagram import util, objects
from pkdiagram.pyqt import Qt, QVBoxLayout, QWidget
from pkdiagram import Scene, Person, QmlWidgetHelper, SceneModel


class PeoplePickerTest(QWidget, QmlWidgetHelper):
    def __init__(self, sceneModel, parent=None):
        super().__init__(parent)
        QVBoxLayout(self)
        self.initQmlWidgetHelper(
            "tests/qml/PeoplePickerTest.qml", sceneModel=sceneModel
        )
        self.checkInitQml()


@pytest.fixture
def scene():
    scene = Scene()
    scene.addItem(Person(first_name="Patrick", last_name="Stinson"))
    scene._sceneModel = SceneModel()
    scene._sceneModel.scene = scene
    yield scene


@pytest.fixture
def picker(scene, qtbot):
    dlg = PeoplePickerTest(scene._sceneModel)
    dlg.resize(600, 800)
    dlg.setRootProp("sceneModel", scene._sceneModel)
    dlg.show()
    dlg.findItem("peoplePicker").clear()
    qtbot.addWidget(dlg)
    qtbot.waitActive(dlg)
    assert dlg.isVisible()

    yield dlg

    dlg.hide()


def test_init(picker):
    pass


def test_one_existing_one_not(picker):
    picker.keyClicks("nameInput", "Patrick")


# test_one_existing_one_not
# test_cancel_add_new
# test_add_existing_then_delete
# test_add_new__then_delete
