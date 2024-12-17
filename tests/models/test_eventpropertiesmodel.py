from pkdiagram import util
from pkdiagram.models import EventPropertiesModel
from pkdiagram.scene import Scene, Person, Event


def test_numWritable():
    scene = Scene()
    model = EventPropertiesModel()
    model.scene = scene
    assert model.numWritable == 0

    # writable
    parent = Person()
    event = Event(
        parent=parent, description="Something happened", dateTime=util.Date(2019, 5, 11)
    )
    model.items = [event]
    assert model.numWritable == 1

    # non-writable
    event2 = Event(
        parent=parent,
        description="Something happened",
        dateTime=util.Date(2019, 5, 11),
        uniqueId="blah",
    )
    model.items = [event2]
    assert model.numWritable == 0

    # just for good measure
    # writable
    model.items = [event]
    assert model.numWritable == 1

    # reset
    model.resetItems()
    assert model.numWritable == 0


def test_parentId():
    scene = Scene()
    personA = Person(name="A")
    personB = Person(name="B")
    event = Event(parent=personA)
    scene.addItems(personA, personB)
    model = EventPropertiesModel()
    model.scene = scene
    model.items = [event]
    assert model.parentId == personA.id

    model.parentId = personB.id
    assert model.parentId == personB.id
    assert event.parent == personB


def test_reset_color_multiple():
    scene = Scene()
    person = Person(name="A")
    scene.addItem(person)
    event_1 = Event(person, description="Something happened")
    event_2 = Event(person, description="Something happened again")
    model = EventPropertiesModel()
    model.scene = scene
    model.items = [event_1, event_2]
    assert model.color == None
    assert model.anyColor == False

    event_1.setColor("#FF0000")
    assert model.color == None
    assert model.anyColor == True

    model.reset("color")
    assert model.color == None
    assert model.anyColor == False
    assert event_1.color() == None
    assert event_2.color() == None
