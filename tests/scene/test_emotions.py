import pytest
from pkdiagram.pyqt import QPointF, QDateTime
from pkdiagram import util
from pkdiagram.scene import Scene, Person, Emotion, Layer, ItemMode
from pkdiagram.scene.emotions import Jig, FannedBox
from pkdiagram.models import SearchModel
from pkdiagram.scene import EventKind, Event
from pkdiagram.scene.relationshipkind import RelationshipKind


@pytest.fixture
def TestFannedBox(mocker):
    count = 0

    class _TestFannedBox(FannedBox):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            nonlocal count
            count += 1

        @staticmethod
        def test_getCount():
            nonlocal count
            return count

    mocker.patch("pkdiagram.scene.emotions.FannedBox", _TestFannedBox)
    return _TestFannedBox


def test_divideBy_2():
    personA = Person()
    personA.setPos(QPointF(-10, 10))
    width = 5.0
    step = 2.0
    circA = 6
    jig = Jig(personA=personA, pointB=QPointF(-50, 50), width=width, circA=circA)

    delta = jig.p1 - jig.aP
    jig1, jig2 = jig.divideBy(2)

    assert jig1.aP - jig2.aP == delta
    assert jig1.bP - jig2.bP == delta
    assert jig1.p1 - jig2.p1 == delta
    assert jig1.p2 - jig2.p2 == delta
    assert jig1.p3 - jig2.p3 == delta
    assert jig1.p4 - jig2.p4 == delta


def test_divideBy_3():
    personA = Person()
    personA.setPos(QPointF(-10, 10))
    width = 5.0
    step = 2.0
    circA = 6
    jig = Jig(personA=personA, pointB=QPointF(-50, 50), width=width, circA=circA)

    delta = jig.p1 - jig.aP
    jig1, jig2, jig3 = jig.divideBy(3)

    assert jig1.aP - jig.aP == delta
    assert jig1.bP - jig.bP == delta
    assert jig1.p1 - jig.p1 == delta
    assert jig1.p2 - jig.p2 == delta
    assert jig1.p3 - jig.p3 == delta
    assert jig1.p4 - jig.p4 == delta

    assert jig2.aP - jig3.aP == delta
    assert jig2.bP - jig3.bP == delta
    assert jig2.p1 - jig3.p1 == delta
    assert jig2.p2 - jig3.p2 == delta
    assert jig2.p3 - jig3.p3 == delta
    assert jig2.p4 - jig3.p4 == delta


def test_divideBy_4():
    personA = Person()
    personA.setPos(QPointF(-10, 10))
    width = 5.0
    step = 2.0
    circA = 6
    jig = Jig(personA=personA, pointB=QPointF(-50, 50), width=width, circA=circA)

    delta = jig.p1 - jig.aP
    jig1, jig2, jig3, jig4 = jig.divideBy(4)

    assert jig1.aP - jig2.aP == delta
    assert jig1.bP - jig2.bP == delta
    assert jig1.p1 - jig2.p1 == delta
    assert jig1.p2 - jig2.p2 == delta
    assert jig1.p3 - jig2.p3 == delta
    assert jig1.p4 - jig2.p4 == delta

    assert jig2.aP - jig3.aP == delta * -2
    assert jig2.bP - jig3.bP == delta * -2
    assert jig2.p1 - jig3.p1 == delta * -2
    assert jig2.p2 - jig3.p2 == delta * -2
    assert jig2.p3 - jig3.p3 == delta * -2
    assert jig2.p4 - jig3.p4 == delta * -2

    assert jig3.aP - jig4.aP == delta * 3
    assert jig3.bP - jig4.bP == delta * 3
    assert jig3.p1 - jig4.p1 == delta * 3
    assert jig3.p2 - jig4.p2 == delta * 3
    assert jig3.p3 - jig4.p3 == delta * 3
    assert jig3.p4 - jig4.p4 == delta * 3


