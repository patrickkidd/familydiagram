from pkdiagram import util, Person, Event, Scene, EventPropertiesModel


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
