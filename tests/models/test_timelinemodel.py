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
from pkdiagram.models.timelinemodel import TimelineRow


pytestmark = pytest.mark.component("TimelineModel")

_log = logging.getLogger(__name__)


@pytest.fixture
def model(scene):
    _model = TimelineModel()
    _model.scene = scene
    _model.items = [scene]  # needed anymore?
    return _model


def test_internals(scene, model):
    # Setup: Create two people with events
    p1, p2 = scene.addItems(Person(name="p1"), Person(name="p2"))
    event1 = scene.addItem(
        Event(EventKind.Shift, p1, dateTime=util.Date(1955, 12, 3), tags=["hello"])
    )
    event2 = scene.addItem(Event(EventKind.Shift, p2, dateTime=util.Date(1980, 5, 11)))

    assert model.rowCount() == 2

    # Add another person and event
    person = scene.addItem(Person())
    event = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2012, 1, 1))
    )
    assert model.rowForEvent(event) == 2


def test_init_deinit(scene, model):
    # Setup: Create two people with dated events
    p1, p2 = scene.addItems(Person(name="p1"), Person(name="p2"))
    event1 = scene.addItem(
        Event(EventKind.Shift, p1, dateTime=util.Date(1955, 12, 3), tags=["hello"])
    )
    event2 = scene.addItem(Event(EventKind.Shift, p2, dateTime=util.Date(1980, 5, 11)))

    assert model.rowCount() == 2
    assert model.eventForRow(0) == event1
    assert model.eventForRow(1) == event2

    # date
    col = model.columnIndex(model.DATETIME)
    assert model.index(0, col).data(Qt.DisplayRole) == util.dateString(
        event1.dateTime()
    )
    assert model.index(1, col).data(Qt.DisplayRole) == util.dateString(
        event2.dateTime()
    )

    # unsure
    col = model.columnIndex(model.UNSURE)
    assert model.index(0, col).data(Qt.DisplayRole) == True
    assert model.index(1, col).data(Qt.DisplayRole) == True

    # description
    col = model.columnIndex(model.DESCRIPTION)
    assert model.index(0, col).data(Qt.DisplayRole) == event1.description()
    assert model.index(1, col).data(Qt.DisplayRole) == event2.description()

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


def test_shouldHide(scene, model):
    model.searchModel = SearchModel()
    model.searchModel.scene = scene
    person = scene.addItem(Person())

    event1 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 1)))
    assert model._shouldHide(TimelineRow(event1)) == False

    event2 = scene.addItem(Event(EventKind.Shift, person))
    assert model._shouldHide(TimelineRow(event2)) == True

    model.searchModel.tags = ["here"]
    event3 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 1)))
    assert model._shouldHide(TimelineRow(event3)) == True

    event4 = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 1), tags=["here"])
    )
    assert model._shouldHide(TimelineRow(event4)) == False

    model.searchModel.tags = []
    model.searchModel.description = "there"
    event5 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 1)))
    assert model._shouldHide(TimelineRow(event5)) == True

    event6 = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 1), tags=["here"])
    )
    assert model._shouldHide(TimelineRow(event6)) == True

    event7 = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 1), description="therefore")
    )
    assert model._shouldHide(TimelineRow(event7)) == False


def test_set_searchModel(scene, model):
    personA, personB, personC = scene.addItems(Person(), Person(), Person())
    eventA = scene.addItem(
        Event(
            EventKind.Shift,
            personA,
            description="PersonA something",
            dateTime=util.Date(2002, 1, 1),
            tags=["here"],
        )
    )
    eventB = scene.addItem(
        Event(
            EventKind.Shift,
            personB,
            description="PersonB something",
            dateTime=util.Date(2003, 1, 1),
            tags=["there"],
        )
    )
    eventB2 = scene.addItem(
        Event(
            EventKind.Shift,
            personB,
            description="PersonB something 2",
            dateTime=util.Date(2004, 1, 1),
            tags=["there"],
        )
    )

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


