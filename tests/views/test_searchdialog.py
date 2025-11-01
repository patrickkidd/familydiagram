import logging

import pytest

from btcopilot.schema import EventKind
from pkdiagram.pyqt import QDateTime, QPointF
from pkdiagram import util
from pkdiagram.scene import Person, Event, Marriage
from pkdiagram.views import SearchDialog

from tests.widgets import TestActiveListEdit


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
def stuff(scene):
    scene.setTags([TAG_1, TAG_2, TAG_3])
    person = scene.addItem(Person())
    event1, event2, event3 = scene.addItems(
        Event(
            EventKind.Shift,
            person,
            loggedDateTime=util.Date(2000, 1, 10),
            dateTime=util.Date(1900, 1, 1),
            description="item1",
            tags=[TAG_1, TAG_2],
        ),
        Event(
            EventKind.Shift,
            person,
            loggedDateTime=util.Date(2000, 2, 10),
            dateTime=util.Date(1900, 1, 1),
            description="item2",
            tags=[TAG_1, TAG_2],
        ),
        Event(
            EventKind.Shift,
            person,
            loggedDateTime=util.Date(2000, 3, 10),
            dateTime=util.Date(1900, 1, 1),
            description="item3",
            tags=[TAG_3],
        ),
    )
    return person, event1, event2, event3


@pytest.fixture
def view(qtbot, scene, stuff, qmlEngine):
    qmlEngine.setScene(scene)
    w = SearchDialog(qmlEngine)
    w.resize(600, 800)
    w.show()
    qtbot.addWidget(w)
    qtbot.waitActive(w)

    yield w

    w.hide()
    w.deinit()


def test_init(view, qmlEngine, model):
    qmlEngine.sceneModel.onEditorMode(True)
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


def test_properties(view, scene, model, qmlEngine):
    marriage = scene.addItem(Marriage(Person(name="A"), Person(name="B")))
    qmlEngine.sceneModel.onEditorMode(True)
    tagsEdit = TestActiveListEdit(view, view.rootProp("tagsEdit"))
    emotionUnitsEdit = TestActiveListEdit(view, view.rootProp("emotionalUnitsEdit"))

    view.keyClicks("descriptionEdit", "item1")
    assert model.description == "item1"

    view.keyClicks("startDateButtons.dateTextInput", "01/01/2001")
    assert model.startDateTime == QDateTime(util.Date(2001, 1, 1))

    view.keyClicks("endDateButtons.dateTextInput", "02/02/2002")
    assert model.endDateTime == QDateTime(util.Date(2002, 2, 2))

    view.keyClicks("loggedStartDateTimeButtons.dateTextInput", "01/01/2001")
    assert model.loggedStartDateTime == QDateTime(util.Date(2001, 1, 1))

    view.keyClicks("loggedEndDateTimeButtons.dateTextInput", "02/02/2002")
    assert model.loggedEndDateTime == QDateTime(util.Date(2002, 2, 2))

    tagsEdit.clickActiveBox(TAG_1)
    assert model.tags == [TAG_1]

    EMOTIONAL_UNITS_Y = (
        view.rootProp("emotionalUnitsEdit")
        .mapToItem(view.qml.rootObject(), QPointF(0, -50))
        .y()
    )
    view.rootProp("propsPage").setProperty("contentY", EMOTIONAL_UNITS_Y)

    emotionUnitsEdit.clickActiveBox(marriage.emotionalUnit().name())
    assert scene.activeLayers() == [marriage.emotionalUnit().layer()]

    # reset

    view.rootProp("propsPage").setProperty("contentY", 0)
    view.keyClicksClear("descriptionEdit")
    assert model.description == ""

    view.keyClicksClear("startDateButtons.dateTextInput")
    assert model.startDateTime == QDateTime()

    view.keyClicksClear("endDateButtons.dateTextInput")
    assert model.endDateTime == QDateTime()

    view.keyClicksClear("loggedStartDateTimeButtons.dateTextInput")
    assert model.loggedStartDateTime == QDateTime()

    view.keyClicksClear("loggedEndDateTimeButtons.dateTextInput")
    assert model.loggedEndDateTime == QDateTime()

    tagsEdit.clickActiveBox(TAG_1)
    assert model.tags == []

    view.rootProp("propsPage").setProperty("contentY", EMOTIONAL_UNITS_Y)
    emotionUnitsEdit.clickActiveBox(marriage.emotionalUnit().name())
    assert scene.activeLayers() == []


def test_clear_0(view, model):
    view.keyClicks("descriptionEdit", "item1")
    model.clear()
    assert model.description == ""