def test_FannedBox_add(TestFannedBox):
    scene = Scene()
    personA, personB = scene.addItems(Person(), Person())
    fusion, projection = scene.addItems(
        Emotion(RelationshipKind.Fusion, personB, person=personA),
        Emotion(RelationshipKind.Projection, personB, person=personA),
    )

    assert fusion.fannedBox is not None
    assert projection.fannedBox is not None
    assert fusion.fannedBox is projection.fannedBox
    assert TestFannedBox.test_getCount() == 1


def test_FannedBox_add_multiple(TestFannedBox):
    scene = Scene()
    personA, personB = scene.addItems(Person(), Person())
    # Add these one at a time to better simulate clicking
    fusion = scene.addItem(Emotion(RelationshipKind.Fusion, personB, person=personA))
    projection = scene.addItem(
        Emotion(RelationshipKind.Projection, personB, person=personA)
    )
    toward = scene.addItem(Emotion(RelationshipKind.Toward, personB, person=personA))

    assert fusion.fannedBox is not None
    assert projection.fannedBox is not None
    assert toward.fannedBox is not None
    assert fusion.fannedBox is projection.fannedBox
    assert fusion.fannedBox is toward.fannedBox
    assert TestFannedBox.test_getCount() == 1


def test_FannedBox_remove(TestFannedBox):

    def find_boxes():
        nonlocal scene
        try:
            ret = [x for x in scene.items() if isinstance(x, FannedBox)]
        except StopIteration as e:
            ret = []
        return ret

    scene = Scene()
    personA, personB = scene.addItems(Person(), Person())
    fusion, projection = scene.addItems(
        Emotion(RelationshipKind.Fusion, personB, person=personA),
        Emotion(RelationshipKind.Projection, personB, person=personA),
    )
    scene.removeItem(projection)
    assert fusion.fannedBox is not None
    assert projection.fannedBox is None
    assert find_boxes() == [fusion.fannedBox]
    assert TestFannedBox.test_getCount() == 1
    assert fusion.fannedBox.currentOffsetFor(fusion) == QPointF()

    scene.removeItem(fusion)
    assert fusion.fannedBox is None
    assert find_boxes() == []
    assert TestFannedBox.test_getCount() == 1


def test_FannedBox_peers_multiple(scene):
    """
    fusion  [2001/02/01 - 2001/04/02]
    proj            [2001/03/01 - ]
    toward              [2001/04/01 - ]
    """
    personA, personB = scene.addItems(Person(), Person())
    fusionEvent = scene.addItem(
        Event(
            EventKind.Shift,
            personA,
            relationship=RelationshipKind.Fusion,
            relationshipTargets=[personB],
            dateTime=util.Date(2001, 2, 1),
            endDateTime=util.Date(2001, 4, 2),
        )
    )
    fusion = scene.emotionsFor(fusionEvent)[0]

    projectionEvent = scene.addItem(
        Event(
            EventKind.Shift,
            personA,
            relationship=RelationshipKind.Projection,
            relationshipTargets=[personB],
            dateTime=util.Date(2001, 3, 1),
        )
    )
    projection = scene.emotionsFor(projectionEvent)[0]

    towardEvent = scene.addItem(
        Event(
            EventKind.Shift,
            personA,
            relationship=RelationshipKind.Toward,
            relationshipTargets=[personB],
            dateTime=util.Date(2001, 4, 1),
        )
    )
    toward = scene.emotionsFor(towardEvent)[0]

    scene.setCurrentDateTime(util.Date(2001, 1, 1))
    assert fusion.peers() == set()
    assert projection.peers() == set()
    assert toward.peers() == set()

    scene.setCurrentDateTime(util.Date(2001, 2, 1))
    assert fusion.peers() == set()
    assert projection.peers() == set()
    assert toward.peers() == set()

    scene.setCurrentDateTime(util.Date(2001, 3, 1))
    assert fusion.peers() == {projection}
    assert projection.peers() == {fusion}
    assert toward.peers() == set()

    scene.setCurrentDateTime(util.Date(2001, 4, 1))
    assert fusion.peers() == {projection, toward}
    assert projection.peers() == {fusion, toward}
    assert toward.peers() == {fusion, projection}

    scene.setCurrentDateTime(util.Date(2001, 5, 1))
    assert fusion.peers() == set()
    assert projection.peers() == {toward}
    assert toward.peers() == {projection}


