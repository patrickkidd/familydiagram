import pytest

from pkdiagram.pyqt import Qt, QDateTime
from pkdiagram import util, Scene
from pkdiagram.objects import Person, Event, Layer, Emotion, Marriage
from pkdiagram.models import TimelineModel, SearchModel, EmotionalUnitsModel


pytestmark = [
    pytest.mark.component("SearchModel"),
    pytest.mark.depends_on("Scene"),
]


@pytest.fixture
def model():
    scene = Scene()
    person = Person()
    event1 = Event(
        parent=person,
        loggedDateTime=util.Date(2000, 1, 10),
        dateTime=util.Date(1900, 1, 1),
    )
    event2 = Event(
        parent=person,
        loggedDateTime=util.Date(2000, 2, 10),
        dateTime=util.Date(1900, 1, 1),
    )
    event3 = Event(
        parent=person,
        loggedDateTime=util.Date(2000, 3, 10),
        dateTime=util.Date(1900, 1, 1),
    )
    scene.addItem(person)
    searchModel = SearchModel()
    searchModel.scene = scene
    searchModel.items = [person]
    return searchModel, event1, event2, event3


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
    scene = model.scene

    timelineModel = TimelineModel()
    timelineModel.scene = scene
    timelineModel.items = [scene]
    timelineModel.searchModel = model

    def num_shown():
        total = 0
        for row in range(timelineModel.rowCount()):
            event = timelineModel.eventForRow(row)
            if not model.shouldHide(event):
                total += 1
        return total

    scene = model.scene
    layer = Layer(name="View 1")
    scene.addItems(layer)
    assert num_shown() == timelineModel.rowCount()

    layer.setActive(True)
    assert num_shown() == timelineModel.rowCount()


@pytest.fixture
def emotionModel():
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
    searchModel = SearchModel()
    searchModel.scene = scene
    searchModel.items = scene
    return searchModel, conflict.startEvent, conflict.endEvent


def test_loggedStartDateTime_emotions(emotionModel):
    model, startEvent, endEvent = emotionModel

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


def test_loggedEndDateTime_emotions(emotionModel):
    model, startEvent, endEvent = emotionModel

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


def test_layers_mutually_exclusive_emotionalUnits():
    scene = Scene()
    person = Person()
    scene.addItem(person)
    searchModel = SearchModel()
    searchModel.scene = scene
    searchModel.items = [person]
    unitsModel = EmotionalUnitsModel()
    unitsModel.scene = scene
    marriages = [
        Marriage(personA=Person(name=f"A-{i}"), personB=Person(name=f"B-{i}"))
        for i in range(3)
    ]
    for marriage in marriages:
        scene.addItems(marriage, marriage.personA(), marriage.personB())
    layer = Layer(name="Some Layer")
    scene.addItems(layer, *marriages)
    assert set(scene.activeLayers(includeInternal=True)) == set()

    unitsModel.setData(
        unitsModel.index(1, 0), Qt.CheckState.Checked, unitsModel.ActiveRole
    )
    assert set(scene.activeLayers(includeInternal=True)) == {
        marriages[1].emotionalUnit().layer()
    }

    layer.setActive(True)
    assert set(scene.activeLayers(includeInternal=True)) == {layer}


def test_emotionalUnits_mutually_exclusive_layers():
    scene = Scene()
    person = Person()
    scene.addItem(person)
    searchModel = SearchModel()
    searchModel.scene = scene
    searchModel.items = [person]
    unitsModel = EmotionalUnitsModel()
    unitsModel.scene = scene
    marriages = [
        Marriage(personA=Person(name=f"A-{i}"), personB=Person(name=f"B-{i}"))
        for i in range(3)
    ]
    for marriage in marriages:
        scene.addItems(marriage, marriage.personA(), marriage.personB())
    layer = Layer(name="Some Layer")
    scene.addItems(layer, *marriages)
    assert set(scene.activeLayers(includeInternal=True)) == set()

    layer.setActive(True)
    assert set(scene.activeLayers(includeInternal=True)) == {layer}

    unitsModel.setData(
        unitsModel.index(1, 0), Qt.CheckState.Checked, unitsModel.ActiveRole
    )
    assert set(scene.activeLayers(includeInternal=True)) == {
        marriages[1].emotionalUnit().layer()
    }
