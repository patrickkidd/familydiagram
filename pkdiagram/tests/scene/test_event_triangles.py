import pytest

from btcopilot.schema import EventKind, RelationshipKind
from pkdiagram.pyqt import QDateTime, QPointF
from pkdiagram.scene import Event, Person, Scene, Layer, LayerLabel, Marriage


@pytest.mark.parametrize(
    "relationship", [RelationshipKind.Inside, RelationshipKind.Outside]
)
def test_triangle(scene, relationship: RelationshipKind):
    """Test setting and getting triangle members."""
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

    person = scene.addItem(Person(name="Person"))
    spouse = scene.addItem(Person(name="Spouse"))
    third = scene.addItem(Person(name="Third"))
    person.setItemPosNow(QPointF(0, 0))
    spouse.setItemPosNow(QPointF(100, 100))
    third.setItemPosNow(QPointF(200, 200))
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

    event = _create_triangle_scene(scene)
    triangle = event.triangle()
    triangle_layer = triangle.layer()

    # Create a custom layer
    custom_layer = scene.addItem(Layer(name="Custom"))

    # Activate triangle
    triangle_layer.setActive(True)
    assert scene.activeTriangle() == triangle

    # Switch to custom layer via setExclusiveLayerActive
    scene.setExclusiveLayerActive(custom_layer)

    # Triangle should be deactivated
    assert triangle_layer.active() is False
    assert scene.activeTriangle() is None
    assert custom_layer.active() is True


def _create_multi_person_triangle_scene(scene):
    mover = scene.addItem(Person(name="Mover"))
    target1 = scene.addItem(Person(name="Target1"))
    target2 = scene.addItem(Person(name="Target2"))
    triangle1 = scene.addItem(Person(name="Triangle1"))
    triangle2 = scene.addItem(Person(name="Triangle2"))
    mover.setItemPosNow(QPointF(0, 0))
    target1.setItemPosNow(QPointF(100, 100))
    target2.setItemPosNow(QPointF(150, 100))
    triangle1.setItemPosNow(QPointF(200, 200))
    triangle2.setItemPosNow(QPointF(250, 200))
    event = scene.addItem(Event(EventKind.Shift, mover))
    event.setDateTime(QDateTime.currentDateTime())
    event.setRelationship(RelationshipKind.Inside)
    event.setRelationshipTargets([target1, target2])
    event.setRelationshipTriangles([triangle1, triangle2])
    return event


def test_triangle_cluster_labels_created_for_all_positions(scene):
    event = _create_multi_person_triangle_scene(scene)
    triangle = event.triangle()
    layer = triangle.layer()
    layer.setActive(True)
    triangle.startPhase2Animation()
    labels = triangle._clusterLabels
    assert len(labels) == 3
    assert all(isinstance(lbl, LayerLabel) for lbl in labels)
    label_texts = {lbl.text() for lbl in labels}
    assert "Mover" in label_texts
    assert "Target1, Target2" in label_texts
    assert "Triangle1, Triangle2" in label_texts


def test_triangle_cluster_labels_visible_when_layer_active(scene):
    event = _create_multi_person_triangle_scene(scene)
    triangle = event.triangle()
    layer = triangle.layer()
    layer.setActive(True)
    triangle.startPhase2Animation()
    for label in triangle._clusterLabels:
        assert label.isVisible() is True


def test_triangle_cluster_labels_removed_on_phase2_stop(scene):
    event = _create_multi_person_triangle_scene(scene)
    triangle = event.triangle()
    layer = triangle.layer()
    layer.setActive(True)
    triangle.startPhase2Animation()
    assert len(triangle._clusterLabels) == 3
    triangle.stopPhase2Animation()
    assert len(triangle._clusterLabels) == 0


def test_triangle_cluster_labels_for_single_person_positions(scene):
    event = _create_triangle_scene(scene)
    triangle = event.triangle()
    layer = triangle.layer()
    layer.setActive(True)
    triangle.startPhase2Animation()
    assert len(triangle._clusterLabels) == 3
    label_texts = {lbl.text() for lbl in triangle._clusterLabels}
    assert "Person" in label_texts
    assert "Spouse" in label_texts
    assert "Third" in label_texts
