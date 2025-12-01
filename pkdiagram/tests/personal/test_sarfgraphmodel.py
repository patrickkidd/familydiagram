import pytest
from btcopilot.schema import EventKind, VariableShift
from pkdiagram.pyqt import QDateTime, QDate
from pkdiagram.scene import Scene, Person, Event
from pkdiagram.personal.sarfgraphmodel import SARFGraphModel


def test_sarfgraphmodel_empty(scene):
    model = SARFGraphModel()
    model.scene = scene
    assert model.hasData == False
    assert model.events == []
    assert model.cumulative == []


def test_sarfgraphmodel_with_events(scene):
    person = Person()
    scene.addItem(person)
    person.setName("Test Person")

    dt = QDateTime(QDate(1990, 5, 15))
    event = Event(kind=EventKind.Shift, person=person, dateTime=dt)
    event.setSymptom(VariableShift.Up)
    scene.addItem(event)

    model = SARFGraphModel()
    model.scene = scene

    assert model.hasData == True
    assert len(model.events) == 1
    assert model.events[0]["year"] == 1990
    assert model.events[0]["symptom"] == "up"
    assert model.cumulative[0]["symptom"] == 1


def test_sarfgraphmodel_cumulative_calculation(scene):
    person = Person()
    scene.addItem(person)
    person.setName("Test Person")

    dt1 = QDateTime(QDate(1990, 5, 15))
    event1 = Event(kind=EventKind.Shift, person=person, dateTime=dt1)
    event1.setSymptom(VariableShift.Up)
    scene.addItem(event1)

    dt2 = QDateTime(QDate(1995, 7, 20))
    event2 = Event(kind=EventKind.Shift, person=person, dateTime=dt2)
    event2.setSymptom(VariableShift.Down)
    scene.addItem(event2)

    model = SARFGraphModel()
    model.scene = scene

    assert len(model.cumulative) == 2
    assert model.cumulative[0]["symptom"] == 1
    assert model.cumulative[1]["symptom"] == 0


def test_sarfgraphmodel_year_range(scene):
    person = Person()
    scene.addItem(person)
    person.setName("Test Person")

    dt1 = QDateTime(QDate(1950, 1, 1))
    event1 = Event(kind=EventKind.Shift, person=person, dateTime=dt1)
    event1.setAnxiety(VariableShift.Up)
    scene.addItem(event1)

    dt2 = QDateTime(QDate(2000, 12, 31))
    event2 = Event(kind=EventKind.Shift, person=person, dateTime=dt2)
    event2.setAnxiety(VariableShift.Down)
    scene.addItem(event2)

    model = SARFGraphModel()
    model.scene = scene

    assert model.yearStart < 1950
    assert model.yearEnd > 2000


def test_sarfgraphmodel_is_life_event():
    model = SARFGraphModel()
    assert model.isLifeEvent("birth") == True
    assert model.isLifeEvent("married") == True
    assert model.isLifeEvent("shift") == False
    assert model.isLifeEvent("death") == False
