import pytest
from pkdiagram.pyqt import Qt, QDateTime, QItemSelectionModel
from pkdiagram import util, objects, EventKind
from pkdiagram import Scene, Person, Marriage, Event, Emotion, TimelineModel


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
    return timelineScene.timelineModel


def test_internals(model):
    assert model.rowCount() == 3
    event = Event(dateTime=util.Date(2012, 1, 1))
    model._ensureEvent(event)
    assert model.rowForEvent(event) == 2  # just before nowEvent


def test_init_deinit(timelineScene, model):
    p1 = timelineScene.query1(name="p1")
    p2 = timelineScene.query1(name="p2")
    assert model.rowCount() == 3
    assert model.eventForRow(0) == p1.birthEvent
    assert model.eventForRow(1) == p2.birthEvent
    assert model.eventForRow(2) == timelineScene.nowEvent
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
    # nowEvent is last
    assert timelineScene.nowEvent == model.eventForRow(model.rowCount() - 1)

    # qtmodeltester.check(model)


def test_shouldHide():
    scene = Scene()
    model = scene.timelineModel
    assert model._shouldHide(Event(dateTime=util.Date(2000, 1, 1))) == False
    assert model._shouldHide(Event()) == True

    scene.searchModel.tags = ["here"]
    assert model._shouldHide(Event(dateTime=util.Date(2000, 1, 1))) == True
    assert (
        model._shouldHide(Event(dateTime=util.Date(2000, 1, 1), tags=["here"])) == False
    )

    scene.searchModel.tags = []
    scene.searchModel.description = "there"
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


def test_init_multiple_people():

    scene = Scene()
    personA, personB, personC = Person(), Person(), Person()
    personA.setBirthDateTime(util.Date(2000, 1, 1))
    personB.setBirthDateTime(util.Date(2001, 1, 1))
    eventA = Event(
        parent=personA, description="PersonA something", dateTime=util.Date(2002, 1, 1)
    )
    eventB = Event(
        parent=personB, description="PersonB something", dateTime=util.Date(2003, 1, 1)
    )
    # add two emotions where only one person's end should should in the timeline
    emotionA = Emotion(
        kind=util.ITEM_DISTANCE,
        personA=personA,
        personB=personC,
        startDateTime=util.Date(2004, 1, 1),
        endDateTime=util.Date(2005, 1, 1),
    )
    emotionB = Emotion(
        kind=util.ITEM_CONFLICT,
        personA=personB,
        personB=personC,
        startDateTime=util.Date(2006, 1, 1),
        endDateTime=util.Date(2007, 1, 1),
    )
    # add one emotion where both ends should be shown but without duplicates.
    emotionC = Emotion(
        kind=util.ITEM_FUSION,
        personA=personA,
        personB=personB,
        startDateTime=util.Date(2008, 1, 1),
        endDateTime=util.Date(2009, 1, 1),
    )
    scene.addItems(personA, personB, personC, emotionA, emotionB, emotionC)
    model = TimelineModel()
    model.scene = scene
    model.items = [personA, personB]

    assert model.rowCount() == 10  # no now event for person|marriage props
    assert (
        model.data(model.index(0, 0), model.DateTimeRole)
        == personA.birthEvent.dateTime()
    )
    assert (
        model.data(model.index(1, 0), model.DateTimeRole)
        == personB.birthEvent.dateTime()
    )
    assert model.data(model.index(2, 0), model.DateTimeRole) == eventA.dateTime()
    assert model.data(model.index(3, 0), model.DateTimeRole) == eventB.dateTime()
    assert model.data(model.index(4, 0), model.DateTimeRole) == emotionA.startDateTime()
    assert model.data(model.index(5, 0), model.DateTimeRole) == emotionA.endDateTime()
    assert model.data(model.index(6, 0), model.DateTimeRole) == emotionB.startDateTime()
    assert model.data(model.index(7, 0), model.DateTimeRole) == emotionB.endDateTime()
    assert model.data(model.index(8, 0), model.DateTimeRole) == emotionC.startDateTime()
    assert model.data(model.index(9, 0), model.DateTimeRole) == emotionC.endDateTime()


