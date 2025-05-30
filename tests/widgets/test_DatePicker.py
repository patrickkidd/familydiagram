import pytest

from pkdiagram.pyqt import QObject, QWidget, QVBoxLayout, QDateTime
from pkdiagram import util
from pkdiagram.scene import Item, Scene
from pkdiagram.models import ModelHelper
from pkdiagram.widgets import QmlWidgetHelper


pytestmark = [pytest.mark.component("DatePicker")]


class DatedItem(Item):

    Item.registerProperties(
        [
            {"attr": "dateTime", "type": QDateTime},
        ]
    )


class DateModel(QObject, ModelHelper):

    PROPERTIES = Item.classProperties(DatedItem)
    ModelHelper.registerQtProperties(PROPERTIES)

    def __init__(self):
        super().__init__()
        self.initModelHelper()

    def onItemProperty(self, prop):
        super().onItemProperty(prop)


class DatePickerTest(QWidget, QmlWidgetHelper):

    # cannot figure out how to set a non-global context property...
    datePickerTestModel = DateModel()

    QmlWidgetHelper.registerQmlMethods(
        [
            {"name": "resetModelDateTime"},
            {"name": "resetButtonsDateTimeByProp"},
            {"name": "printModel"},
        ]
    )

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.model = DateModel()
        self.model.scene = Scene()
        self.initQmlWidgetHelper(engine, "tests/qml/DatePickerTest.qml")
        self.checkInitQml()
        self.setRootProp("model", self.model)
        item = DatedItem()
        self.model.scene.addItem(item)
        self.model.items = [item]
        self.resize(800, 600)
        Layout = QVBoxLayout(self)
        Layout.setContentsMargins(0, 0, 0, 0)
        Layout.addWidget(self.qml)


@pytest.fixture
def datePickerTest(qtbot, qmlEngine):
    dlg = DatePickerTest(qmlEngine)
    dlg.show()
    qtbot.addWidget(dlg)
    qtbot.waitActive(dlg)

    yield dlg

    dlg.hide()
    dlg.deinit()


def test_init(datePickerTest):
    view = datePickerTest
    item = view.model.items[0]
    item.setDateTime(util.Date(2001, 2, 3, 4, 5, 6))
    assert view.itemProp("dateButtons.dateTextInput", "text") == "02/03/2001"
    assert view.itemProp("dateButtons.timeTextInput", "text") == "4:05 am"


def test_set_date_retains_time(datePickerTest):
    view = datePickerTest
    item = view.model.items[0]
    item.setDateTime(util.Date(2001, 2, 3, 4, 5))
    view.focusItem("dateButtons.dateTextInput")  # open picker
    view.setItemProp("dateButtons.dateTextInput", "text", "08/09/2007")
    view.resetFocus("dateButtons.dateTextInput")
    assert item.dateTime() == util.Date(2007, 8, 9, 4, 5)
    assert view.itemProp("dateButtons.dateTextInput", "text") == "08/09/2007"
    assert view.itemProp("dateButtons.timeTextInput", "text") == "4:05 am"


def test_set_time_retains_date(datePickerTest):
    view = datePickerTest
    item = view.model.items[0]
    item.setDateTime(util.Date(2001, 2, 3, 4, 5, 6))
    view.focusItem("dateButtons.timeTextInput")  # open picker
    view.setItemProp("dateButtons.timeTextInput", "text", "1:23 pm")
    view.resetFocus("dateButtons.timeTextInput")  # open picker
    assert item.dateTime() == util.Date(2001, 2, 3, 13, 23, 0)
    assert view.itemProp("dateButtons.timeTextInput", "text") == "1:23 pm"
    assert view.itemProp("dateButtons.dateTextInput", "text") == "02/03/2001"