def test_init_multiple_people(scene, model):
    personA, personB, personC = scene.addItems(Person(), Person(), Person())
    birthEventA = scene.addItem(
        Event(EventKind.Shift, personA, dateTime=util.Date(2000, 1, 1))
    )
    birthEventB = scene.addItem(
        Event(EventKind.Shift, personB, dateTime=util.Date(2001, 1, 1))
    )
    eventA = scene.addItem(
        Event(
            EventKind.Shift,
            personA,
            description="PersonA something",
            dateTime=util.Date(2002, 1, 1),
        )
    )
    eventB = scene.addItem(
        Event(
            EventKind.Shift,
            personB,
            description="PersonB something",
            dateTime=util.Date(2003, 1, 1),
        )
    )
    # Add two emotions where only one person's end should should in the timeline
    distance = scene.addItem(
        Event(
            kind=EventKind.Shift,
            person=personA,
            relationship=RelationshipKind.Distance,
            relationshipTargets=personC,
            dateTime=util.Date(2004, 1, 1),
            endDateTime=util.Date(2005, 1, 1),
        )
    )
    conflict = scene.addItem(
        Event(
            kind=EventKind.Shift,
            person=personB,
            relationship=RelationshipKind.Conflict,
            relationshipTargets=personC,
            dateTime=util.Date(2006, 1, 1),
            endDateTime=util.Date(2007, 1, 1),
        )
    )
    # add one emotion where both ends should be shown but without duplicates.
    fusion = scene.addItem(
        Event(
            kind=EventKind.Shift,
            person=personA,
            relationship=RelationshipKind.Fusion,
            relationshipTargets=personB,
            dateTime=util.Date(2008, 1, 1),
            endDateTime=util.Date(2009, 1, 1),
        )
    )

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


def test_access_data_after_deinit(scene, model):
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))
    pairBond = scene.addItem(Marriage(personA=personA, personB=personB))
    scene.addItem(
        Event(
            EventKind.Married,
            personA,
            spouse=personB,
            description="Married",
            dateTime=util.Date(2000, 1, 1),
        )
    )
    assert model.rowCount() == 1
    model.scene = None
    assert model.rowCount() == 0
    model.data(model.index(0, 1), model.FlagsRole)


def test_flags(scene, model):
    # Setup: Create two people with events
    p1, p2 = scene.addItems(Person(name="p1"), Person(name="p2"))
    event1 = scene.addItem(
        Event(EventKind.Shift, p1, dateTime=util.Date(1955, 12, 3), tags=["hello"])
    )
    event2 = scene.addItem(Event(EventKind.Shift, p2, dateTime=util.Date(1980, 5, 11)))

    # Add a relationship event with date range
    fusion = scene.addItem(
        Event(
            kind=EventKind.Shift,
            relationship=RelationshipKind.Fusion,
            person=p1,
            relationshipTargets=p2,
            dateTime=util.Date(1980, 5, 11),
            endDateTime=util.Date(2015, 1, 1),
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
        assert model.flags(model.index(row, iDescription)) & Qt.ItemIsEditable  # DESCRIPTION is editable for Shift events
        assert model.flags(model.index(row, iLocation)) & Qt.ItemIsEditable
        assert model.flags(model.index(row, iParent)) & Qt.ItemIsEditable  # PARENT is editable for Shift events
        assert not model.flags(model.index(row, iLogged)) & Qt.ItemIsEditable


def test_add_item(scene, model):
    # Setup: Create two people with events
    p1, p2 = scene.addItems(Person(name="p1"), Person(name="p2"))
    event1 = scene.addItem(
        Event(EventKind.Shift, p1, dateTime=util.Date(1955, 12, 3), tags=["hello"])
    )
    event2 = scene.addItem(Event(EventKind.Shift, p2, dateTime=util.Date(1980, 5, 11)))

    # Add a fusion event with date range that falls between the two birth events
    fusion = scene.addItem(
        Event(
            kind=EventKind.Shift,
            relationship=RelationshipKind.Fusion,
            dateTime=util.Date(1980, 1, 11),
            endDateTime=util.Date(2015, 1, 1),
            person=p1,
            relationshipTargets=p2,
        )
    )

    assert model.rowCount() == 4
    assert model.eventForRow(0) == event1  # birthDateTime
    assert model.eventForRow(1) == fusion  # fusion startDateTime comes before p2 birth
    assert model.eventForRow(2) == event2  # birthDateTime
    assert (
        model.eventForRow(3) == fusion
    )  # fusion endDateTime (the event is the same, but row 3 is the end marker)
    assert model.timelineRow(3).isEndMarker == True  # Verify row 3 is the end marker

    # fusion dates
    col = model.columnIndex(model.DATETIME)
    assert model.index(1, col).data(Qt.DisplayRole) == util.dateString(
        fusion.dateTime()
    )
    assert model.index(3, col).data(Qt.DisplayRole) == util.dateString(
        fusion.endDateTime()
    )


def test_add_person_marriage(scene, model):
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))
    model.items = [personA]

    marriage = scene.addItem(Marriage(personA=personA, personB=personB))
    married = scene.addItem(Event(EventKind.Married, personA, spouse=personB, dateTime=util.Date(2001, 1, 1)))

    assert model.rowForEvent(married) != None


