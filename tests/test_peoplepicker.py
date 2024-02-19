import pytest
from pkdiagram import util, objects, EventKind
from pkdiagram.pyqt import Qt, QVBoxLayout, QWidget
from pkdiagram.addanythingdialog import AddAnythingDialog
from pkdiagram import QmlWidgetHelper


class PeoplePickerTest(QWidget, QmlWidgetHelper):
   def __init__(self, parent=None):
        super().__init__(parent)
        QVBoxLayout(self)
        self.initQmlWidgetHelper("tests/qml/PeoplePickerTest.qml")
        self.checkInitQml()
     


@pytest.fixture
def picker(qmlScene, qtbot):
    dlg = AddAnythingDialog()
    dlg.resize(600, 800)
    dlg.setRootProp('sceneModel', qmlScene._sceneModel)
    dlg.setScene(qmlScene)
    dlg.show()
    qtbot.addWidget(dlg)
    qtbot.waitActive(dlg)
    assert dlg.isShown()
    assert dlg.itemProp('AddEverything_addButton', 'text') == 'Add'

    yield dlg
    
    dlg.setScene(None)
    dlg.hide()