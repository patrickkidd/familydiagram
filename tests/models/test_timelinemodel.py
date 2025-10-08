import logging

import pytest

from pkdiagram.pyqt import Qt, QDateTime, QItemSelectionModel
from pkdiagram import util
from pkdiagram.scene import (
    Scene,
    Person,
    Marriage,
    Event,
    Emotion,
    EventKind,
    Marriage,
    RelationshipKind,
    ItemMode,
)
from pkdiagram.models import SearchModel, TimelineModel


pytestmark = pytest.mark.component("TimelineModel")

_log = logging.getLogger(__name__)


@pytest.fixture
def timelineScene(simpleScene):
    p1 = simpleScene.query1(name="p1")
    p2 = simpleScene.query1(name="p2")
    p1.setBirthDateTime(util.Date(1955, 12, 3))
    p2.setBirthDateTime(util.Date(1980, 5, 11))
    p1.birthEvent.setTags(["hello"])
    return simpleScene


@pytest.fixture
def model(timelineScene):
    _model = TimelineModel()
    _model.scene = timelineScene
    _model.items = [timelineScene]
    return _model


def test_internals(model):
    assert model.rowCount() == 2
    event = Event(dateTime=util.Date(2012, 1, 1))
    model._ensureEvent(event)
    assert model.rowForEvent(event) == 2


def test_init_deinit(timelineScene, model):
    p1 = timelineScene.query1(name="p1")
    p2 = timelineScene.query1(name="p2")
    assert model.rowCount() == 2
    assert model.eventForRow(0) == p1.birthEvent
    assert model.eventForRow(1) == p2.birthEvent
    # date
    col = model.columnIndex(model.DATETIME)
    assert model.index(0, col).data(Qt.DisplayRole) == util.dateString(
        p1.birthDateTime()
    )
    assert model.index(1, col).data(Qt.DisplayRole) == util.dateString(
        p2.birthDateTime()
    )
    # unsure
    col = model.columnIndex(model.UNSURE)
    assert model.index(0, col).data(Qt.DisplayRole) == True
    assert model.index(1, col).data(Qt.DisplayRole) == True
    # description
    col = model.columnIndex(model.DESCRIPTION)
    assert model.index(0, col).data(Qt.DisplayRole) == p1.birthEvent.description()
    assert model.index(1, col).data(Qt.DisplayRole) == p2.birthEvent.description()
    # parent
    col = model.columnIndex(model.PARENT)
    assert model.index(0, col).data(Qt.DisplayRole) == p1.name()
    assert model.index(1, col).data(Qt.DisplayRole) == p2.name()
    # logged
    col = model.columnIndex(model.LOGGED)
    assert model.index(0, col).data(Qt.DisplayRole) == util.dateString(
        QDateTime.currentDateTime()
    )
    assert model.index(1, col).data(Qt.DisplayRole) == util.dateString(
        QDateTime.currentDateTime()
    )

    # qtmodeltester.check(model)


def test_shouldHide():
    scene = Scene()
    model = TimelineModel()
    model.scene = scene
    model.searchModel = SearchModel()
    model.searchModel.scene = scene
    assert model._shouldHide(Event(dateTime=util.Date(2000, 1, 1))) == False
    assert model._shouldHide(Event()) == True

    model.searchModel.tags = ["here"]
    assert model._shouldHide(Event(dateTime=util.Date(2000, 1, 1))) == True
    assert (
        model._shouldHide(Event(dateTime=util.Date(2000, 1, 1), tags=["here"])) == False
    )

    model.searchModel.tags = []
    model.searchModel.description = "there"
    assert model._shouldHide(Event(dateTime=util.Date(2000, 1, 1))) == True
    assert (
        model._shouldHide(Event(dateTime=util.Date(2000, 1, 1), tags=["here"])) == True
    )
    assert (
        model._shouldHide(
            Event(dateTime=util.Date(2000, 1, 1), description=["therefore"])
        )
        == False
    )