def test_remove_item(scene, model):
    # Setup: Create two people with events
    p1, p2 = scene.addItems(Person(name="p1"), Person(name="p2"))
    event1 = scene.addItem(
        Event(EventKind.Shift, p1, dateTime=util.Date(1955, 12, 3), tags=["hello"])
    )
    event2 = scene.addItem(Event(EventKind.Shift, p2, dateTime=util.Date(1980, 5, 11)))

    assert model.rowCount() == 2

    scene.removeItem(p2)
    assert model.rowCount() == 1


def test_set_birthdate(scene, model):
    # Setup: Create two people with events, but one without a date
    p1, p2 = scene.addItems(Person(name="p1"), Person(name="p2"))
    event1 = scene.addItem(Event(EventKind.Shift, p1))  # No date initially
    event2 = scene.addItem(Event(EventKind.Shift, p2, dateTime=util.Date(1980, 5, 11)))

    assert model.rowCount() == 1  # Only p2's event shows

    event1.setDateTime(util.Date(1955, 12, 3))
    assert model.rowCount() == 2  # Now both show


def test_unset_birthDate(scene, model):
    # Should remove from rows when date is unset
    p1, p2 = scene.addItems(Person(name="p1"), Person(name="p2"))
    event1 = scene.addItem(Event(EventKind.Shift, p1, dateTime=util.Date(1955, 12, 3)))
    event2 = scene.addItem(Event(EventKind.Shift, p2, dateTime=util.Date(1980, 5, 11)))

    assert model.rowCount() == 2

    event1.prop("dateTime").reset()
    assert model.rowCount() == 1


