import pytest

from pkdiagram.pyqt import Qt, QDateTime
from pkdiagram import util
from pkdiagram.scene import Person, Emotion, person
from pkdiagram.views import QmlDrawer


@pytest.fixture
def emotionProps():
    """Could even rotate these just for fun."""
    return {
        "kind": util.ITEM_PROJECTION,
        "startDateTime": util.Date(2000, 4, 21),
        "endDateTime": util.Date(2001, 3, 20),
        # 'startDateUnsure': True,
        # 'endDateUnsure': False,
        "intensity": 2,
        "color": "#3c3c3c",
        "notes": "Here are some notes.",
    }


# @pytest.fixture
# def emotion(emotionProps):
#     emotion = scene.Emotion()
#     for key, value in emotionProps.items():
#         emotion.prop(key).set(value)
#     return emotion


def runEmotionProperties(props, ep, personAName=None, personBName=None, updates={}):

    props = dict(props)
    props.update(updates)

    ep.clickComboBoxItem("emotionKindBox", Emotion.kindLabelForKind(props["kind"]))
    if personAName:
        ep.clickComboBoxItem("personABox", personAName)
        assert ep.itemProp("personABox", "currentText") == personAName
    if personBName:
        ep.clickComboBoxItem("personBBox", personBName)
        assert ep.itemProp("personBBox", "currentText") == personBName
    ep.keyClicks(
        "startDateButtons.dateTextInput",
        util.dateString(props["startDateTime"]),
        resetFocus=False,
    )
    # if props['startDateUnsure'] != ep.itemProp('startDateButtons', 'unsure'):
    #     ep.keyClick('startDateButtons.unsureBox', Qt.Key_Space, resetFocus=False)
    ep.keyClicks(
        "endDateButtons.dateTextInput",
        util.dateString(props["endDateTime"]),
        resetFocus=False,
    )
    # if props['endDateUnsure'] != ep.itemProp('endDateButtons', 'unsure'):
    #     ep.keyClick('endDateButtons.unsureBox', Qt.Key_Space, resetFocus=False)
    ep.clickComboBoxItem(
        "intensityBox", util.emotionIntensityNameForIntensity(props["intensity"])
    )
    ep.clickComboBoxItem("colorBox", props["color"])
    ep.clickTabBarButton("tabBar", 1)
    ep.keyClicks("emotionNotesEdit", props["notes"])
    ep.mouseClick("emotion_doneButton", Qt.LeftButton)


def assertEmotionProperties(
    emotion, props, updates={}, personAName=None, personBName=None
):
    assert emotion.kind() == props["kind"]
    if personAName:
        assert emotion.personA().name() == personAName
    if personBName:
        assert emotion.personB().name() == personBName
    assert emotion.startDateTime() == props["startDateTime"]
    assert emotion.endDateTime() == props["endDateTime"]
    assert emotion.intensity() == props["intensity"]
    assert emotion.notes().strip() == props["notes"]
    assert emotion.kind() == props["kind"]


@pytest.fixture
def ep(qtbot, scene, qmlEngine):
    qmlEngine.setScene(scene)
    ep = QmlDrawer(
        qmlEngine, "qml/EmotionPropertiesDrawer.qml", propSheetModel="emotionModel"
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


def assertEmotionPropertiesInit(props, ep):
    # should be 'Projection'
    assert ep.itemProp("emotionKindBox", "currentText") == Emotion.kindLabelForKind(
        props["kind"]
    )
    # should be 'Medium'
    assert ep.itemProp(
        "intensityBox", "currentText"
    ) == util.emotionIntensityNameForIntensity(props["intensity"])


def test_show_init(scene, ep, emotionProps):
    personA, personB = Person(name="personA"), Person(name="personB")
    scene.addItems(personA, personB)
    initProps = {"kind": util.ITEM_PROJECTION, "intensity": 2}
    emotion = Emotion(personA=personA, personB=personB, **initProps)
    scene.addItem(emotion)
    ep.show(emotion)
    assertEmotionPropertiesInit(initProps, ep)

    runEmotionProperties(
        emotionProps, ep, personAName=personA.name(), personBName=personB.name()
    )
    assertEmotionProperties(
        emotion, emotionProps, personAName=personA.name(), personBName=personB.name()
    )


def test_fields_disabled(scene, ep):

    personA, personB = Person(name="Harold"), Person(name="Maude")
    scene.addItems(personA, personB)

    cutoff = Emotion(kind=util.ITEM_CUTOFF, personA=personA)
    scene.addItem(cutoff)

    projection = Emotion(kind=util.ITEM_PROJECTION, personA=personA, personB=personB)
    scene.addItem(projection)

    ep.emotionModel.items = [cutoff]
    assert ep.emotionModel.kind == util.ITEM_CUTOFF
    assert ep.itemProp("swapButton", "enabled") == False
    assert ep.itemProp("personBBox", "enabled") == False

    ep.emotionModel.items = [projection]
    assert ep.emotionModel.kind == util.ITEM_PROJECTION
    assert ep.itemProp("swapButton", "enabled") == True
    assert ep.itemProp("personBBox", "enabled") == True

    ep.emotionModel.items = [cutoff]
    assert ep.emotionModel.kind == util.ITEM_CUTOFF
    assert ep.itemProp("swapButton", "enabled") == False
    assert ep.itemProp("personBBox", "enabled") == False


def test_show_init_multiple_different(scene, ep):
    personA, personB = Person(name="personA"), Person(name="personB")
    emotion1 = Emotion(personA=personA, personB=personB, kind=util.ITEM_PROJECTION)
    emotion2 = Emotion(personA=personA, personB=personB, kind=util.ITEM_CONFLICT)
    scene.addItems(emotion1, emotion2)

    # first init with single kind
    ep.show(emotion1)
    assert ep.itemProp("emotionKindBox", "currentIndex") > -1

    # then re-init with different kinds
    ep.show([emotion1, emotion2])
    assert ep.itemProp("emotionKindBox", "currentIndex") == -1


@pytest.mark.parametrize("startDateTime", [util.Date(2000, 4, 21), QDateTime()])
def test_notes_field_has_start_datetime(scene, ep, startDateTime):
    personA, personB = Person(name="personA"), Person(name="personB")
    emotion = Emotion(personA=personA, personB=personB, kind=util.ITEM_PROJECTION)
    emotion.startEvent.setDateTime(startDateTime)
    scene.addItem(emotion)
    ep.show(emotion, tab="notes")
    emotionNotesEdit = ep.rootProp("emotionNotesEdit")
    notesHiddenHelpText = ep.rootProp("notesHiddenHelpText")
    if startDateTime:
        assert emotionNotesEdit.property("visible") == False
        assert notesHiddenHelpText.property("visible") == True
    else:
        assert emotionNotesEdit.property("visible") == True
        assert notesHiddenHelpText.property("visible") == False
