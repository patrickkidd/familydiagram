import pytest

from pkdiagram import util
from pkdiagram.scene import LifeChange, Event, Person


def test_init():
    """Try to break ctor."""
    person = Person()
    event = Event(person)
    assert event in person.events()


@pytest.mark.parametrize("undo", [True, False])
def test_setParent(scene, undo):
    """
    We really only need to test switching parents, not setting back to None.
    """
    personA, personB = Person(), Person()
    scene.addItems(personA, personB)
    event = Event(parent=personB)
    scene.addItem(event)
    #
    event.setParent(personA, undo=undo)
    assert event in personA.events()
    assert event not in personB.events()
    scene.undo()
    if undo:
        assert event not in personA.events()
        assert event in personB.events()
    else:
        assert event in personA.events()
        assert event not in personB.events()


def __test___lt__():
    parent = Person()
    birth = Event(uniqueId=LifeChange.Birth.value)
    death = Event(uniqueId=LifeChange.Death.value)
    eventA = Event()

    birth.setParent(parent)
    death.setParent(parent)
    eventA.setParent(parent)

    # test birth < eventA < death (blank dates)
    assert birth < eventA
    assert not (eventA < birth)
    assert eventA < death
    assert not (death < eventA)

    # test birth < eventA < death (set eventA date)
    eventA.setDateTime(util.Date(2005, 1, 6))
    assert birth < eventA
    assert not (eventA < birth)
    assert eventA < death
    assert not (death < eventA)


def test_sorted_every_other():
    """Test sorting a list where every other has no date."""
    dateTime = util.Date(2001, 1, 1)
    events = []
    for i in range(10):
        event = Event()
        if i % 2:
            event.setDateTime(dateTime)
            dateTime = dateTime.addDays(1)
        events.append(event)
    sortedEvents = sorted(events)

    # events with dates should filter to the front
    lastEvent = sortedEvents[0]
    for event in sortedEvents[1:]:
        if event.dateTime() is not None:
            assert lastEvent.dateTime() < event.dateTime()
        else:
            break
        lastEvent = event


def test_QDate_lt():
    d1 = util.Date(2000, 1, 2)
    d2 = util.Date(2000, 1, 2)
    assert not (d1 < d2)

    d1 = util.Date(2001, 12, 4)
    d2 = util.Date(2001, 12, 5)
    assert d1 < d2

    d1 = util.Date(2001, 11, 5)
    d2 = util.Date(2001, 12, 5)
    assert d1 < d2

    d1 = util.Date(2000, 12, 5)
    d2 = util.Date(2001, 12, 5)
    assert d1 < d2

    d1 = util.Date(2002, 12, 5)
    d2 = util.Date(2001, 12, 5)
    assert not (d1 < d2)

    d1 = util.Date(2001, 12, 5)
    d2 = util.Date(2001, 11, 5)
    assert not (d1 < d2)

    d1 = util.Date(2001, 12, 6)
    d2 = util.Date(2001, 12, 5)
    assert not (d1 < d2)


def test_QDate_lt_eq():

    d1 = util.Date(2000, 1, 2)
    d2 = util.Date(2000, 1, 2)
    assert d1 <= d2

    d1 = util.Date(2001, 12, 4)
    d2 = util.Date(2001, 12, 5)
    assert d1 <= d2

    d1 = util.Date(2001, 11, 5)
    d2 = util.Date(2001, 12, 5)
    assert d1 <= d2

    d1 = util.Date(2000, 12, 5)
    d2 = util.Date(2001, 12, 5)
    assert d1 <= d2

    d1 = util.Date(2002, 12, 5)
    d2 = util.Date(2001, 12, 5)
    assert not (d1 <= d2)

    d1 = util.Date(2001, 12, 5)
    d2 = util.Date(2001, 11, 5)
    assert not (d1 <= d2)

    d1 = util.Date(2001, 12, 6)
    d2 = util.Date(2001, 12, 5)
    assert not (d1 <= d2)


def test_lt():
    d1 = Event(dateTime=util.Date(2000, 1, 2))
    d2 = Event(dateTime=util.Date(2000, 1, 2))
    assert not (d1 < d2)

    d1 = Event(dateTime=util.Date(2001, 12, 4))
    d2 = Event(dateTime=util.Date(2001, 12, 5))
    assert d1 < d2

    d1 = Event(dateTime=util.Date(2001, 11, 5))
    d2 = Event(dateTime=util.Date(2001, 12, 5))
    assert d1 < d2

    d1 = Event(dateTime=util.Date(2000, 12, 5))
    d2 = Event(dateTime=util.Date(2001, 12, 5))
    assert d1 < d2

    d1 = Event(dateTime=util.Date(2002, 12, 5))
    d2 = Event(dateTime=util.Date(2001, 12, 5))
    assert not (d1 < d2)

    d1 = Event(dateTime=util.Date(2001, 12, 5))
    d2 = Event(dateTime=util.Date(2001, 11, 5))
    assert not (d1 < d2)

    d1 = Event(dateTime=util.Date(2001, 12, 6))
    d2 = Event(dateTime=util.Date(2001, 12, 5))
    assert not (d1 < d2)


@pytest.mark.skip("__le__ not supported yet")
def test_lt_eq():

    d1 = Event(dateTime=util.Date(2000, 1, 2))
    d2 = Event(dateTime=util.Date(2000, 1, 2))
    assert d1 <= d2

    d1 = Event(dateTime=util.Date(2001, 12, 4))
    d2 = Event(dateTime=util.Date(2001, 12, 5))
    assert d1 <= d2

    d1 = Event(dateTime=util.Date(2001, 11, 5))
    d2 = Event(dateTime=util.Date(2001, 12, 5))
    assert d1 <= d2

    d1 = Event(dateTime=util.Date(2000, 12, 5))
    d2 = Event(dateTime=util.Date(2001, 12, 5))
    assert d1 <= d2

    d1 = Event(dateTime=util.Date(2002, 12, 5))
    d2 = Event(dateTime=util.Date(2001, 12, 5))
    assert not (d1 <= d2)

    d1 = Event(dateTime=util.Date(2001, 12, 5))
    d2 = Event(dateTime=util.Date(2001, 11, 5))
    assert not (d1 <= d2)

    d1 = Event(dateTime=util.Date(2001, 12, 6))
    d2 = Event(dateTime=util.Date(2001, 12, 5))
    assert not (d1 <= d2)
