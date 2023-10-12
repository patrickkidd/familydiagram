import pytest
from pkdiagram import util, objects
from pkdiagram.addemotiondialog import AddEmotionDialog
from test_emotionproperties import emotionProps, runEmotionProperties, assertEmotionProperties

@pytest.fixture
def ep(qmlScene, qtbot):
    dlg = AddEmotionDialog()
    dlg.resize(600, 800)
    dlg.setRootProp('sceneModel', qmlScene._sceneModel)
    dlg.setScene(qmlScene)
    dlg.show()
    qtbot.addWidget(dlg)
    qtbot.waitActive(dlg)
    assert dlg.isShown()
    assert dlg.itemProp('emotion_doneButton', 'text') == 'Add'

    yield dlg
    
    dlg.setScene(None)
    dlg.hide()


def test_add_emotion_to_person(ep, emotionProps):
    scene = ep.rootProp('emotionModel').scene

    personA = objects.Person(name='Harold')
    scene.addItem(personA)

    personB = objects.Person(name='Maude')
    scene.addItem(personB)
    
    emotionAdded = util.Condition()
    scene.emotionAdded.connect(emotionAdded)
    assert ep.itemProp('personABox', 'currentIndex') == -1
    assert ep.itemProp('personABox', 'currentText') == ''
    assert ep.itemProp('personBBox', 'currentIndex') == -1
    assert ep.itemProp('personBBox', 'currentText') == ''
    assert ep.itemProp('stack', 'enabled') == True
    runEmotionProperties(emotionProps, ep,
                         personAName=personA.name(), personBName=personB.name())
    assert emotionAdded.callCount == 1
    
    emotion = emotionAdded.callArgs[0][0]
    assertEmotionProperties(emotion, emotionProps,
                            personAName=personA.name(), personBName=personB.name())


def test_complaints(ep, qtbot):
    qtbot.clickOkAfter(
        lambda: ep.mouseClick('emotion_doneButton'),
        text='You must choose the kind of relationship you want to add.'
    )

    ep.clickComboBoxItem('emotionKindBox', objects.Emotion.kindLabelForKind(util.ITEM_CONFLICT))
    qtbot.clickOkAfter(
        lambda: ep.mouseClick('emotion_doneButton'),
        text='You must set both people to add a dyadic relationship.'
    )

    scene = ep.rootProp('emotionModel').scene
    personA = objects.Person(name='Harold')
    personB = objects.Person(name='Maude')
    scene.addItems(personA, personB)
    ep.clickComboBoxItem('personABox', personA.name())
    qtbot.clickOkAfter(
        lambda: ep.mouseClick('emotion_doneButton'),
        text='You must set both people to add a dyadic relationship.'
    )

    ep.clickComboBoxItem('personBBox', personB.name())
    ep.mouseClick('emotion_doneButton')
    assert scene.emotions()[0].personA() is personA
    assert scene.emotions()[0].personB() is personB
    assert scene.emotions()[0].kind() is util.ITEM_CONFLICT