def test_FannedBox_peers_different_layers(scene):
    layer = scene.addItem(Layer(name="View 1"))
    personA, personB = scene.addItems(Person(), Person())
    personA.setLayers([layer])
    fusion, projection = scene.addItems(
        Emotion(RelationshipKind.Fusion, personB, person=personA),
        Emotion(RelationshipKind.Projection, personB, person=personA),
    )
    personA.setLayers([layer.id])
    personB.setLayers([layer.id])
    projection.setLayers([layer.id])
    assert fusion.peers() == {projection}
    assert projection.peers() == {fusion}
    assert fusion.isVisible() == True
    assert projection.isVisible() == True

    layer.setActive(True)
    assert fusion.peers() == set()
    assert projection.peers() == set()
    assert fusion.isVisible() == False
    assert projection.isVisible() == True

    layer.setActive(False)
    assert fusion.peers() == {projection}
    assert projection.peers() == {fusion}
    assert fusion.isVisible() == True
    assert projection.isVisible() == True
    assert fusion.fannedBox.dirty == False


@pytest.mark.skip("not sure what this should test")
def test_FannedBox_posDelta_adapt():
    scene = Scene()
    personA, personB = scene.addItems(Person(), Person())
    fusion, projection = scene.addItems(
        Emotion(RelationshipKind.Fusion, personB, person=personA),
        Emotion(RelationshipKind.Projection, personB, person=personA),
    )
    personA.setPos(100, 100)
    personB.setPos(-100, -100)
    fannedBox = fusion.fannedBox
    assert fusion.isVisible() == True
    assert projection.isVisible() == True

    personA.setPos(200, 200)  # Should stop anim and snap to end?
    assert fannedBox.currentOffsetFor(fusion) == fannedBox.endPosDeltaFor(fusion)
    assert fannedBox.currentOffsetFor(projection) == fannedBox.endPosDeltaFor(
        projection
    )


@pytest.mark.skip("Need to replace with a meaningful test")
def test_shouldShowFor():
    scene = Scene()
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))
    conflict = scene.addItem(
        Emotion(RelationshipKind.Conflict, personB, person=personA)
    )

    # No tags
    assert conflict.shouldShowFor(QDateTime()) == True

    # Parents not shown
    conflict.setTags(["tags1"])
    assert conflict.shouldShowFor(QDateTime()) == False

    # One parent shown, one not
    personA.setTags(["tags1"])
    conflict.setTags(["tags1"])
    assert conflict.shouldShowFor(QDateTime()) == False

    # One parent shown, one not
    personA.setTags(["tags1"])
    personB.setTags(["tags2"])
    conflict.setTags(["tags1"])
    assert conflict.shouldShowFor(QDateTime()) == False

    # Both parent shown + emotion shown
    personA.setTags(["tags1"])
    personB.setTags(["tags1"])
    conflict.setTags(["tags1"])
    assert conflict.shouldShowFor(QDateTime()) == True

    # Both parent shown + emotion hidden
    personA.setTags(["tags1"])
    personB.setTags(["tags1"])
    conflict.setTags([])
    assert conflict.shouldShowFor(QDateTime()) == True

    # Both parent shown + emotion hidden
    personA.setTags(["tags1"])
    personB.setTags(["tags1"])
    conflict.setTags(["tags2"])
    assert conflict.shouldShowFor(QDateTime()) == True


