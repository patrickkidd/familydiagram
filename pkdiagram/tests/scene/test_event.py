import pytest

from btcopilot.schema import EventKind, RelationshipKind, VariableShift, DateCertainty
from pkdiagram import util
from pkdiagram.scene import Event, Person, Scene


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


@pytest.mark.parametrize(
    "relationship", [RelationshipKind.Inside, RelationshipKind.Outside]
)
def test_triangle(scene, relationship: RelationshipKind):
    """Test setting and getting triangle members."""
    from pkdiagram.pyqt import QDateTime

    person = scene.addItem(Person(name="Person"))
    spouse = scene.addItem(Person(name="Spouse"))
    third = scene.addItem(Person(name="Third"))
    event = scene.addItem(Event(EventKind.Shift, person))
    event.setDateTime(QDateTime.currentDateTime())
    event.setRelationship(relationship)
    event.setRelationshipTargets(spouse)
    event.setRelationshipTriangles(third)
    assert event.relationshipTargets() == [spouse]
    assert event.relationshipTriangles() == [third]
    # Triangle object should be created
    assert event.triangle() is not None
    assert event.triangle().mover() == person
    assert event.triangle().targets() == [spouse]
    assert event.triangle().triangles() == [third]
    assert event.triangle().layer() is not None
    assert event.triangle().layer().internal() is True

    # Verify badge shows when currentDateTime matches event date
    scene.setCurrentDateTime(event.dateTime())
    triangleEvents = person.triangleEventsForMover()
    assert len(triangleEvents) == 1
    assert triangleEvents[0] == event
    # Badge should have a path (not empty) when date matches - updateTriangleBadge() should be called by setCurrentDateTime
    assert not person.triangleBadgeItem.path().isEmpty(), (
        f"Badge empty. _activeTriangleEvent={person._activeTriangleEvent}, "
        f"event.dateTime()={event.dateTime()}, scene.currentDateTime()={scene.currentDateTime()}, "
        f"event.dateTime().date()={event.dateTime().date()}, currentDateTime.date()={scene.currentDateTime().date()}"
    )

    # Badge should be empty when date doesn't match
    scene.setCurrentDateTime(QDateTime())
    person.updateTriangleBadge()
    assert person.triangleBadgeItem.path().isEmpty()

    # Verify Triangle survives save/load round-trip
    data = {}
    scene.write(data)
    scene2 = Scene()
    scene2.read(data)
    event2 = [e for e in scene2.events() if e.relationship() == relationship][0]
    assert event2.triangle() is not None
    assert event2.triangle().mover().name() == "Person"
    assert [t.name() for t in event2.triangle().targets()] == ["Spouse"]
    assert [t.name() for t in event2.triangle().triangles()] == ["Third"]
    assert event2.triangle().layer() is not None
    assert event2.triangle().layer().internal() is True

    # Verify badge shows after file load
    scene2.setCurrentDateTime(event2.dateTime())
    person2 = event2.triangle().mover()
    triangleEvents2 = person2.triangleEventsForMover()
    assert len(triangleEvents2) == 1
    assert not person2.triangleBadgeItem.path().isEmpty()


def _create_triangle_scene(scene):
    """Helper to create a scene with a triangle event."""
    from pkdiagram.pyqt import QDateTime

    person = scene.addItem(Person(name="Person"))
    spouse = scene.addItem(Person(name="Spouse"))
    third = scene.addItem(Person(name="Third"))
    event = scene.addItem(Event(EventKind.Shift, person))
    event.setDateTime(QDateTime.currentDateTime())
    event.setRelationship(RelationshipKind.Inside)
    event.setRelationshipTargets(spouse)
    event.setRelationshipTriangles(third)
    return event


def test_triangle_layer_activation_deactivation(scene):
    """Test triangle layer can be activated and deactivated without errors."""
    event = _create_triangle_scene(scene)
    triangle = event.triangle()
    layer = triangle.layer()

    assert layer.active() is False
    assert scene.activeTriangle() is None

    layer.setActive(True)
    assert layer.active() is True
    assert scene.activeTriangle() == triangle

    layer.setActive(False)
    assert layer.active() is False
    assert scene.activeTriangle() is None


def test_triangle_layer_reset_all(scene):
    """Test resetAll properly deactivates triangle layer without errors."""
    event = _create_triangle_scene(scene)
    triangle = event.triangle()
    layer = triangle.layer()

    layer.setActive(True)
    assert layer.active() is True
    assert scene.activeTriangle() == triangle

    # This was causing errors when onLayerAnimationFinished tried to start Phase 2
    # during deactivation
    scene.resetAll()
    assert layer.active() is False
    assert scene.activeTriangle() is None


def test_triangle_layer_toggle_via_badge(scene):
    """Test badge click toggles triangle layer on and off."""
    from pkdiagram.pyqt import QDateTime

    event = _create_triangle_scene(scene)
    triangle = event.triangle()
    layer = triangle.layer()
    person = triangle.mover()

    scene.setCurrentDateTime(event.dateTime())
    person.updateTriangleBadge()

    assert layer.active() is False
    person.toggleTriangleLayer()
    assert layer.active() is True

    person.toggleTriangleLayer()
    assert layer.active() is False


def test_triangle_layer_no_emotional_unit(scene):
    """Test triangle layer does not have an emotional unit (unlike EU layers)."""
    event = _create_triangle_scene(scene)
    triangle = event.triangle()
    layer = triangle.layer()

    # Triangle layers are internal but don't have an emotional unit
    assert layer.internal() is True
    assert layer.emotionalUnit() is None


def test_triangle_with_emotional_unit_layers(scene):
    """Test triangle layer coexists with emotional unit layers."""
    from pkdiagram.scene import Marriage

    # Create an emotional unit (marriage creates one)
    personA = scene.addItem(Person(name="A"))
    personB = scene.addItem(Person(name="B"))
    marriage = scene.addItem(Marriage(personA=personA, personB=personB))
    eu_layer = marriage.emotionalUnit().layer()

    # Create a triangle
    event = _create_triangle_scene(scene)
    triangle_layer = event.triangle().layer()

    # Both should be internal layers
    internal_layers = scene.layers(onlyInternal=True)
    assert eu_layer in internal_layers
    assert triangle_layer in internal_layers

    # EU layer has emotionalUnit, triangle layer doesn't
    assert eu_layer.emotionalUnit() is not None
    assert triangle_layer.emotionalUnit() is None


def test_triangle_deactivate_via_scene_method(scene):
    """Test scene.deactivateTriangle() works correctly."""
    event = _create_triangle_scene(scene)
    triangle = event.triangle()
    layer = triangle.layer()

    layer.setActive(True)
    assert scene.activeTriangle() == triangle

    scene.deactivateTriangle()
    assert layer.active() is False
    assert scene.activeTriangle() is None


def test_triangle_next_layer_deactivates_triangle(scene):
    """Test switching to custom layer deactivates triangle layer."""
    from pkdiagram.scene import Layer

    event = _create_triangle_scene(scene)
    triangle = event.triangle()
    triangle_layer = triangle.layer()

    # Create a custom layer
    custom_layer = scene.addItem(Layer(name="Custom"))

    # Activate triangle
    triangle_layer.setActive(True)
    assert scene.activeTriangle() == triangle

    # Switch to custom layer via setExclusiveCustomLayerActive
    scene.setExclusiveCustomLayerActive(custom_layer)

    # Triangle should be deactivated
    assert triangle_layer.active() is False
    assert scene.activeTriangle() is None
    assert custom_layer.active() is True
