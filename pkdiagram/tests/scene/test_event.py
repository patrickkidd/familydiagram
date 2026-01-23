import pytest

from btcopilot.schema import EventKind, RelationshipKind, VariableShift, DateCertainty
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
    "attr, setter, value",
    [
        ("symptom", "setSymptom", VariableShift.Up),
        ("anxiety", "setAnxiety", VariableShift.Down),
        ("relationship", "setRelationship", RelationshipKind.Conflict),
        ("functioning", "setFunctioning", VariableShift.Same),
        ("dateCertainty", "setDateCertainty", DateCertainty.Approximate),
    ],
)
def test_enum_property_set_get(scene, attr, setter, value):
    """Test that enum properties can be set and retrieved correctly."""
    person = scene.addItem(Person())
    event = scene.addItem(Event(EventKind.Shift, person))
    getattr(event, setter)(value)
    assert getattr(event, attr)() == value


@pytest.mark.parametrize(
    "attr, value",
    [
        ("symptom", VariableShift.Up),
        ("anxiety", VariableShift.Down),
        ("relationship", RelationshipKind.Conflict),
        ("functioning", VariableShift.Same),
        ("dateCertainty", DateCertainty.Approximate),
    ],
)
def test_enum_property_via_kwargs(scene, attr, value):
    """Test that enum properties can be passed via constructor kwargs."""
    person = scene.addItem(Person())
    event = scene.addItem(Event(EventKind.Shift, person, **{attr: value}))
    assert getattr(event, attr)() == value


@pytest.mark.parametrize(
    "attr, setter, value",
    [
        ("symptom", "setSymptom", VariableShift.Up),
        ("anxiety", "setAnxiety", VariableShift.Down),
        ("relationship", "setRelationship", RelationshipKind.Conflict),
        ("functioning", "setFunctioning", VariableShift.Same),
        ("dateCertainty", "setDateCertainty", DateCertainty.Approximate),
    ],
)
def test_enum_property_undo(scene, attr, setter, value):
    """Test that enum property changes can be undone."""
    person = scene.addItem(Person())
    event = scene.addItem(Event(EventKind.Shift, person))
    assert getattr(event, attr)() is None
    getattr(event, setter)(value, undo=True)
    assert getattr(event, attr)() == value
    scene.undo()
    assert getattr(event, attr)() is None


@pytest.mark.skip(reason="Validation code needs to be added for importing journal notes in personal app")
def test_read_filters_invalid_relationshipTargets(scene, caplog):
    """Test that invalid person IDs in relationshipTargets are filtered and logged."""
    from pkdiagram.scene import Scene

    person = scene.addItem(Person())
    target = scene.addItem(Person())

    event = scene.addItem(
        Event(
            EventKind.Shift,
            person,
            dateTime=util.Date(2020, 1, 1),  # Need dateTime to avoid pruning
            relationship=RelationshipKind.Distance,
            relationshipTargets=[target],
        )
    )
    assert event.relationshipTargets() == [target]

    # Save the scene
    data = scene.data()

    # Corrupt the data by adding a non-existent person ID to relationshipTargets
    for eventChunk in data["events"]:
        if eventChunk["id"] == event.id:
            eventChunk["relationshipTargets"].append(99999)  # Non-existent ID
            break

    # Load into a new scene - should not crash
    newScene = Scene()
    newScene.read(data)

    # Verify error was logged
    assert "invalid relationshipTarget IDs" in caplog.text
    assert "99999" in caplog.text

    # Verify the invalid ID was filtered out
    loadedEvent = newScene.find(id=event.id)
    assert len(loadedEvent.relationshipTargets()) == 1
    loadedTarget = loadedEvent.relationshipTargets()[0]
    assert loadedTarget.id == target.id

    newScene.deinit()


@pytest.mark.skip(reason="Validation code needs to be added for importing journal notes in personal app")
def test_read_filters_invalid_relationshipTriangles(scene, caplog):
    """Test that invalid person IDs in relationshipTriangles are filtered and logged."""
    from pkdiagram.scene import Scene

    person = scene.addItem(Person())
    target = scene.addItem(Person())
    triangle = scene.addItem(Person())

    event = scene.addItem(
        Event(
            EventKind.Shift,
            person,
            dateTime=util.Date(2020, 1, 1),  # Need dateTime to avoid pruning
            relationship=RelationshipKind.Inside,
            relationshipTargets=[target],
            relationshipTriangles=[triangle],
        )
    )
    assert event.relationshipTriangles() == [triangle]

    # Save the scene
    data = scene.data()

    # Corrupt the data by adding a non-existent person ID to relationshipTriangles
    for eventChunk in data["events"]:
        if eventChunk["id"] == event.id:
            eventChunk["relationshipTriangles"].append(88888)  # Non-existent ID
            break

    # Load into a new scene - should not crash
    newScene = Scene()
    newScene.read(data)

    # Verify error was logged
    assert "invalid relationshipTriangle IDs" in caplog.text
    assert "88888" in caplog.text

    # Verify the invalid ID was filtered out
    loadedEvent = newScene.find(id=event.id)
    assert len(loadedEvent.relationshipTriangles()) == 1
    loadedTriangle = loadedEvent.relationshipTriangles()[0]
    assert loadedTriangle.id == triangle.id

    newScene.deinit()