def test_honors_searchModel_tags_plus_dates():
    TAGS = ["triangle"]
    scene = Scene()
    personA = Person(name="A")
    personB = Person(name="B")
    scene.addItems(personA, personB)
    conflictEvent = scene.addItem(
        Event(
            EventKind.Shift,
            personA,
            relationship=RelationshipKind.Conflict,
            relationshipTargets=[personB],
            dateTime=util.Date(2000, 1, 1),
            endDateTime=util.Date(2001, 1, 1),
        )
    )
    conflict = scene.emotionsFor(conflictEvent)[0]
    conflict.setTags(TAGS)
    scene.setCurrentDateTime(util.Date(1990, 1, 1))
    assert conflict.isVisible() == False

    # has to match both date and tags
    scene.setCurrentDateTime(util.Date(2000, 1, 1))
    assert conflict.isVisible() == True

    # middle of date range
    scene.setCurrentDateTime(util.Date(2000, 5, 1))
    assert conflict.isVisible() == True

    # end of date range
    scene.setCurrentDateTime(util.Date(2001, 1, 1))
    assert conflict.isVisible() == False

    # after date range
    scene.setCurrentDateTime(util.Date(2002, 1, 1))
    assert conflict.isVisible() == False


def test_persons_hidden_tags_shown(scene):
    TAGS = ["triangle"]
    searchModel = SearchModel()
    searchModel.scene = scene
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))
    event = scene.addItem(
        Event(
            EventKind.Shift,
            personA,
            relationship=RelationshipKind.Conflict,
            relationshipTargets=[personB],
            dateTime=util.Date(2000, 1, 1),
            endDateTime=util.Date(2001, 1, 1),
        )
    )
    conflict = scene.emotionsFor(event)[0]
    conflict.prop("tags").set(TAGS)

    layer = scene.addItem(Layer(name="View 1"))

    personA.setLayers([layer.id])
    searchModel.setTags(TAGS)
    scene.setCurrentDateTime(util.Date(2000, 5, 1))  # during conflict
    assert personA.isVisible() == True
    assert personB.isVisible() == True
    assert conflict.isVisible() == True

    layer.setActive(True)
    assert personA.isVisible() == True
    assert personB.isVisible() == False
    assert conflict.isVisible() == False


def test_descriptions_diff_dates(scene):
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))
    event = scene.addItem(
        Event(
            EventKind.Shift,
            personA,
            relationship=RelationshipKind.Conflict,
            relationshipTargets=[personB],
            dateTime=util.Date(2000, 1, 1),
            endDateTime=util.Date(2001, 1, 1),
        )
    )
    conflict = scene.emotionsFor(event)[0]
    assert conflict.sourceEvent().description() == "Shift"


def test_descriptions_same_dates(scene):
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))
    event = scene.addItem(
        Event(
            EventKind.Shift,
            personA,
            relationship=RelationshipKind.Conflict,
            relationshipTargets=[personB],
            dateTime=util.Date(2000, 1, 1),
            endDateTime=util.Date(2000, 1, 1),
        )
    )
    conflict = scene.emotionsFor(event)[0]
    assert event.description() == "Shift"


def test_add_emotion_sets_scene_currentDate():

    START_DATETIME = util.Date(2001, 1, 1, 6, 7)

    scene = Scene()
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))
    event = scene.addItem(
        Event(
            EventKind.Shift,
            personA,
            relationship=RelationshipKind.Conflict,
            relationshipTargets=[personB],
            dateTime=START_DATETIME,
        )
    )
    assert scene.currentDateTime() == START_DATETIME


def test_emotion_intensity_defers_to_event():
    scene = Scene()
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))

    event = scene.addItem(
        Event(
            EventKind.Shift,
            personA,
            relationship=RelationshipKind.Conflict,
            relationshipTargets=[personB],
            relationshipIntensity=1,
        )
    )
    emotion = scene.emotionsFor(event)[0]
    emotion.prop("intensity").set(2)

    assert emotion.intensity() == 1  # Should defer to event
    assert emotion.intensity() == event.relationshipIntensity()


