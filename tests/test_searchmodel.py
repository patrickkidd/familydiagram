import logging

import pytest

from pkdiagram.pyqt import *
from pkdiagram import util, Scene, Person, Event, Layer, Emotion


_log = logging.getLogger(__name__)


@pytest.fixture
def model():
    scene = Scene()
    category = scene.categoriesModel.addRow()
    layer = scene.layers()[0]
    inside = Person(name="Inside")
    inside_2 = Person(name="Inside 2")
    outside = Person(name="Outside")
    event1 = Event(
        parent=inside,
        loggedDateTime=util.Date(2000, 1, 10),
        dateTime=util.Date(1900, 1, 1),
        tags=[category],
    )
    event2 = Event(
        parent=inside,
        loggedDateTime=util.Date(2000, 2, 10),
        dateTime=util.Date(1900, 1, 1),
    )
    event3 = Event(
        parent=inside,
        loggedDateTime=util.Date(2000, 3, 10),
        dateTime=util.Date(1900, 1, 1),
    )
    scene.addItems(inside, inside_2, outside)
    inside.setLayers([layer.id])
    inside_2.setLayers([layer.id])
    scene.searchModel.items = [inside]
    return scene.searchModel, event1, event2, event3


def test_isBlank_separate(model):
    model, event1, event2, event3 = model

    assert model.isBlank == True

    model.tags = ["here"]
    assert model.isBlank == False

    model.description = "also here"
    assert model.isBlank == False

    model.reset("description")
    assert model.isBlank == False

    model.reset("tags")
    assert model.isBlank == True


PROPERTY_VALUES = {
    "category": "Some Category",
    "description": "something",
    "startDateTime": util.Date(2000, 1, 1),
    "endDateTime": util.Date(2000, 1, 1),
    "loggedStartDateTime": util.Date(2000, 1, 1),
    "loggedEndDateTime": util.Date(2000, 1, 1),
    "nodal": True,
    "tags": ["some", "tags"],
}


@pytest.mark.parametrize("attr", PROPERTY_VALUES.keys())
def test_changed_and_isBlank(model, attr):
    model, event1, event2, event3 = model

    changed = util.Condition(model.changed)
    attrChanged = util.Condition(getattr(model, f"{attr}Changed"))

    value = PROPERTY_VALUES[attr]
    assert model.isBlank == True

    setattr(model, attr, value)
    assert model.isBlank == False
    assert changed.test() == True
    assert attrChanged.test() == True

    changed.reset()
    model.reset(attr)
    assert model.isBlank == True
    assert changed.test() == True
    assert attrChanged.test() == True


def test_isBlank_clear(model):
    model, event1, event2, event3 = model

    assert model.isBlank == True

    model.tags = ["here"]
    assert model.isBlank == False

    model.description = "also here"
    assert model.isBlank == False

    model.clear()
    assert model.isBlank == True


def test_loggedStartDateTime(model):
    model, event1, event2, event3 = model

    # before first date
    model.loggedStartDateTime = QDateTime(util.Date(2000, 1, 1))
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == False
    assert model.shouldHide(event3) == False

    # one day before last date
    model.loggedStartDateTime = QDateTime(util.Date(2000, 3, 9))
    assert model.shouldHide(event1) == True
    assert model.shouldHide(event2) == True
    assert model.shouldHide(event3) == False

    # same day as last date
    model.loggedStartDateTime = QDateTime(util.Date(2000, 3, 10))
    assert model.shouldHide(event1) == True
    assert model.shouldHide(event2) == True
    assert model.shouldHide(event3) == False

    # one day after last date
    model.loggedStartDateTime = QDateTime(util.Date(2000, 3, 11))
    assert model.shouldHide(event1) == True
    assert model.shouldHide(event2) == True
    assert model.shouldHide(event3) == True

    model.resetLoggedStartDateTime()
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == False
    assert model.shouldHide(event3) == False


def test_loggedEndDateTime(model):
    model, event1, event2, event3 = model

    # after last date
    model.loggedEndDateTime = QDateTime(util.Date(2000, 3, 12))
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == False
    assert model.shouldHide(event3) == False

    # one day after first date
    model.loggedEndDateTime = QDateTime(util.Date(2000, 1, 11))
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == True
    assert model.shouldHide(event3) == True

    # same day as first date
    model.loggedEndDateTime = QDateTime(util.Date(2000, 1, 10))
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == True
    assert model.shouldHide(event3) == True

    # one day before first date
    model.loggedEndDateTime = QDateTime(util.Date(2000, 1, 9))
    assert model.shouldHide(event1) == True
    assert model.shouldHide(event2) == True
    assert model.shouldHide(event3) == True

    model.resetLoggedEndDateTime()
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == False
    assert model.shouldHide(event3) == False