def test_include_marriage_events():

    scene = Scene()
    personA, personB = Person(), Person()
    marriage = Marriage(personA=personA, personB=personB)
    scene.addItems(personA, personB, marriage)
    model = TimelineModel()
    model.scene = scene
    model.items = [personA]
    assert model.rowCount() == 0

    # marriage events for one person
    separated = Event(
        parent=marriage,
        uniqueId=EventKind.Separated.value,
        dateTime=util.Date(2001, 1, 1),
    )
    assert model.rowCount() == 1
    assert model.data(model.index(0, 0), model.DateTimeRole) == util.Date(2001, 1, 1)

    # more marriage events for one person
    married = Event(
        parent=marriage,
        uniqueId=EventKind.Married.value,
        dateTime=util.Date(2000, 1, 1),
    )
    assert model.rowCount() == 2
    assert model.data(model.index(0, 0), model.DateTimeRole) == util.Date(2000, 1, 1)
    assert model.data(model.index(1, 0), model.DateTimeRole) == util.Date(2001, 1, 1)

    # don't duplicate marriage events when both people/ends are added
    model.items = [personA, personB]
    assert model.rowCount() == 2
    assert model.data(model.index(0, 0), model.DateTimeRole) == util.Date(2000, 1, 1)
    assert model.data(model.index(1, 0), model.DateTimeRole) == util.Date(2001, 1, 1)


def test_flags(qtbot, timelineScene, model):
    p1 = timelineScene.query1(name="p1")
    p2 = timelineScene.query1(name="p2")

    fusion = objects.Emotion(kind=util.ITEM_FUSION)
    fusion.setPersonA(p1)
    fusion.setPersonB(p2)
    fusion.startEvent.setDateTime(util.Date(1980, 5, 11))
    fusion.endEvent.setDateTime(util.Date(2015, 1, 1))
    timelineScene.addItem(fusion)

    for row in range(model.rowCount()):
        item = model.itemForRow(row)
        iBuddies = model.columnIndex(model.BUDDIES)
        iDate = model.columnIndex(model.DATETIME)
        iDescription = model.columnIndex(model.DESCRIPTION)
        iLocation = model.columnIndex(model.LOCATION)
        iParent = model.columnIndex(model.PARENT)
        iLogged = model.columnIndex(model.LOGGED)
        assert not model.flags(model.index(row, iBuddies)) & Qt.ItemIsEditable
        if item.isEmotion:
            assert model.flags(model.index(row, iDate)) & Qt.ItemIsEditable
            assert not model.flags(model.index(row, iDescription)) & Qt.ItemIsEditable
            assert not model.flags(model.index(row, iParent)) & Qt.ItemIsEditable
            assert model.flags(model.index(row, iLocation)) & Qt.ItemIsEditable
        else:
            event = model.eventForRow(row)
            if event.uniqueId() == "now":
                assert not model.flags(model.index(row, iDate)) & Qt.ItemIsEditable
                assert (
                    not model.flags(model.index(row, iDescription)) & Qt.ItemIsEditable
                )
                assert not model.flags(model.index(row, iLocation)) & Qt.ItemIsEditable
                assert not model.flags(model.index(row, iParent)) & Qt.ItemIsEditable
            elif event.uniqueId():
                assert model.flags(model.index(row, iDate)) & Qt.ItemIsEditable
                assert (
                    not model.flags(model.index(row, iDescription)) & Qt.ItemIsEditable
                )
                assert model.flags(model.index(row, iLocation)) & Qt.ItemIsEditable
                assert not model.flags(model.index(row, iParent)) & Qt.ItemIsEditable
            else:
                assert model.flags(model.index(row, iDate)) & Qt.ItemIsEditable
                assert model.flags(model.index(row, iDescription)) & Qt.ItemIsEditable
                assert model.flags(model.index(row, iLocation)) & Qt.ItemIsEditable
                assert model.flags(model.index(row, iParent)) & Qt.ItemIsEditable
        assert not model.flags(model.index(row, iLogged)) & Qt.ItemIsEditable


