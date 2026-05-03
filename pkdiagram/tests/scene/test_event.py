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


def test_read_filters_invalid_relationshipTargets(scene, caplog):
    """Bad ids in relationshipTargets are filtered out, the valid target
    is preserved, and a structured warning identifies the dropped id."""
    import logging
    from pkdiagram.scene import Scene

    person = scene.addItem(Person())
    target = scene.addItem(Person())

    event = scene.addItem(
        Event(
            EventKind.Shift,
            person,
            dateTime=util.Date(2020, 1, 1),
            relationship=RelationshipKind.Distance,
            relationshipTargets=[target],
        )
    )
    assert event.relationshipTargets() == [target]

    data = scene.data()
    for eventChunk in data["events"]:
        if eventChunk["id"] == event.id:
            eventChunk["relationshipTargets"].append(99999)
            break

    newScene = Scene()
    with caplog.at_level(logging.WARNING):
        newScene.read(data)

    assert "dangling" in caplog.text.lower()
    assert "99999" in caplog.text

    loadedEvent = newScene.find(id=event.id)
    assert len(loadedEvent.relationshipTargets()) == 1
    assert loadedEvent.relationshipTargets()[0].id == target.id

    resaved = newScene.data()
    resavedEvent = next(e for e in resaved["events"] if e["id"] == event.id)
    assert 99999 not in resavedEvent["relationshipTargets"]

    newScene.deinit()


def test_read_filters_invalid_relationshipTriangles(scene, caplog):
    """Bad ids in relationshipTriangles are filtered out, the valid triangle
    is preserved, and a structured warning identifies the dropped id."""
    import logging
    from pkdiagram.scene import Scene

    person = scene.addItem(Person())
    target = scene.addItem(Person())
    triangle = scene.addItem(Person())

    event = scene.addItem(
        Event(
            EventKind.Shift,
            person,
            dateTime=util.Date(2020, 1, 1),
            relationship=RelationshipKind.Inside,
            relationshipTargets=[target],
            relationshipTriangles=[triangle],
        )
    )
    assert event.relationshipTriangles() == [triangle]

    data = scene.data()
    for eventChunk in data["events"]:
        if eventChunk["id"] == event.id:
            eventChunk["relationshipTriangles"].append(88888)
            break

    newScene = Scene()
    with caplog.at_level(logging.WARNING):
        newScene.read(data)

    assert "dangling" in caplog.text.lower()
    assert "88888" in caplog.text

    loadedEvent = newScene.find(id=event.id)
    assert len(loadedEvent.relationshipTriangles()) == 1
    assert loadedEvent.relationshipTriangles()[0].id == triangle.id

    newScene.deinit()


def test_read_drops_shift_with_unresolvable_person(scene, caplog):
    """Shift event whose person id resolves to nothing is dropped on load
    rather than crashing _do_addItem on `person.updateEvents()`."""
    import logging
    from pkdiagram.scene import Scene

    person = scene.addItem(Person())
    target = scene.addItem(Person())
    event = scene.addItem(
        Event(
            EventKind.Shift,
            person,
            dateTime=util.Date(2020, 1, 1),
            relationship=RelationshipKind.Distance,
            relationshipTargets=[target],
        )
    )

    data = scene.data()
    for eventChunk in data["events"]:
        if eventChunk["id"] == event.id:
            eventChunk["person"] = 77777
            break

    newScene = Scene()
    with caplog.at_level(logging.WARNING):
        newScene.read(data)

    assert "irrecoverable" in caplog.text.lower()
    assert newScene.find(id=event.id) is None
    assert newScene.find(id=person.id) is not None
    assert newScene.find(id=target.id) is not None

    newScene.deinit()


def test_read_drops_birth_with_unresolvable_child(scene, caplog):
    """Birth event whose child id resolves to nothing is dropped — otherwise
    _do_addItem crashes on `item.child().onEventAdded()`."""
    import logging
    from pkdiagram.scene import Scene

    parentA = scene.addItem(Person())
    parentB = scene.addItem(Person())
    child = scene.addItem(Person())
    from pkdiagram.scene import Marriage

    marriage = scene.addItem(Marriage(personA=parentA, personB=parentB))
    event = scene.addItem(
        Event(
            EventKind.Birth,
            person=parentA,
            spouse=parentB,
            child=child,
            dateTime=util.Date(2020, 1, 1),
        )
    )

    data = scene.data()
    for eventChunk in data["events"]:
        if eventChunk["id"] == event.id:
            eventChunk["child"] = 66666
            break

    newScene = Scene()
    with caplog.at_level(logging.WARNING):
        newScene.read(data)

    assert "irrecoverable" in caplog.text.lower()
    assert newScene.find(id=event.id) is None
    assert newScene.find(id=parentA.id) is not None

    newScene.deinit()


def test_read_drops_shift_with_no_resolved_targets(scene, caplog):
    """Shift with `relationship` set but every relationshipTarget id is
    dangling becomes a meaningless event — drop it."""
    import logging
    from pkdiagram.scene import Scene

    person = scene.addItem(Person())
    target = scene.addItem(Person())
    event = scene.addItem(
        Event(
            EventKind.Shift,
            person,
            dateTime=util.Date(2020, 1, 1),
            relationship=RelationshipKind.Distance,
            relationshipTargets=[target],
        )
    )

    data = scene.data()
    for eventChunk in data["events"]:
        if eventChunk["id"] == event.id:
            eventChunk["relationshipTargets"] = [55555]
            break

    newScene = Scene()
    with caplog.at_level(logging.WARNING):
        newScene.read(data)

    assert newScene.find(id=event.id) is None
    assert "irrecoverable" in caplog.text.lower()

    newScene.deinit()


def test_diagramData_warns_on_outgoing_dangling_refs(scene, caplog):
    """Writer-side defense: if outgoing scene chunks reference person ids
    that aren't in the people list, a structured warning fires so the bug
    surfaces in telemetry. No data mutation."""
    import logging
    from btcopilot.schema import DiagramData

    person = scene.addItem(Person())
    target = scene.addItem(Person())
    scene.addItem(
        Event(
            EventKind.Shift,
            person,
            dateTime=util.Date(2020, 1, 1),
            relationship=RelationshipKind.Distance,
            relationshipTargets=[target],
        )
    )

    data = scene.data()
    targetId = target.id
    data["people"] = [p for p in data["people"] if p.get("id") != targetId]

    with caplog.at_level(logging.WARNING):

        class _Probe(scene.__class__):
            pass

        scene._reportDanglingRefs(data)

    assert "dangling" in caplog.text.lower()
    assert str(targetId) in caplog.text