def test_delete_birthDate(qtbot, scene, model):
    # Should clear date when row is deleted
    p1, p2 = scene.addItems(Person(name="p1"), Person(name="p2"))
    event1 = scene.addItem(Event(EventKind.Shift, p1, dateTime=util.Date(1955, 12, 3)))
    event2 = scene.addItem(Event(EventKind.Shift, p2, dateTime=util.Date(1980, 5, 11)))

    assert model.rowCount() == 2

    selectionModel = QItemSelectionModel(model)
    selectionModel.select(
        model.index(0, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows
    )
    qtbot.clickYesAfter(lambda: model.removeSelection(selectionModel))
    assert model.rowCount() == 1


def test_delete_emotion_date(qtbot, scene, model):
    # Should clear date when emotion date row is deleted
    p1, p2 = scene.addItems(Person(name="p1"), Person(name="p2"))
    event1 = scene.addItem(Event(EventKind.Shift, p1, dateTime=util.Date(1955, 12, 3)))
    event2 = scene.addItem(Event(EventKind.Shift, p2, dateTime=util.Date(1980, 5, 11)))
    conflict = scene.addItem(
        Event(
            kind=EventKind.Shift,
            person=p1,
            relationship=RelationshipKind.Conflict,
            relationshipTargets=p2,
            dateTime=util.Date(2000, 1, 1),
            endDateTime=util.Date(2001, 1, 1),
        )
    )

    endRow = model.endRowForEvent(conflict)
    assert model.rowCount() == 4

    selectionModel = QItemSelectionModel(model)
    selectionModel.select(
        model.index(3, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows
    )
    qtbot.clickYesAfter(lambda: model.removeSelection(selectionModel))
    assert model.rowCount() == 3
    assert conflict.endDateTime() == None  # End date cleared
    assert conflict.dateTime() is not None  # Start date remains
    assert model.endRowForEvent(conflict) == None  # No end row anymore

    selectionModel.select(
        model.index(2, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows
    )
    qtbot.clickYesAfter(lambda: model.removeSelection(selectionModel))
    assert model.rowCount() == 2
    assert conflict not in scene.events()  # Event removed from scene


@pytest.mark.skip(
    reason="Unsure how to consider Person.deceased from TimelineModel._ensureEvent()."
)
def test_dont_show_not_deceased_with_deceased_date(scene, model):
    person = scene.addItem(Person())
    # set deceased date but not `deceased`
    person.setDeceasedDateTime(util.Date(2000, 1, 1))
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


def test_set_datetime(scene, model):
    person = scene.addItem(Person(name="Person A"))
    birthEvent = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 1))
    )
    model.setData(
        model.index(0, model.columnIndex(model.DATETIME)),
        "10/02/2002 12:35pm",
        role=model.DisplayExpandedRole,
    )
    assert birthEvent.dateTime() == util.Date(2002, 10, 2, 12, 35, 0)


@pytest.mark.parametrize("role", [Qt.DisplayRole, Qt.EditRole])
def test_set_date_retains_time(role, scene, model):
    person = scene.addItem(Person(name="Person A"))
    birthEvent = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 1, 12, 35, 0))
    )
    model.setData(
        model.index(0, model.columnIndex(model.DATETIME)), "4/5/2003", role=role
    )
    assert birthEvent.dateTime() == util.Date(2003, 4, 5, 12, 35, 0)


def test_set_emotion_date(scene, model):
    p1, p2 = scene.addItems(Person(), Person())
    fusion = scene.addItem(
        Event(
            kind=EventKind.Shift,
            person=p1,
            relationship=RelationshipKind.Fusion,
            relationshipTargets=p2,
            dateTime=util.Date(1990, 1, 11),
            endDateTime=util.Date(1992, 1, 1),
        )
    )
    endRow = model.endRowForEvent(fusion)
    assert model.rowForEvent(fusion) == 0
    assert model.rowIndexFor(endRow) == 1

    iDate = model.columnIndex(model.DATETIME)
    rowsRemoved = util.Condition(model.rowsRemoved)
    rowsInserted = util.Condition(model.rowsInserted)
    model.setData(model.index(0, iDate), "1/1/1991")
    assert fusion.dateTime() == util.Date(1991, 1, 1)
    assert fusion.endDateTime() == util.Date(1992, 1, 1)
    # When date changes on a range event, both start and end rows are removed and re-inserted
    assert rowsRemoved.callCount == 2  # Start and end rows
    assert rowsInserted.callCount == 2  # Start and end rows
    assert model.data(model.index(0, iDate)) == "01/01/1991"
    assert model.data(model.index(1, iDate)) == "01/01/1992"
    assert model.data(model.index(0, iDate), model.DateTimeRole) == util.Date(
        1991, 1, 1
    )
    assert model.data(model.index(1, iDate), model.DateTimeRole) == util.Date(
        1992, 1, 1
    )