def test_set_searchModel():
    scene = Scene()
    personA, personB, personC = Person(), Person(), Person()
    personA.setBirthDateTime(util.Date(2000, 1, 1))
    personB.setBirthDateTime(util.Date(2001, 1, 1))
    eventA = Event(
        parent=personA,
        description="PersonA something",
        dateTime=util.Date(2002, 1, 1),
        tags=["here"],
    )
    eventB = Event(
        parent=personB,
        description="PersonB something",
        dateTime=util.Date(2003, 1, 1),
        tags=["there"],
    )
    eventB2 = Event(
        parent=personB,
        description="PersonB something 2",
        dateTime=util.Date(2004, 1, 1),
        tags=["there"],
    )
    scene.addItems(personA, personB, personC)

    model = TimelineModel()
    model.scene = scene

    searchModel_1 = SearchModel()
    searchModel_1.tags = ["here"]
    searchModel_1.scene = scene
    model.searchModel = searchModel_1
    assert model.rowCount() == 1

    searchModel_2 = SearchModel()
    searchModel_2.tags = ["there"]
    searchModel_2.scene = scene
    model.searchModel = searchModel_2
    assert model.rowCount() == 2


def test_init_multiple_people():

    scene = Scene()
    personA, personB, personC = Person(), Person(), Person()
    birthEventA = scene.addItem(Event(personA, dateTime=util.Date(2000, 1, 1)))
    birthEventB = scene.addItem(Event(personB, dateTime=util.Date(2001, 1, 1)))
    eventA = Event(
        personA, description="PersonA something", dateTime=util.Date(2002, 1, 1)
    )
    eventB = Event(
        personB, description="PersonB something", dateTime=util.Date(2003, 1, 1)
    )
    # Add two emotions where only one person's end should should in the timeline
    distance = Event(
        kind=EventKind.Shift,
        person=personA,
        relationship=RelationshipKind.Distance,
        relationshipTargets=personC,
        dateTime=util.Date(2004, 1, 1),
        endDateTime=util.Date(2005, 1, 1),
    )
    conflict = Event(
        kind=EventKind.Shift,
        person=personB,
        relationship=RelationshipKind.Conflict,
        relationshipTargets=personC,
        dateTime=util.Date(2006, 1, 1),
        endDateTime=util.Date(2007, 1, 1),
    )
    # add one emotion where both ends should be shown but without duplicates.
    fusion = Event(
        kind=EventKind.Shift,
        person=personA,
        relationship=RelationshipKind.Fusion,
        relationshipTargets=personB,
        dateTime=util.Date(2008, 1, 1),
        endDateTime=util.Date(2009, 1, 1),
    )
    scene.addItems(personA, personB, personC, distance, conflict, fusion)
    model = TimelineModel()
    model.scene = scene

    assert model.rowCount() == 10
    assert model.data(model.index(0, 0), model.DateTimeRole) == birthEventA.dateTime()
    assert model.data(model.index(1, 0), model.DateTimeRole) == birthEventB.dateTime()
    assert model.data(model.index(2, 0), model.DateTimeRole) == eventA.dateTime()
    assert model.data(model.index(3, 0), model.DateTimeRole) == eventB.dateTime()
    assert model.data(model.index(4, 0), model.DateTimeRole) == distance.dateTime()
    assert model.data(model.index(5, 0), model.DateTimeRole) == distance.endDateTime()
    assert model.data(model.index(6, 0), model.DateTimeRole) == conflict.dateTime()
    assert model.data(model.index(7, 0), model.DateTimeRole) == conflict.endDateTime()
    assert model.data(model.index(8, 0), model.DateTimeRole) == fusion.dateTime()
    assert model.data(model.index(9, 0), model.DateTimeRole) == fusion.endDateTime()


def test_access_data_after_deinit():
    scene = Scene()
    model = TimelineModel()
    model.scene = scene
    personA, personB = Person(name="A"), Person(name="B")
    pairBond = Marriage(personA=personA, personB=personB)
    Event(parent=pairBond, description="Married", dateTime=util.Date(2000, 1, 1))
    scene.addItems(personA, personB, pairBond)
    assert model.rowCount() == 1
    model.scene = None
    assert model.rowCount() == 0
    model.data(model.index(0, 1), model.FlagsRole)