def test_emotion_color_defers_to_event():
    scene = Scene()
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))

    event = scene.addItem(
        Event(
            kind=EventKind.Shift,
            person=personA,
            relationship=RelationshipKind.Distance,
            relationshipTargets=[personB],
            color="#FF5733",
        )
    )
    emotion = scene.emotionsFor(event)[0]
    emotion.prop("color").set("#FF000")  # Set local property, should be ignored

    assert emotion.color() == "#FF5733"  # Should defer to event
    assert emotion.color() == event.color()


def test_emotion_notes_defers_to_event():
    scene = Scene()
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))

    event = scene.addItem(
        Event(
            kind=EventKind.Shift,
            person=personA,
            relationship=RelationshipKind.Conflict,
            relationshipTargets=[personB],
            notes="Important relationship notes",
        )
    )

    emotion = scene.emotionsFor(event)[0]
    emotion.prop("notes").set("some other notes")

    assert emotion.notes() == "Important relationship notes"
    assert emotion.notes() == event.notes()


def test_emotion_properties_fallback_without_event():
    scene = Scene()
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))

    emotion = scene.addItem(
        Emotion(
            RelationshipKind.Conflict,
            personB,
            person=personA,
            color="#123456",
            notes="Local notes",
        )
    )

    assert emotion.color() == "#123456"
    assert emotion.notes() == "Local notes"
    assert (
        emotion.intensity() == util.DEFAULT_EMOTION_INTENSITY
    )  # Uses local property default


def test_emotion_honors_layers_for_user_drawn():
    scene = Scene()
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))
    layer1, layer2 = scene.addItems(Layer(name="Layer 1"), Layer(name="Layer 2"))

    personA.setLayers([layer1.id, layer2.id])
    personB.setLayers([layer1.id, layer2.id])

    userDrawnEmotion = scene.addItem(
        Emotion(RelationshipKind.Conflict, personB, person=personA)
    )

    userDrawnEmotion.setLayers([layer1.id])
    assert userDrawnEmotion.layers() == [layer1.id]
    assert (
        userDrawnEmotion.shouldShowFor(util.Date(2020, 1, 1), layers=[layer1]) == True
    )
    assert (
        userDrawnEmotion.shouldShowFor(util.Date(2020, 1, 1), layers=[layer2]) == False
    )

    userDrawnEmotion.setLayers([layer1.id, layer2.id])
    assert (
        userDrawnEmotion.shouldShowFor(util.Date(2020, 1, 1), layers=[layer1]) == True
    )
    assert (
        userDrawnEmotion.shouldShowFor(util.Date(2020, 1, 1), layers=[layer2]) == True
    )

    userDrawnEmotion.setLayers([])
    assert (
        userDrawnEmotion.shouldShowFor(util.Date(2020, 1, 1), layers=[layer1]) == False
    )
    assert (
        userDrawnEmotion.shouldShowFor(util.Date(2020, 1, 1), layers=[layer2]) == False
    )


def test_emotion_ignores_layers_for_event_based():
    scene = Scene()
    personA, personB = scene.addItems(Person(name="A"), Person(name="B"))
    layer1, layer2 = scene.addItems(Layer(name="Layer 1"), Layer(name="Layer 2"))

    personA.setLayers([layer1.id, layer2.id])
    personB.setLayers([layer1.id, layer2.id])

    event = scene.addItem(
        Event(
            EventKind.Shift,
            personA,
            relationship=RelationshipKind.Conflict,
            relationshipTargets=[personB],
            dateTime=util.Date(2000, 1, 1),
        )
    )
    eventEmotion = scene.emotionsFor(event)[0]

    eventEmotion.setLayers([layer1.id])
    assert eventEmotion.shouldShowFor(util.Date(2000, 1, 1), layers=[layer1]) == True
    assert eventEmotion.shouldShowFor(util.Date(2000, 1, 1), layers=[layer2]) == True

    eventEmotion.setLayers([])
    assert eventEmotion.shouldShowFor(util.Date(2000, 1, 1), layers=[layer1]) == True
    assert eventEmotion.shouldShowFor(util.Date(2000, 1, 1), layers=[layer2]) == True