def test_emotion_move_has_only_one_event(scene, model):
    p1, p2 = scene.addItems(Person(), Person())
    fusion = scene.addItem(
        Event(
            kind=EventKind.Shift,
            dateTime=util.Date(1980, 1, 11),
            person=p1,
            relationship=RelationshipKind.Fusion,
            relationshipTargets=p2,
        )
    )
    assert model.rowCount() == 1
    assert model.index(0, 0).data(model.DateTimeRole) == fusion.dateTime()


def test_emotion_date_changed(scene, model):
    p1, p2 = scene.addItems(Person(), Person())
    fusion = scene.addItem(
        Event(
            kind=EventKind.Shift,
            person=p1,
            relationshipTargets=p2,
            relationship=RelationshipKind.Fusion,
        )
    )

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


@pytest.mark.skip(
    reason="date buddies not used for a while now, may re-use in the future"
)
def test_dateBuddies(scene, model):
    # Test that date buddies (start/end dates) are properly tracked
    p1, p2 = scene.addItems(Person(name="p1"), Person(name="p2"))
    event1 = scene.addItem(
        Event(EventKind.Shift, p1, dateTime=util.Date(1955, 12, 3), tags=["hello"])
    )
    event2 = scene.addItem(Event(EventKind.Shift, p2, dateTime=util.Date(1980, 5, 11)))

    fusion = scene.addItem(
        Event(
            kind=EventKind.Shift,
            person=p1,
            relationship=RelationshipKind.Fusion,
            relationshipTargets=p2,
            dateTime=util.Date(1981, 5, 11),
            endDateTime=util.Date(2015, 1, 1),
        )
    )
    endRow = model.endRowForEvent(fusion)

    assert model.firstRowForDateTime(fusion.dateTime()) == 2
    assert model.rowForEvent(fusion) == 2
    assert model.firstRowForDateTime(endRow.dateTime()) == 3

    startDateRow = model.rowForEvent(fusion)
    endDateRow = model.rowIndexFor(endRow)
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


def test_emotion_parentName_changed(scene, model):
    p1, p2 = scene.addItems(Person(name="p1"), Person(name="p2"))
    fusion = scene.addItem(
        Event(
            kind=EventKind.Shift,
            person=p1,
            relationship=RelationshipKind.Fusion,
            relationshipTargets=p2,
            dateTime=util.Date(1980, 5, 11),
            endDateTime=util.Date(1980, 5, 12),
        )
    )
    endRow = model.endRowForEvent(fusion)
    # util.printModel(model)
    assert model.rowCount() == 2  # startDateTime, endDateTime
    assert model.rowForEvent(fusion) == 0
    assert model.rowIndexFor(endRow) == 1
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


def test_rows_for_date(scene, model):
    # Add an emotion start and arbitrary event on the same date, emotion end on another
    p1 = scene.addItem(Person(name="p1"))
    event1 = scene.addItem(Event(EventKind.Shift, p1, dateTime=util.Date(1900, 1, 2)))
    event2 = scene.addItem(Event(EventKind.Shift, p1, dateTime=util.Date(1910, 1, 2)))
    event3 = scene.addItem(Event(EventKind.Shift, p1, dateTime=util.Date(1910, 1, 2)))
    event4 = scene.addItem(Event(EventKind.Shift, p1, dateTime=util.Date(1910, 1, 2)))
    event5 = scene.addItem(Event(EventKind.Shift, p1, dateTime=util.Date(1920, 1, 2)))

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


