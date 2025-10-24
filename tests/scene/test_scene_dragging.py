import pytest


from btcopilot.schema import RelationshipKind, EventKind
from pkdiagram.pyqt import QPointF
from pkdiagram import util
from pkdiagram.scene import Scene, Person, Marriage, Emotion


def test_emotion_drags_with_person(scene):
    personA, personB = scene.addItems(Person(), Person())
    personA.setPos(QPointF(0, 0))
    personB.setPos(QPointF(100, 0))
    emotion = scene.addItem(
        Emotion(
            RelationshipKind.Conflict,
            personB,
            person=personA,
        )
    )
    initial_emotion_pos = emotion.scenePos()

    personA.setPos(QPointF(50, 50))

    new_emotion_pos = emotion.scenePos()
    assert new_emotion_pos != initial_emotion_pos
    assert new_emotion_pos.y() > initial_emotion_pos.y()
    assert new_emotion_pos.x() > initial_emotion_pos.x()


def test_marriage_drags_with_person(scene):
    personA, personB = scene.addItems(Person(), Person())
    personA.setPos(QPointF(0, 0))
    personB.setPos(QPointF(100, 0))

    marriage = scene.addItem(Marriage(personA=personA, personB=personB))

    initial_marriage_pos = marriage.scenePos()

    personA.setPos(QPointF(50, 50))

    marriage.updateGeometry()
    new_marriage_pos = marriage.scenePos()

    assert new_marriage_pos != initial_marriage_pos


def test_childof_drags_with_person(scene):
    parentA, parentB, child = scene.addItems(Person(), Person(), Person())
    parentA.setPos(QPointF(0, 0))
    parentB.setPos(QPointF(100, 0))
    child.setPos(QPointF(50, 100))

    marriage = scene.addItem(Marriage(personA=parentA, personB=parentB))
    child.setParents(marriage)

    assert child.childOf is not None
    assert child.childOf.parentItem() == child

    initial_childof_scene_pos = child.childOf.scenePos()

    child.setPos(QPointF(100, 150))

    new_childof_scene_pos = child.childOf.scenePos()

    assert new_childof_scene_pos != initial_childof_scene_pos
    assert new_childof_scene_pos.x() > initial_childof_scene_pos.x()
    assert new_childof_scene_pos.y() > initial_childof_scene_pos.y()
