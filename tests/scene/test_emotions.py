import pytest
from pkdiagram.pyqt import QPointF, QDateTime
from pkdiagram import util
from pkdiagram.scene import Scene, Person, Emotion, Layer
from pkdiagram.scene.emotions import Jig, FannedBox
from pkdiagram.models import SearchModel
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
    personA = Person()
    personB = Person()
    fusion = Emotion(kind=util.ITEM_FUSION, personA=personA, personB=personB)
    projection = Emotion(kind=util.ITEM_PROJECTION, personA=personA, personB=personB)
    scene.addItems(personA, personB, fusion, projection)

    assert fusion.fannedBox is not None
    assert projection.fannedBox is not None
    assert fusion.fannedBox is projection.fannedBox
    assert TestFannedBox.test_getCount() == 1


def test_FannedBox_add_multiple(TestFannedBox):
    scene = Scene()
    personA = Person()
    personB = Person()
    fusion = Emotion(kind=util.ITEM_FUSION, personA=personA, personB=personB)
    projection = Emotion(kind=util.ITEM_PROJECTION, personA=personA, personB=personB)
    toward = Emotion(kind=util.ITEM_TOWARD, personA=personA, personB=personB)
    scene.addItem(personA, personB)
    # Add these one at a time to better simulate clicking
    scene.addItem(fusion)
    scene.addItem(projection)
    scene.addItem(toward)

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
    personA = Person()
    personB = Person()
    fusion = Emotion(kind=util.ITEM_FUSION, personA=personA, personB=personB)
    projection = Emotion(kind=util.ITEM_PROJECTION, personA=personA, personB=personB)
    scene.addItems(personA, personB, fusion, projection)
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


def test_FannedBox_peers_multiple():
    """
    fusion  [2001/02/01 - 2001/04/02]
    proj            [2001/03/01 - ]
    toward              [2001/04/01 - ]
    """
    scene = Scene()
    personA = Person()
    personB = Person()
    personA.birthEvent.setDateTime(util.Date(2001, 1, 1))
    fusion = Emotion(
        kind=util.ITEM_FUSION,
        personA=personA,
        personB=personB,
        startDateTime=util.Date(2001, 2, 1),
        endDateTime=util.Date(2001, 4, 2),
    )
    projection = Emotion(
        kind=util.ITEM_PROJECTION,
        personA=personA,
        personB=personB,
        isDateRange=True,
        startDateTime=util.Date(2001, 3, 1),
    )
    toward = Emotion(
        kind=util.ITEM_TOWARD,
        personA=personA,
        personB=personB,
        isDateRange=True,
        startDateTime=util.Date(2001, 4, 1),
    )
    scene.addItems(personA, personB, fusion, projection, toward)

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


def test_FannedBox_peers_different_tags():
    ## TODO: Not sure if emotions respond to tags?
    scene = Scene(tags=["tag-1"])
    searchModel = SearchModel()
    searchModel.scene = scene
    searchModel.tagsChanged.connect(lambda x: scene.setActiveTags(x))
    personA = Person()
    personB = Person()
    fusion = Emotion(kind=util.ITEM_FUSION, personA=personA, personB=personB)
    projection = Emotion(
        kind=util.ITEM_PROJECTION, personA=personA, personB=personB, tags=["tag-1"]
    )
    scene.addItems(personA, personB, fusion, projection)
    assert fusion.peers() == {projection}
    assert projection.peers() == {fusion}
    assert fusion.isVisible() == True
    assert projection.isVisible() == True

    searchModel.setTags(["tag-1"])
    assert fusion.peers() == set()
    assert projection.peers() == set()
    assert fusion.isVisible() == False
    assert projection.isVisible() == True

    searchModel.setTags([])
    assert fusion.peers() == {projection}
    assert projection.peers() == {fusion}
    assert fusion.isVisible() == True
    assert projection.isVisible() == True
    assert fusion.fannedBox.dirty == False


@pytest.mark.skip("not sure what this should test")
def test_FannedBox_posDelta_adapt():
    scene = Scene()
    personA = Person()
    personB = Person()
    fusion = Emotion(kind=util.ITEM_FUSION, personA=personA, personB=personB)
    projection = Emotion(kind=util.ITEM_PROJECTION, personA=personA, personB=personB)
    scene.addItems(personA, personB, fusion, projection)
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
    personA = Person(name="A")
    personB = Person(name="B")
    conflict = Emotion(personA, personB, kind=util.ITEM_CONFLICT)
    scene.addItems(personA, personB, conflict)

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


def test_honors_searchModel_tags():
    TAGS = ["triangle"]
    scene = Scene()
    personA = Person(name="A")
    personB = Person(name="B")
    conflict = Emotion(personA, personB, kind=util.ITEM_CONFLICT, tags=TAGS)
    scene.addItems(personA, personB, conflict)
    searchModel = SearchModel()
    searchModel.scene = scene
    searchModel.tags = TAGS
    searchModel.tagsChanged.connect(lambda x: scene.setActiveTags(x))
    assert conflict.isVisible() == True

    searchModel.tags = ["nowhere"]
    assert conflict.isVisible() == False

    searchModel.tags = TAGS
    assert conflict.isVisible() == True