def test_add_item(timelineScene, model):
    p1 = timelineScene.query1(name="p1")
    p2 = timelineScene.query1(name="p2")

    fusion = objects.Emotion(kind=util.ITEM_FUSION)
    fusion.setPersonA(p1)
    fusion.setPersonB(p2)
    fusion.startEvent.setDateTime(util.Date(1980, 5, 11))
    fusion.endEvent.setDateTime(util.Date(2015, 1, 1))
    timelineScene.addItem(fusion)
    #
    assert model.rowCount() == 5
    #
    assert model.eventForRow(0) == p1.birthEvent  # birthDateTime
    assert model.eventForRow(1) == p2.birthEvent  # birthDateTime
    assert model.eventForRow(2) == fusion.startEvent  # startDateTime
    assert model.eventForRow(3) == fusion.endEvent  # endDateTime
    assert model.eventForRow(4) == timelineScene.nowEvent
    # fusion dates
    col = model.columnIndex(model.DATETIME)
    assert model.index(2, col).data(Qt.DisplayRole) == util.dateString(
        fusion.startDateTime()
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

    marriage = objects.Marriage(personA=personA, personB=personB)
    married = Event(
        parent=marriage, date=util.Date(2001, 1, 1), uniqueId=EventKind.Married.value
    )
    scene.addItem(marriage)

    assert model.rowForEvent(married) != None


def test_remove_item(timelineScene, model):
    assert model.rowCount() == 3

    p2 = timelineScene.query1(name="p2")
    timelineScene.removeItem(p2)
    assert model.rowCount() == 2


def test_set_birthdate(timelineScene, model):
    p1 = timelineScene.query1(name="p1")
    p1.birthEvent.prop("dateTime").reset()

    assert model.rowCount() == 2

    p1.setBirthDateTime(util.Date(1955, 12, 3))
    assert model.rowCount() == 3


def test_unset_birthDate(timelineScene, model):
    # should remove from rows
    p1 = timelineScene.query1(name="p1")
    p1.setBirthDateTime(util.Date(1955, 12, 3))
    assert model.rowCount() == 3

    p1.birthEvent.prop("dateTime").reset()
    assert model.rowCount() == 2


def test_delete_birthDate(qtbot, timelineScene, model):
    # should clear date
    p1 = timelineScene.query1(name="p1")
    p1.setBirthDateTime(util.Date(1955, 12, 3))
    assert model.rowCount() == 3

    selectionModel = QItemSelectionModel(model)
    selectionModel.select(
        model.index(0, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows
    )
    qtbot.clickYesAfter(lambda: model.removeSelection(selectionModel))
    assert model.rowCount() == 2


def test_delete_emotion_date(qtbot, timelineScene, model):
    # should clear date
    p1 = timelineScene.query1(name="p1")
    p2 = timelineScene.query1(name="p2")
    conflict = Emotion(
        kind=util.ITEM_CONFLICT,
        startDateTime=util.Date(2000, 1, 1),
        endDateTime=util.Date(2001, 1, 1),
    )
    timelineScene.addItem(conflict)
    assert model.rowCount() == 5

    selectionModel = QItemSelectionModel(model)
    selectionModel.select(
        model.index(3, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows
    )
    qtbot.clickYesAfter(lambda: model.removeSelection(selectionModel))
    assert model.rowCount() == 4
    assert conflict.endEvent.dateTime() == None
    assert conflict.endEvent in timelineScene.events()

    selectionModel.select(
        model.index(2, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows
    )
    qtbot.clickYesAfter(lambda: model.removeSelection(selectionModel))
    assert model.rowCount() == 3
    assert conflict.startEvent.dateTime() == None
    assert conflict.startEvent in timelineScene.events()


@pytest.mark.skip(
    reason="Unsure how to consider Person.deceased from TimelineModel._ensureEvent()."
)
def test_dont_show_not_deceased_with_deceased_date():
    scene = Scene()
    model = scene.timelineModel
    person = Person()
    # set deceased date but not `deceased`
    person.setDeceasedDateTime(util.Date(2000, 1, 1))
    scene.addItem(person)
    assert model.rowCount() == 1
    assert model.eventForRow(0) == scene.nowEvent


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
    model = scene.timelineModel
    person = Person(name="Person A")
    person.birthEvent.setDateTime(util.Date(2000, 1, 1))
    scene.addItems(person)
    model.setData(
        model.index(0, model.columnIndex(model.DATETIME)),
        "10/02/2002 12:35pm",
        role=model.DisplayExpandedRole,
    )
    assert person.birthEvent.dateTime() == util.Date(2002, 10, 2, 12, 35, 0)


@pytest.mark.parametrize("role", [Qt.DisplayRole, Qt.EditRole])
def test_set_date_retains_time(role):
    scene = Scene()
    model = scene.timelineModel
    person = Person(name="Person A")
    person.birthEvent.setDateTime(util.Date(2000, 1, 1, 12, 35, 0))
    scene.addItems(person)
    model.setData(
        model.index(0, model.columnIndex(model.DATETIME)), "4/5/2003", role=role
    )
    assert person.birthEvent.dateTime() == util.Date(2003, 4, 5, 12, 35, 0)


def test_set_emotion_date():

    scene = Scene()
    model = scene.timelineModel
    model.scene = scene
    model.items = [scene]

    p1 = objects.Person()
    p2 = objects.Person()
    scene.addItems(p1, p2)
    fusion = objects.Emotion(
        kind=util.ITEM_FUSION,
        personA=p1,
        personB=p2,
        startDateTime=util.Date(1990, 1, 11),
        endDateTime=util.Date(1992, 1, 1),
    )
    scene.addItem(fusion)
    assert model.rowForEvent(fusion.startEvent) == 0
    assert model.rowForEvent(fusion.endEvent) == 1

    iDate = model.columnIndex(model.DATETIME)
    rowsRemoved = util.Condition(model.rowsRemoved)
    rowsInserted = util.Condition(model.rowsInserted)
    model.setData(model.index(0, iDate), "1/1/1991")
    assert fusion.startDateTime() == util.Date(1991, 1, 1)
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


def test_emotion_date_changed():

    scene = Scene()
    model = TimelineModel()
    model.scene = scene
    model.items = [scene]
    p1 = objects.Person()
    p2 = objects.Person()
    fusion = objects.Emotion(kind=util.ITEM_FUSION)
    fusion.setPersonA(p1)
    fusion.setPersonB(p2)
    scene.addItems(p1, p2, fusion)

    dateTime = util.Date(1980, 1, 11)

    iDate = model.columnIndex(model.DATETIME)
    rowsRemoved = util.Condition(model.rowsRemoved)
    rowsInserted = util.Condition(model.rowsInserted)
    fusion.startEvent.setDateTime(dateTime)
    assert rowsRemoved.callCount == 0
    assert rowsInserted.callCount == 1
    assert rowsInserted.callArgs[0][1] == 0
    assert rowsInserted.callArgs[0][2] == 0
    assert model.data(model.index(0, iDate)) == util.dateString(dateTime)
    assert model.data(model.index(0, iDate), model.DateTimeRole) == dateTime


def test_SortedList():
    from sortedcontainers import SortedList

    d1 = util.Date(1955, 12, 3)
    d2 = util.Date(1980, 5, 11)
    d3 = util.Date(1980, 5, 11)
    d4 = util.Date(2015, 1, 1)
    stuff = SortedList()
    stuff.add(d1)
    stuff.add(d2)
    stuff.add(d3)
    stuff.add(d4)
    assert d2 in stuff
    assert d3 in stuff


def test_dateBuddies(timelineScene, model):
    p1 = timelineScene.query1(name="p1")
    p2 = timelineScene.query1(name="p2")

    fusion = objects.Emotion(
        kind=util.ITEM_FUSION,
        personA=p1,
        personB=p2,
        startDateTime=util.Date(1980, 5, 11),
        endDateTime=util.Date(2015, 1, 1),
    )
    timelineScene.addItem(fusion)

    assert model.firstRowForDateTime(fusion.startEvent.dateTime()) == 1
    assert model.rowForEvent(fusion.startEvent) == 2
    assert model.firstRowForDateTime(fusion.endEvent.dateTime()) == 3

    startDateRow = model.rowForEvent(fusion.startEvent)
    endDateRow = model.rowForEvent(fusion.endEvent)
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


def test_dateBuddies_sameDate(timelineScene, model):
    p1 = timelineScene.query1(name="p1")
    p2 = timelineScene.query1(name="p2")

    fusion = objects.Emotion(kind=util.ITEM_FUSION)
    fusion.setPersonA(p1)
    fusion.setPersonB(p2)
    fusion.startEvent.setDateTime(util.Date(1980, 5, 11))
    fusion.endEvent.setDateTime(util.Date(1980, 5, 12))
    timelineScene.addItem(fusion)

    assert model.firstRowForDateTime(fusion.startDateTime()) == 1
    assert model.rowForEvent(fusion.startEvent) == 2
    assert model.lastRowForDateTime(fusion.endEvent.dateTime()) == 3

    startDateRow = model.rowForEvent(fusion.startEvent)
    endDateRow = model.rowForEvent(fusion.endEvent)
    assert startDateRow == 2
    assert endDateRow == 3

    startDateBuddyRow = model.dateBuddyForRow(startDateRow)
    endDateBuddyRow = model.dateBuddyForRow(endDateRow)
    assert startDateBuddyRow == endDateRow
    assert endDateBuddyRow == startDateRow

    dateBuddies = model.dateBuddiesInternal()
    assert len(dateBuddies) == 1
    row1, row2, item = dateBuddies[0]
    assert row1 == 2
    assert row2 == 3
    assert item == fusion


def test_emotion_parentName_changed():
    scene = Scene()
    model = scene.timelineModel
    p1 = Person(name="p1")
    p2 = Person(name="p2")
    fusion = Emotion(
        kind=util.ITEM_FUSION,
        personA=p1,
        personB=p2,
        startDateTime=util.Date(1980, 5, 11),
        endDateTime=util.Date(1980, 5, 12),
    )
    scene.addItems(p1, p2, fusion)
    # util.printModel(model)
    assert model.rowCount() == 3  # startDateTime, endDateTime, now
    assert model.rowForEvent(fusion.startEvent) == 0
    assert model.rowForEvent(fusion.endEvent) == 1
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
    model = scene.timelineModel
    p1 = Person(name="p1")
    event1 = Event(parent=p1, dateTime=util.Date(1900, 1, 2))
    event2 = Event(parent=p1, dateTime=util.Date(1910, 1, 2))
    event3 = Event(parent=p1, dateTime=util.Date(1910, 1, 2))
    event4 = Event(parent=p1, dateTime=util.Date(1910, 1, 2))
    event5 = Event(parent=p1, dateTime=util.Date(1920, 1, 2))
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
    model = scene.timelineModel
    p1 = Person(name="p1")
    event1 = Event(parent=p1, dateTime=util.Date(1900, 1, 2))
    event2 = Event(parent=p1, dateTime=util.Date(1910, 1, 2), tags=["bleh"])  # 0
    event3 = Event(parent=p1, dateTime=util.Date(1910, 1, 2))
    event4 = Event(parent=p1, dateTime=util.Date(1910, 1, 2), tags=["bleh"])  # 1
    event5 = Event(parent=p1, dateTime=util.Date(1920, 1, 2), tags=["bleh"])  # 2
    scene.addItems(p1)

    scene.searchModel.tags = ["bleh"]

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


def test_showAliases_signals():
    scene = Scene()
    patrick = Person(name="Patrick", alias="Marco", notes="Patrick Bob")
    bob = Person(name="Bob", nickName="Robby", alias="John")
    e1 = Event(
        parent=patrick, dateTime=util.Date(1900, 1, 1), description="Bob came home"
    )
    e2 = Event(
        parent=patrick,
        dateTime=util.Date(1900, 1, 2),
        description="robby came home, took Robby's place",
    )
    e3 = Event(
        parent=bob,
        dateTime=util.Date(1900, 1, 3),
        description="Patrick came home with bob",
    )
    distance = Emotion(
        kind=util.ITEM_DISTANCE,
        startDateTime=util.Date(1900, 1, 4),
        endDateTime=util.Date(1900, 1, 5),
        personA=patrick,
        personB=bob,
    )
    marriage = Marriage(personA=patrick, personB=bob)
    marriedEvent = Event(
        parent=marriage,
        uniqueId=EventKind.Married.value,
        dateTime=util.Date(1900, 1, 5),
    )
    scene.addItems(patrick, bob, distance, marriage)
    model = scene.timelineModel
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

    assert distance.parentName() == "Patrick & Bob"
    assert model.index(3, 3).data() == "Distance began"
    assert model.index(3, 5).data() == "Patrick & Bob"
    assert model.index(4, 3).data() == "Distance ended"
    assert model.index(4, 5).data() == "Patrick & Bob"

    assert marriedEvent.parentName() == "Patrick & Bob"
    assert model.index(5, 5).data() == "Patrick & Bob"

    util.runModel(model, silent=True)
    scene.setShowAliases(True)
    assert dataChanged.callCount == 12

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

    assert marriedEvent.parentName() == "[Marco] & [John]"
    assert model.index(5, 5).data() == "[Marco] & [John]"


def test_get_all_variables():
    """model was bombing on now event."""
    scene = Scene()
    scene.addEventProperty("anxiety")
    person = Person(name="Person A")
    person.birthEvent.setDateTime(util.Date(2000, 1, 1))
    scene.addItem(person)
    prop = person.birthEvent.dynamicProperty("anxiety")
    prop.set("up")
    model = scene.timelineModel
    # for i in range(model.rowCount()):
    #     for j in range(model.columnCount()):
    #         Debug(i, j, model.data(model.index(i, j)))
