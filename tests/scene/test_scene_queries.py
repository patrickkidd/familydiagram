import os, os.path, pickle

import pytest

from pkdiagram.pyqt import Qt, QGraphicsView, QPointF, QRectF, QDateTime
from pkdiagram import util
from pkdiagram.scene import (
    Scene,
    Item,
    Person,
    Marriage,
    Emotion,
    Event,
    MultipleBirth,
    Layer,
    LifeChange,
)
from pkdiagram.models import SceneLayerModel

pytestmark = [
    pytest.mark.component("Scene"),
    pytest.mark.depends_on("Item"),
]


def test_query_not_all_kwargs():
    scene = Scene()
    scene.addItems(
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
        Person(name="John", lastName="Smith"),
    )
    assert scene.query(lastName="Doe", nickName="Donny") == []


def test_query_multiple():
    scene = Scene()
    scene.addItems(
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
        Person(name="John", lastName="Smith"),
    )
    person1, person2 = scene.query(lastName="Doe")
    assert person1.name() == "John"
    assert person2.name() == "Jane"


def test_query_methods():
    people = [
        Person(name="John", lastName="Doe"),
        Person(name="Jane", lastName="Doe"),
        Person(name="John", lastName="Smith"),
    ]
    scene = Scene()
    scene.addItems(*people)
    people = scene.query(methods={"fullNameOrAlias": "John Doe"})
    assert len(people) == 1
    assert people[0].fullNameOrAlias() == "John Doe"


def test_find_by_ids():
    person_1 = Person(name="John", lastName="Doe")
    person_2 = Person(name="Jane", lastName="Doe")
    person_3 = Person(name="John", lastName="Smith")
    scene = Scene()
    scene.addItems(person_1, person_2, person_3)

    items = scene.find(ids=[person_1.id, person_2.id])
    assert len(items) == 2
    assert set(items) == {person_1, person_2}

    items = scene.find(ids=[person_1.id, person_2.id, person_3.id])
    assert len(items) == 3
    assert set(items) == {person_1, person_2, person_3}


def test_find_by_types(simpleScene):
    """ """
    people = simpleScene.find(types=Person)
    assert len(people) == 3

    people = simpleScene.find(types=[Person])
    assert len(people) == 3

    pairBonds = simpleScene.find(types=[Marriage])
    assert len(pairBonds) == 1


def test_find_by_tags(simpleScene):
    p1 = simpleScene.query1(name="p1")
    p = simpleScene.query1(name="p")
    p1.setTags(["hello"])
    p.setTags(["hello"])
    p1.birthEvent.setTags(["hello"])

    items = simpleScene.find(tags="hello")
    assert len(items) == 3

    items = simpleScene.find(tags=["hello"])
    assert len(items) == 3


def test_find_by_types_and_tags(simpleScene):
    p1 = simpleScene.query1(name="p1")
    p2 = simpleScene.query1(name="p2")
    p = simpleScene.query1(name="p")
    p1.setTags(["hello"])
    p.setTags(["hello"])
    p1.birthEvent.setTags(["hello"])

    items = simpleScene.find(tags="hello", types=Event)
    assert len(items) == 1

    items = simpleScene.find(tags=["hello"], types=Person)
    assert len(items) == 2