def test_loggedStartDateTime_loggedEndDateTime(model):
    model, event1, event2, event3 = model

    # same as first date
    model.loggedStartDateTime = QDateTime(util.Date(2000, 1, 10))
    # same as last date
    model.loggedEndDateTime = QDateTime(util.Date(2000, 3, 10))
    assert model.shouldHide(event1) == False
    assert model.shouldHide(event2) == False
    assert model.shouldHide(event3) == False

    # after first date
    model.loggedStartDateTime = QDateTime(util.Date(2000, 1, 11))
    # before last date
    model.loggedEndDateTime = QDateTime(util.Date(2000, 3, 9))
    assert model.shouldHide(event1) == True
    assert model.shouldHide(event2) == False
    assert model.shouldHide(event3) == True


def test_ignores_layer_tags(model):
    model, event1, event2, event3 = model

    def num_shown():
        total = 0
        for row in range(scene.timelineModel.rowCount()):
            event = scene.timelineModel.eventForRow(row)
            if not scene.searchModel.shouldHide(event):
                total += 1
        return total

    scene = model.scene
    layer = Layer(name="View 1")
    scene.addItems(layer)
    assert num_shown() == scene.timelineModel.rowCount()

    layer.setActive(True)
    assert num_shown() == scene.timelineModel.rowCount()


@pytest.fixture
def emotion_model():
    scene = Scene()
    personA = Person(name="Person A")
    personB = Person(name="Person B")
    conflict = Emotion(
        personA=personA,
        personB=personB,
        kind=util.ITEM_CONFLICT,
    )
    conflict.startEvent.setDateTime(util.Date(2010, 1, 10))
    conflict.endEvent.setDateTime(util.Date(2010, 2, 10))
    conflict.startEvent.setLoggedDateTime(util.Date(2000, 1, 10))
    conflict.endEvent.setLoggedDateTime(util.Date(2000, 2, 10))
    scene.addItems(personA, personB, conflict)
    scene.searchModel.items = scene
    return scene.searchModel, conflict.startEvent, conflict.endEvent


def test_loggedStartDateTime_emotions(emotion_model):
    model, startEvent, endEvent = emotion_model

    # before first date
    model.loggedStartDateTime = QDateTime(util.Date(2000, 1, 1))
    assert model.shouldHide(startEvent) == False
    assert model.shouldHide(endEvent) == False

    # one day before last date
    model.loggedStartDateTime = QDateTime(util.Date(2000, 2, 9))
    assert model.shouldHide(startEvent) == True
    assert model.shouldHide(endEvent) == False

    # same day as last date
    model.loggedStartDateTime = QDateTime(util.Date(2000, 2, 10))
    assert model.shouldHide(startEvent) == True
    assert model.shouldHide(endEvent) == False

    # one day after last date
    model.loggedStartDateTime = QDateTime(util.Date(2000, 2, 11))
    assert model.shouldHide(startEvent) == True
    assert model.shouldHide(endEvent) == True

    model.resetLoggedStartDateTime()
    assert model.shouldHide(startEvent) == False
    assert model.shouldHide(endEvent) == False


def test_loggedEndDateTime_emotions(emotion_model):
    model, startEvent, endEvent = emotion_model

    # after last date
    model.loggedEndDateTime = QDateTime(util.Date(2000, 2, 12))
    assert model.shouldHide(startEvent) == False
    assert model.shouldHide(endEvent) == False

    # one day after first date
    model.loggedEndDateTime = QDateTime(util.Date(2000, 1, 11))
    assert model.shouldHide(startEvent) == False
    assert model.shouldHide(endEvent) == True

    # same day as first date
    model.loggedEndDateTime = QDateTime(util.Date(2000, 1, 10))
    assert model.shouldHide(startEvent) == False
    assert model.shouldHide(endEvent) == True

    # one day before first date
    model.loggedEndDateTime = QDateTime(util.Date(2000, 1, 9))
    assert model.shouldHide(startEvent) == True
    assert model.shouldHide(endEvent) == True

    model.resetLoggedEndDateTime()
    assert model.shouldHide(startEvent) == False
    assert model.shouldHide(endEvent) == False


def test_category(model):
    model, event1, event2, event3 = model
    scene = model.scene
    inside = scene.query1(type=Person, name="Inside")
    inside_2 = scene.query1(type=Person, name="Inside 2")
    outside = scene.query1(type=Person, name="Outside")
    category = scene.categoriesModel.data(scene.categoriesModel.index(0, 0))
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