def test_flags(timelineScene, model):
    p1 = timelineScene.query1(name="p1")
    p2 = timelineScene.query1(name="p2")

    timelineScene.addItem(
        Event(
            kind=ItemMode.Fusion,
            event=Event(
                dateTime=util.Date(1980, 5, 11), endDateTime=util.Date(2015, 1, 1)
            ),
            person=p1,
            targate=p2,
        )
    )

    for row in range(model.rowCount()):
        iBuddies = model.columnIndex(model.BUDDIES)
        iDate = model.columnIndex(model.DATETIME)
        iDescription = model.columnIndex(model.DESCRIPTION)
        iLocation = model.columnIndex(model.LOCATION)
        iParent = model.columnIndex(model.PARENT)
        iLogged = model.columnIndex(model.LOGGED)
        assert not model.flags(model.index(row, iBuddies)) & Qt.ItemIsEditable
        assert model.flags(model.index(row, iDate)) & Qt.ItemIsEditable
        assert not model.flags(model.index(row, iDescription)) & Qt.ItemIsEditable
        assert model.flags(model.index(row, iLocation)) & Qt.ItemIsEditable
        assert not model.flags(model.index(row, iParent)) & Qt.ItemIsEditable
        assert not model.flags(model.index(row, iLogged)) & Qt.ItemIsEditable


def test_add_item(timelineScene, model):
    p1 = timelineScene.query1(name="p1")
    p2 = timelineScene.query1(name="p2")

    fusion = timelineScene.addItem(
        Event(
            kind=EventKind.Shift,
            relationship=RelationshipKind.Fusion,
            dateTime=util.Date(1980, 1, 11),
            endDateTime=util.Date(2015, 1, 1),
            person=p1,
            target=p2,
        )
    )
    #
    assert model.rowCount() == 4
    #
    assert model.eventForRow(0) == p1.birthEvent  # birthDateTime
    assert model.eventForRow(1) == p2.birthEvent  # birthDateTime
    assert model.eventForRow(2) == fusion.startEvent  # startDateTime
    assert model.eventForRow(3) == fusion.endEvent  # endDateTime
    # fusion dates
    col = model.columnIndex(model.DATETIME)
    assert model.index(2, col).data(Qt.DisplayRole) == util.dateString(
        fusion.dateTime()
    )
    assert model.index(3, col).data(Qt.DisplayRole) == util.dateString(
        fusion.endDateTime()
    )


def test_add_person_marriage():
    scene = Scene()
    personA = Person(name="A")
    personB = Person(name="B")
    scene.addItems(personA, personB)
    model = TimelineModel()
    model.scene = scene
    model.items = [personA]

    marriage = Marriage(personA=personA, personB=personB)
    married = Event(parent=marriage, date=util.Date(2001, 1, 1), kind=EventKind.Married)
    scene.addItem(marriage)

    assert model.rowForEvent(married) != None


def test_remove_item(timelineScene, model):
    assert model.rowCount() == 2

    p2 = timelineScene.query1(name="p2")
    timelineScene.removeItem(p2)
    assert model.rowCount() == 1


def test_set_birthdate(timelineScene, model):
    p1 = timelineScene.query1(name="p1")
    p1.birthEvent.prop("dateTime").reset()

    assert model.rowCount() == 1

    p1.setBirthDateTime(util.Date(1955, 12, 3))
    assert model.rowCount() == 2


def test_unset_birthDate(timelineScene, model):
    # should remove from rows
    p1 = timelineScene.query1(name="p1")
    p1.setBirthDateTime(util.Date(1955, 12, 3))
    assert model.rowCount() == 2

    p1.birthEvent.prop("dateTime").reset()
    assert model.rowCount() == 1