# was: test_clear_time_clears_dateTime
def test_clear_time_clears_only_time(datePickerTest):
    view = datePickerTest
    item = view.model.items[0]
    item.setDateTime(util.Date(2001, 2, 3, 4, 5, 6))
    view.keyClicksClear("dateButtons.timeTextInput")
    # view.setItemProp("dateButtons.timeTextInput", "text", "")
    assert item.dateTime().time().hour() == 0
    assert item.dateTime().time().minute() == 0
    assert item.dateTime().time().second() == 0
    assert view.itemProp("dateButtons.timeTextInput", "text") == util.BLANK_TIME_TEXT
    assert view.itemProp("dateButtons.dateTextInput", "text") == "02/03/2001"
    # assert view.itemProp("dateButtons.dateTextInput", "text") == util.BLANK_DATE_TEXT


def test_reset_prop_by_text_input(qtbot, datePickerTest):
    view = datePickerTest

    # reset date from gui
    view.keyClicksClear("dateButtons.dateTextInput")
    assert view.model.dateTime == QDateTime()


def test_reset_prop_by_prop(qmlEngine):
    view = DatePickerTest(qmlEngine)

    view.model.dateTime = QDateTime(2001, 2, 3, 0, 0)
    assert view.itemProp("dateButtons", "dateTime") == QDateTime(2001, 2, 3, 0, 0)
    assert view.itemProp("dateButtons.dateTextInput", "text") == "02/03/2001"

    view.resetButtonsDateTimeByProp()  # should also reset model date
    assert view.model.dateTime == QDateTime()
    assert view.itemProp("dateButtons.dateTextInput", "text") == "--/--/----"

    # then do it all one more time...
    view.model.dateTime = QDateTime(2002, 3, 4, 0, 0)
    assert view.itemProp("dateButtons", "dateTime") == QDateTime(2002, 3, 4, 0, 0)
    assert view.itemProp("dateButtons.dateTextInput", "text") == "03/04/2002"


def test_reset_prop_from_buttons(datePickerTest):
    view = datePickerTest

    view.model.dateTime = QDateTime(2001, 2, 3, 0, 0)
    assert view.itemProp("dateButtons", "dateTime") == QDateTime(2001, 2, 3, 0, 0)
    assert view.itemProp("dateButtons.dateTextInput", "text") == "02/03/2001"
    assert view.model.items[0].dateTime() == util.Date(2001, 2, 3)

    view.focusItem("dateButtons.dateTextInput")  # open picker
    view.mouseClick("clearButton")
    assert view.model.dateTime == QDateTime()
    assert view.itemProp("dateButtons.dateTextInput", "text") == "--/--/----"
    assert view.model.items[0].dateTime() == None


def test_reset_undo_redo(datePickerTest):
    view = datePickerTest
    scene = view.rootProp("model").scene
    dateTime = QDateTime(2001, 2, 3, 0, 0)
    view.model.dateTime = dateTime  # 0
    assert view.itemProp("dateButtons.dateTextInput", "text") == "02/03/2001"

    view.focusItem("dateButtons.dateTextInput")  # open picker
    view.mouseClick("clearButton")  # 1
    assert view.itemProp("dateButtons.dateTextInput", "text") == "--/--/----"

    scene.undo()  # 0
    assert view.itemProp("dateButtons.dateTextInput", "text") == "02/03/2001"
    assert view.itemProp("dateButtons", "dateTime") == dateTime
    assert view.itemProp("datePickerTumbler", "dateTime") == dateTime

    scene.redo()  # 1
    assert view.itemProp("dateButtons.dateTextInput", "text") == "--/--/----"

    scene.undo()  # 0
    assert view.itemProp("dateButtons.dateTextInput", "text") == "02/03/2001"

    scene.redo()  # 1
    assert view.itemProp("dateButtons.dateTextInput", "text") == "--/--/----"


def test_clear_button_clears_time_too(datePickerTest):
    view = datePickerTest
    item = view.model.items[0]
    item.setDateTime(util.Date(2001, 2, 3, 4, 5, 6))
    assert view.itemProp("dateButtons.dateTextInput", "text") == "02/03/2001"

    view.focusItem("dateButtons.dateTextInput")  # open picker
    view.mouseClick("clearButton")
    assert item.dateTime() == None