def test_clear(view, model):

    view.keyClicks("descriptionEdit", "item1")
    view.keyClicks("startDateButtons.dateTextInput", "01/01/2001")
    view.keyClicks("endDateButtons.dateTextInput", "02/02/2002")
    view.keyClicks("loggedStartDateTimeButtons.dateTextInput", "01/01/2001")
    view.keyClicks("loggedEndDateTimeButtons.dateTextInput", "02/02/2002")
    assert view.isEnabled() == True
    assert view.rootProp("enabled") == True
    assert view.itemProp("startDateButtons.dateTextInput", "text") == "01/01/2001"
    assert view.itemProp("endDateButtons.dateTextInput", "text") == "02/02/2002"
    assert (
        view.itemProp("loggedStartDateTimeButtons.dateTextInput", "text")
        == "01/01/2001"
    )
    assert (
        view.itemProp("loggedEndDateTimeButtons.dateTextInput", "text") == "02/02/2002"
    )

    model.clear()
    assert model.description == ""
    assert model.startDateTime == QDateTime()
    assert model.endDateTime == QDateTime()
    assert model.loggedStartDateTime == QDateTime()
    assert model.loggedEndDateTime == QDateTime()
    assert view.itemProp("startDateButtons.dateTextInput", "text") == "--/--/----"
    assert view.itemProp("endDateButtons.dateTextInput", "text") == "--/--/----"
    assert (
        view.itemProp("loggedStartDateTimeButtons.dateTextInput", "text")
        == "--/--/----"
    )
    assert (
        view.itemProp("loggedEndDateTimeButtons.dateTextInput", "text") == "--/--/----"
    )


def test_description(qmlEngine, view, stuff, model):
    person, event1, event2, event3 = stuff
    row1, row2, row3 = (
        qmlEngine.timelineModel.timelineRowsFor(event1)[0],
        qmlEngine.timelineModel.timelineRowsFor(event2)[0],
        qmlEngine.timelineModel.timelineRowsFor(event3)[0],
    )
    view.keyClicks("descriptionEdit", "item1")
    assert model.shouldHide(row1) == False
    assert model.shouldHide(row2) == True
    assert model.shouldHide(row3) == True


def test_loggedStartDateTime(qmlEngine, view, stuff, model):
    person, event1, event2, event3 = stuff
    row1, row2, row3 = (
        qmlEngine.timelineModel.timelineRowsFor(event1)[0],
        qmlEngine.timelineModel.timelineRowsFor(event2)[0],
        qmlEngine.timelineModel.timelineRowsFor(event3)[0],
    )

    # before first date
    view.keyClicks("loggedStartDateTimeButtons.dateTextInput", "01/01/2000")
    assert model.shouldHide(row1) == False
    assert model.shouldHide(row2) == False
    assert model.shouldHide(row3) == False

    # one day before last date
    view.keyClicks("loggedStartDateTimeButtons.dateTextInput", "03/09/2000")
    assert model.shouldHide(row1) == True
    assert model.shouldHide(row2) == True
    assert model.shouldHide(row3) == False

    # same day as last date
    view.keyClicks("loggedStartDateTimeButtons.dateTextInput", "03/10/2000")
    assert model.shouldHide(row1) == True
    assert model.shouldHide(row2) == True
    assert model.shouldHide(row3) == False

    # one day after last date
    view.keyClicks("loggedStartDateTimeButtons.dateTextInput", "03/11/2000")
    assert model.shouldHide(row1) == True
    assert model.shouldHide(row2) == True
    assert model.shouldHide(row3) == True

    view.keyClicksClear("loggedStartDateTimeButtons.dateTextInput")
    assert model.shouldHide(row1) == False
    assert model.shouldHide(row2) == False
    assert model.shouldHide(row3) == False


def test_loggedEndDateTime(qmlEngine, view, stuff, model):
    person, event1, event2, event3 = stuff
    row1, row2, row3 = (
        qmlEngine.timelineModel.timelineRowsFor(event1)[0],
        qmlEngine.timelineModel.timelineRowsFor(event2)[0],
        qmlEngine.timelineModel.timelineRowsFor(event3)[0],
    )

    # after last date
    view.keyClicks("loggedEndDateTimeButtons.dateTextInput", "03/12/2000")
    assert model.shouldHide(row1) == False
    assert model.shouldHide(row2) == False
    assert model.shouldHide(row3) == False

    # one day after first date
    view.keyClicks("loggedEndDateTimeButtons.dateTextInput", "01/11/2000")
    assert model.shouldHide(row1) == False
    assert model.shouldHide(row2) == True
    assert model.shouldHide(row3) == True

    # same day as first date
    view.keyClicks("loggedEndDateTimeButtons.dateTextInput", "01/10/2000")
    assert model.shouldHide(row1) == False
    assert model.shouldHide(row2) == True
    assert model.shouldHide(row3) == True

    # one day before first date
    view.keyClicks("loggedEndDateTimeButtons.dateTextInput", "01/09/2000")
    assert model.shouldHide(row1) == True
    assert model.shouldHide(row2) == True
    assert model.shouldHide(row3) == True

    view.keyClicksClear("loggedEndDateTimeButtons.dateTextInput")
    assert model.shouldHide(row1) == False
    assert model.shouldHide(row2) == False
    assert model.shouldHide(row3) == False