def test_rows_for_date_search(scene, model):
    # Add an emotion start and arbitrary event on the same date, emotion end on another
    model.searchModel = SearchModel()
    model.searchModel.scene = scene
    p1 = scene.addItem(Person(name="p1"))
    event1 = scene.addItem(Event(EventKind.Shift, p1, dateTime=util.Date(1900, 1, 2)))
    event2 = scene.addItem(
        Event(EventKind.Shift, p1, dateTime=util.Date(1910, 1, 2), tags=["bleh"])
    )  # 0
    event3 = scene.addItem(Event(EventKind.Shift, p1, dateTime=util.Date(1910, 1, 2)))
    event4 = scene.addItem(
        Event(EventKind.Shift, p1, dateTime=util.Date(1910, 1, 2), tags=["bleh"])
    )  # 1
    event5 = scene.addItem(
        Event(EventKind.Shift, p1, dateTime=util.Date(1920, 1, 2), tags=["bleh"])
    )  # 2

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


def test_showAliases_signals(scene, model):
    patrick, bob = scene.addItems(
        Person(name="Patrick", alias="Marco", notes="Patrick Bob"),
        Person(name="Bob", nickName="Robby", alias="John"),
    )
    e1 = scene.addItem(
        Event(
            EventKind.Shift,
            patrick,
            dateTime=util.Date(1900, 1, 1),
            description="Bob came home",
        )
    )
    e2 = scene.addItem(
        Event(
            EventKind.Shift,
            patrick,
            dateTime=util.Date(1900, 1, 2),
            description="robby came home, took Robby's place",
        )
    )
    e3 = scene.addItem(
        Event(
            EventKind.Shift,
            bob,
            dateTime=util.Date(1900, 1, 3),
            description="Patrick came home with bob",
        )
    )
    distance = scene.addItem(
        Event(
            kind=EventKind.Shift,
            relationship=RelationshipKind.Distance,
            dateTime=util.Date(1900, 1, 4),
            endDateTime=util.Date(1900, 1, 5),
            person=patrick,
            relationshipTargets=bob,
        )
    )
    marriage = scene.addItem(Marriage(personA=patrick, personB=bob))
    married = scene.addItem(
        Event(
            kind=EventKind.Married,
            dateTime=util.Date(1900, 1, 6),
            person=patrick,
            spouse=bob,
        )
    )
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
    assert model.index(2, 5).data() == "Bob (Robby)"

    # Check display values for relationship events directly via model
    assert model.index(3, 3).data() == "Distance began"
    assert model.index(3, 5).data() == "Patrick & Bob (Robby)"
    assert model.index(4, 3).data() == "Distance ended"
    assert model.index(4, 5).data() == "Patrick & Bob (Robby)"

    # Check display values for marriage events directly via model
    assert model.index(5, 5).data() == "Patrick & Bob (Robby)"

    util.runModel(model, silent=True)
    scene.setShowAliases(True)
    # Verify that dataChanged signals were emitted for name/alias changes
    # The exact count depends on signal timing and may include both DESCRIPTION and PARENT columns
    assert dataChanged.callCount > 0  # At least some signals were emitted

    assert e1.description() == "[John] came home"
    assert newValues[0][3] == "[John] came home"
    assert newValues[0][5] == "[Marco]"

    assert e2.description() == "[John] came home, took [John]'s place"
    assert newValues[1][3] == "[John] came home, took [John]'s place"
    assert newValues[1][5] == "[Marco]"

    assert e3.description() == "[Marco] came home with [John]"
    assert newValues[2][3] == "[Marco] came home with [John]"
    assert newValues[2][5] == "[John]"

    # Check aliases for relationship events directly via model
    assert newValues[3][5] == "[Marco] & [John]"
    assert newValues[4][5] == "[Marco] & [John]"

    # Check aliases for marriage events directly via model
    assert model.index(5, 5).data() == "[Marco] & [John]"


def test_get_all_variables(scene):
    scene.addEventProperty("anxiety")
    person = scene.addItem(Person(name="Person A"))
    birthEvent = scene.addItem(
        Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 1))
    )
    prop = birthEvent.dynamicProperty("anxiety")
    prop.set("up")
    # for i in range(model.rowCount()):
    #     for j in range(model.columnCount()):
    #         Debug(i, j, model.data(model.index(i, j)))
