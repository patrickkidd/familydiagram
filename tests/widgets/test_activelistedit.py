import pytest

from pkdiagram.pyqt import (
    Qt,
    QApplication,
    QDateTime,
    QVBoxLayout,
    QWidget,
    QStandardItemModel,
    QStandardItem,
)
from pkdiagram import util, Scene, QmlWidgetHelper
from pkdiagram.objects import Person, Event, Marriage
from pkdiagram.widgets.qml.activelistedit import ActiveListEdit

pytestmark = [
    pytest.mark.component("ActiveListView"),
]


ActiveRole = Qt.ItemDataRole.UserRole + 1
FlagsRole = Qt.ItemDataRole.UserRole - 1  # from qstandarditemmodel.cpp


@pytest.fixture
def model():
    model = QStandardItemModel()
    model.ActiveRole = ActiveRole
    model.FlagsRole = FlagsRole
    model.setItemRoleNames(
        {
            Qt.ItemDataRole.DisplayRole: b"name",
            ActiveRole: b"active",
            FlagsRole: b"flags",
        }
    )
    return model


def test_model_read(model):
    for i in range(3):
        model.appendRow(QStandardItem(f"Item {i}"))
    assert model.rowCount() == 3
    assert model.data(model.index(0, 0)) == "Item 0"
    assert model.data(model.index(1, 0)) == "Item 1"
    assert model.data(model.index(2, 0)) == "Item 2"
    assert model.data(model.index(0, 0), role=ActiveRole) == None
    assert model.data(model.index(1, 0), role=ActiveRole) == None
    assert model.data(model.index(2, 0), role=ActiveRole) == None


def test_model_set_active(model):
    dataChanged = util.Condition(model.dataChanged)
    for i in range(3):
        model.appendRow(QStandardItem(f"Item {i}"))
    model.setData(model.index(0, 0), False, role=ActiveRole)
    model.setData(model.index(1, 0), True, role=ActiveRole)
    model.setData(model.index(2, 0), False, role=ActiveRole)
    assert dataChanged.callCount == 3
    assert dataChanged.callArgs[0] == (
        model.index(0, 0),
        model.index(0, 0),
        [ActiveRole],
    )
    assert dataChanged.callArgs[1] == (
        model.index(1, 0),
        model.index(1, 0),
        [ActiveRole],
    )
    assert dataChanged.callArgs[2] == (
        model.index(2, 0),
        model.index(2, 0),
        [ActiveRole],
    )
    assert model.data(model.index(0, 0), role=ActiveRole) == False
    assert model.data(model.index(1, 0), role=ActiveRole) == True
    assert model.data(model.index(2, 0), role=ActiveRole) == False


@pytest.fixture
def view(qtbot, qmlEngine, model):
    class ActiveListViewTest(QWidget, QmlWidgetHelper):

        def __init__(self, parent=None):
            super().__init__(parent)
            self.initQmlWidgetHelper(qmlEngine, "qml/PK/ActiveListEdit.qml")
            self.checkInitQml()
            Layout = QVBoxLayout(self)
            Layout.setContentsMargins(0, 0, 0, 0)
            Layout.addWidget(self.qml)

    _view = ActiveListViewTest()
    _view.setRootProp("model", model)
    _view.show()
    _view.resize(300, 300)
    qtbot.addWidget(_view)
    qtbot.waitActive(_view)
    yield ActiveListEdit(_view, _view.qml.rootObject())
    _view.deinit()


def test_read(view, model):
    for i in range(3):
        model.appendRow(QStandardItem(f"Item {i}"))
        model.setData(model.index(i, 0), Qt.CheckState.Unchecked, role=ActiveRole)
    util.waitUntil(lambda: view.delegate("Item 0", throw=False))
    assert view.textEdit("Item 0") != None
    assert view.textEdit("Item 1") != None
    assert view.textEdit("Item 2") != None
    assert view.checkBox("Item 0").property("checkState") == Qt.CheckState.Unchecked
    assert view.checkBox("Item 1").property("checkState") == Qt.CheckState.Unchecked
    assert view.checkBox("Item 2").property("checkState") == Qt.CheckState.Unchecked


def test_rename(view, model):
    for i in range(3):
        model.appendRow(QStandardItem(f"Item {i}"))
        model.setData(model.index(i, 0), Qt.CheckState.Unchecked, role=ActiveRole)
        model.item(i).setFlags(model.item(i).flags() | Qt.ItemFlag.ItemIsEditable)
    util.waitUntil(lambda: view.delegate("Item 1", throw=False))
    view.renameRow("Item 1", "New Item")
    assert view.textEdit("New Item") != None


def test_set_active(view, model):
    for i in range(3):
        model.appendRow(QStandardItem(f"Item {i}"))
        model.setData(model.index(i, 0), Qt.CheckState.Unchecked, role=ActiveRole)
    util.waitUntil(lambda: view.delegate("Item 0", throw=False))
    view.clickActiveBox("Item 1")
    assert view.checkBox("Item 0").property("checkState") == Qt.CheckState.Unchecked
    assert view.checkBox("Item 1").property("checkState") == Qt.CheckState.Checked
    assert view.checkBox("Item 2").property("checkState") == Qt.CheckState.Unchecked
    assert model.data(model.index(0, 0), role=ActiveRole) == Qt.CheckState.Unchecked
    assert model.data(model.index(1, 0), role=ActiveRole) == Qt.CheckState.Checked
    assert model.data(model.index(2, 0), role=ActiveRole) == Qt.CheckState.Unchecked


def tests_rename_and_set_active(view, model):
    for i in range(3):
        model.appendRow(QStandardItem(f"Item {i}"))
        model.setData(model.index(i, 0), Qt.CheckState.Unchecked, role=ActiveRole)
        model.item(i).setFlags(model.item(i).flags() | Qt.ItemFlag.ItemIsEditable)
    util.waitUntil(lambda: view.delegate("Item 1", throw=False))
    view.renameRow("Item 1", "New Item")
    assert view.textEdit("New Item") != None

    view.clickActiveBox("New Item")
    assert view.checkBox("Item 0").property("checkState") == Qt.CheckState.Unchecked
    assert view.checkBox("New Item").property("checkState") == Qt.CheckState.Checked
    assert view.checkBox("Item 2").property("checkState") == Qt.CheckState.Unchecked
    assert model.data(model.index(0, 0), role=ActiveRole) == Qt.CheckState.Unchecked
    assert model.data(model.index(1, 0), role=ActiveRole) == Qt.CheckState.Checked
    assert model.data(model.index(2, 0), role=ActiveRole) == Qt.CheckState.Unchecked


def test_dataChanged(view, model):
    for i in range(3):
        model.appendRow(QStandardItem(f"Item {i}"))
        model.setData(model.index(i, 0), Qt.CheckState.Unchecked, role=ActiveRole)
        model.item(i).setFlags(model.item(i).flags() | Qt.ItemFlag.ItemIsEditable)
    util.waitUntil(lambda: view.delegate("Item 1", throw=False))
    assert view.checkBox("Item 1").property("checkState") == Qt.CheckState.Unchecked

    model.setData(model.index(1, 0), Qt.CheckState.Checked, role=ActiveRole)
    assert view.checkBox("Item 1").property("checkState") == Qt.CheckState.Checked