def test_loggedStartDateTime_loggedEndDateTime(qmlEngine, view, stuff, model):
    person, event1, event2, event3 = stuff

    row1, row2, row3 = (
        qmlEngine.timelineModel.timelineRowsFor(event1)[0],
        qmlEngine.timelineModel.timelineRowsFor(event2)[0],
        qmlEngine.timelineModel.timelineRowsFor(event3)[0],
    )

    # same as first date
    view.keyClicks("loggedStartDateTimeButtons.dateTextInput", "01/10/2000")
    # same as last date
    view.keyClicks("loggedEndDateTimeButtons.dateTextInput", "03/10/2000")
    assert model.shouldHide(row1) == False
    assert model.shouldHide(row2) == False
    assert model.shouldHide(row3) == False

    # after first date
    view.keyClicks("loggedStartDateTimeButtons.dateTextInput", "01/11/2000")
    # before last date
    view.keyClicks("loggedEndDateTimeButtons.dateTextInput", "03/09/2000")
    assert model.shouldHide(row1) == True
    assert model.shouldHide(row2) == False
    assert model.shouldHide(row3) == True


def test_emotional_units_populated(view, scene, model):
    personA, personB = Person(name="A"), Person(name="B")
    scene.addItems(personA, personB)
    marriage = Marriage(personA=personA, personB=personB)
    scene.addItem(marriage)
    assert (
        view.rootProp("emotionalUnitsEdit").property("noItemsText").property("visible")
        == False
    )


def test_emotional_units_empty_no_pairbonds_with_names(scene, view, model):
    personA, personB = Person(), Person()
    scene.addItems(personA, personB)
    assert (
        view.rootProp("emotionalUnitsEdit").property("noItemsText").property("visible")
        == True
    )
    assert (
        view.rootProp("emotionalUnitsEdit").property("noItemsText").property("text")
        == util.S_NO_EMOTIONAL_UNITS_SHOWN_NO_PAIRBONDS_WITH_NAMES
    )
    assert (
        view.rootProp("emotionalUnitsEdit").property("emptyText")
        == util.S_NO_EMOTIONAL_UNITS_SHOWN_NO_PAIRBONDS_WITH_NAMES
    )


def test_emotional_units_empty_no_pairbonds_with_names__unnamed(scene, view, model):
    personA, personB = Person(), Person()
    scene.addItems(personA, personB)
    marriage = Marriage(personA=personA, personB=personB)
    scene.addItem(marriage)
    assert (
        view.rootProp("emotionalUnitsEdit").property("noItemsText").property("visible")
        == True
    )
    assert (
        view.rootProp("emotionalUnitsEdit").property("noItemsText").property("text")
        == util.S_NO_EMOTIONAL_UNITS_SHOWN_NO_PAIRBONDS_WITH_NAMES
    )
    assert (
        view.rootProp("emotionalUnitsEdit").property("emptyText")
        == util.S_NO_EMOTIONAL_UNITS_SHOWN_NO_PAIRBONDS_WITH_NAMES
    )


def test_emotional_units_names_hidden(qmlEngine, scene, view, model):
    personA, personB = Person(name="A"), Person(name="B")
    scene.addItems(personA, personB)
    marriage = Marriage(personA=personA, personB=personB)
    scene.addItem(marriage)
    qmlEngine.sceneModel.hideNames = True
    assert (
        view.rootProp("emotionalUnitsEdit").property("noItemsText").property("visible")
        == True
    )
    assert (
        view.rootProp("emotionalUnitsEdit").property("noItemsText").property("text")
        == util.S_NO_EMOTIONAL_UNITS_SHOWN_NAMES_HIDDEN
    )
    assert (
        view.rootProp("emotionalUnitsEdit").property("emptyText")
        == util.S_NO_EMOTIONAL_UNITS_SHOWN_NAMES_HIDDEN
    )
