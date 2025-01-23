import pytest

from pkdiagram.pyqt import QPointF, QDateTime
from pkdiagram import util
from pkdiagram.scene import (
    Scene,
    Person,
    Marriage,
    MultipleBirth,
    Layer,
    Person,
    Event,
)


def test_init():
    person = Person(name="personA")
    assert person.birthEvent not in person.events()


def test_write_read():
    chunk = {}
    person1 = Person(name="personA", lastName="bleh")
    person1.write(chunk)
    person2 = Person()
    person2.read(chunk, lambda id: None)
    assert person1.name() == person2.name()
    assert person1.lastName() == person2.lastName()


def test_childItem_parent():
    personA = Person()
    personB = Person()
    marriage = Marriage(personA=personA, personB=personB)
    childA = Person()
    childA.setParents(marriage)
    scene = Scene()
    scene.addItems(personA, personB, marriage, childA)
    for person in (personA, personB, childA):
        if person.parents() is None:
            assert person.childOf == None
        else:
            assert person.childOf != None
            assert person.childOf.parentItem() is not None


def test_Cutoff_parent():
    """Cutoff.parentItem() was being reset by Scene.addItem if it was listed
    before it's Person. Fixed by adding Cutoff.setParent() in Person.updateAll().
    """
    data = {
        "items": [
            # put the cutoff first so that addItem() clears the parentItem added.
            {"id": 2, "kind": "Cutoff", "person_a": 1, "notes": ""},
            {"id": 1, "kind": "Person", "notes": ""},
        ]
    }
    scene = Scene()
    assert scene.read(data) == None

    person = scene.find(1)
    cutoff = scene.find(2)
    assert cutoff in person.emotions()
    assert cutoff.scene() is scene
    assert person.scene() is scene
    assert cutoff.parentItem() is person


def test_multiple_births(simpleScene):
    scene = simpleScene
    parentA = scene.query1(name="p1")
    parentB = scene.query1(name="p2")
    marriage = parentA.marriages[0]

    childA = Person()
    childB = Person()
    childC = Person()
    mb = MultipleBirth(marriage)
    childA.setParents(mb)
    childB.setParents(mb)
    childC.setParents(mb)

    assert childA.childOf.multipleBirth is not None
    assert childB.childOf.multipleBirth is not None
    assert childC.childOf.multipleBirth is not None
    assert childA.childOf.multipleBirth.children() == [childA, childB, childC]
    assert childB.childOf.multipleBirth.children() == [childA, childB, childC]
    assert childC.childOf.multipleBirth.children() == [childA, childB, childC]


def test_detailsText_visible_at_pos():
    scene = Scene()
    person = Person()
    # test that ItemDetails is initialized to initial pos
    assert person.detailsText.pos() == person.initialDetailsPos()
    scene.addItem(person)
    # test that ItemDetails itemPos is set and pos doesn't change afte radd.
    assert person.detailsText.pos() == person.initialDetailsPos()

    # test that showing doesn't change pos
    person.setDiagramNotes("here are some notes")
    assert person.detailsText.isVisible() == True
    assert person.detailsText.pos() == person.initialDetailsPos()


@pytest.fixture
def detailsText_person(scene):
    scene.addEventProperty("varX")
    scene.setCurrentDateTime(util.Date(2001, 1, 1))
    person = Person(name="Roger")
    scene.addItem(person)
    person.setDiagramNotes("here are some notes")
    person.setBirthDateTime(util.Date(2001, 1, 1))
    event = Event(person, dateTime=scene.currentDateTime())
    scene.addItem(event)
    event.dynamicProperty("varx").set("123")
    scene.addItem(event)
    person.updateDetails()
    return person


def test_detailsText_all(detailsText_person):
    person = detailsText_person
    assert person.detailsText.isVisible() == True
    assert person.name() in person.detailsText.text()
    assert util.dateString(person.birthDateTime()) in person.detailsText.text()
    assert person.diagramNotes() in person.detailsText.text()
    assert "varX" in person.detailsText.text()


