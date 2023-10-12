from pkdiagram.pyqt import QPointF
from pkdiagram import util, Scene, Person, Emotion, EmotionPropertiesModel



def test_init(simpleScene):
    scene = Scene()
    p1, p2 = Person(name='p1'), Person(name='p2')
    conflict = Emotion(kind=util.ITEM_CONFLICT, personA=p1, personB=p2)
    scene.addItems(p1, p2, conflict)
    model = EmotionPropertiesModel()
    model.scene = scene
    model.items = [conflict]
    assert model.startEventId == conflict.startEvent.id
    assert model.endEventId == conflict.endEvent.id


def test_swap_people(simpleScene):

    p1 = simpleScene.query1(name='p1')
    p2 = simpleScene.query1(name='p2')
    conflict = Emotion(kind=util.ITEM_CONFLICT, personA=p1, personB=p2)
    simpleScene.addItem(conflict)
    assert conflict in p1.emotions()
    assert conflict in p2.emotions()
    assert conflict.personA() is p1
    assert conflict.personB() is p2

    model = EmotionPropertiesModel()
    model.scene = simpleScene
    model.items = [conflict]
    assert model.personAId == p1.id
    assert model.personBId == p2.id
    
    model.personAId, model.personBId = model.personBId, model.personAId
    assert model.personAId == p2.id
    assert model.personBId == p1.id
