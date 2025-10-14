import pytest

from pkdiagram.pyqt import Qt, QDateTime
from pkdiagram import util
from pkdiagram.scene import Person, Emotion, RelationshipKind, EventKind, Event
from pkdiagram.views import QmlDrawer


@pytest.fixture
def ep(qtbot, scene, qmlEngine):
    qmlEngine.setScene(scene)
    ep = QmlDrawer(
        qmlEngine, "qml/EmotionProperties.qml", propSheetModel="emotionModel"
    )
    ep.checkInitQml()
    ep.emotionModel = ep.rootProp("emotionModel")
    ep.setScene(scene)
    ep.show()
    qtbot.waitActive(ep)
    assert ep.isShown()

    yield ep

    ep.setScene(None)
    # ep.rootProp('emotionModel').items = []
    ep.hide()


def test_init_dated(scene, ep):

    COLOR = "#3c3c3c"
    INTENSITY = 2

    personA, personB = scene.addItems(Person(name="personA"), Person(name="personB"))
    event = scene.addItem(
        Event(
            kind=EventKind.Shift,
            person=personA,
            relationship=RelationshipKind.Projection,
            relationshipTargets=personB,
            relationshipIntensity=INTENSITY,
            color=COLOR,
        )
    )
    emotion = scene.emotionsFor(event)[0]

    #

    ep.show(emotion)
    intensityBox = ep.rootProp("intensityBox")
    colorBox = ep.rootProp("colorBox")
    titleLabel = ep.rootProp("titleLabel")
    assert colorBox.property("currentText") == COLOR
    assert titleLabel.property("text") == RelationshipKind.Projection.name
    assert intensityBox.property(
        "currentText"
    ) == util.emotionIntensityNameForIntensity(2)


def test_init_undated(scene, ep):

    COLOR = "#3c3c3c"
    INTENSITY = 2
    NOTES = "Here are some notes."

    personA, personB = scene.addItems(Person(name="personA"), Person(name="personB"))
    emotion = scene.addItem(
        Emotion(
            RelationshipKind.Projection,
            personB,
            person=personA,
            intensity=INTENSITY,
            notes=NOTES,
            color=COLOR,
        )
    )

    #

    ep.show(emotion)
    intensityBox = ep.rootProp("intensityBox")
    colorBox = ep.rootProp("colorBox")
    notesEdit = ep.rootProp("notesEdit")
    titleLabel = ep.rootProp("titleLabel")
    assert colorBox.property("currentText") == COLOR
    assert notesEdit.property("text") == NOTES
    assert titleLabel.property("text") == RelationshipKind.Projection.name
    assert intensityBox.property(
        "currentText"
    ) == util.emotionIntensityNameForIntensity(2)


def test_edit_dated(scene, ep):

    COLOR = "#3c3c3c"
    INTENSITY = 2
    NOTES = "Here are some notes."

    personA, personB = scene.addItems(Person(name="personA"), Person(name="personB"))
    event = scene.addItem(
        Event(
            kind=EventKind.Shift,
            person=personA,
            relationship=RelationshipKind.Projection,
            relationshipTargets=personB,
            relationshipIntensity=2,
            notes=NOTES,
            color=COLOR,
        )
    )
    emotion = scene.emotionsFor(event)[0]

    #

    ep.show(emotion)
    intensityBox = ep.rootProp("intensityBox")
    colorBox = ep.rootProp("colorBox")
    notesEdit = ep.rootProp("notesEdit")

    #

    ep.clickComboBoxItem(intensityBox, util.emotionIntensityNameForIntensity(INTENSITY))
    ep.clickComboBoxItem(colorBox, COLOR)
    ep.keyClicks(notesEdit, NOTES)
    ep.clickComboBoxItem(colorBox, COLOR)  # to move focus away from notes

    #

    assert emotion.kind() == RelationshipKind.Projection
    assert emotion.intensity() == INTENSITY
    assert emotion.notes().strip() == NOTES


def test_edit_undated(scene, ep):

    COLOR = "#3c3c3c"
    INTENSITY = 2
    NOTES = "Here are some notes."

    personA, personB = scene.addItems(Person(name="personA"), Person(name="personB"))
    emotion = scene.addItem(
        Emotion(
            RelationshipKind.Projection,
            personB,
            person=personA,
            intensity=INTENSITY,
            notes=NOTES,
            color=COLOR,
        )
    )

    #

    ep.show(emotion)
    intensityBox = ep.rootProp("intensityBox")
    colorBox = ep.rootProp("colorBox")
    notesEdit = ep.rootProp("notesEdit")

    #

    ep.clickComboBoxItem(intensityBox, util.emotionIntensityNameForIntensity(INTENSITY))
    ep.clickComboBoxItem(colorBox, COLOR)
    ep.keyClicks(notesEdit, NOTES)

    #

    assert emotion.kind() == RelationshipKind.Projection
    assert emotion.intensity() == INTENSITY
    assert emotion.notes().strip() == NOTES


def test_show_init_multiple_different(scene, ep):
    personA, personB = scene.addItems(Person(name="personA"), Person(name="personB"))

    event1 = Event(
        person=personA,
        kind=EventKind.Shift,
        relationship=RelationshipKind.Projection,
        relationshipTargets=personB,
        color="#3c3c3c",
        intensity=1,
        notes="Some notes",
    )
    event2 = Event(
        person=personA,
        kind=EventKind.Shift,
        relationship=RelationshipKind.Conflict,
        relationshipTargets=personB,
        color="#3c3c3c",
        intensity=1,
    )

    scene.addItems(event1, event2)
    emotion1 = scene.emotionsFor(event1)[0]
    emotion2 = scene.emotionsFor(event2)[0]

    ep.show([emotion1])
    model = ep.rootProp("emotionModel")
    assert model.color == event1.color()
    assert model.intensity == event1.relationshipIntensity()
    assert model.notes == event1.notes()

    ep.hide()
    ep.show([emotion1, emotion2])
    assert model.color == event1.color()
    assert model.intensity == event1.relationshipIntensity()
    assert model.notes == None

    ep.hide()
    event2.setColor("#00ff00")
    event2.setRelationshipIntensity(3)
    event2.setNotes("Different notes")
    ep.show([emotion1, emotion2])
    assert model.color == None
    assert model.intensity == 1  # pulls default, ignoring for now
    assert model.notes == None


@pytest.mark.parametrize(
    "dateTime", [util.Date(2000, 4, 21), QDateTime()], ids=["dated", "undated"]
)
def test_notes_field_has_start_datetime(scene, ep, dateTime):
    personA, personB = scene.addItems(Person(name="personA"), Person(name="personB"))
    event = scene.addItem(
        Event(
            kind=EventKind.Shift,
            person=personA,
            relationship=RelationshipKind.Projection,
            relationshipTargets=personB,
            dateTime=dateTime,
        )
    )
    emotion = scene.emotionsFor(event)[0]
    ep.show(emotion, tab="notes")
    notesEdit = ep.rootProp("notesEdit")
    notesHiddenHelpText = ep.rootProp("notesHiddenHelpText")
    if dateTime:
        assert notesEdit.property("visible") == False
        assert notesHiddenHelpText.property("visible") == True
    else:
        assert notesEdit.property("visible") == True
        assert notesHiddenHelpText.property("visible") == False
