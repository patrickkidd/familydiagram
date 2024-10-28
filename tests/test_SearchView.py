import pytest
import conftest
from pkdiagram.pyqt import *
from pkdiagram import util, Scene, Person, Event, QmlWidgetHelper, SceneModel


class SearchViewTest(QWidget, QmlWidgetHelper):

    QmlWidgetHelper.registerQmlMethods([{"name": "clearSearch"}])

    def __init__(self, parent=None):
        super().__init__(parent)
        Layout = QVBoxLayout(self)
        self.initQmlWidgetHelper("tests/qml/SearchViewTest.qml")
        self.checkInitQml()


@pytest.fixture
def tst_stuff():
    inside = Person(name="Inside")
    inside_2 = Person(name="Inside 2")
    outside = Person(name="Outside")
    event1 = Event(
        parent=inside,
        loggedDateTime=util.Date(2000, 1, 10),
        dateTime=util.Date(1900, 1, 1),
        description="item1",
    )
    event2 = Event(
        parent=inside_2,
        loggedDateTime=util.Date(2000, 2, 10),
        dateTime=util.Date(1900, 1, 1),
        description="item2",
    )
    event3 = Event(
        parent=outside,
        loggedDateTime=util.Date(2000, 3, 10),
        dateTime=util.Date(1900, 1, 1),
        description="item3",
    )
    return inside, inside_2, outside, event1, event2, event3


@pytest.fixture
def tst(qtbot, request, tst_stuff):
    scene = Scene()
    scene.addItems(*tst_stuff)
    sceneModel = SceneModel()
    sceneModel.scene = scene
    w = SearchViewTest()
    w.setRootProp("sceneModel", sceneModel)
    w.resize(600, 800)
    w.show()
    qtbot.addWidget(w)
    qtbot.waitActive(w)
    yield w
    w.hide()


def test_init(tst):
    pass


def test_properties(tst):
    model = tst.rootProp("model")

    tst.keyClicks("descriptionEdit", "item1")
    assert model.description == "item1"

    tst.keyClicks("startDateButtons.dateTextInput", "01/01/2001")
    assert model.startDateTime == QDateTime(util.Date(2001, 1, 1))

    tst.keyClicks("endDateButtons.dateTextInput", "02/02/2002")
    assert model.endDateTime == QDateTime(util.Date(2002, 2, 2))

    tst.keyClicks("loggedStartDateTimeButtons.dateTextInput", "01/01/2001")
    assert model.loggedStartDateTime == QDateTime(util.Date(2001, 1, 1))

    tst.keyClicks("loggedEndDateTimeButtons.dateTextInput", "02/02/2002")
    assert model.loggedEndDateTime == QDateTime(util.Date(2002, 2, 2))

    # reset

    tst.keyClicksClear("descriptionEdit")
    assert model.description == ""

    tst.keyClicksClear("startDateButtons.dateTextInput")
    assert model.startDateTime == QDateTime()

    tst.keyClicksClear("endDateButtons.dateTextInput")
    assert model.endDateTime == QDateTime()

    tst.keyClicksClear("loggedStartDateTimeButtons.dateTextInput")
    assert model.loggedStartDateTime == QDateTime()

    tst.keyClicksClear("loggedEndDateTimeButtons.dateTextInput")
    assert model.loggedEndDateTime == QDateTime()


def test_clear_0(tst):
    model = tst.rootProp("model")
    tst.keyClicks("descriptionEdit", "item1")
    model.clear()
    assert model.description == ""


def test_clear(tst):
    model = tst.rootProp("model")
    tst.keyClicks("descriptionEdit", "item1")
    tst.keyClicks("startDateButtons.dateTextInput", "01/01/2001")
    tst.keyClicks("endDateButtons.dateTextInput", "02/02/2002")
    tst.keyClicks("loggedStartDateTimeButtons.dateTextInput", "01/01/2001")
    tst.keyClicks("loggedEndDateTimeButtons.dateTextInput", "02/02/2002")
    assert tst.isEnabled() == True
    assert tst.rootProp("enabled") == True
    assert tst.itemProp("startDateButtons.dateTextInput", "text") == "01/01/2001"
    assert tst.itemProp("endDateButtons.dateTextInput", "text") == "02/02/2002"
    assert (
        tst.itemProp("loggedStartDateTimeButtons.dateTextInput", "text") == "01/01/2001"
    )
    assert (
        tst.itemProp("loggedEndDateTimeButtons.dateTextInput", "text") == "02/02/2002"
    )

    model.clear()
    assert model.description == ""
    assert model.startDateTime == QDateTime()
    assert model.endDateTime == QDateTime()
    assert model.loggedStartDateTime == QDateTime()
    assert model.loggedEndDateTime == QDateTime()
    assert tst.itemProp("startDateButtons.dateTextInput", "text") == "--/--/----"
    assert tst.itemProp("endDateButtons.dateTextInput", "text") == "--/--/----"
    assert (
        tst.itemProp("loggedStartDateTimeButtons.dateTextInput", "text") == "--/--/----"
    )
    assert (
        tst.itemProp("loggedEndDateTimeButtons.dateTextInput", "text") == "--/--/----"
    )


