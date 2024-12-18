import pytest

from pkdiagram import util, slugify
from pkdiagram.scene import Scene, Person, VariablesDatabase, Event


VAR_1 = "Var 1"
VAR_2 = "Var 2"
ATTR_0 = slugify(VAR_1)
ATTR_1 = slugify(VAR_2)


@pytest.fixture
def mock():
    d0 = util.Date(2000, 1, 1)
    d1 = util.Date(2000, 1, 2)
    d2 = util.Date(2000, 1, 3)
    d3 = util.Date(2000, 1, 4)
    data = (
        (ATTR_0, d0, "one"),  # event0
        (ATTR_1, d0, "two"),  # event0
        (ATTR_0, d1, None),  # event1, defer
        (ATTR_1, d1, "three"),  # event1
        # ATTR_0, d2, defer
        # ATTR_1, d2, defer
        (ATTR_0, d3, "four"),  # event2
        (ATTR_1, d3, None),  # event2, defer
    )
    return data, (d0, d1, d2, d3)


def assert_mock(db, _mock):
    data, (d0, d1, d2, d3) = _mock
    d00 = d0.addDays(-1)
    assert db.get(ATTR_0, d00) == (None, False)
    assert db.get(ATTR_1, d00) == (None, False)
    assert db.get(ATTR_0, d0) == (data[0][2], True)
    assert db.get(ATTR_1, d0) == (data[1][2], True)
    assert db.get(ATTR_0, d1) == (data[0][2], False)  # defer
    assert db.get(ATTR_1, d1) == (data[3][2], True)
    assert db.get(ATTR_0, d2) == (data[0][2], False)  # defer
    assert db.get(ATTR_1, d2) == (data[3][2], False)  # defer
    assert db.get(ATTR_0, d3) == (data[4][2], True)
    assert db.get(ATTR_1, d3) == (data[3][2], False)  # defer


def test_set_get(mock):
    data, dates = mock

    db = VariablesDatabase()
    for attr, date, value in data:
        if value is not None:
            db.set(attr, date, value)

    assert_mock(db, mock)


def test_person_init(mock):
    data, (d0, d1, d2, d3) = mock

    scene = Scene()
    scene.replaceEventProperties([VAR_1, VAR_2])
    person = Person()
    scene.addItem(person)

    event0 = Event(parent=person, dateTime=d0)
    event1 = Event(parent=person, dateTime=d1)
    event2 = Event(parent=person, dateTime=d3)

    for attr, dateTime, value in data:
        if value is not None:
            event = next(x for x in person.events() if x.dateTime() == dateTime)
            event.dynamicProperty(attr).set(value)

    assert_mock(person.variablesDatabase, mock)