def test_delete_birthDate(qtbot, timelineScene, model):
    # should clear date
    p1 = timelineScene.query1(name="p1")
    p1.setBirthDateTime(util.Date(1955, 12, 3))
    assert model.rowCount() == 2

    selectionModel = QItemSelectionModel(model)
    selectionModel.select(
        model.index(0, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows
    )
    qtbot.clickYesAfter(lambda: model.removeSelection(selectionModel))
    assert model.rowCount() == 1


def test_delete_emotion_date(qtbot, timelineScene: Scene, model: TimelineModel):
    # should clear date
    p1 = timelineScene.query1(name="p1")
    p2 = timelineScene.query1(name="p2")
    conflict = Event(
        kind=EventKind.Shift,
        person=p1,
        relationship=RelationshipKind.Conflict,
        relationshipTargets=p2,
        dateTime=util.Date(2000, 1, 1),
        endDateTime=util.Date(2001, 1, 1),
    )
    timelineScene.addItem(conflict)
    endRow = model.endEventForEvent(conflict)
    assert model.rowCount() == 4

    selectionModel = QItemSelectionModel(model)
    selectionModel.select(
        model.index(3, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows
    )
    qtbot.clickYesAfter(lambda: model.removeSelection(selectionModel))
    assert model.rowCount() == 3
    assert conflict.dateTime() == None
    assert model.endRowForEvent(conflict) == endRow

    selectionModel.select(
        model.index(2, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows
    )
    qtbot.clickYesAfter(lambda: model.removeSelection(selectionModel))
    assert model.rowCount() == 2
    assert conflict.dateTime() == None
    assert conflict in timelineScene.events()


@pytest.mark.skip(
    reason="Unsure how to consider Person.deceased from TimelineModel._ensureEvent()."
)
def test_dont_show_not_deceased_with_deceased_date():
    scene = Scene()
    model = TimelineModel()
    model.scene = scene
    person = Person()
    # set deceased date but not `deceased`
    person.setDeceasedDateTime(util.Date(2000, 1, 1))
    scene.addItem(person)
    assert model.rowCount() == 1


## TODO: test consistency of internal data structures (perhaps using accecssors methods?)


# def test_set_date_resort(model):
#     midRow = model.rowCount() / 2
#     dateTimeForRow, item = model.entryForRow(midRow)
#     index = model.index(midRow, model.columnIndex(model.DATETIME))
#     dateTime = model.data(index, model.DateTimeRole)
#     assert dateTime == dateTimeForRow

#     newDateTime = dateTime.addDays(-365)
#     model.setData(index, newDateTime)
#     newDateTimeForRow, newItem = model.entryForRow(midRow)
#     assert model.rowForEvent(newDateTimeForRow, newItem) ==


def test_set_datetime():
    scene = Scene()
    model = TimelineModel()
    model.scene = scene
    person = scene.addItem(Person(name="Person A"))
    birthEvent = scene.addItem(Event(person=person, dateTime=util.Date(2000, 1, 1)))
    scene.addItems(person)
    model.setData(
        model.index(0, model.columnIndex(model.DATETIME)),
        "10/02/2002 12:35pm",
        role=model.DisplayExpandedRole,
    )
    assert birthEvent.dateTime() == util.Date(2002, 10, 2, 12, 35, 0)


@pytest.mark.parametrize("role", [Qt.DisplayRole, Qt.EditRole])
def test_set_date_retains_time(role):
    scene = Scene()
    model = TimelineModel()
    model.scene = scene
    person = scene.addItem(Person(name="Person A"))
    birthEvent = scene.addItem(Event(dateTime=util.Date(2000, 1, 1, 12, 35, 0)))
    scene.addItems(person)
    model.setData(
        model.index(0, model.columnIndex(model.DATETIME)), "4/5/2003", role=role
    )
    assert birthEvent.dateTime() == util.Date(2003, 4, 5, 12, 35, 0)


def test_set_emotion_date():

    scene = Scene()
    model = TimelineModel()
    model.scene = scene

    p1 = Person()
    p2 = Person()
    scene.addItems(p1, p2)
    fusion = Event(
        kind=EventKind.Shift,
        person=p1,
        relationship=RelationshipKind.Fusion,
        relationshipTarget=p2,
        dateTime=util.Date(1990, 1, 11),
        endDateTime=util.Date(1992, 1, 1),
    )
    scene.addItem(fusion)
    endEvent = model.endEventForEvent(fusion)
    assert model.rowForEvent(fusion) == 0
    assert model.rowForEvent(endEvent) == 1

    iDate = model.columnIndex(model.DATETIME)
    rowsRemoved = util.Condition(model.rowsRemoved)
    rowsInserted = util.Condition(model.rowsInserted)
    model.setData(model.index(0, iDate), "1/1/1991")
    assert fusion.dateTime() == util.Date(1991, 1, 1)
    assert fusion.endDateTime() == util.Date(1992, 1, 1)
    assert rowsRemoved.callCount == 1
    assert rowsRemoved.callArgs[0][1] == 0
    assert rowsRemoved.callArgs[0][2] == 0
    assert rowsInserted.callCount == 1
    assert rowsInserted.callArgs[0][1] == 0
    assert rowsInserted.callArgs[0][2] == 0
    assert model.data(model.index(0, iDate)) == "01/01/1991"
    assert model.data(model.index(1, iDate)) == "01/01/1992"
    assert model.data(model.index(0, iDate), model.DateTimeRole) == util.Date(
        1991, 1, 1
    )
    assert model.data(model.index(1, iDate), model.DateTimeRole) == util.Date(
        1992, 1, 1
    )


def test_emotion_move_has_only_one_event(scene):
    model = TimelineModel()
    model.scene = scene
    p1 = Person()
    p2 = Person()
    fusion = Event(
        kind=EventKind.Shift,
        dateTime=util.Date(1980, 1, 11),
        person=p1,
        relationship=RelationshipKind.Fusion,
        relationshipTargets=p2,
    )
    scene.addItems(p1, p2, fusion)
    assert model.rowCount() == 1
    assert model.index(0, 0).data(model.DateTimeRole) == fusion.dateTime()


def test_emotion_date_changed(scene):

    model = TimelineModel()
    model.scene = scene
    p1 = Person()
    p2 = Person()
    fusion = Event(
        kind=EventKind.Shift,
        person=p1,
        relationshipTargets=p2,
        relationship=RelationshipKind.Fusion,
    )
    scene.addItems(p1, p2, fusion)

    dateTime = util.Date(1980, 1, 11)

    iDate = model.columnIndex(model.DATETIME)
    rowsRemoved = util.Condition(model.rowsRemoved)
    rowsInserted = util.Condition(model.rowsInserted)
    fusion.setDateTime(dateTime)
    assert rowsRemoved.callCount == 0
    assert rowsInserted.callCount == 1
    assert rowsInserted.callArgs[0][1] == 0
    assert rowsInserted.callArgs[0][2] == 0
    assert model.data(model.index(0, iDate)) == util.dateString(dateTime)
    assert model.data(model.index(0, iDate), model.DateTimeRole) == dateTime


def test_dateBuddies(timelineScene, model):
    p1 = timelineScene.query1(name="p1")
    p2 = timelineScene.query1(name="p2")

    fusion = Event(
        kind=EventKind.Shift,
        person=p1,
        relationship=RelationshipKind.Fusion,
        relationshipTargets=p2,
        dateTime=util.Date(1981, 5, 11),
        endDateTime=util.Date(2015, 1, 1),
    )
    timelineScene.addItem(fusion)
    endEvent = timelineScene.endEventForEvent(fusion)

    assert model.firstRowForDateTime(fusion.dateTime()) == 2
    assert model.rowForEvent(fusion) == 2
    assert model.firstRowForDateTime(endEvent.dateTime()) == 3

    startDateRow = model.rowForEvent(fusion)
    endDateRow = model.rowForEvent(endEvent)
    assert startDateRow == 2
    assert endDateRow == 3

    startDateBuddy = model.dateBuddyForRow(startDateRow)
    endDateBuddy = model.dateBuddyForRow(endDateRow)
    assert startDateBuddy == endDateRow
    assert endDateBuddy == startDateRow

    dateBuddies = model.dateBuddiesInternal()
    assert len(dateBuddies) == 1
    row1, row2, item = dateBuddies[0]
    assert row1 == 2
    assert row2 == 3
    assert item == fusion


# def test_dateBuddies_sameDate(timelineScene, model):
#     p1 = timelineScene.query1(name="p1")
#     p2 = timelineScene.query1(name="p2")

#     fusion = Emotion(kind=util.ITEM_FUSION)
#     fusion.setPersonA(p1)
#     fusion.setPersonB(p2)
#     fusion.startEvent.setDateTime(util.Date(1980, 5, 11))
#     fusion.endEvent.setDateTime(util.Date(1980, 5, 12))
#     timelineScene.addItem(fusion)

#     assert model.firstRowForDateTime(fusion.startDateTime()) == 1
#     assert model.rowForEvent(fusion.startEvent) == 2
#     assert model.lastRowForDateTime(fusion.endEvent.dateTime()) == 3

#     startDateRow = model.rowForEvent(fusion.startEvent)
#     endDateRow = model.rowForEvent(fusion.endEvent)
#     assert startDateRow == 2
#     assert endDateRow == 3

#     startDateBuddyRow = model.dateBuddyForRow(startDateRow)
#     endDateBuddyRow = model.dateBuddyForRow(endDateRow)
#     assert startDateBuddyRow == endDateRow
#     assert endDateBuddyRow == startDateRow

#     dateBuddies = model.dateBuddiesInternal()
#     assert len(dateBuddies) == 1
#     row1, row2, item = dateBuddies[0]
#     assert row1 == 2
#     assert row2 == 3
#     assert item == fusion


def test_emotion_parentName_changed():
    scene = Scene()
    model = TimelineModel()
    model.scene = scene
    p1 = Person(name="p1")
    p2 = Person(name="p2")
    fusion = Event(
        kind=EventKind.Shift,
        person=p1,
        relationship=RelationshipKind.Fusion,
        relationshipTargets=p2,
        dateTime=util.Date(1980, 5, 11),
        endDateTime=util.Date(1980, 5, 12),
    )
    scene.addItems(p1, p2, fusion)
    endEvent = model.endEventForEvent(fusion)
    # util.printModel(model)
    assert model.rowCount() == 2  # startDateTime, endDateTime
    assert model.rowForEvent(fusion) == 0
    assert model.rowForEvent(endEvent) == 1
    assert model.data(model.index(0, model.COLUMNS.index(model.PARENT))) == "p1 & p2"

    dataChanged = util.Condition()
    model.dataChanged.connect(dataChanged)
    p1.setName("Bleh")
    assert dataChanged.callCount == 2
    assert dataChanged.callArgs[0][0].row() == 0
    assert dataChanged.callArgs[1][0].row() == 1
    assert dataChanged.callArgs[0][0].column() == model.COLUMNS.index(model.PARENT)
    assert dataChanged.callArgs[1][0].column() == model.COLUMNS.index(model.PARENT)
    assert model.data(model.index(0, model.COLUMNS.index(model.PARENT))) == "Bleh & p2"
    assert model.data(model.index(1, model.COLUMNS.index(model.PARENT))) == "Bleh & p2"


def test_rows_for_date():
    # Add an emotion start and arbitrary event on the same date, emotion end on another
    scene = Scene()
    model = TimelineModel()
    model.scene = scene
    p1 = Person(name="p1")
    event1 = Event(person=p1, dateTime=util.Date(1900, 1, 2))
    event2 = Event(person=p1, dateTime=util.Date(1910, 1, 2))
    event3 = Event(person=p1, dateTime=util.Date(1910, 1, 2))
    event4 = Event(person=p1, dateTime=util.Date(1910, 1, 2))
    event5 = Event(person=p1, dateTime=util.Date(1920, 1, 2))
    scene.addItems(p1)

    dateTime = util.Date(1899, 1, 2)
    assert model.firstRowForDateTime(dateTime) == -1
    assert model.lastRowForDateTime(dateTime) == -1
    assert model.dateBetweenRow(dateTime) == 0

    dateTime = util.Date(1900, 1, 2)
    assert model.firstRowForDateTime(dateTime) == 0
    assert model.lastRowForDateTime(dateTime) == 0
    assert model.dateBetweenRow(dateTime) == -1

    dateTime = util.Date(1910, 1, 2)
    assert model.firstRowForDateTime(dateTime) == 1
    assert model.lastRowForDateTime(dateTime) == 3
    assert model.dateBetweenRow(dateTime) == -1

    dateTime = util.Date(1915, 1, 2)  # random date between rows
    assert model.firstRowForDateTime(dateTime) == -1
    assert model.lastRowForDateTime(dateTime) == -1
    assert model.dateBetweenRow(dateTime) == 3

    dateTime = util.Date(1920, 1, 2)
    assert model.firstRowForDateTime(dateTime) == 4
    assert model.lastRowForDateTime(dateTime) == 4
    assert model.dateBetweenRow(dateTime) == -1

    dateTime = util.Date(1930, 1, 2)  # after last shown row
    assert model.firstRowForDateTime(dateTime) == -1
    assert model.lastRowForDateTime(dateTime) == -1
    assert model.dateBetweenRow(dateTime) == 4


def test_rows_for_date_search():
    # Add an emotion start and arbitrary event on the same date, emotion end on another
    scene = Scene()
    model = TimelineModel()
    model.scene = scene
    model.searchModel = SearchModel()
    model.searchModel.scene = scene
    p1 = Person(name="p1")
    event1 = Event(person=p1, dateTime=util.Date(1900, 1, 2))
    event2 = Event(person=p1, dateTime=util.Date(1910, 1, 2), tags=["bleh"])  # 0
    event3 = Event(person=p1, dateTime=util.Date(1910, 1, 2))
    event4 = Event(person=p1, dateTime=util.Date(1910, 1, 2), tags=["bleh"])  # 1
    event5 = Event(person=p1, dateTime=util.Date(1920, 1, 2), tags=["bleh"])  # 2
    scene.addItems(p1)

    model.searchModel.tags = ["bleh"]

    dateTime = util.Date(1899, 1, 2)  # before first date
    assert model.firstRowForDateTime(dateTime) == -1
    assert model.lastRowForDateTime(dateTime) == -1
    assert model.dateBetweenRow(dateTime) == 0

    dateTime = util.Date(1900, 1, 2)  # first date, before first shown date
    assert model.firstRowForDateTime(dateTime) == -1
    assert model.lastRowForDateTime(dateTime) == -1
    assert model.dateBetweenRow(dateTime) == 0

    dateTime = util.Date(1910, 1, 2)  # first shown date, also multiple rows
    assert model.firstRowForDateTime(dateTime) == 0
    assert model.lastRowForDateTime(dateTime) == 1
    assert model.dateBetweenRow(dateTime) == -1

    dateTime = util.Date(1915, 1, 2)  # random date between shown rows
    assert model.firstRowForDateTime(dateTime) == -1
    assert model.lastRowForDateTime(dateTime) == -1
    assert model.dateBetweenRow(dateTime) == 1

    dateTime = util.Date(1920, 1, 2)  # last shown row
    assert model.firstRowForDateTime(dateTime) == 2
    assert model.lastRowForDateTime(dateTime) == 2
    assert model.dateBetweenRow(dateTime) == -1

    dateTime = util.Date(1930, 1, 2)  # after last shown row
    assert model.firstRowForDateTime(dateTime) == -1
    assert model.lastRowForDateTime(dateTime) == -1
    assert model.dateBetweenRow(dateTime) == 2


def test_showAliases_signals(scene: Scene):
    model = TimelineModel()
    model.scene = scene
    patrick = Person(name="Patrick", alias="Marco", notes="Patrick Bob")
    bob = Person(name="Bob", nickName="Robby", alias="John")
    e1 = Event(
        person=patrick, dateTime=util.Date(1900, 1, 1), description="Bob came home"
    )
    e2 = Event(
        person=patrick,
        dateTime=util.Date(1900, 1, 2),
        description="robby came home, took Robby's place",
    )
    e3 = Event(
        person=bob,
        dateTime=util.Date(1900, 1, 3),
        description="Patrick came home with bob",
    )
    distance = Event(
        kind=EventKind.Shift,
        relationship=RelationshipKind.Distance,
        dateTime=util.Date(1900, 1, 4),
        endDateTime=util.Date(1900, 1, 5),
        person=patrick,
        relationshipTargets=bob,
    )
    marriage = Marriage(personA=patrick, personB=bob)
    married = Event(
        kind=EventKind.Married,
        dateTime=util.Date(1900, 1, 5),
        person=patrick,
        spouse=bob,
    )
    scene.addItems(patrick, bob, distance, marriage)
    newValues = {}

    def namesAndDescriptions(fromIndex, toIndex, roles):
        if not fromIndex.row() in newValues:
            newValues[fromIndex.row()] = {}
        newValues[fromIndex.row()][fromIndex.column()] = fromIndex.data()
        if fromIndex.column() in (
            TimelineModel.COLUMNS.index(TimelineModel.DESCRIPTION),
            TimelineModel.COLUMNS.index(TimelineModel.PARENT),
        ):
            x = fromIndex.data()
            return True
        else:
            return False

    dataChanged = util.Condition(only=namesAndDescriptions)
    model.dataChanged.connect(dataChanged)

    assert e1.description() == "Bob came home"
    assert model.index(0, 3).data() == "Bob came home"
    assert model.index(0, 5).data() == "Patrick"

    assert e2.description() == "robby came home, took Robby's place"
    assert model.index(1, 3).data() == "robby came home, took Robby's place"
    assert model.index(1, 5).data() == "Patrick"

    assert e3.description() == "Patrick came home with bob"
    assert model.index(2, 3).data() == "Patrick came home with bob"
    assert model.index(2, 5).data() == "Bob"

    assert distance.personName() == "Patrick & Bob"
    assert model.index(3, 3).data() == "Distance began"
    assert model.index(3, 5).data() == "Patrick & Bob"
    assert model.index(4, 3).data() == "Distance ended"
    assert model.index(4, 5).data() == "Patrick & Bob"

    assert married.personName() == "Patrick & Bob"
    assert model.index(5, 5).data() == "Patrick & Bob"

    util.runModel(model, silent=True)
    scene.setShowAliases(True)
    assert dataChanged.callCount == 13

    assert e1.description() == "[John] came home"
    assert newValues[0][3] == "[John] came home"
    assert newValues[0][5] == "[Marco]"

    assert e2.description() == "[John] came home, took [John]'s place"
    assert newValues[1][3] == "[John] came home, took [John]'s place"
    assert newValues[1][5] == "[Marco]"

    assert e3.description() == "[Marco] came home with [John]"
    assert newValues[2][3] == "[Marco] came home with [John]"
    assert newValues[2][5] == "[John]"

    assert distance.parentName() == "[Marco] & [John]"
    assert newValues[3][5] == "[Marco] & [John]"
    assert newValues[4][5] == "[Marco] & [John]"

    assert married.parentName() == "[Marco] & [John]"
    assert model.index(5, 5).data() == "[Marco] & [John]"


def test_get_all_variables():
    scene = Scene()
    scene.addEventProperty("anxiety")
    person = Person(name="Person A")
    person.birthEvent.setDateTime(util.Date(2000, 1, 1))
    scene.addItem(person)
    prop = person.birthEvent.dynamicProperty("anxiety")
    prop.set("up")
    # for i in range(model.rowCount()):
    #     for j in range(model.columnCount()):
    #         Debug(i, j, model.data(model.index(i, j)))