def test_honors_searchModel_tags_plus_dates():
    TAGS = ["triangle"]
    scene = Scene()
    personA = Person(name="A")
    personB = Person(name="B")
    conflict = Emotion(
        personA,
        personB,
        kind=util.ITEM_CONFLICT,
        startDateTime=util.Date(2000, 1, 1),
        endDateTime=util.Date(2001, 1, 1),
        tags=TAGS,
    )
    scene.addItems(personA, personB, conflict)
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


def test_persons_hidden_tags_shown():
    TAGS = ["triangle"]
    scene = Scene()
    searchModel = SearchModel()
    searchModel.scene = scene
    personA = Person(name="A")
    personB = Person(name="B")
    conflict = Emotion(
        personA,
        personB,
        kind=util.ITEM_CONFLICT,
        startDateTime=util.Date(2000, 1, 1),
        endDateTime=util.Date(2001, 1, 1),
        tags=TAGS,
    )
    layer = Layer(name="View 1")
    scene.addItems(personA, personB, conflict, layer)
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


def test_descriptions_diff_dates():
    personA = Person(name="A")
    personB = Person(name="B")
    conflict = Emotion(
        personA,
        personB,
        kind=util.ITEM_CONFLICT,
        startDateTime=util.Date(2000, 1, 1),
        endDateTime=util.Date(2001, 1, 1),
    )
    assert conflict.startEvent.description() == "Conflict began"
    assert conflict.endEvent.description() == "Conflict ended"


def test_descriptions_same_dates():
    personA = Person(name="A")
    personB = Person(name="B")
    conflict = Emotion(
        personA,
        personB,
        kind=util.ITEM_CONFLICT,
        startDateTime=util.Date(2000, 1, 1),
        endDateTime=util.Date(2000, 1, 1),
    )
    assert conflict.startEvent.description() == "Conflict"
    assert conflict.endEvent.description() == None


def test_descriptions_no_dates():
    personA = Person(name="A")
    personB = Person(name="B")
    conflict = Emotion(RelationshipKind.Conflict, personA, personB)
    assert conflict.startEvent.description() == None
    assert conflict.endEvent.description() == None


def test_add_emotion_sets_scene_currentDate():

    START_DATETIME = util.Date(2001, 1, 1, 6, 7)

    scene = Scene()
    personA = Person(name="A")
    personB = Person(name="B")
    conflict = Emotion(
        personA, personB, kind=util.ITEM_CONFLICT, startDateTime=START_DATETIME
    )
    scene.addItem(conflict)
    assert scene.currentDateTime() == START_DATETIME


def test_mirror_notes_set_from_item():
    NOTES = "bleh"

    personA, personB = Person(), Person()
    emotion = Emotion(personA=personA, personB=personB, kind=util.ITEM_CONFLICT)
    scene = Scene()
    scene.addItem(emotion)
    emotion.setNotes(NOTES)
    assert emotion.startEvent.notes() == NOTES


def test_mirror_notes_set_from_startEvent():
    NOTES = "bleh"

    personA, personB = Person(), Person()
    emotion = Emotion(personA=personA, personB=personB, kind=util.ITEM_CONFLICT)
    scene = Scene()
    scene.addItem(emotion)
    emotion.startEvent.setNotes(NOTES)
    assert emotion.notes() == NOTES


def test_emotion_intensity_defers_to_event():
    from pkdiagram.scene import Event, EventKind

    scene = Scene()
    personA = Person(name="A")
    personB = Person(name="B")

    event = Event(
        kind=EventKind.Shift,
        person=personA,
        relationship=RelationshipKind.Conflict,
        relationshipTargets=[personB],
    )
    event.setRelationshipIntensity(75)

    emotion = Emotion(kind=RelationshipKind.Conflict, target=personB, event=event)

    scene.addItems(personA, personB, event, emotion)

    assert emotion.intensity() == 75
    assert emotion.intensity() == event.relationshipIntensity()


def test_emotion_color_defers_to_event():
    from pkdiagram.scene import Event, EventKind

    scene = Scene()
    personA = Person(name="A")
    personB = Person(name="B")

    event = Event(
        kind=EventKind.Shift,
        person=personA,
        relationship=RelationshipKind.Distance,
        relationshipTargets=[personB],
    )
    event.setColor("#FF5733")

    emotion = Emotion(kind=RelationshipKind.Distance, target=personB, event=event)

    scene.addItems(personA, personB, event, emotion)

    assert emotion.color() == "#FF5733"
    assert emotion.color() == event.color()


def test_emotion_notes_defers_to_event():
    from pkdiagram.scene import Event, EventKind

    scene = Scene()
    personA = Person(name="A")
    personB = Person(name="B")

    event = Event(
        kind=EventKind.Shift,
        person=personA,
        relationship=RelationshipKind.Conflict,
        relationshipTargets=[personB],
    )
    event.setNotes("Important relationship notes")

    emotion = Emotion(kind=RelationshipKind.Conflict, target=personB, event=event)

    scene.addItems(personA, personB, event, emotion)

    assert emotion.notes() == "Important relationship notes"
    assert emotion.notes() == event.notes()


def test_emotion_properties_fallback_without_event():
    scene = Scene()
    personA = Person(name="A")
    personB = Person(name="B")

    emotion = Emotion(kind=RelationshipKind.Conflict, target=personB)
    emotion.prop("color").set("#123456")
    emotion.prop("notes").set("Local notes")

    scene.addItems(personA, personB, emotion)

    assert emotion.color() == "#123456"
    assert emotion.notes() == "Local notes"
    assert emotion.intensity() == 0
