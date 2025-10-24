import pytest

from btcopilot.schema import EventKind, RelationshipKind
from pkdiagram import util
from pkdiagram.scene import Event, Person


def test_init(scene):
    """Try to break ctor."""
    person = scene.addItem(Person())
    event = scene.addItem(Event(EventKind.Shift, person))
    assert event in scene.eventsFor(person)


# @pytest.mark.parametrize("undo", [True, False])
# def test_setParent(scene, undo):
#     """
#     We really only need to test switching parents, not setting back to None.
#     """
#     personA, personB = Person(), Person()
#     scene.addItems(personA, personB)
#     event = scene.addItem(Event(EventKind.Shift, personA))
#     assert event in scene.eventsFor(personA)
#     #
#     event.setPerson(personB, undo=undo)
#     assert event in scene.eventsFor(personB)
#     assert event not in scene.eventsFor(personA)
#     scene.undo()
#     if undo:
#         assert event not in scene.eventsFor(personB)
#         assert event in scene.eventsFor(personA)
#     else:
#         assert event in scene.eventsFor(personB)
#         assert event not in scene.eventsFor(personA)


def __test___lt__():
    person = Person()
    birth = Event(EventKind.Birth, person=person)
    death = Event(EventKind.Death, person=person)
    eventA = Event(EventKind.Shift, person=person)

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


def test_sorted_every_other(scene):
    """Test sorting a list where every other has no date."""
    dateTime = util.Date(2001, 1, 1)
    events = []
    for i in range(10):
        person = scene.addItem(Person())
        event = scene.addItem(Event(EventKind.Shift, person))
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


def test_lt(scene):
    person = scene.addItem(Person())
    d1 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 2)))
    d2 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 2)))
    assert not (d1 < d2)

    d1 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 4)))
    d2 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 5)))
    assert d1 < d2

    d1 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 11, 5)))
    d2 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 5)))
    assert d1 < d2

    d1 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2000, 12, 5)))
    d2 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 5)))
    assert d1 < d2

    d1 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2002, 12, 5)))
    d2 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 5)))
    assert not (d1 < d2)

    d1 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 5)))
    d2 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 11, 5)))
    assert not (d1 < d2)

    d1 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 6)))
    d2 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 5)))
    assert not (d1 < d2)


@pytest.mark.skip("__le__ not supported yet")
def test_lt_eq(scene):
    person = scene.addItem(Person())
    d1 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 2)))
    d2 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2000, 1, 2)))
    assert d1 <= d2

    d1 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 4)))
    d2 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 5)))
    assert d1 <= d2

    d1 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 11, 5)))
    d2 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 5)))
    assert d1 <= d2

    d1 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2000, 12, 5)))
    d2 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 5)))
    assert d1 <= d2

    d1 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2002, 12, 5)))
    d2 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 5)))
    assert not (d1 <= d2)

    d1 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 5)))
    d2 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 11, 5)))
    assert not (d1 <= d2)

    d1 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 6)))
    d2 = scene.addItem(Event(EventKind.Shift, person, dateTime=util.Date(2001, 12, 5)))
    assert not (d1 <= d2)


@pytest.mark.parametrize(
    "attr, value",
    [
        ("symptom", util.VAR_SYMPTOM_UP),
        ("anxiety", util.VAR_ANXIETY_DOWN),
        ("relationship", RelationshipKind.Conflict),
        ("functioning", util.VAR_FUNCTIONING_SAME),
    ],
)
def test_variables(scene, attr, value):
    scene.addEventProperty(util.ATTR_SYMPTOM)
    scene.addEventProperty(util.ATTR_ANXIETY)
    scene.addEventProperty(util.ATTR_RELATIONSHIP)
    scene.addEventProperty(util.ATTR_FUNCTIONING)
    person = scene.addItem(Person())
    event = scene.addItem(Event(EventKind.Shift, person))
    getattr(event, f"set{attr.capitalize()}")(value)
    assert getattr(event, attr)() == value


@pytest.mark.parametrize(
    "relationship", [RelationshipKind.Inside, RelationshipKind.Outside]
)
def test_triangle(scene, relationship: RelationshipKind):
    """Test setting and getting triangle members."""
    scene.addEventProperty(util.ATTR_SYMPTOM)
    scene.addEventProperty(util.ATTR_ANXIETY)
    scene.addEventProperty(util.ATTR_RELATIONSHIP)
    scene.addEventProperty(util.ATTR_FUNCTIONING)
    person = scene.addItem(Person(name="Person"))
    spouse = scene.addItem(Person(name="Spouse"))
    third = scene.addItem(Person(name="Third"))
    event = scene.addItem(Event(EventKind.Shift, person))
    event.setRelationship(relationship)
    event.setRelationshipTargets(spouse)
    event.setRelationshipTriangles(third)
    assert event.relationshipTargets() == [spouse]
    assert event.relationshipTriangles() == [third]