def test_detailsText_none(detailsText_person):
    person = detailsText_person
    person.setHideDetails(True)
    person.setHideDates(True)
    person.setHideVariables(True)
    assert person.detailsText.isVisible() == False
    assert person.detailsText.isEmpty() == True


def test_detailsText_hideDetails(detailsText_person):
    person = detailsText_person
    person.setHideDetails(True)
    assert person.detailsText.isVisible() == True
    assert person.name() not in person.detailsText.text()
    assert util.dateString(person.birthDateTime()) in person.detailsText.text()
    assert person.diagramNotes() not in person.detailsText.text()
    assert "varX" in person.detailsText.text()


def test_detailsText_hideDates(detailsText_person):
    person = detailsText_person
    person.setHideDates(True)
    assert person.detailsText.isVisible() == True
    assert person.name() in person.detailsText.text()
    assert util.dateString(person.birthDateTime()) not in person.detailsText.text()
    assert person.diagramNotes() in person.detailsText.text()
    assert "varX" in person.detailsText.text()


def test_detailsText_hideVariables(detailsText_person):
    person = detailsText_person
    person.setHideVariables(True)
    assert person.detailsText.isVisible() == True
    assert person.name() in person.detailsText.text()
    assert util.dateString(person.birthDateTime()) in person.detailsText.text()
    assert person.diagramNotes() in person.detailsText.text()
    assert "varX" not in person.detailsText.text()


def test_hide_age_when_no_deceased_date():
    person = Person()
    scene = Scene()
    scene.addItem(person)
    scene.setCurrentDateTime(QDateTime.currentDateTime())
    person.setBirthDateTime(util.Date(1990, 1, 1))
    person.setDeceased(True)
    assert person.ageItem.text() == ""
    assert person.ageItem.isVisible() == False

    person.setDeceasedDateTime(util.Date(2000, 1, 1))
    assert person.ageItem.text() == "10"
    assert person.ageItem.isVisible() == True


def test_updateAll_layer_props_init():
    """itemOpacity was not set directly in Person.updateAll()."""
    data = {
        "items": [
            {"id": 1, "kind": "Person", "size": 5, "layers": [2]},
            {
                "id": 2,
                "kind": "Layer",
                "active": True,
                "itemProperties": {
                    1: {"itemOpacity": 0.1, "color": "#f0f0f0", "size": 3}
                },
            },
        ]
    }
    scene = Scene()
    assert scene.read(data) == None

    person = scene.find(1)
    layer = scene.find(2)
    assert person.opacity() == 0.1
    assert person.opacity() == person.itemOpacity()
    assert person.size() == 3
    assert person.color() == "#f0f0f0"

    layer.setActive(False)
    assert person.opacity() == 1.0
    assert person.size() == 5
    assert person.color() == None


def test_layered_properties():
    """Ensure correct layered prop updates for marriage+marriage-indicators."""
    scene = Scene()
    person = Person()
    person.setPos(QPointF(-100, -50))
    layer = Layer(name="View 1", storeGeometry=True)
    scene.addItems(person, layer)
    #
    unlayered = {
        "itemPos": person.pos(),
        "color": None,
        "itemOpacity": None,
        "size": util.DEFAULT_PERSON_SIZE,
    }
    layered = {
        "itemPos": QPointF(-200, -150),
        "color": "#ff0000",
        "itemOpacity": 0.3,
        "size": 2,
    }
    for k, v in unlayered.items():
        person.prop(k).set(v)
    for k, v in layered.items():
        layer.setItemProperty(person.id, k, v)
    for k, v in unlayered.items():
        assert person.prop(k).get() == v
    assert person.size() == util.DEFAULT_PERSON_SIZE
    assert person.scale() == util.scaleForPersonSize(util.DEFAULT_PERSON_SIZE)

    layer.setActive(True)
    for k, v in layered.items():
        assert person.prop(k).get() == v
    assert person.size() == person.size()
    assert person.scale() == util.scaleForPersonSize(person.size())

    layer.setActive(False)
    for k, v in unlayered.items():
        assert person.prop(k).get() == v
    assert person.size() == util.DEFAULT_PERSON_SIZE
    assert person.scale() == util.scaleForPersonSize(util.DEFAULT_PERSON_SIZE)

    # scale wasn't updating when setting property outside of setting active layers
    layer.setActive(True)
    assert person.size() == person.size()
    assert person.scale() == util.scaleForPersonSize(person.size())

    # ...now set prop directly...
    person.setSize(3)
    assert person.size() == person.size()
    assert person.scale() == util.scaleForPersonSize(person.size())

    # ...and then make sure it goes back to normal again.
    layer.setActive(False)
    for k, v in unlayered.items():
        assert person.prop(k).get() == v
    assert person.size() == util.DEFAULT_PERSON_SIZE
    assert person.scale() == util.scaleForPersonSize(util.DEFAULT_PERSON_SIZE)


