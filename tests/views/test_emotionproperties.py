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


def test_show_init(scene, ep):

    COLOR = "#3c3c3c"
    INTENSITY = 2
    NOTES = "Here are some notes."

    personA, personB = Person(name="personA"), Person(name="personB")
    event = Event(
        kind=EventKind.Shift,
        person=personA,
        relationship=RelationshipKind.Projection,
        relationshipTargets=personB,
        relationshipIntensity=2,
    )
    emotion = event.emotions()[0]
    scene.addItems(personA, personB, event)

    #

    ep.show(emotion)
    assert ep.itemProp("emotionKindBox", "currentText") == Emotion.kindLabelForKind(
        RelationshipKind.Conflict.value
    )
    assert ep.itemProp(
        "intensityBox", "currentText"
    ) == util.emotionIntensityNameForIntensity(2)

    #

    intensityBox = ep.rootProp("intensityBox")
    ep.clickComboBoxItem(intensityBox, util.emotionIntensityNameForIntensity(INTENSITY))

    colorBox = ep.rootProp("colorBox")
    ep.clickComboBoxItem(colorBox, COLOR)

    emotionNotesEdit = ep.rootProp("emotionNotesEdit")
    ep.keyClicks(emotionNotesEdit, NOTES, resetFocus=False)

    #

    assert emotion.kind() == RelationshipKind.Conflict
    assert event.kind() == EventKind.Shift
    assert emotion.intensity() == INTENSITY
    assert emotion.notes().strip() == NOTES


def test_show_init_multiple_different(scene, ep):
    personA, personB = Person(name="personA"), Person(name="personB")

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
    assert model.intensity == event1.intensity()
    assert model.notes == event1.notes()

    ep.show([emotion1, emotion2])
    assert model.color == event1.color()
    assert model.intensity == event1.intensity()
    assert model.notes == event1.notes()

    event2.setColor("#00ff00")
    event2.setIntensity(3)
    event2.setNotes("Different notes")
    ep.show([emotion1, emotion2])
    assert model.color == None
    assert model.intensity == None
    assert model.notes == None


@pytest.mark.parametrize("dateTime", [util.Date(2000, 4, 21), QDateTime()])
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
    emotionNotesEdit = ep.rootProp("emotionNotesEdit")
    notesHiddenHelpText = ep.rootProp("notesHiddenHelpText")
    if dateTime:
        assert emotionNotesEdit.property("visible") == False
        assert notesHiddenHelpText.property("visible") == True
    else:
        assert emotionNotesEdit.property("visible") == True
        assert notesHiddenHelpText.property("visible") == False