def test_description(tst, tst_stuff):
    inside, inside_2, outside, event1, event2, event3 = tst_stuff
    timelineModel = tst.rootProp("sceneModel").scene.timelineModel
    model = tst.rootProp("model")
    tst.keyClicks("descriptionEdit", "item1")
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == True
    assert model.shouldHide(event3) == True


def test_loggedStartDateTime(tst, tst_stuff):
    inside, inside_2, outside, event1, event2, event3 = tst_stuff
    model = tst.rootProp("model")
    timelineModel = tst.rootProp("sceneModel").scene.timelineModel

    # before first date
    tst.keyClicks("loggedStartDateTimeButtons.dateTextInput", "01/01/2000")
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == False
    assert model.shouldHide(event3) == False

    # one day before last date
    tst.keyClicks("loggedStartDateTimeButtons.dateTextInput", "03/09/2000")
    assert model.shouldHide(event1) == True
    assert model.shouldHide(event2) == True
    assert model.shouldHide(event3) == False

    # same day as last date
    tst.keyClicks("loggedStartDateTimeButtons.dateTextInput", "03/10/2000")
    assert model.shouldHide(event1) == True
    assert model.shouldHide(event2) == True
    assert model.shouldHide(event3) == False

    # one day after last date
    tst.keyClicks("loggedStartDateTimeButtons.dateTextInput", "03/11/2000")
    assert model.shouldHide(event1) == True
    assert model.shouldHide(event2) == True
    assert model.shouldHide(event3) == True

    tst.keyClicksClear("loggedStartDateTimeButtons.dateTextInput")
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == False
    assert model.shouldHide(event3) == False


def test_loggedEndDateTime(tst, tst_stuff):
    inside, inside_2, outside, event1, event2, event3 = tst_stuff
    model = tst.rootProp("model")
    timelineModel = tst.rootProp("sceneModel").scene.timelineModel

    # after last date
    tst.keyClicks("loggedEndDateTimeButtons.dateTextInput", "03/12/2000")
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == False
    assert model.shouldHide(event3) == False

    # one day after first date
    tst.keyClicks("loggedEndDateTimeButtons.dateTextInput", "01/11/2000")
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == True
    assert model.shouldHide(event3) == True

    # same day as first date
    tst.keyClicks("loggedEndDateTimeButtons.dateTextInput", "01/10/2000")
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == True
    assert model.shouldHide(event3) == True

    # one day before first date
    tst.keyClicks("loggedEndDateTimeButtons.dateTextInput", "01/09/2000")
    assert model.shouldHide(event1) == True
    assert model.shouldHide(event2) == True
    assert model.shouldHide(event3) == True

    tst.keyClicksClear("loggedEndDateTimeButtons.dateTextInput")
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == False
    assert model.shouldHide(event3) == False


def test_loggedStartDateTime_loggedEndDateTime(tst, tst_stuff):
    inside, inside_2, outside, event1, event2, event3 = tst_stuff
    model = tst.rootProp("model")
    timelineModel = tst.rootProp("sceneModel").scene.timelineModel

    # same as first date
    tst.keyClicks("loggedStartDateTimeButtons.dateTextInput", "01/10/2000")
    # same as last date
    tst.keyClicks("loggedEndDateTimeButtons.dateTextInput", "03/10/2000")
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == False
    assert model.shouldHide(event3) == False

    # after first date
    tst.keyClicks("loggedStartDateTimeButtons.dateTextInput", "01/11/2000")
    # before last date
    tst.keyClicks("loggedEndDateTimeButtons.dateTextInput", "03/09/2000")
    assert model.shouldHide(event1) == True
    assert model.shouldHide(event2) == False
    assert model.shouldHide(event3) == True


def test_category(tst, tst_stuff):
    inside, inside_2, outside, event1, event2, event3 = tst_stuff
    scene = tst.rootProp("sceneModel").scene
    scene.categoriesModel.addRow()
    category = scene.categoriesModel.data(scene.categoriesModel.index(0, 0))
    event1.setTags([category])
    layer = scene.layers()[0]
    scene.addItems(inside, inside_2, outside, event1, event2, event3)
    inside.setLayers([layer.id])
    inside_2.setLayers([layer.id])
    assert scene.searchModel.shouldHide(event1) == False
    assert scene.searchModel.shouldHide(event2) == False
    assert scene.searchModel.shouldHide(event3) == False
    assert inside.shouldShowRightNow() == True
    assert inside_2.shouldShowRightNow() == True
    assert outside.shouldShowRightNow() == True

    scene.searchModel.category = category
    assert scene.searchModel.shouldHide(event1) == False
    assert scene.searchModel.shouldHide(event2) == True
    assert scene.searchModel.shouldHide(event3) == True
    assert inside.shouldShowRightNow() == True
    assert inside_2.shouldShowRightNow() == True
    assert outside.shouldShowRightNow() == False