def test_shouldShowFor():
    scene = Scene()
    person = Person(name="A")
    layer = Layer(name="View 1")
    scene.addItems(person, layer)

    assert person.shouldShowFor(QDateTime(), [], []) == True

    assert person.shouldShowFor(QDateTime(), [], [layer]) == False

    person.setLayers([layer.id])
    assert person.shouldShowFor(QDateTime(), [], [layer]) == True

    person.setLayers([])
    assert person.shouldShowFor(QDateTime(), [], [layer]) == False


def test_person_setLayers():
    scene = Scene()
    layer1 = Layer()
    layer2 = Layer()
    person = Person()
    scene.addItems(layer1, layer2, person)
    person.setLayers([layer1.id, layer2.id])
    assert set(person.layers()) == set([layer1.id, layer2.id])

    person.setLayers([layer1.id])
    assert set(person.layers()) == set([layer1.id])


def test_new_event_adds_variable_values(scene):
    scene.addEventProperty("var1")

    person = Person()
    scene.addItems(person)

    # Simulate AddEventDialog setup.
    event = Event(parent=person, dateTime=util.Date(2021, 5, 11))
    for entry in scene.eventProperties():
        event.addDynamicProperty(entry["attr"])
    prop = event.dynamicProperties[0]
    prop.set("123")
    scene.addItem(event)

    assert person.variablesDatabase.get("var1", event.dateTime().addYears(-1)) == (
        None,
        False,
    )
    assert person.variablesDatabase.get("var1", event.dateTime()) == ("123", True)
    assert person.variablesDatabase.get("var1", event.dateTime().addYears(1)) == (
        "123",
        False,
    )


KINDS = ["male", "female"]
BUILTIN_VARS = {
    "anxiety": (util.VAR_ANXIETY_DOWN, util.VAR_ANXIETY_SAME, util.VAR_ANXIETY_UP),
    "functioning": (
        util.VAR_FUNCTIONING_DOWN,
        util.VAR_FUNCTIONING_SAME,
        util.VAR_FUNCTIONING_UP,
    ),
    "symptom": (util.VAR_SYMPTOM_DOWN, util.VAR_SYMPTOM_SAME, util.VAR_SYMPTOM_UP),
}


@pytest.mark.parametrize(
    "kind, attr, value",
    [
        (kind, var, value)
        for kind in ["male", "female"]
        for var, values in BUILTIN_VARS.items()
        for value in values
    ],
)
def test_draw_builtin_vars(kind, attr, value):
    DATE = util.Date(2021, 5, 11)
    scene = Scene()
    scene.addEventProperty(attr)
    scene.setCurrentDateTime(DATE)

    person = Person(kind=kind)
    scene.addItems(person)

    event = Event(parent=person, dateTime=DATE)
    event.addDynamicProperty(attr)
    event.dynamicProperties[0].set(value)
    person.updateGeometry()

    # Failure state is exception
