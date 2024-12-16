import logging

import pytest

from pkdiagram.pyqt import QDateTime, QApplication, QPointF
from pkdiagram import util, Scene
from pkdiagram.objects import Person, Event, Marriage
from pkdiagram.widgets.qml.activelistedit import ActiveListEdit
from pkdiagram.views import SearchDialog


pytestmark = [
    pytest.mark.component("SearchDialog"),
    pytest.mark.depends_on("Scene", "SearchModel", "TagsModel"),
]

_log = logging.getLogger(__name__)


@pytest.fixture
def model(qmlEngine):
    return qmlEngine.searchModel


TAG_1 = "tag_1"
TAG_2 = "tag_2"
TAG_3 = "tag_3"


@pytest.fixture
def tst_stuff():
    person = Person()
    event1 = Event(
        parent=person,
        loggedDateTime=util.Date(2000, 1, 10),
        dateTime=util.Date(1900, 1, 1),
        description="item1",
        tags=[TAG_1, TAG_2],
    )
    event2 = Event(
        parent=person,
        loggedDateTime=util.Date(2000, 2, 10),
        dateTime=util.Date(1900, 1, 1),
        description="item2",
        tags=[TAG_1, TAG_2],
    )
    event3 = Event(
        parent=person,
        loggedDateTime=util.Date(2000, 3, 10),
        dateTime=util.Date(1900, 1, 1),
        description="item3",
        tags=[TAG_3],
    )
    return person, event1, event2, event3


@pytest.fixture
def tst(qtbot, tst_stuff, qmlEngine):
    scene = Scene()
    scene.setTags([TAG_1, TAG_2, TAG_3])
    scene.addItems(*tst_stuff)
    qmlEngine.setScene(scene)
    w = SearchDialog(qmlEngine)
    w.resize(600, 800)
    w.show()
    qtbot.addWidget(w)
    qtbot.waitActive(w)

    yield w

    w.hide()
    w.deinit()


def test_init(tst, qmlEngine):
    qmlEngine.sceneModel.onEditorMode(True)
    model = qmlEngine.searchModel
    assert model.description == ""
    assert model.startDateTime == QDateTime()
    assert model.endDateTime == QDateTime()
    assert model.loggedStartDateTime == QDateTime()
    assert model.loggedEndDateTime == QDateTime()

    assert model.description == ""
    assert model.startDateTime == QDateTime()
    assert model.endDateTime == QDateTime()
    assert model.loggedStartDateTime == QDateTime()
    assert model.loggedEndDateTime == QDateTime()


def test_properties(tst, model, qmlEngine):
    scene = model.scene
    marriage = Marriage(Person(name="A"), Person(name="B"))
    scene.addItem(marriage)
    qmlEngine.sceneModel.onEditorMode(True)
    tagsEdit = ActiveListEdit(tst, tst.rootProp("tagsEdit"))
    emotionUnitsEdit = ActiveListEdit(tst, tst.rootProp("emotionalUnitsEdit"))

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

    tagsEdit.clickActiveBox(TAG_1)
    assert model.tags == [TAG_1]

    EMOTIONAL_UNITS_Y = (
        tst.rootProp("emotionalUnitsEdit")
        .mapToItem(tst.qml.rootObject(), QPointF(0, -50))
        .y()
    )
    tst.rootProp("propsPage").setProperty("contentY", EMOTIONAL_UNITS_Y)

    emotionUnitsEdit.clickActiveBox(marriage.emotionalUnit().name())
    assert scene.activeLayers() == [marriage.emotionalUnit().layer()]

    # reset

    tst.rootProp("propsPage").setProperty("contentY", 0)
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

    tagsEdit.clickActiveBox(TAG_1)
    assert model.tags == []

    tst.rootProp("propsPage").setProperty("contentY", EMOTIONAL_UNITS_Y)
    emotionUnitsEdit.clickActiveBox(marriage.emotionalUnit().name())
    assert scene.activeLayers() == []


def test_clear_0(tst, model):
    tst.keyClicks("descriptionEdit", "item1")
    model.clear()
    assert model.description == ""


def test_clear(tst, model):

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


def test_description(tst, tst_stuff, model):
    person, event1, event2, event3 = tst_stuff
    tst.keyClicks("descriptionEdit", "item1")
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == True
    assert model.shouldHide(event3) == True


def test_loggedStartDateTime(tst, tst_stuff, model):
    person, event1, event2, event3 = tst_stuff

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


def test_loggedEndDateTime(tst, tst_stuff, model):
    person, event1, event2, event3 = tst_stuff

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


def test_loggedStartDateTime_loggedEndDateTime(tst, tst_stuff, model):
    person, event1, event2, event3 = tst_stuff

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


def test_emotional_units_populated(tst, model):
    personA, personB = Person(name="A"), Person(name="B")
    model.scene.addItems(personA, personB)
    marriage = Marriage(personA=personA, personB=personB)
    model.scene.addItem(marriage)
    assert (
        tst.rootProp("emotionalUnitsEdit").property("noItemsText").property("visible")
        == False
    )


def test_emotional_units_empty_no_pairbonds_with_names(tst, model):
    personA, personB = Person(), Person()
    model.scene.addItems(personA, personB)
    assert (
        tst.rootProp("emotionalUnitsEdit").property("noItemsText").property("visible")
        == True
    )
    assert (
        tst.rootProp("emotionalUnitsEdit").property("noItemsText").property("text")
        == util.S_NO_EMOTIONAL_UNITS_SHOWN_NO_PAIRBONDS_WITH_NAMES
    )
    assert (
        tst.rootProp("emotionalUnitsEdit").property("emptyText")
        == util.S_NO_EMOTIONAL_UNITS_SHOWN_NO_PAIRBONDS_WITH_NAMES
    )


def test_emotional_units_empty_no_pairbonds_with_names__unnamed(tst, model):
    personA, personB = Person(), Person()
    model.scene.addItems(personA, personB)
    marriage = Marriage(personA=personA, personB=personB)
    model.scene.addItem(marriage)
    assert (
        tst.rootProp("emotionalUnitsEdit").property("noItemsText").property("visible")
        == True
    )
    assert (
        tst.rootProp("emotionalUnitsEdit").property("noItemsText").property("text")
        == util.S_NO_EMOTIONAL_UNITS_SHOWN_NO_PAIRBONDS_WITH_NAMES
    )
    assert (
        tst.rootProp("emotionalUnitsEdit").property("emptyText")
        == util.S_NO_EMOTIONAL_UNITS_SHOWN_NO_PAIRBONDS_WITH_NAMES
    )


def test_emotional_units_names_hidden(qmlEngine, tst, model):
    personA, personB = Person(name="A"), Person(name="B")
    model.scene.addItems(personA, personB)
    marriage = Marriage(personA=personA, personB=personB)
    model.scene.addItem(marriage)
    qmlEngine.sceneModel.hideNames = True
    assert (
        tst.rootProp("emotionalUnitsEdit").property("noItemsText").property("visible")
        == True
    )
    assert (
        tst.rootProp("emotionalUnitsEdit").property("noItemsText").property("text")
        == util.S_NO_EMOTIONAL_UNITS_SHOWN_NAMES_HIDDEN
    )
    assert (
        tst.rootProp("emotionalUnitsEdit").property("emptyText")
        == util.S_NO_EMOTIONAL_UNITS_SHOWN_NAMES_HIDDEN
    )
